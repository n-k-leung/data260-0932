import asyncio
import json
import sys
import uuid
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from common import FINAL_TOPIC, INBOX_TOPIC, KAFKA_BOOTSTRAP_SERVERS, from_bytes, log, to_bytes

DEFAULT_QUESTION = (
    "A Critical vulnerability (CVE202023337) was reported in the open source package "
    "pip 4.18.03. What should our team do about it?"
)

async def main():
    question = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUESTION
    correlation_id = str(uuid.uuid4())

    #reading s0932_final first so the answer is not ignored
    consumer = AIOKafkaConsumer(
        FINAL_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset="earliest",
    )
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await consumer.start()
    await producer.start()

    try:
        message = {"correlation_id": correlation_id, "question": question}
        metadata = await producer.send_and_wait(INBOX_TOPIC, to_bytes(message))
        log(f"YOU SEND to {metadata.topic} partition={metadata.partition} offset={metadata.offset} correlation_id={correlation_id}")
        log(f"YOU question={question}")
        log(f"YOU Waiting for the result on {FINAL_TOPIC}...")

        #skip older results until the one with the correlation_id shows up
        async for msg in consumer:
            result = from_bytes(msg.value)
            if result.get("correlation_id") == correlation_id:
                log(f"YOU RECEIVE from {msg.topic} partition={msg.partition} offset={msg.offset} correlation_id={correlation_id}")
                print("\nFinal JSON message:")
                print(json.dumps(result, indent=2))
                break
    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
