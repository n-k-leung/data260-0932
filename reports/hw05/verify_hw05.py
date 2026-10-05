import csv
import glob
import json
import os
import random
import subprocess
import sys
import time
import requests

HOMEWORK = 5
SID4 = "0932"
SEED = 932
VERIFY_SEED = 260000 + 932
PORT = 8032
BASE = "http://localhost:" + str(PORT)

here = os.path.dirname(os.path.abspath(__file__))

try:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=here, text=True).strip()
except Exception:
    commit = "unknown"
random.seed(VERIFY_SEED)

model = "unknown"
agent_file = os.path.join(here, "mcp", "agent.py")
if os.path.exists(agent_file):
    for line in open(agent_file, encoding="utf-8"):
        if line.startswith("MODEL ="):
            model = line.split("=")[1].split("#")[0].strip().strip('"')

def backend_is_up():
    try:
        return requests.get(BASE + "/health", timeout=2).status_code == 200
    except requests.exceptions.RequestException:
        return False
    
server = None
if not backend_is_up():
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORT)],cwd=os.path.join(here, "backend"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(20):
        if backend_is_up():
            break
        time.sleep(1)

email = "verify" + str(VERIFY_SEED) + "@example.com"
s = requests.Session()

def check_backend_responds():
    r = requests.get(BASE + "/health", timeout=5)
    return r.status_code == 200, "GET /health returned " + str(r.status_code)
def check_login_required():
    r = requests.get(BASE + "/vuls")
    return r.status_code == 401, "GET /vulnerabilities without login returned " + str(r.status_code)

def check_login_sets_cookie():
    s.post(BASE + "/auth/register", json={"name": "Verify", "email": email, "password": "verify1234"})
    r = s.post(BASE + "/auth/login", json={"email": email, "password": "verify1234"})
    header = r.headers.get("set-cookie", "").lower()
    ok = r.status_code == 200 and "session_id" in header and "httponly" in header
    return ok, "login returned " + str(r.status_code) + ", HTTP-only session cookie set: " + str(ok)

def check_domain_mcp_tool():
    sys.path.insert(0, os.path.join(here, "mcp"))
    import vul
    result = vul.count_by_severity()
    ok = isinstance(result, dict) and "ok" in result
    return ok, "vul.count_by_severity() returned: " + str(result)

def check_meals_mcp_tool():
    sys.path.insert(0, os.path.join(here, "mcp"))
    import meals
    result = meals.random_meal()
    ok = isinstance(result, dict) and ("name" in result or "message" in result)
    return ok, "meals_server.random_meal() returned keys: " + str(list(result.keys()))

checks = [
    ("backend responds on PORT_BASE", check_backend_responds),
    ("list endpoint needs login", check_login_required),
    ("login sets an HTTP-only session cookie", check_login_sets_cookie),
    ("vul MCP server starts up and responds to a tool call", check_domain_mcp_tool),
    ("meals MCP server starts up and responds to a tool call", check_meals_mcp_tool),
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
"model": model,
"seed": SEED,
"verify_seed": VERIFY_SEED,
"checks": results,
}
with open(os.path.join(here, "verification.json"), "w") as f:
    json.dump(report, f, indent=2)

print("verification.json outputted")

