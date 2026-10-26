import json
import agent
import tool_part4

# fake tool runner so no database is needed
tool_part4.execute_tool = lambda name, inputs: json.dumps({"ok": True, "data": {"id": 1}, "error": None})
passed = 0
total = 0

def check(label, condition):
    global passed, total
    total += 1
    passed += 1 if condition else 0
    print(("PASS - " if condition else "FAIL - ") + label)

def call(name, arguments):
    return {"content": "", "tool_calls": [{"name": name, "arguments": arguments}]}


def text(words):
    return {"content": words, "tool_calls": []}

def scripted(replies, seen=None):
    items = list(replies)
    def model_fn(messages):
        if seen is not None:
            seen.append(messages[-1]["content"])
        return items.pop(0)
    return model_fn

good = call("get_vulnerability", {"vuln_id": 1})

#unknown tool
seen = []
r = agent.run_agent("q", model_fn=scripted([call("find_bug", {}), good, text("done")], seen))
check("unknown tool is repaired", r["stop_reason"] == "final_answer" and r["total_tool_calls"] == 1)
check("reprompt names the problem", "unknown tool 'find_bug'" in seen[1])

#arguments prob
bad = call("get_vulnerability", {"vuln_id": "one"})
r = agent.run_agent("q", model_fn=scripted([bad, good, text("done")]))
kinds = [e["kind"] for e in r["events"]]
check("malformed arguments are repaired", kinds[0] == "malformed_arguments" and r["stop_reason"] == "final_answer")

#missing or unexpected arguments
r = agent.run_agent("q", model_fn=scripted([call("get_vulnerability", {}), good, text("ok")]))
check("missing argument is caught", r["events"][0]["kind"] == "malformed_arguments")
r = agent.run_agent("q", model_fn=scripted([call("count_by_severity", {"x": 1}), good, text("ok")]))
check("unexpected argument is caught", r["events"][0]["kind"] == "malformed_arguments")

#text when a tool was required
r = agent.run_agent("q", model_fn=scripted([text("I guess 5"), good, text("ok")]), require_tool=True)
check("text instead of tool is repaired", r["events"][0]["kind"] == "text_when_tool_required" and r["total_tool_calls"] == 1)

#repair fails twice in a row
r = agent.run_agent("q", model_fn=scripted([call("nope", {}), call("nope", {})]))
check("failed repair stops cleanly", r["stop_reason"] == "repair_failed" and r["total_tool_calls"] == 0)

#hard ceiling
r = agent.run_agent("q", model_fn=scripted([good] * 5), max_steps=3)
check("max_steps ceiling stops the loop", r["stop_reason"] == "max_steps_reached" and r["total_tool_calls"] == 3)

def crashing(name, inputs):
    raise RuntimeError("database is down")


tool_part4.execute_tool = crashing
r = agent.run_agent("q", model_fn=scripted([good, text("sorry")]))
check("tool crash does not crash the agent", r["stop_reason"] == "final_answer" and r["tool_calls"][0]["ok"] is False)

print(str(passed) + "/" + str(total) + " tests passed")