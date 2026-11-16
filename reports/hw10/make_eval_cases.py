import asyncio
import csv
import json
import os
import sys
import uuid
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "agents"))

from common import DRAFTS_TOPIC, INBOX_TOPIC, KAFKA_BOOTSTRAP_SERVERS, from_bytes, log, to_bytes
CASES_FILE = os.path.join(HERE, "eval_cases.json")
LABELS_FILE = os.path.join(HERE, "human_labels.csv")
WAIT_SECONDS = 300

QUESTIONS = [
    "Which version of lodash fixes CVE-2021-23337, and what should our team do about it?",
    "What type of vulnerability is CVE-2019-10744 in lodash, and how do we fix it?",
    "How serious is CVE-2020-28500 in lodash, and which version fixes it?",
    "Which version of requests fixes CVE-2018-18074?",
    "What is CVE-2023-32681 in requests and how should we fix it?",
    "What should our team do about Log4Shell (CVE-2021-44228) in log4j-core?",
    "Which log4j-core version fixes CVE-2021-45046?",
    "What type of vulnerability is CVE-2021-3749 in axios, and which version fixes it?",
    "How do we fix CVE-2022-25883 in the semver package?",
    "What is CVE-2020-7598 in minimist and which version fixes it?",
    "Which version of jsonwebtoken fixes CVE-2022-23529?",
    "What is CVE-2024-29041 in express and how do we fix it?",
    "Which urllib3 version fixes CVE-2023-43804?",
    "What type of vulnerability is CVE-2024-22195 in Jinja2, and which version fixes it?",
    "How should we handle CVE-2020-14343 in PyYAML?",
    "Which version of Pillow fixes CVE-2023-50447?",
    "What is CVE-2022-0235 in node-fetch and which version fixes it?",
    "What type of vulnerability is CVE-2021-32803 in the npm tar package?",
    "Which version of moment fixes CVE-2022-24785?",
    "What is CVE-2022-0155 in follow-redirects and how do we fix it?",
]

async def collect_drafts():
    cases = []
    consumer = AIOKafkaConsumer(DRAFTS_TOPIC, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS, auto_offset_reset="earliest")
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await consumer.start()
    await producer.start()
    try:
        for number, question in enumerate(QUESTIONS, start=1):
            correlation_id = str(uuid.uuid4())
            await producer.send_and_wait(INBOX_TOPIC, to_bytes({"correlation_id": correlation_id, "question": question}))
            log(f"Case {number} of {len(QUESTIONS)}: sent {question}")

            async def wait_for_draft():
                async for msg in consumer:
                    try:
                        message = from_bytes(msg.value)
                    except Exception:
                        continue
                    if message.get("correlation_id") == correlation_id:
                        return message["draft"]
            try:
                draft = await asyncio.wait_for(wait_for_draft(), timeout=WAIT_SECONDS)
            except asyncio.TimeoutError:
                log(f"No draft after {WAIT_SECONDS} s, skipping case {number}")
                continue
            cases.append({"case_id": f"case-{number:02d}", "trace_id": correlation_id,
                          "question": question, "draft": draft})
            log(f"Case {number}: got the draft")
    finally:
        await consumer.stop()
        await producer.stop()
    return cases

def main():
    if os.path.exists(CASES_FILE) or os.path.exists(LABELS_FILE):
        print("eval_cases.json or human_labels.csv already exists")
        return
    cases = asyncio.run(collect_drafts())
    with open(CASES_FILE, "w") as f:
        json.dump(cases, f, indent=2)
    with open(LABELS_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "human_label"])
        for case in cases:
            writer.writerow([case["case_id"], ""])
    print(f"\nsaved {len(cases)} cases in eval_cases.json")

if __name__ == "__main__":
    main()
