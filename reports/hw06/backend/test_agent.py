import json
import os

from app import file_mem as fm

BUGGY_CODE = """def average(numbers):
    total = 0
    for n in numbers:
        total = total + n
    try:
        return total / len(numbers)
    except:
        pass
"""
CLEAN_CODE = """def add_numbers(first, second):
    # add two numbers and return the result
    return first + second
"""

cases = [("buggy code", BUGGY_CODE, False), ("clean code", CLEAN_CODE, True)]
output = []
all_passed = True
for name, code, expect_no_issue in cases:
    print("\n === case:", name, " === ")
    reply = fm.review_code(code)
    print("reply:\n" + reply)
    results = fm.check_reply_follows_agent_md(reply, expect_no_issue)
    for rule, passed, detail in results:
        print(f" [{'PASS' if passed else 'FAIL'}] {rule}: {detail}")
        all_passed = all_passed and passed
    output.append(
        {
            "case": name,
            "reply": reply,
            "checks": [{"rule": r, "passed": p, "detail": d} for r, p, d in results],
        }
    )

print("\nOVERALL:", "ALL RULES FOLLOWED" if all_passed else "SOME RULES BROKEN")
raw_dir = os.path.join(os.path.dirname(__file__), "..", "reports", "hw06", "raw")
os.makedirs(raw_dir, exist_ok=True)
with open(os.path.join(raw_dir, "agent_md_check.json"), "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)
