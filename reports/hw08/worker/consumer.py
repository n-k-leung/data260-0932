import asyncio
import json
import os
import uuid
from datetime import datetime
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
REQUEST_TOPIC = "s0932_vulnerability_requests"
SEVERITY_LEVELS = ["Critical", "High", "Medium", "Low"]

vulnerabilities = {}

def log(text):
    print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} {text}", flush=True)

def validate_vulnerability(data):
    for field in ["package_name", "severity", "vul_code"]:
        value = data.get(field)
        if not isinstance(value, str) or value.strip() == "":
            return f"{field} is required and must be a non-empty string"

    if data["severity"] not in SEVERITY_LEVELS:
        return "severity must be one of: Critical, High, Medium, Low"

    vendor_id = data.get("vendor_id")
    if type(vendor_id) is not int or vendor_id <= 0:
        return "vendor_id is required and must be a positive integer"

    return None

def process_request(operation, data):
    if not isinstance(data, dict):
        return {"success": False, "error": "data must be a JSON object"}

    if operation == "CREATE_VULNERABILITY":
        error = validate_vulnerability(data)
        if error:
            return {"success": False, "error": error}

        vulnerability_id = str(uuid.uuid4())
        vulnerabilities[vulnerability_id] = {
            "vulnerability_id": vulnerability_id,
            "package_name": data["package_name"].strip(),
            "severity": data["severity"],
            "vul_code": data["vul_code"].strip(),
            "vendor_id": data["vendor_id"],
        }
        return {
            "success": True,
            "vulnerability_id": vulnerability_id,
            "message": "Vulnerability created",
        }
    elif operation == "GET_VULNERABILITY":
        vulnerability_id = data.get("vulnerability_id")
        if not vulnerability_id:
            return {"success": False, "error": "vulnerability_id is required"}
        if vulnerability_id not in vulnerabilities:
            return {"success": False, "error": "Vulnerability not found"}
        return {"success": True, "vulnerability": vulnerabilities[vulnerability_id]}
    else:
        return {"success": False, "error": "Unknown operation"}

async def main():
    consumer = AIOKafkaConsumer(
        REQUEST_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="s0932-vulnerability-worker-group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

    await consumer.start()
    await producer.start()
    log("Consumer is ready and listening...")
    try:
        async for msg in consumer:
            request = json.loads(msg.value.decode())
            correlation_id = request.get("correlation_id")
            reply_to = request.get("reply_to")
            operation = request.get("operation")
            data = request.get("data")
            log(f"WORKER RECEIVE from topic={msg.topic} partition={msg.partition} offset={msg.offset}")
            log(f"WORKER RECEIVE message={json.dumps(request)}")
            log(f"WORKER PROCESS operation={operation} correlation_id={correlation_id}")
            result = process_request(operation, data)
            response = {"correlation_id": correlation_id}
            response.update(result)
            metadata = await producer.send_and_wait(reply_to, json.dumps(response).encode())
            log(f"WORKER REPLY to topic={metadata.topic} partition={metadata.partition} offset={metadata.offset}")
            log(f"WORKER REPLY message={json.dumps(response)}")
    finally:
        await consumer.stop()
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(main())
