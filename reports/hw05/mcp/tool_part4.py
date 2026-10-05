import json
import vul

ALLOWED_TOOLS = ["search_vulnerabilities", "get_vulnerability", "count_by_severity"]
def violates_safety_rule(name, inputs):
    if name == "search_vulnerabilities":
        term = str(inputs.get("package_name","")).strip()
        if 0 < len(term) < 3:
            return ("SAFETY: search term must be at least " + str(3) + "characters (got \"" + term + "\")")
    return None

def execute_tool(name, inputs):
    if name not in ALLOWED_TOOLS:
        result = vul.envelope(False, error="unknown tool: " + str(name))
        return json.dumps(result)
    block_reason = violates_safety_rule(name, inputs)
    if block_reason:
        return json.dumps(vul.envelope(False, error=block_reason))
    tool_function = getattr(vul, name)
    try:
        result = tool_function( ** inputs)
    except Exception as e:
        result = vul.envelope(False, error=str(e))

    return json.dumps (result)

if __name__ == "__main__":
    print("Allowed call (3+ characters):")
    print(execute_tool("search_vulnerabilities", {"package_name": "lodash"}))
    print("\nBlocked call (too short, violates the safety rule):")
    print(execute_tool("search_vulnerabilities", {"package_name": "ab"}))