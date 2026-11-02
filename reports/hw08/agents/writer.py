import asyncio
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from common import (DRAFTS_TOPIC, KAFKA_BOOTSTRAP_SERVERS, TASKS_TOPIC, ask_llm, from_bytes, log, to_bytes)

SYSTEM_PROMPT = (
    "You are the Writer for an open source package vulnerability team."
    "Answer the question by following the plan. Keep the answer under 150 words."
)
async def main():
    consumer = AIOKafkaConsumer(
        TASKS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="s0932-writer-group",
        auto_offset_reset="earliest",
    )
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await consumer.start()
    await producer.start()
    log(f"WRITER Listening on {TASKS_TOPIC}...")

    try:
        async for msg in consumer:
            task = from_bytes(msg.value)
            correlation_id = task["correlation_id"]
            log(f"WRITER RECEIVE from {msg.topic} partition={msg.partition} offset={msg.offset} correlation_id={correlation_id}")

            prompt = f"Question: {task['question']}\n\nPlan:\n{task['plan']}"
            draft = await ask_llm(SYSTEM_PROMPT, prompt)
            draft_message = {
                "correlation_id": correlation_id,
                "question": task["question"],
                "plan": task["plan"],
                "draft": draft,
            }
            metadata = await producer.send_and_wait(DRAFTS_TOPIC, to_bytes(draft_message))
            log(f"WRITER SEND to {metadata.topic} partition={metadata.partition} offset={metadata.offset} correlation_id={correlation_id}")
            log(f"WRITER draft={draft}")
    finally:
        await consumer.stop()
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(main())
