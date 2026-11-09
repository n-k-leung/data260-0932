import asyncio
import os
import sys
import time
import uuid
import numpy as np
import redis
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from redis.commands.search.query import Query
from sentence_transformers import SentenceTransformer
AGENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents")
sys.path.insert(0, AGENTS_DIR)
from common import FINAL_TOPIC, INBOX_TOPIC, KAFKA_BOOTSTRAP_SERVERS, from_bytes, log, to_bytes

PREFIX = "s0932"
INDEX_NAME = f"{PREFIX}:semantic_cache_idx"
KEY_PREFIX = f"{PREFIX}:semantic_cache:"
DATA_VERSION_KEY = f"{PREFIX}:data_version"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
THRESHOLD = 0.85
AGENT_TIMEOUT_SECONDS = 300

async def ask_agents(question):
    correlation_id = str(uuid.uuid4())
    consumer = AIOKafkaConsumer(FINAL_TOPIC, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS, auto_offset_reset="earliest")
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await consumer.start()
    await producer.start()

    try:
        await producer.send_and_wait(INBOX_TOPIC, to_bytes({"correlation_id": correlation_id, "question": question}))
        log(f"Sent the question to {INBOX_TOPIC} (correlation_id {correlation_id})")

        #skip older results
        async def wait_for_result():
            async for msg in consumer:
                result = from_bytes(msg.value)
                if result.get("correlation_id") == correlation_id:
                    return result

        result = await asyncio.wait_for(wait_for_result(), timeout=AGENT_TIMEOUT_SECONDS)
        log(f"Got the answer from {FINAL_TOPIC} (correlation_id {correlation_id}, status {result.get('status')})")
        return result
    finally:
        await consumer.stop()
        await producer.stop()


class SemanticResponseCache:
    def __init__(self, threshold=THRESHOLD):
        self.threshold = threshold
        self.redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
        self.redis_client.ping()
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self._create_index()

    def _create_index(self):
        try:
            self.redis_client.ft(INDEX_NAME).info()
        except redis.ResponseError:
            self.redis_client.execute_command(
                "FT.CREATE", INDEX_NAME, "ON", "HASH", "PREFIX", "1", KEY_PREFIX,
                "SCHEMA",
                "query", "TEXT",
                "answer", "TEXT",
                "data_version", "TAG",
                "embedding", "VECTOR", "FLAT", "6",
                "TYPE", "FLOAT32", "DIM", EMBEDDING_DIM, "DISTANCE_METRIC", "COSINE",
            )
            log(f"Created vector index {INDEX_NAME}")

    def embed(self, text):
        return self.model.encode(text).astype(np.float32).tobytes()

    def get_data_version(self):
        self.redis_client.setnx(DATA_VERSION_KEY, 1)
        return self.redis_client.get(DATA_VERSION_KEY)

    def find_most_similar(self, embedding):
        query = (
            Query("*=>[KNN 1 @embedding $vec AS distance]")
            .sort_by("distance")
            .return_fields("query", "answer", "data_version", "distance")
            .dialect(2)
        )
        results = self.redis_client.ft(INDEX_NAME).search(query, query_params={"vec": embedding})
        if not results.docs:
            return None, 0.0
        best = results.docs[0]
        similarity = 1 - float(best.distance)
        return best, similarity

    def store(self, question, embedding, answer):
        key = KEY_PREFIX + str(uuid.uuid4())
        self.redis_client.hset(key, mapping={
            "query": question,
            "embedding": embedding,
            "answer": answer,
            "data_version": self.get_data_version(),
            "created_at": time.time(),
        })
        return key

    def handle_query(self, question):
        log(f"Start: {question}")
        start = time.perf_counter()
        embedding = self.embed(question)
        best, similarity = self.find_most_similar(embedding)

        if best is not None and similarity >= self.threshold:
            latency_ms = (time.perf_counter() - start) * 1000
            log(f"Cache hit, similarity {similarity:.3f}, matched: {best.query}")
            log(f"End: {latency_ms:.1f} ms")
            return {
                "question": question,
                "answer": best.answer,
                "is_cached": True,
                "similarity": round(similarity, 3),
                "cached_query": best.query,
                "data_version": best.data_version,
                "latency_ms": round(latency_ms, 1),
            }
        log(f"Cache miss, best similarity {similarity:.3f}, asking the agents")
        result = asyncio.run(ask_agents(question))
        answer = result["answer"]
        self.store(question, embedding, answer)

        latency_ms = (time.perf_counter() - start) * 1000
        log(f"End: {latency_ms:.1f} ms")
        return {
            "question": question,
            "answer": answer,
            "is_cached": False,
            "similarity": round(similarity, 3),
            "cached_query": None,
            "data_version": self.get_data_version(),
            "latency_ms": round(latency_ms, 1),
        }

    def clear(self):
        try:
            self.redis_client.ft(INDEX_NAME).dropindex(delete_documents=True)
        except redis.ResponseError:
            pass
        self._create_index()