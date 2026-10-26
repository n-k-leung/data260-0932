import agent
import tool_part4

for case in agent.load_cases():
    print("\nTask " + case["id"] + ": " + case["name"])
    print("USER:", case["prompt"])
    result = agent.run_agent(case["prompt"], require_tool=True)
    used = [call["name"] for call in result["tool_calls"]]
    done = agent.chain_is_complete(result["tool_calls"], case["min_calls"])
    print("tools used:", used)
    print("AGENT:", result["final_answer"])
    enough = result["total_tool_calls"] >= 2 and done
    print("chacking more than 2 tool calls with just one prompt:", "PASS" if enough else "FAIL")

print("\nError recovery: nonexistent id")
print("execute_tool directly:", tool_part4.execute_tool("get_vulnerability", {"vuln_id": 999999}))
result = agent.run_agent(
    "Show me the full details of vulnerability id 999999.", require_tool=True
)
print("AGENT:", result["final_answer"])
finished = result["stop_reason"] == "final_answer"
print("Check if agent answered without crashing:", "PASS" if finished else "FAIL")