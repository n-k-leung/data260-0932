import http.server
import importlib
import json
import os
import random
import shutil
import socketserver
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import requests

HOMEWORK = 7
SID4 = "0932"
SEED = 932
VERIFY_SEED = 260000 + 932
PORT = 8032
BASE = "http://localhost:8032"

here = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(here, "backend")
mcp_dir = os.path.join(here, "mcp")
bike_dir = os.path.join(here, "part4")
file_dir = os.path.join(here, "part6")

random.seed(VERIFY_SEED)
os.environ["NO_PROXY"] = "127.0.0.1,localhost"

try:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=here, text=True).strip()
except Exception:
    commit = "unknown"
try:
    tag = subprocess.check_output(["git", "describe", "--tags", "--exact-match", "HEAD"],
                                  cwd=here, text=True, stderr=subprocess.DEVNULL).strip()
except Exception:
    tag = "not tagged"

model = os.environ.get("SMOL_MODEL", "")
env_file = os.path.join(backend_dir, ".env")
if not model and os.path.exists(env_file):
    for line in open(env_file, encoding="utf-8"):
        if line.startswith("SMOL_MODEL"):
            model = line.split("=", 1)[1].split("#")[0].strip().strip('"')
if not model:
    model = "qwen3:8b"

def backend_is_up():
    try:
        return requests.get(BASE + "/health", timeout=2).status_code == 200
    except requests.exceptions.RequestException:
        return False

server = None
if not backend_is_up():
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORT)], cwd=backend_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(20):
        if backend_is_up():
            break
        time.sleep(1)

def load_module(name, folder):
    for path in (folder, backend_dir):
        if path not in sys.path:
            sys.path.insert(0, path)
    return importlib.import_module(name)
def load_module_from_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec. loader. exec_module(module)
    return module

def login(username, password):
    # /auth/login takes form fields
    return requests.post(BASE + "/auth/login", data={"username": username, "password": password},
                         timeout=10)

def get_token(username, password):
    r = login(username, password)
    return r.json().get("access_token") if r.status_code == 200 else None

def check_backend_responds():
    r = requests.get(BASE + "/health", timeout=5)
    return r.status_code == 200, "GET /health returned " + str(r.status_code)

def check_login_valid():
    r = login("bob", "bob123")
    data = r.json() if r.status_code == 200 else {}
    token = data.get("access_token")
    ok = isinstance(token, str) and len(token) > 20 and str(data.get("token_type")).lower() == "bearer"
    return ok, "POST /auth/login (bob) returned " + str(r.status_code) + ", token received: " + str(ok)

def check_login_invalid():
    r = login("bob", "wrong-password-" + str(VERIFY_SEED))
    return r.status_code == 401, "POST /auth/login with a wrong password returned " + str(r.status_code)

def check_me_needs_token():
    r = requests.get(BASE + "/auth/me", timeout=10)
    return r.status_code == 401, "GET /auth/me without a token returned " + str(r.status_code)

def check_me_with_token():
    token = get_token("bob", "bob123")
    r = requests.get(BASE + "/auth/me", headers={"Authorization": "Bearer " + str(token)}, timeout=10)
    data = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and data.get("username") == "bob" and data.get("role") == "writer"
    return ok, "GET /auth/me with bob's token returned " + str(r.status_code) + ", role: " + str(data.get("role"))

def check_reader_cannot_write():
    token = get_token("alice", "alice123")
    r = requests.post(BASE + "/vuls", json={}, headers={"Authorization": "Bearer " + str(token)}, timeout=10)
    return r.status_code == 403, "reader POST /vuls returned " + str(r.status_code) + " (403 = wrong role)"

def check_csv_sql_read_only():
    tools = load_module_from_file("part4_tools", os.path. join(bike_dir, "tools.py"))
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE trips (duration_sec REAL)")
    conn.executemany("INSERT INTO trips VALUES (?)", [(60,), (120,), (300,)])
    count = tools.csv_sql(conn, "SELECT COUNT(*) AS n FROM trips")
    drop = tools.csv_sql(conn, "DROP TABLE trips")
    after = tools.csv_sql(conn, "SELECT COUNT(*) AS n FROM trips")
    ok = (count["success"] and count["data"]["rows"][0]["n"] == 3 and not drop["success"]
          and after["success"] and after["data"]["rows"][0]["n"] == 3)
    return ok, "SELECT worked, DROP TABLE refused: " + str(not drop["success"]) + ", table still intact: " + str(after["success"])

def check_untrusted_label():
    agent = load_module("agent", bike_dir)
    web = agent.observation_message("policy_retriever", {"passages": []})
    other = agent.observation_message("csv_sql", {"rows": []})
    ok = agent.UNTRUSTED_LABEL and "UNTRUSTED" in web and "UNTRUSTED" not in other
    return ok, "web text is labelled untrusted: " + str("UNTRUSTED" in web) + ", SQL results are not: " + str("UNTRUSTED" not in other)

def check_tools():
    ft = load_module_from_file("part6_tools", os.path. join(file_dir, "tools.py"))
    sandbox = tempfile.mkdtemp(prefix="course_sandbox_")
    try:
        ft.set_sandbox(sandbox)
        marker = "DEBUG_" + str(random.randint(1000, 9999))
        ft.write_file("a.py", "x = 1\n" + marker + "\n")
        first_line = ft.read_file("a.py", max_lines=1)
        found_file = ft.glob_files("*.py")["files"]
        found_text = ft.search_in_files(marker, "*.py")["match_count"]
        outside = ft.read_file("../outside.txt")
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)
    ok = (first_line["ok"] and first_line["content"] == "x = 1" and found_file == ["a.py"]
          and found_text == 1 and not outside["ok"])
    return ok, "write/read/glob/search worked inside the sandbox, path outside it blocked: " + str(not outside["ok"])


checks = [
    ("backend responds on PORT_BASE", check_backend_responds),
    ("/auth/login returns a token for valid credentials", check_login_valid),
    ("/auth/login returns 401 for invalid credentials", check_login_invalid),
    ("/auth/me without a token returns 401", check_me_needs_token),
    ("/auth/me with a valid token returns the user and role", check_me_with_token),
    ("a reader is refused on a write route with 403", check_reader_cannot_write),
    ("csv_sql runs SELECT and refuses DROP TABLE", check_csv_sql_read_only),
    ("retrieved page text is labelled untrusted", check_untrusted_label),
    ("file tools work inside the sandbox and block outside paths", check_tools),
]
results = []

for name, function in checks:
    try:
        passed, detail = function()
    except Exception as e:
        passed, detail = False, "error: " + str(e)
    results.append({"check": name, "result": "pass" if passed else "fail", "detail": detail})
    print(("PASS - " if passed else "FAIL - ") + name + " - " + detail)

if server:
    server.terminate()

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

print("verification.json outputted")