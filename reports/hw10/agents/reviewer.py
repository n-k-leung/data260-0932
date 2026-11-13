"""Reviewer: reads a draft from s0932_drafts and sends the approved answer to s0932_final."""
import asyncio

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from common import (DRAFTS_TOPIC, FINAL_TOPIC, KAFKA_BOOTSTRAP_SERVERS, ask_llm,
                    from_bytes, log, to_bytes)

SYSTEM_PROMPT = (
    "You are the Reviewer for an open source package vulnerability team. "
    "Check that the draft answers the question correctly and clearly. "
    "Reply with APPROVED or NEEDS_CHANGES on the first line, then one sentence explaining why."
)


async def main():
    consumer = AIOKafkaConsumer(
        DRAFTS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="s0932-reviewer-group",
        auto_offset_reset="earliest",
    )
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await consumer.start()
    await producer.start()
    log(f"[REVIEWER] Listening on {DRAFTS_TOPIC}...")

    try:
        async for msg in consumer:
            draft_message = from_bytes(msg.value)
            correlation_id = draft_message["correlation_id"]
            log(f"[REVIEWER] RECEIVE from {msg.topic} partition={msg.partition} offset={msg.offset} correlation_id={correlation_id}")

            prompt = f"Question: {draft_message['question']}\n\nDraft:\n{draft_message['draft']}"
            review = await ask_llm(SYSTEM_PROMPT, prompt)

            # The first word of the review decides the status
            if review.upper().startswith("APPROVED"):
                status = "approved"
            else:
                status = "needs_changes"

            # Final JSON: same correlation_id, plus status and answer
            final_message = {
                "correlation_id": correlation_id,
                "status": status,
                "answer": draft_message["draft"],
                "review": review,
            }
            metadata = await producer.send_and_wait(FINAL_TOPIC, to_bytes(final_message))
            log(f"[REVIEWER] SEND to {metadata.topic} partition={metadata.partition} offset={metadata.offset} correlation_id={correlation_id}")
            log(f"[REVIEWER] status={status} review={review}")
    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
