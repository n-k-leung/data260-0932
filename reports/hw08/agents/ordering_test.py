import asyncio
import csv
import glob
import os
import random
import sys
from datetime import datetime
from aiokafka import AIOKafkaProducer
from common import KAFKA_BOOTSTRAP_SERVERS, RAW_DIR, TASKS_TOPIC, VERIFY_SEED, log, to_bytes

ORDERING_FILES = os.path.join(RAW_DIR, "ordering_runs_*.csv")
ENTITIES = ["lodash", "pip", "requests"]
NUM_MESSAGES = 20

def make_messages(run_id):
    rng = random.Random(VERIFY_SEED)
    seq_numbers = {entity: 0 for entity in ENTITIES}
    messages = []
    for i in range(1, NUM_MESSAGES + 1):
        entity = rng.choice(ENTITIES)
        seq_numbers[entity] += 1
        messages.append({
            "correlation_id": f"{run_id}-{i:02d}",
            "question": f"Update #{seq_numbers[entity]} for package {entity}",
            "plan": "ordering test",
            "ordering_test": {"run": run_id, "entity": entity, "seq": seq_numbers[entity]},
        })
    return messages

def read_results(run_id):
    rows = []
    for path in glob.glob(ORDERING_FILES):
        with open(path, newline="") as f:
            rows += [row for row in csv.DictReader(f) if row["run"] == run_id]
    rows.sort(key=lambda row: row["processed_at"])
    return rows

async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ["nokey", "key"]:
        print("Use: python ordering_test.py nokey or python ordering_test.py key")
        return

    #time is added so every run has new correlation_ids bc if not then idempotency would skip them
    run_id = f"{mode}-{datetime.now().strftime('%H%M%S')}"
    log(f"[TEST] run={run_id} VERIFY_SEED={VERIFY_SEED} messages={NUM_MESSAGES}")

    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    try:
        for message in make_messages(run_id):
            test = message["ordering_test"]
            # Run 2 uses the package name as the key, so one package always goes to one partition
            key = test["entity"].encode() if mode == "key" else None
            metadata = await producer.send_and_wait(TASKS_TOPIC, to_bytes(message), key=key)
            log(f"[TEST] SEND {message['correlation_id']} entity={test['entity']} seq={test['seq']} key={key} -> partition={metadata.partition}")
    finally:
        await producer.stop()

    #wait until the writers have processed all 20 messages
    log("[TEST] Waiting for the writers to process all messages...")
    rows = []
    for _ in range(60):
        rows = read_results(run_id)
        if len(rows) >= NUM_MESSAGES:
            break
        await asyncio.sleep(1)

    print(f"\nProcessing order for run {run_id} ({len(rows)}/{NUM_MESSAGES} processed):")
    print(f"{'#':>3}  {'processed_at':<23}  {'writer':<6}  {'partition':<9}  {'entity':<9}  seq")
    for number, row in enumerate(rows, start=1):
        print(f"{number:>3}  {row['processed_at']:<23}  {row['writer']:<6}  {row['partition']:<9}  {row['entity']:<9}  {row['seq']}")

    #check that its updates were processed
    print("\nOrder check per package:")
    for entity in ENTITIES:
        entity_rows = [row for row in rows if row["entity"] == entity]
        seqs = [int(row["seq"]) for row in entity_rows]
        partitions = sorted(set(row["partition"] for row in entity_rows))
        status = "IN ORDER" if seqs == sorted(seqs) else "OUT OF ORDER"
        print(f"  {entity:<9} partitions={partitions}  processed seq order={seqs}  -> {status}")

if __name__ == "__main__":
    asyncio.run(main())