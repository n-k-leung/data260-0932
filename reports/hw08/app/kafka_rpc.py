import asyncio
import json
import os
import uuid
from datetime import datetime
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
REQUEST_TOPIC = "s0932_vulnerability_requests"
RESPONSE_TOPIC = "s0932_vulnerability_responses"
TIMEOUT_SECONDS = 10

#to print times when action is done to make sure it is going in order cause sometimes id didnt for somereason
def log(text):
    print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} {text}", flush=True)


class KafkaRPC:
    def __init__(self):
        self.producer = None
        self.consumer = None
        self.pending = {}
        self.consumer_task = None

    #to create producer and consumer
    async def start(self):
        self.producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
        self.consumer = AIOKafkaConsumer(
            RESPONSE_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id="s0932-api-response-group",
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        await self.producer.start()
        await self.consumer.start()
        self.consumer_task = asyncio.create_task(self.consume_responses())
        log(f"[API] Listening for Kafka responses on topic: {RESPONSE_TOPIC}")

    #when FastAPI shuts down
    async def stop(self):
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass
        await self.consumer.stop()
        await self.producer.stop()

    async def consume_responses(self):
        async for msg in self.consumer:
            response = json.loads(msg.value.decode())
            correlation_id = response.get("correlation_id")

            log(f"[API] RECEIVE  from topic={msg.topic} partition={msg.partition} offset={msg.offset}")
            log(f"[API] RECEIVE  message={json.dumps(response)}")

            if correlation_id in self.pending:
                future = self.pending.pop(correlation_id)
                if not future.done():
                    future.set_result(response)
            else:
                log(f"[API] No pending request for correlation_id={correlation_id}")

    async def make_request(self, request):
        correlation_id = request.get("correlation_id") or str(uuid.uuid4())

        message = {
            "correlation_id": correlation_id,
            "reply_to": RESPONSE_TOPIC,
            "operation": request.get("operation"),
            "data": request.get("data", {}),
        }

        future = asyncio.get_running_loop().create_future()
        self.pending[correlation_id] = future

        metadata = await self.producer.send_and_wait(REQUEST_TOPIC, json.dumps(message).encode())
        log(f"API SEND to topic={metadata.topic} partition={metadata.partition} offset={metadata.offset}")
        log(f"API SEND message={json.dumps(message)}")
        try:
            response = await asyncio.wait_for(future, timeout=TIMEOUT_SECONDS)
            log(f"API RETURN response to caller for correlation_id={correlation_id}")
            return response
        except asyncio.TimeoutError:
            self.pending.pop(correlation_id, None)
            return {
                "correlation_id": correlation_id,
                "success": False,
                "error": "Timed out waiting for the worker response",
            }