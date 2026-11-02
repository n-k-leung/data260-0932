import json
import uuid
from datetime import datetime
import requests

API_URL = "http://127.0.0.1:8032/vuls"
REQUEST_TOPIC = "s0932_vulnerability_requests"
RESPONSE_TOPIC = "s0932_vulnerability_responses"

#to print times when action is done to make sure it is going in order cause sometimes id didnt for somereason
def log(text):
    print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} {text}", flush=True)


def send_request(correlation_id, operation, data):
    request = {"correlation_id": correlation_id, "operation": operation, "data": data}
    log(f"CLIENT SEND {operation} -> {REQUEST_TOPIC}")
    log(f"CLIENT SEND message={json.dumps(request)}")

    response = requests.post(API_URL, json=request, timeout=15).json()

    log(f"CLIENT RESPONSE from {RESPONSE_TOPIC} (through FastAPI)")
    log(f"CLIENT RESPONSE message={json.dumps(response)}")
    return response


print("\ncreating vulnerability")

create_correlation_id = str(uuid.uuid4())
log(f"CLIENT created correlation_id={create_correlation_id}")

vulnerability_data = {
    "package_name": "pip",
    "severity": "High",
    "vul_code": "CVE202023337",
    "vendor_id": 1,
}
create_response = send_request(create_correlation_id, "CREATE_VULNERABILITY", vulnerability_data)

if not create_response.get("success"):
    print("cannot create vul failed:", create_response)
    raise SystemExit(1)

vulnerability_id = create_response["vulnerability_id"]
log(f"CLIENT generated vulnerability_id={vulnerability_id}")

print("\nget vulneraiblity")

get_correlation_id = str(uuid.uuid4())
log(f"CLIENT created correlation_id={get_correlation_id}")
get_response = send_request(get_correlation_id, "GET_VULNERABILITY", {"vulnerability_id": vulnerability_id})

print("\n output")
print("retrieved vulnerability:")
print(json.dumps(get_response.get("vulnerability"), indent=2))

create_preserved = create_response.get("correlation_id") == create_correlation_id
get_preserved = get_response.get("correlation_id") == get_correlation_id
print(f"CREATE correlation_id preserved: {create_preserved} ({create_correlation_id})")
print(f"GET correlation_id preserved: {get_preserved} ({get_correlation_id})")
