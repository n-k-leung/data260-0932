import csv
import glob
import json
import os
import random
import subprocess
import sys
import time
import requests

HOMEWORK = 4
SID4 = "0932"
SEED = 932
VERIFY_SEED = 260000 + 932
PORT = 8032
BASE = "http://localhost:" + str(PORT)

here = os.path.dirname(os.path.abspath(__file__))
try:
  commit = subprocess.check.output(["git", "rev-parse", "HEAD"], cud=here, text=True).strip()
except Exception:
  commit = "unknown"
random.seed (VERIFY_SEED)
model = "unknown"
for line in open(os.path.join(here, "rag.py"), encoding="utf-8"):
  if line.startswith("MODEL ="):
    model = line.split("=")[1].split("#")[0].strip().strip('"')

def backend_is_up():
  try:
    return requests.get(BASE + "/health", timeout=2).status_code == 200
  except requests.exceptions.RequestException:
    return False

  

server = None
if not backend_is_up():
  server = subprocess. Popen (
    [sys.executable, "-m", "uvicorn", "app.main:app", " -- port", str(PORT)],
    cwd=os.path.join(here, "backend"),
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
  for i in range(20):
    if backend_is_up():
      break
    time.sleep(1)
    
size = random.choice([10, 50, 200])
email = "verify" + str(VERIFY_SEED) + "@example.com"
s = requests.Session()

def check_backend_responds():
  r = requests.get(BASE + "/health", timeout=5)
  return r.status_code == 200, "GET /health returned " + str(r.status_code)

def check_login_required():
  r = requests.get(BASE + "/vuls")
  return r.status_code == 401, "GET /vuls without login returned " + str(r.status_code)

def check_login_sets_cookie():
  s.post(BASE + "/auth/register", json={"name": "Verify", "email": email, "password": "verify1234"})
  r = s.post(BASE + "/auth/login", json={"email": email, "password": "verify1234"})
  header = r.headers.get("set-cookie", "").lower()
  ok = r.status_code == 200 and "session_id" in header and "httponly" in header
  return ok, "login returned " + str(r.status_code) + ", HTTP-only session cookie set: " + str(ok)

def check_naive_returns_data():
  r = s.get(BASE + "/vuls/naive", params={"limit": size})
  return r.status_code == 200 and len(r.json()) == size, "limit " + str(size) + " -> " + str(len(r.json())) + " records"

def check_fixed_returns_data():
  r = s.get(BASE + "/vuls/fixed", params={"limit": size})
  return r.status_code == 200 and len(r. json()) == size, "limit " + str(size) + " -> "+ str(len(r.json())) + " records"

def check_same_data():
  a = s.get(BASE + "/vuls/naive", params={"limit": size}).json()
  b = s.get(BASE + "/vuls/fixed", params={"limit": size}).json()
  return a == b, "naive and fixed return the same records: " + str(a == b)

def check_raw_has_180_requests():
  rows = list(csv.DictReader(open(os.path. join(here, "raw", "n_plus_one_raw.csv"))))
  return len(rows) == 180, "raw/n_plus_one_raw.csv has " + str(len(rows)) + " rows"

def check_rag_corpus():
  docs = glob.glob(os.path.join(here, "docs", "*.txt"))
  return len(docs) >= 5, str(len(docs)) + " documents in rag/docs"

checks = [
("backend responds on PORT_BASE", check_backend_responds),
("list endpoint needs login", check_login_required),
("login sets an HTTP-only session cookie", check_login_sets_cookie),
("naive list endpoint returns data", check_naive_returns_data),
("fixed list endpoint returns data", check_fixed_returns_data),
("naive and fixed return the same data", check_same_data),
("raw/ has all 180 N+1 requests", check_raw_has_180_requests),
("RAG corpus has at least 5 documents", check_rag_corpus),
]

results = []
for name, function in checks:
  try:
    passed, detail = function()
  except Exception as e:
    passed, detail = False, "error: " + str(e)
  results.append({"check": name, "result": "pass" if passed else "fail", "detail": detail})
  print(("PASS " if passed else "FAIL ") + name + " -" + detail)

if server:
  server. terminate()

report = {
  "homework": HOMEWORK,
  "sid4": SID4,
  "commit": commit,
  "model": model,
  "seed": SEED,
  "verify_seed": VERIFY_SEED,
  "checks": results,
}
with open(os.path.join(here, "verification. json"), "w") as f:
  json.dump(report, f)