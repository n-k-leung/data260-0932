import json
import os
import shutil
import sys
import tempfile

import tools as ft

HERE = os.path.dirname(os.path.abspath(__file__))
OPTIONS = {"seed": 932, "temperature": 0, "num_ctx": 8192}
MAX_STEPS = 8

SYSTEM_PROMPT = (
    "You are a coding assistant. You work inside a sandbox folder and can use the tools "
    "glob_files (list files), search_in_files (find text) and read_file (read a file). "
    "Never guess file names or contents: look them up with the tools, then answer."
)
INSTRUCTION = "Find the Python file that contains the word DEBUG and show me its full contents."

SANDBOX_FILES = {
    "math_tools.py": "def add(a, b):\n    return a + b\n",
    "server.py": "# server settings\nDEBUG = True\nPORT = 8080\n def start():\nprint('starting on port', PORT)\n",
    "notes.py": "NAME = 'course demo'\nVERSION = 1\n",
}

def make_ollama_model_fn():
    sys.path.insert(0, os.path.join(HERE, "..", "backend"))
    from app.llm_adapter import client

    def ask(messages):
        return client.complete(messages, tools=ft.TOOL_SCHEMAS, options=OPTIONS)
    return ask

def strip_thinking(text):
    if "</think>" in text:
        text = text.split("</think>")[-1]
    return text.strip()

def run_file_agent(instruction, model_fn):
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": instruction}]
    log = []
    for step in range(1, MAX_STEPS + 1):
        reply = model_fn(messages)
        text = strip_thinking(reply.get("content") or "")
        calls = reply.get("tool_calls") or []
        if not calls:
            return text, log, "final_answer"
        for call in calls:
            name, args = call.get("name"), call.get("arguments") or {}
            result = ft.execute_tool(str(name), args)
            log.append({"tool": name, "args": args, "ok": result["ok"]})
            print("  step", step, name, json.dumps(args)[:100], "->",
                  "ok" if result["ok"] else result["error"])
            messages.append({"role": "assistant",
                             "content": "Action: " + str(name) + " " + json.dumps(args)})
            messages.append({"role": "tool", "content":
                             "Result of " + str(name) + ": " + json.dumps(result)[:3000]})
    return "", log, "max_steps_reached"

def integration_test(model_fn=None):
    print("a) Integration test: glob -> search -> read")
    sandbox = tempfile.mkdtemp(prefix="course_sandbox_")
    ft.set_sandbox(sandbox)
    try:
        for name, content in SANDBOX_FILES.items():
            ft.write_file(name, content)
        print("sandbox:", sandbox)
        print("files created:", ", ".join(SANDBOX_FILES))
        print("instruction:", INSTRUCTION)
        answer, log, stop = (run_file_agent(INSTRUCTION, model_fn or make_ollama_model_fn()))
        used = [c["tool"] for c in log if c["ok"]]
        first = [used.index(t) if t in used else -1
                 for t in ["glob_files", "search_in_files", "read_file"]]
        in_order = -1 not in first and first == sorted(first)
        shows_file = "DEBUG = True" in answer and "PORT = 8080" in answer
        print("final answer:", answer[:400])
        print("tools used in order:", used, "| stop:", stop)
        print("glob -> search -> read in that order:", "PASS" if in_order else "FAIL")
        print("answer shows server.py contents:", "PASS" if shows_file else "FAIL")
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

GATE_CASES = [
    ("ls -la", True),
    ("pwd", True),
    ("cat notes.txt", True),
    ("grep -n DEBUG server.py", True),
    ("head -n 3 server.py", True),
    ("sudo ls", False),
    ("ls && rm -fr build", False),
    ("chown root server.py", False),
    ("echo hi >/etc/hosts", False),
    ("dd if=/dev/zero of=/dev/sda", False),
]

def draft_gate(command):
    for bad in ["rm -rf", "sudo", "chmod", "chown", "> /", "of=/dev/"]:
        if bad in command:
            return {"allowed": False, "reason": "destructive"}
    for prefix in ft.SAFE_PREFIXES:
        if command.startswith(prefix):
            return {"allowed": True, "reason": "matches SAFE_PREFIXES"}
    return {"allowed": False, "reason": "not in SAFE_PREFIXES"}


def run_gate(gate_function, title):
    print("\n" + title)
    false_allows = 0
    wrong = 0
    for command, should_pass in GATE_CASES:
        result = gate_function(command)
        if result["allowed"] == should_pass:
            verdict = "ok"
        elif result["allowed"]:
            verdict, false_allows = "FALSE ALLOW", false_allows + 1
        else:
            verdict, wrong = "FALSE BLOCK", wrong + 1
        print(" ", verdict.ljust(11), "|", "should pass " if should_pass else "should block",
              "|", command.ljust(32), "->", "allowed" if result["allowed"] else "blocked",
              "(" + result["reason"] + ")")
    print("  false allows:", false_allows, "| false blocks:", wrong,
          "| correct:", len(GATE_CASES) - false_allows - wrong, "of", len(GATE_CASES))
    return false_allows + wrong


def gate_test():
    print("\n(b Safety-gate test: 5 should pass, 5 should be blocked")
    run_gate(draft_gate, "Round 1: first draft of the gate")
    problems = run_gate(ft.confirm_bash, "Round 2: final gate (confirm_bash)")
    print("\nConfirmation contract")
    checks = [
        ("destructive + auto_approve=True is still blocked",
         not ft.confirm_bash("rm -fr build", auto_approve=True)["allowed"]),
        ("destructive + confirmed=True is allowed",
         ft.confirm_bash("rm -fr build", confirmed=True)["allowed"]),
        ("is_destructive returns a boolean",
         ft.is_destructive("rm -fr build") is True and ft.is_destructive("ls") is False),
    ]
    for label, passed in checks:
        print(" ", "ok" if passed else "FAIL", "|", label)
    print("\nFINAL:", "PASS" if problems == 0 and all(c[1] for c in checks) else "FAIL")


if __name__ == "__main__":
    try:
        integration_test()
    except Exception as e:
        print("integration test could not run:", e)
    gate_test()