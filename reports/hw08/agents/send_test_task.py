import asyncio
import sys
import uuid
from aiokafka import AIOKafkaProducer
from common import KAFKA_BOOTSTRAP_SERVERS, TASKS_TOPIC, log, to_bytes

TEST_KEY = b"failure-test"

def make_task():
    return {
        "correlation_id": str(uuid.uuid4()),
        "question": "Should we upgrade the open source package requests 2.19.0 because of CVE-2018-18074?",
        "plan": "1. Explain the risk\n2. Name the fixed version\n3. Say how quickly to upgrade",
    }

async def send(producer, value, label):
    metadata = await producer.send_and_wait(TASKS_TOPIC, value, key=TEST_KEY)
    log(f"TEST SEND {label} to {metadata.topic} partition={metadata.partition} offset={metadata.offset}")

async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "once"
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()

    try:
        if mode == "once":
            task = make_task()
            await send(producer, to_bytes(task), f"task correlation_id={task['correlation_id']}")
        elif mode == "duplicate":
            #the same correlation_id is sent two times
            task = make_task()
            await send(producer, to_bytes(task), f"task correlation_id={task['correlation_id']} (first time)")
            await send(producer, to_bytes(task), f"task correlation_id={task['correlation_id']} (REPLAY)")
        elif mode == "poison":
            #not valid JSON
            await send(producer, b"this is not valid JSON {", "POISON message")
            task = make_task()
            await send(producer, to_bytes(task), f"normal task after the poison, correlation_id={task['correlation_id']}")
        else:
            print("Use: python send_test_task.py once | duplicate | poison")
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(main())