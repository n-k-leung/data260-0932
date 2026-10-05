import json
import time
import requests
import tool_part4
MODEL = "qwen3:8b" #check
SYSTEM_INSTRUCTIONS = """You are an assistant for an open source package vulnerability tracker.
You have three tools:
1. search_vulnerabilities - inputs: {"package_name": "<text, at least 3 characters>"}
2. get_vulnerability - inputs: {"vuln_id": <integer>}
3. count_by_severity - inputs: {"min_count": <integer, 0 or more>}

To call a tool, reply with ONLY a JSON object like this, and nothing else:
{"tool": "search_vulnerabilities", "inputs": {"package_name": "lodash"}}

If you already have enough information to answer the user, reply in plain
English instead (do not use any JSON in that case).
"""
def ask_ollama(prompt):
    body = {"model": MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0}}
    response = requests.post("http://localhost:11434/api/generate", json=body, timeout=120)
    return response.json() ["response"]

def try_parse_tool_call(reply):
    try:
        data = json.loads(reply)
    except ValueError:
        return None
    if isinstance(data, dict) and "tool" in data and "inputs" in data:
        return data["tool"], data["inputs"]
    return None

def run_agent(user_input, model_fn=None, max_steps=5, log_path="agent_runs.json1"):
    if model_fn is None:
        model_fn = ask_ollama
    conversation = SYSTEM_INSTRUCTIONS + "\nUser question: " + user_input + "\n"
    steps_log = []
    stop_reason = None
    final_answer = None
    step = 0
    while step < max_steps:
        step += 1
        reply = model_fn(conversation).strip()
        tool_call = try_parse_tool_call(reply)
        if tool_call is None:
            final_answer = reply
            stop_reason = "normal_completion"
            steps_log.append({"step": step, "tool": None, "inputs": None, "result": None, "model_reply": reply})
            break
        name, inputs = tool_call
        result = json.loads(tool_part4.execute_tool(name, inputs))
        steps_log.append({"step": step, "tool": name, "inputs": inputs, "result": result})
        if not result["ok"] and str(result["error"]).startswith("SAFETY:"):
            stop_reason = "safety_rule_block"
            final_answer = "I can't do that: " + str(result["error"])
            break
        conversation += "\nTool " + name + " returned "+ json.dumps(result) + "\n"
    if stop_reason is None:
        stop_reason = "max_steps_reached"
        final_answer = "Stopped after reaching the " + str(max_steps) + "-step limit."
    record = {
        "time": time.strftime("%Y-%m-%d %H:%M: %S"),
        "user_input": user_input,
        "steps": steps_log,
        "stop_reason": stop_reason,
        "final_answer": final_answer,
    }
    with open(log_path, "a") as f:
            f.write(json.dumps(record) + "\n")

    return {"final_answer": final_answer, "stop_reason": stop_reason, "steps": steps_log}



    