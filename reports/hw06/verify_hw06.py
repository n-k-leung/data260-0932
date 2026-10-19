import csv
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
import requests

HOMEWORK = 6
SID4 = "0932"
SEED = 932
VERIFY_SEED = 260000 + 932
PORT = 8032
BASE = "http://localhost:" + str(PORT)

here = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(here, "backend")

try:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=here, text=True).strip()
except Exception:
    commit = "unknown"
random.seed (VERIFY_SEED)

# model name: read SMOL_MODEL from backend/.env (same setting 11m_adapter.py uses)
model = os.environ.get("SMOL_MODEL", "")
env_file = os.path.join(backend_dir, ".env")
if not model and os.path.exists(env_file):
    for line in open(env_file, encoding="utf-8"):
        if line.startswith("SMOL_MODEL"):
            model = line.split("=",1)[1].split("#")[0].strip().strip('"')
if not model:
    model = "qwen3:8b"
def backend_is_up():
    try:
        return requests.get(BASE + "/health", timeout=2).status_code == 200
    except requests.exceptions.RequestException:
        return False

server = None
if not backend_is_up():
    server = subprocess.Popen([sys .executable,"-m", "uvicorn", "app.main:app", "--port", str(PORT)],cwd=backend_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(20):
        if backend_is_up():
            break
        time.sleep(1)

# test data: random but repeatable because of VERIFY_SEED
TICKET = "T-"+ str(random.randint(1000, 9999))
USER = "verify" + str(VERIFY_SEED)
OTHER_USER = USER + "_other"
SESSION = "verify-session-" + str(VERIFY_SEED)
created_doc_ids = []

def count_usage_rows():
# find chat_usage.csv anywhere under this folder (skipping big folders) and count its data rows
    files = []
    rows = 0
    for folder, dirs, names in os.walk(here):
        dirs[:] = [d for d in dirs if d not in ("venv", "node_modules", ".git", "__pycache__")]
        if "chat_usage.csv" in names:
            path = os.path.join(folder, "chat_usage.csv")
            files.append(path)
            with open(path, newline="", encoding="utf-8") as f:
                rows += max(sum(1 for _ in csv.reader(f)) - 1, 0)
    return files, rows
    
usage_rows_before = count_usage_rows () [1]

def load_file_mem():
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from app import file_mem
    return file_mem

def check_backend_responds():
    r = requests.get(BASE + "/health", timeout=5)
    return r.status_code == 200, "GET /health returned " + str(r.status_code)

def check_doc_crud():
    body = {"title": "verify doc", "category": "injection", "discovered_at": "2026-10-01T10:00:00"}
    r = requests.post(BASE + "/api/vul-docs", json=body, timeout=10)
    doc_id = r.json().get("id") if r.status_code == 201 else None
    if not doc_id:
        return False, "POST /api/vul-docs returned " + str(r.status_code)
    created_doc_ids.append(doc_id)
    got = requests.get(BASE + "/api/vul-docs/" + doc_id, timeout=10)
    deleted = requests.delete(BASE + "/api/vul-docs/" + doc_id, timeout=10)
    gone = requests.get(BASE + "/api/vul-docs/" + doc_id, timeout=10)
    ok = got.status_code == 200 and deleted.status_code == 200 and gone.status_code == 404
    return ok, "create 201, get " + str(got.status_code) + ", delete " + str(deleted.status_code) + ", get after delete " + str(gone.status_code)

def check_doc_validation():
    body = {"title": "x", "category": "not-a-real-category", "discovered_at": "2026-10-01T10:00:00"}
    r = requests.post(BASE + "/api/vul-docs", json=body, timeout=10)
    return r.status_code == 422, "POST with an invalid category returned " + str(r.status_code)

def check_chat_returns_reply():
    message = "Remember that my ticket number is " + TICKET + ".Answer in one short sentence."
    r = requests.post(BASE + "/api/chat", json={"user_id": USER, "session_id": SESSION, "message": message}, timeout=600)
    data = r.json() if r.status_code == 200 else {}
    reply = data.get("reply")
    ok = r.status_code == 200 and isinstance(reply, str) and len(reply.strip()) > 0 and "memory_used" in data
    return ok, "POST /api/chat returned " + str(r.status_code) + ", reply length: " + str(len(reply) if isinstance(reply, str) else 0)

def check_messages_saved():
    r = requests.get(BASE + "/api/memory/" + USER, timeout=10)
    messages = r.json().get("messages", []) if r.status_code == 200 else []
    roles = [m.get("role") for m in messages]
    has_ticket = any(TICKET in m.get("content", "") for m in messages if m.get("role") == "user")
    ok = "user" in roles and "assistant" in roles and has_ticket
    return ok, "GET /api/memory returned " + str(len(messages)) + " messages, user + assistant saved: " + str(ok)

def check_short_term_window():
    r = requests.post(BASE + "/api/chat", json={"user_id": USER, "session_id": SESSION, "message": "What is two plus two?"}, timeout=600)
    data = r.json() if r.status_code == 200 else {}
    count = data.get("memory_used", {}).get("short_term_count", 0)
    return r.status_code == 200 and count >= 2, "second turn short_term_count = " + str(count) + " (needs 2 or more)"

def check_aggregate():
    r = requests.get(BASE + "/api/aggregate/" + USER, timeout=10)
    days = r.json().get("daily_message_counts", []) if r.status_code == 200 else []
    total = sum(d.get("count", 0) for d in days)
    return r.status_code == 200 and total >= 2, "GET /api/aggregate returned " + str(r.status_code) + ", total messages counted: " + str(total)

def check_user_isolation():
    r = requests.get(BASE + "/api/memory/" + OTHER_USER, timeout=10)
    data = r.json() if r.status_code == 200 else {"messages": ["error"]}
    ok = r.status_code == 200 and data.get("messages") == [] and data.get("episodic_facts") == []
    return ok, "a different user_id sees no messages or facts: " + str(ok)

def check_usage_logged():
    files, rows_after = count_usage_rows()
    header_ok = False
    for path in files:
        header = open(path, encoding="utf-8").readline()
        if all(col in header for col in ("prompt_tokens", "completion_tokens", "latency_ms")):
            header_ok = True
    ok = header_ok and rows_after > usage_rows_before
    return ok, "chat_usage.csv rows " + str(usage_rows_before) + " -> " + str(rows_after) + ", token and latency columns present: " + str(header_ok)

def check_memory_files_loaded():
    fm = load_file_mem()
    agent_text, memory_text = fm.load_files()
    prompt = fm.build_system_prompt()
    ok = len(agent_text.strip()) > 0 and len(memory_text.strip()) > 0 and agent_text.strip()[:30] in prompt
    return ok, "AGENT.md chars: " + str(len(agent_text)) + ", MEMORY.md chars: " + str(len(memory_text)) + ", AGENT.md in system prompt: " + str(ok)

def check_consolidation_trigger():
    fm = load_file_mem()
    long_text = "\n".join("- [t" + str(i) + "] fact " + str(i) + " (2026-01-01)" for i in range(41))
    short_text = fm.make_stamp_line(datetime.now(timezone.utc)) + "\n- [a.b] x (2026-01-01)\n"
    long_needs, _= fm.needs_consolidation(long_text)
    short_needs, _= fm.needs_consolidation(short_text)
    return long_needs and not short_needs, "41 lines needs consolidation: " + str(long_needs) + ", small recent file needs it: " + str(short_needs)

checks = [
    ("backend responds on PORT_BASE", check_backend_responds),
    ("document API create, read, delete works", check_doc_crud),
    ("invalid document is rejected with 422", check_doc_validation),
    ("POST /api/chat returns a reply", check_chat_returns_reply),
    ("user and assistant messages are saved", check_messages_saved),
    ("short-term window is used on the next turn", check_short_term_window),
    ("aggregate endpoint counts messages", check_aggregate),
    ("memory is isolated between users", check_user_isolation),
    ("chat request is logged with tokens and latency", check_usage_logged),
    ("AGENT.md and MEMORY.md load into the system prompt", check_memory_files_loaded),
    ("consolidation trigger (over 40 lines / 24 hours)", check_consolidation_trigger),
]
results = []

for name, function in checks:
    try:
        passed, detail = function()
    except Exception as e:
        passed, detail = False, "error: " + str(e)
    results.append({"check": name, "result": "pass" if passed else "fail", "detail": detail})
    print(("PASS - " if passed else "FAIL - ") + name + " - " + detail)

# remove the temporary test data this script created
try:
    from pymongo import MongoClient
    db = MongoClient(os.environ.get("MONGODB_URI", "mongodb://localhost:27017"), serverSelectionTimeoutMS=3000)["s" + SID4 + "_doc"]
    for collection in ("messages", "summaries", "episodes"):
        db[collection].delete_many({"user_id": {"$in": [USER, OTHER_USER]}})
    for doc_id in created_doc_ids:
        requests.delete(BASE + "/api/vul-docs/" + doc_id, timeout=5)
except Exception as e:
    print("cleanup skipped: " + str(e))

if server:
    server.terminate()

report = {
    "homework": HOMEWORK,
    "sid4": SID4,
    "commit": commit,
    "model": model,
    "seed": SEED,
    "verify_seed": VERIFY_SEED,
    "checks": results,
}
with open(os.path.join(here, "verification.json"), "w") as f:
    json.dump(report, f, indent=2)

print("verification.json outputted")