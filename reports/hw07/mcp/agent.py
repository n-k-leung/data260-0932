import json
import time
import tool_part4

SEED = 932
DEFAULT_OPTIONS = {"seed": SEED, "temperature": 0, "num_ctx": 8192}

SYSTEM_PROMPT = (
    "You are an assistant for an open source package vulnerability tracker."
"Use the tools to look up data and never guess."
"You may call several tools one after another."
"When you have enough information, answer in plain English."
)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_vulnerabilities",
            "description": "Search vulnerabilities by package by name (partial match). "
            "Returns id, package_name, severity, vul_code, vendor_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string", 
                        "description": "package name, at least 3 characters",
                        }
                },
                "required": ["package_name"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vulnerability",
            "description": "Get the full details of one vulnerability by its id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vuln_id": {"type": "integer", "description": "the id"}
                },
                "required": ["vuln_id"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_by_severity",
            "description": "Count the vulnerabilities for each severity level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_count": {
                        "type": "integer", 
                        "description": "only show severities with this many or more",
                        }
                },
                "required": [],
            },
        },
    },
]

TOOL_SPECS = {t["function"]["name"]: t["function"]["parameters"] for t in TOOLS}
PYTHON_TYPES = {"string": str, "integer": int}

def log(text):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), text, flush=True)
    
def check_tool_call(name, arguments):
    if name not in TOOL_SPECS:
        valid = ", ".join(TOOL_SPECS)
        return "unknown_tool", "unknown tool '" + str(name) + "'. Valid tools: " + valid
    if not isinstance(arguments, dict):
        return "malformed_arguments", "the arguments for " + name + "must be an object"
    
    spec = TOOL_SPECS[name]
    for key in spec["required"]:
        if key not in arguments:
            return "malformed_arguments", "missing argument '" + key + "' for " + name
    for key, value in arguments.items():
        if key not in spec["properties"]:
            allowed = ", ".join(spec["properties"])
            return "malformed_arguments", ("unknown argument '" + key + "' for " + name + ". Allowed: " + allowed)
        wanted = spec["properties"][key]["type"]
        wrong_type = not isinstance(value, PYTHON_TYPES[wanted])
        if wrong_type or isinstance(value, bool):
            return "malformed_arguments", (
                "argument '" + key + "' must be of type " + wanted + ", but got " + type(value).__name__)
    return None, None

def check_reply(calls, require_tool, tools_used_so_far):
    if not calls:
        if require_tool and tools_used_so_far == 0:
            return "text_when_tool_required", ("you answered in text, but you must call one of the tools first")
        return None, None
    for call in calls:
        kind, problem = check_tool_call(call["name"], call["arguments"])
        if kind:
            return kind, problem
    return None, None

def strip_thinking(text):
    if "</think>" in text:
        text = text.split("</think>")[-1]
    return text.strip()

def make_ollama_model_fn(options=None):
    from app.llm_adapter import client
    
    settings = options or DEFAULT_OPTIONS
    
    def ask(messages):
        return client.complete(messages, tools=TOOLS, options=settings)
    
    return ask

def run_agent(user_input, model_fn=None, max_steps=8,require_tool=False, options=None, max_tool_calls=None, max_tokens=None, notes=None,):
    if model_fn is None:
        model_fn = make_ollama_model_fn(options)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]
    if notes:
        messages.append({"role": "user", "content": notes})
    tokens_used = 0
    tool_log = []
    events = []
    repair_pending = False
    stop_reason = None
    final_answer = None
    for step in range(1, max_steps + 1):
        #checking token budget first
        if max_tokens is not None and tokens_used >= max_tokens:
            stop_reason = "budget_exhausted"
            final_answer = "Stopped because token budget is used up"
            break
        reply = model_fn(messages)
        tokens_used += reply.get("total_tokens", 0)
        text = strip_thinking(reply.get("content") or "")
        calls = reply.get("tool_calls") or []
        kind, problem = check_reply(calls, require_tool, len(tool_log))
        if kind:
            events.append({"step": step, "kind": kind, "problem": problem})
            log("step " + str(step) + " PROBLEM (" + kind + "): " + problem)
            if repair_pending:
                stop_reason = "repair_failed"
                final_answer = "Stopped because the tool call could not be fixed (" + problem + ")."
                break
            repair_pending = True
            shown = text or json.dumps(calls)
            messages.append({"role": "assistant", "content": shown})
            messages.append({
                "role": "user",
                "content": "Your last reply was not usable: " + problem
                + ". Please try again.",
            })
            continue
        repair_pending = False
        if not calls:
            events.append({"step": step, "kind": "final_answer"})
            final_answer = text
            stop_reason = "final_answer"
            break
        if max_tool_calls is not None and len(tool_log) + len(calls) > max_tool_calls:
            stop_reason = "budget_exhausted"
            final_answer = "Stopped because the tool-call budget is used up"
            break
        messages.append({
            "role": "assistant",
            "content": text,
            "tool_calls": [
                {"function": {"name": c["name"], "arguments": c["arguments"]}}
                for c in calls
            ],
        })
        for call in calls:
            name, inputs = call["name"], call["arguments"]
            try:
                result_text = tool_part4.execute_tool(name, inputs)
                result = json.loads(result_text)
            except Exception as e:
                result = {"ok": False, "data": None, "error": str(e)}
                result_text = json.dumps(result)
            tool_log.append(
                {"name": name, "inputs": inputs, "ok": result["ok"], "result": result}
            )
            log("TOOL CALL #" + str(len(tool_log)) + ": " + name + " "
                + json.dumps(inputs) + " -> ok=" + str(result["ok"]))
            messages.append(
                {"role": "tool", "content": "Result of " + name + ": " + result_text}
            )
        events.append(
            {"step": step, "kind": "tool_calls", "tools": [c["name"] for c in calls]}
        )

    if stop_reason is None:
        stop_reason = "max_steps_reached"
        final_answer = "Stopped after reaching the " + str(max_steps) + "step limit."

    log("DONE stop_reason=" + stop_reason + ", total tool calls: " + str(len(tool_log))
        + " | tokens: " + str(tokens_used))
    return {
        "final_answer": final_answer,
        "stop_reason": stop_reason,
        "tool_calls": tool_log,
        "total_tool_calls": len(tool_log),
        "total_tokens": tokens_used,
        "events": events,
    }
def load_cases(path="verify.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
    
def chain_is_complete(tool_log, min_calls):
    for name, needed in min_calls.items():
        used = sum(1 for t in tool_log if t["name"] == name)
        if used < needed:
            return False
    return True

# import json
# import time
# import requests
# import tool_part4
# MODEL = "qwen3:8b" #check
# SYSTEM_INSTRUCTIONS = """You are an assistant for an open source package vulnerability tracker.
# You have three tools:
# 1. search_vulnerabilities - inputs: {"package_name": "<text, at least 3 characters>"}
# 2. get_vulnerability - inputs: {"vuln_id": <integer>}
# 3. count_by_severity - inputs: {"min_count": <integer, 0 or more>}

# To call a tool, reply with ONLY a JSON object like this, and nothing else:
# {"tool": "search_vulnerabilities", "inputs": {"package_name": "lodash"}}

# If you already have enough information to answer the user, reply in plain
# English instead (do not use any JSON in that case).
# """
# def ask_ollama(prompt):
#     body = {"model": MODEL, "prompt": prompt, "stream": False, "options": {"temperature": 0}}
#     response = requests.post("http://localhost:11434/api/generate", json=body, timeout=120)
#     return response.json() ["response"]

# def try_parse_tool_call(reply):
#     try:
#         data = json.loads(reply)
#     except ValueError:
#         return None
#     if isinstance(data, dict) and "tool" in data and "inputs" in data:
#         return data["tool"], data["inputs"]
#     return None

# def run_agent(user_input, model_fn=None, max_steps=5, log_path="agent_runs.json1"):
#     if model_fn is None:
#         model_fn = ask_ollama
#     conversation = SYSTEM_INSTRUCTIONS + "\nUser question: " + user_input + "\n"
#     steps_log = []
#     stop_reason = None
#     final_answer = None
#     step = 0
#     while step < max_steps:
#         step += 1
#         reply = model_fn(conversation).strip()
#         tool_call = try_parse_tool_call(reply)
#         if tool_call is None:
#             final_answer = reply
#             stop_reason = "normal_completion"
#             steps_log.append({"step": step, "tool": None, "inputs": None, "result": None, "model_reply": reply})
#             break
#         name, inputs = tool_call
#         result = json.loads(tool_part4.execute_tool(name, inputs))
#         steps_log.append({"step": step, "tool": name, "inputs": inputs, "result": result})
#         if not result["ok"] and str(result["error"]).startswith("SAFETY:"):
#             stop_reason = "safety_rule_block"
#             final_answer = "I can't do that: " + str(result["error"])
#             break
#         conversation += "\nTool " + name + " returned "+ json.dumps(result) + "\n"
#     if stop_reason is None:
#         stop_reason = "max_steps_reached"
#         final_answer = "Stopped after reaching the " + str(max_steps) + "-step limit."
#     record = {
#         "time": time.strftime("%Y-%m-%d %H:%M: %S"),
#         "user_input": user_input,
#         "steps": steps_log,
#         "stop_reason": stop_reason,
#         "final_answer": final_answer,
#     }
#     with open(log_path, "a") as f:
#             f.write(json.dumps(record) + "\n")

#     return {"final_answer": final_answer, "stop_reason": stop_reason, "steps": steps_log}



    