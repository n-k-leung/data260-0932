import asyncio
import os
import sys
import uuid
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from deepeval.metrics import GEval
from deepeval.metrics.g_eval import Rubric
from deepeval.models import OllamaModel
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "agents"))
from common import FINAL_TOPIC, INBOX_TOPIC, KAFKA_BOOTSTRAP_SERVERS, from_bytes, log, to_bytes
from tracing import kafka_time, now, write_span

RUBRIC = [
    Rubric(score_range=(1, 1), expected_outcome="Very poor"),
    Rubric(score_range=(2, 2), expected_outcome="Poor"),
    Rubric(score_range=(3, 3), expected_outcome="Average"),
    Rubric(score_range=(4, 4), expected_outcome="Good"),
    Rubric(score_range=(5, 5), expected_outcome="Excellent"),
]

def make_evaluator():
    judge = OllamaModel(model="qwen3:8b", base_url="http://localhost:11434", temperature=0, generation_kwargs={"seed": 932}, timeout=180)
    return GEval(
        name="Final Answer Helpfulness",
        evaluation_steps=[
            "Check that the answer directly answers the user's question",
            "Check that the facts (CVE, package, versions, severity) are accurate",
            "Check that the advice is useful and actionable for a software team",
            "Penalize missing key facts, wrong facts or unrelated content",
        ],
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        rubric=RUBRIC, model=judge, async_mode=False,
    )

async def wait_for_final(trace_id, question, timeout):
    consumer = AIOKafkaConsumer(FINAL_TOPIC, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS, auto_offset_reset="earliest")
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await consumer.start()
    await producer.start()
    async def read_final():
        async for msg in consumer:
            try:
                message = from_bytes(msg.value)
            except Exception:
                continue
            if message.get("correlation_id") == trace_id:
                return msg, message

    try:
        await producer.send_and_wait(INBOX_TOPIC, to_bytes({"correlation_id": trace_id, "question": question}))
        waiting_since = now()
        try:
            msg, message = await asyncio.wait_for(read_final(), timeout=timeout)
        except asyncio.TimeoutError:
            error = f"TimeoutError: no answer on {FINAL_TOPIC} after {timeout} s (an agent did not finish)"
            write_span("client", trace_id, "final", waiting_since, now(), status="error", error=error)
            return None
        write_span("client", trace_id, "final", kafka_time(msg), now())
        return message
    finally:
        await consumer.stop()
        await producer.stop()


def run_request(question, cache, evaluator=None, store_answer=True, timeout=300):
    trace_id = str(uuid.uuid4())
    log(f"trace_id {trace_id}: {question}")

    #cache_lookup span
    start = now()
    embedding = cache.embed(question)
    best, similarity = cache.find_most_similar(embedding)
    hit = best is not None and similarity >= cache.threshold
    write_span("client", trace_id, "cache_lookup", start, now(),
               cache="hit" if hit else "miss", similarity=round(similarity, 3))
    if hit:
        log(f"Cache hit (similarity {similarity:.3f})")
        return {"trace_id": trace_id, "cache": "hit", "answer": best.answer, "status": "ok"}
    log(f"Cache miss (best similarity {similarity:.3f}), asking the agents")

    #inbox -> planner -> tasks -> writer -> drafts -> reviewer -> final
    final = asyncio.run(wait_for_final(trace_id, question, timeout))
    if final is None:
        log("Failed: no final answer")
        return {"trace_id": trace_id, "cache": "miss", "answer": None, "status": "error"}
    answer = final["answer"]
    if store_answer:
        cache.store(question, embedding, answer)

    #evaluator span
    if evaluator is not None:
        start = now()
        try:
            evaluator.measure(LLMTestCase(input=question, actual_output=answer))
            write_span("client", trace_id, "evaluator", start, now(), score=round(1 + 4 * evaluator.score, 2))
        except Exception as error:
            write_span("client", trace_id, "evaluator", start, now(), status="error", error=repr(error))

    log("Done")
    return {"trace_id": trace_id, "cache": "miss", "answer": answer, "status": "ok"}
