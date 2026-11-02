import asyncio
import csv
import os
import sys
from datetime import datetime
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from common import (DEAD_LETTER_TOPIC, DRAFTS_TOPIC, KAFKA_BOOTSTRAP_SERVERS, RAW_DIR, TASKS_TOPIC, ask_llm, from_bytes, log, to_bytes)

SYSTEM_PROMPT = (
    "You are the Writer for an open source package vulnerability team. "
    "Answer the question by following the plan. Keep the answer under 150 words."
)

options = sys.argv[1:]
BEFORE_FIX = "--before" in options
SLOW = "--slow" in options
names = [option for option in options if not option.startswith("--")]
WRITER_NAME = names[0] if names else "A"
TAG = f"[WRITER-{WRITER_NAME}]"
MAX_RETRIES = 3
PROCESSED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "writer_processed_ids.txt")
ORDERING_FILE = os.path.join(RAW_DIR, f"ordering_runs_{WRITER_NAME}.csv")

def load_processed_ids():
    if not os.path.exists(PROCESSED_FILE):
        return set()
    with open(PROCESSED_FILE) as f:
        return set(line.strip() for line in f if line.strip())

def remember_processed_id(correlation_id, processed_ids):
    processed_ids.add(correlation_id)
    with open(PROCESSED_FILE, "a") as f:
        f.write(correlation_id + "\n")

def record_ordering(test, msg):
    os.makedirs(RAW_DIR, exist_ok=True)
    new_file = not os.path.exists(ORDERING_FILE)
    with open(ORDERING_FILE, "a", newline="") as f:
        csv_writer = csv.writer(f)
        if new_file:
            csv_writer.writerow(["run", "processed_at", "writer", "entity", "seq", "partition", "offset"])
        csv_writer.writerow([
            test["run"],
            datetime.now().isoformat(timespec="milliseconds"),
            WRITER_NAME,
            test["entity"],
            test["seq"],
            msg.partition,
            msg.offset,
        ])

async def send_to_dead_letter(producer, msg, error):
    dead_letter = {
        "source_topic": msg.topic,
        "partition": msg.partition,
        "offset": msg.offset,
        "original_message": msg.value.decode(errors="replace"),
        "error": repr(error),
        "attempts": MAX_RETRIES,
    }
    metadata = await producer.send_and_wait(DEAD_LETTER_TOPIC, to_bytes(dead_letter))
    log(f"{TAG} DEAD LETTER sent to {metadata.topic} partition={metadata.partition} offset={metadata.offset}")
    log(f"{TAG} DEAD LETTER message={dead_letter}")

async def handle_task(msg, producer, processed_ids):
    task = from_bytes(msg.value)  #if not json then fail
    correlation_id = task["correlation_id"]
    log(f"{TAG} correlation_id={correlation_id}")

    #idempotency check
    if not BEFORE_FIX and correlation_id in processed_ids:
        log(f"{TAG} DUPLICATE correlation_id={correlation_id} was already processed -> skipped, no new draft")
        return
    if "ordering_test" in task:
        test = task["ordering_test"]
        await asyncio.sleep(0.3)
        record_ordering(test, msg)
        log(f"{TAG} ORDER run={test['run']} entity={test['entity']} seq={test['seq']} partition={msg.partition} offset={msg.offset}")
        remember_processed_id(correlation_id, processed_ids)
        return
    if SLOW:
        log(f"{TAG} PROCESSING... waiting 15 seconds (press Ctrl+C now to kill the writer mid-processing)")
        await asyncio.sleep(15)

    prompt = f"Question: {task['question']}\n\nPlan:\n{task['plan']}"
    draft = await ask_llm(SYSTEM_PROMPT, prompt)
    draft_message = {
        "correlation_id": correlation_id,
        "question": task["question"],
        "plan": task["plan"],
        "draft": draft,
    }
    metadata = await producer.send_and_wait(DRAFTS_TOPIC, to_bytes(draft_message))
    log(f"{TAG} SEND to {metadata.topic} partition={metadata.partition} offset={metadata.offset} correlation_id={correlation_id}")
    log(f"{TAG} draft={draft}")
    remember_processed_id(correlation_id, processed_ids)


async def main():
    consumer = AIOKafkaConsumer(
        TASKS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="s0932-writer-group",
        auto_offset_reset="earliest",
        enable_auto_commit=BEFORE_FIX,
    )
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await consumer.start()
    await producer.start()
    processed_ids = load_processed_ids()
    if BEFORE_FIX:
        log(f"{TAG} Listening on {TASKS_TOPIC}... mode=BEFORE FIX (no idempotency, auto commit, no retries)")
    else:
        log(f"{TAG} Listening on {TASKS_TOPIC}... mode=AFTER FIX (idempotency, commit after success, {MAX_RETRIES} retries + dead letter)")
    try:
        async for msg in consumer:
            log(f"{TAG} RECEIVE from {msg.topic} partition={msg.partition} offset={msg.offset}")

            if BEFORE_FIX:
                #no retries so crash
                await handle_task(msg, producer, processed_ids)
                continue

            #retries then send to dead letter topic
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    await handle_task(msg, producer, processed_ids)
                    break
                except Exception as error:
                    log(f"{TAG} RETRY attempt {attempt}/{MAX_RETRIES} failed: {error!r}")
                    if attempt == MAX_RETRIES:
                        await send_to_dead_letter(producer, msg, error)
                    else:
                        await asyncio.sleep(1)
            await consumer.commit()
            log(f"{TAG} COMMIT partition={msg.partition} offset={msg.offset} (next offset to read: {msg.offset + 1})")
    finally:
        await consumer.stop()
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(main())