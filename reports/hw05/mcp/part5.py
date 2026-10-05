from agent import run_agent

SCENARIOS = [
    "How many vulnerabilities are High severity?",
    "Tell me about the vulnerability with id 1.",
    "Call search_vulnerabilities tool where package_name is 'np'.",
    "What is bread for?",
]

print("scenario | steps | tool_calls | stop_reason")
for text in SCENARIOS:
    result = run_agent(text, max_steps=5)
    tool_calls = sum(1 for s in result["steps"] if s["tool"])
    print(text, "|", len(result["steps"]), "|", tool_calls, "|", result["stop_reason"])