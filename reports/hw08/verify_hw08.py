import csv
import glob
import importlib.util
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import requests

HOMEWORK = 8
SID4 = "0932"
SEED = 932
VERIFY_SEED = 260000 + 932
PORT = 8032
BASE = "http://127.0.0.1:8032"
API_URL = BASE + "/vuls"
here = os.path.dirname(os.path.abspath(__file__))
agents_dir = os.path.join(here, "agents")
raw_dir = os.path.join(here, "raw")

random.seed(VERIFY_SEED)
os.environ["NO_PROXY"] = "127.0.0.1,localhost"

try:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=here, text=True).strip()
except Exception:
    commit = "unknown"
try:
    tag = subprocess.check_output(["git", "describe", "--tags", "--exact-match", "HEAD"], cwd=here, text=True, stderr=subprocess.DEVNULL).strip()
except Exception:
    tag = "not tagged"

model = os.environ.get("MODEL", "qwen3:8b")

def api_is_up():
    try:
        return requests.get(BASE + "/", timeout=2).status_code == 200
    except requests.exceptions.RequestException:
        return False

started_docker = False
if not api_is_up():
    subprocess.run(["docker", "compose", "up", "-d"], cwd=here,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    started_docker = True
    for i in range(60):
        if api_is_up():
            break
        time.sleep(1)
    time.sleep(5)

def load_module_from_file(name, path):
    if agents_dir not in sys.path:
        sys.path.insert(0, agents_dir)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def kafka_command(args):
    result = subprocess.run(["docker", "exec", "kafka"] + args, capture_output=True, text=True, timeout=60)
    return result.stdout

def send(operation, data):
    correlation_id = str(uuid.uuid4())
    r = requests.post(API_URL, json={"correlation_id": correlation_id, "operation": operation, "data": data}, timeout=20)
    return correlation_id, r.json()

def is_uuid(value):
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False

test_vulnerability = {
    "package_name": "verify-package-" + str(random.randint(1000, 9999)),
    "severity": "High",
    "vul_code": "CVE-VERIFY-" + str(VERIFY_SEED),
    "vendor_id": 1,
}
saved = {}

def check_api_responds():
    r = requests.get(BASE + "/", timeout=5)
    return r.status_code == 200, "GET / returned " + str(r.status_code)

def check_create():
    correlation_id, data = send("CREATE_VULNERABILITY", test_vulnerability)
    saved["id"] = data.get("vulnerability_id")
    ok = data.get("success") is True and is_uuid(saved["id"]) and data.get("correlation_id") == correlation_id
    return ok, "success: " + str(data.get("success")) + ", vulnerability_id is a UUID: " + str(is_uuid(saved["id"])) + ", correlation_id preserved: " + str(data.get("correlation_id") == correlation_id)

def check_get():
    correlation_id, data = send("GET_VULNERABILITY", {"vulnerability_id": saved.get("id")})
    vulnerability = data.get("vulnerability") or {}
    same_fields = all(vulnerability.get(key) == value for key, value in test_vulnerability.items())
    ok = (data.get("success") is True and data.get("correlation_id") == correlation_id
          and vulnerability.get("vulnerability_id") == saved.get("id") and same_fields)
    return ok, "success: " + str(data.get("success")) + ", same fields as created: " + str(same_fields) + ", correlation_id preserved: " + str(data.get("correlation_id") == correlation_id)

def check_get_unknown_id():
    correlation_id, data = send("GET_VULNERABILITY", {"vulnerability_id": str(uuid.uuid4())})
    ok = data.get("success") is False and bool(data.get("error")) and data.get("correlation_id") == correlation_id
    return ok, "success: " + str(data.get("success")) + ", has error: " + str(bool(data.get("error"))) + ", correlation_id preserved: " + str(data.get("correlation_id") == correlation_id)


def check_unknown_operation():
    correlation_id, data = send("DELETE_VULNERABILITY", {})
    ok = data.get("success") is False and bool(data.get("error")) and data.get("correlation_id") == correlation_id
    return ok, "success: " + str(data.get("success")) + ", has error: " + str(bool(data.get("error"))) + ", correlation_id preserved: " + str(data.get("correlation_id") == correlation_id)

def check_invalid_field():
    bad = dict(test_vulnerability, severity="NotASeverity")
    correlation_id, data = send("CREATE_VULNERABILITY", bad)
    ok = data.get("success") is False and "vulnerability_id" not in data and data.get("correlation_id") == correlation_id
    return ok, "invalid severity rejected: " + str(data.get("success") is False) + ", no id created: " + str("vulnerability_id" not in data)

def check_topics():
    topics = kafka_command(["/opt/kafka/bin/kafka-topics.sh", "--list", "--bootstrap-server", "localhost:9092"]).split()
    needed = ["s0932_vulnerability_requests", "s0932_vulnerability_responses", "s0932_inbox", "s0932_tasks","s0932_drafts", "s0932_final", "s0932_dead_letter"]
    missing = [topic for topic in needed if topic not in topics]
    describe = kafka_command(["/opt/kafka/bin/kafka-topics.sh", "--describe", "--topic", "s0932_tasks", "--bootstrap-server", "localhost:9092"])
    two_partitions = "PartitionCount: 2" in describe
    ok = not missing and two_partitions
    return ok, "missing topics: " + str(missing) + ", s0932_tasks has 2 partitions: " + str(two_partitions)

def check_idempotency():
    writer = load_module_from_file("verify_writer", os.path.join(agents_dir, "writer.py"))
    temp_dir = tempfile.mkdtemp(prefix="verify_hw08_")
    try:
        #a temporary file so the real writer_processed_ids.txt is not changed
        writer.PROCESSED_FILE = os.path.join(temp_dir, "processed_ids.txt")
        correlation_id = "verify-" + str(random.randint(1000, 9999))
        processed_ids = writer.load_processed_ids()
        seen_before = correlation_id in processed_ids
        writer.remember_processed_id(correlation_id, processed_ids)
        after_restart = writer.load_processed_ids()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    ok = not seen_before and correlation_id in after_restart
    return ok, "new id not seen before: " + str(not seen_before) + ", id still seen as processed after a restart: " + str(correlation_id in after_restart)

def check_dead_letter():
    output = kafka_command(["/opt/kafka/bin/kafka-console-consumer.sh", "--bootstrap-server", "localhost:9092", "--topic", "s0932_dead_letter", "--from-beginning", "--timeout-ms", "5000"])
    messages = []
    for line in output.splitlines():
        if line.startswith("{"):
            messages.append(json.loads(line))
    good = [m for m in messages if m.get("attempts") == 3 and m.get("source_topic") == "s0932_tasks"]
    return len(good) > 0, str(len(good)) + " dead letter message(s) from s0932_tasks after 3 attempts"

def check_ordering_with_key():
    rows = []
    for path in glob.glob(os.path.join(raw_dir, "ordering_runs_*.csv")):
        with open(path, newline="") as f:
            rows += list(csv.DictReader(f))
    key_runs = sorted(set(row["run"] for row in rows if row["run"].startswith("key-")))
    if not key_runs:
        return False, "no key run found in raw/ordering_runs_*.csv"
    run = key_runs[-1]
    run_rows = sorted([row for row in rows if row["run"] == run], key=lambda row: row["processed_at"])
    all_good = True
    for entity in set(row["entity"] for row in run_rows):
        entity_rows = [row for row in run_rows if row["entity"] == entity]
        seqs = [int(row["seq"]) for row in entity_rows]
        partitions = set(row["partition"] for row in entity_rows)
        if len(partitions) != 1 or seqs != sorted(seqs):
            all_good = False
    ok = len(run_rows) == 20 and all_good
    return ok, "run " + run + ": " + str(len(run_rows)) + "/20 processed, each package in one partition and in order: " + str(all_good)

checks = [
    ("FastAPI responds on PORT_BASE", check_api_responds),
    ("CREATE_VULNERABILITY through Kafka returns a UUID and the same correlation_id", check_create),
    ("GET_VULNERABILITY through Kafka returns the created vulnerability", check_get),
    ("GET_VULNERABILITY with an unknown id returns an error with the same correlation_id", check_get_unknown_id),
    ("an unknown operation returns an error with the same correlation_id", check_unknown_operation),
    ("CREATE_VULNERABILITY with an invalid field is rejected", check_invalid_field),
    ("all s0932 topics exist and s0932_tasks has 2 partitions", check_topics),
    ("writer idempotency remembers processed correlation_ids after a restart", check_idempotency),
    ("poison message was moved to s0932_dead_letter after 3 attempts", check_dead_letter),
    ("keyed ordering run kept each package in one partition and in order", check_ordering_with_key),
]
results = []

for name, function in checks:
    try:
        passed, detail = function()
    except Exception as e:
        passed, detail = False, "error: " + str(e)
    results.append({"check": name, "result": "pass" if passed else "fail", "detail": detail})
    print(("PASS - " if passed else "FAIL - ") + name + " - " + detail)

if started_docker:
    subprocess.run(["docker", "compose", "stop"], cwd=here, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
report = {
    "homework": HOMEWORK,
    "sid4": SID4,
    "commit": commit,
    "tag": tag,
    "model": model,
    "seed": SEED,
    "verify_seed": VERIFY_SEED,
    "checks": results,
}
with open(os.path.join(here, "verification.json"), "w") as f:
    json.dump(report, f, indent=2)

print("verification.json dones")