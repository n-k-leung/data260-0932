import json
import os
import sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app import models
import vul
import tool_part4
from agent import run_agent

testdb = "test.db"
if os.path.exists(testdb):
    os.remove(testdb)

test_engine = create_engine("sqlite:///" + testdb)
Base.metadata.create_all(bind=test_engine)
TestSession = sessionmaker (bind=test_engine)
vul.get_session = TestSession
tool_part4.get_session=TestSession
db = TestSession()
vendor = models.Vendor(name="microsoft", industry="software", contact_email="microsoft@microsoft.org")
db.add (vendor)
db.commit()
db.refresh(vendor)
db.add(models.Vul(package_name="npm", severity="low", vul_code="fe9s5fs", vendor_id=vendor.id))
db.commit()
db.close()

passed = 0
total = 0

def check(label, condition):
    global passed, total
    total += 1
    try:
        assert condition
        passed += 1
        print("PASS -", label)
    except AssertionError:
        print("FAIL -", label)
# test 1: search_vulnerabilities, valid input
r = json.loads(tool_part4.execute_tool("search_vulnerabilities", {"package_name": "npm"}))
check("search_vulnerabilities valid input returns ok", r["ok"] is True and len(r["data"]) == 1)

# test 2: search_vulnerabilities, invalid input (blank package_name)
r = json.loads(tool_part4.execute_tool("search_vulnerabilities", {"package_name": " "}))
check("search_vulnerabilities blank input is rejected", r["ok"] is False)

# test 3: get_vulnerability, valid input
r = json.loads(tool_part4.execute_tool("get_vulnerability", {"vuln_id": 1}))
check("get_vulnerability valid id returns ok", r["ok"] is True and r["data"]["package_name"] == "npm")

# test 4: get_vulnerability, invalid input (id that does not exist)
r = json.loads(tool_part4.execute_tool("get_vulnerability", {"vuln_id": 27}))
check("get_vulnerability missing id is rejected", r["ok"] is False)

# test 5: count_by_severity, valid input
r = json.loads(tool_part4.execute_tool("count_by_severity", {"min_count": 0}))
check("count_by_severity valid input returns ok", r["ok"] is True)

# test 6: count_by_severity, invalid input (negative min_count)
r = json.loads(tool_part4.execute_tool("count_by_severity", {"min_count": -1}))
check("count_by_severity negative min_count is rejected", r["ok"] is False)
# test 7: safety rule
r = json.loads(tool_part4.execute_tool("search_vulnerabilities", {"package_name": "ab"}))
check("execute_tool blocks a call that violates the safety rule", r["ok"] is False and r["error"].startswith("SAFETY:"))
def mock_model_always_calls_tool(prompt):
    return json.dumps({"tool": "get_vulnerability", "inputs": {"vuln_id": 1}})

# test 8: run_agent
test_log = "test_agent_runs.jsonl"
result = run_agent("test question", model_fn=mock_model_always_calls_tool, max_steps=3, log_path=test_log)
check("run_agent stops after reaching max_steps",
result["stop_reason"] == "max_steps_reached" and len(result["steps"]) == 3)
if os.path.exists(test_log):
    os.remove(test_log)

print(str(passed) + "/" + str(total) +"tests passed")

test_engine.dispose() #for permissin to remove testdb or errror
os.remove(testdb)