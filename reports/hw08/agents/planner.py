import asyncio
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from common import (INBOX_TOPIC, KAFKA_BOOTSTRAP_SERVERS, TASKS_TOPIC, ask_llm, from_bytes, log, to_bytes)

SYSTEM_PROMPT = (
    "You are the Planner for an open source package vulnerability team."
    "Break the user's question into 3 short numbered steps the Writer should cover."
    "Only return the steps."
)

async def main():
    consumer = AIOKafkaConsumer(
        INBOX_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="s0932-planner-group",
        auto_offset_reset="earliest",
    )
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await consumer.start()
    await producer.start()
    log(f"PLANNER Listening on {INBOX_TOPIC}...")
    try:
        async for msg in consumer:
            message = from_bytes(msg.value)
            correlation_id = message["correlation_id"]
            log(f"PLANNER RECEIVE from {msg.topic} partition={msg.partition} offset={msg.offset} correlation_id={correlation_id}")
            log(f"PLANNER question={message['question']}")
            plan = await ask_llm(SYSTEM_PROMPT, message["question"])
            task = {
                "correlation_id": correlation_id,
                "question": message["question"],
                "plan": plan,
            }
            metadata = await producer.send_and_wait(TASKS_TOPIC, to_bytes(task))
            log(f"PLANNER SEND to {metadata.topic} partition={metadata.partition} offset={metadata.offset} correlation_id={correlation_id}")
            log(f"PLANNER plan={plan}")
    finally:
        await consumer.stop()
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(main())
