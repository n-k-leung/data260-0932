import csv
import json
import os
import agent

VERIFY_SEED = 260932
ATTEMPTS_PER_CASE = 7
TEMPERATURE = 0.7
RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raw")
PROBLEM_KINDS = ["malformed_arguments", "unknown_tool", "text_when_tool_required"]
FAILURE_TYPES = PROBLEM_KINDS + ["lost_multi_step_chain"]

def classify(result, case):
    problems = [e["kind"] for e in result["events"] if e["kind"] in PROBLEM_KINDS]
    lost = not agent.chain_is_complete(result["tool_calls"], case["min_calls"])
    if problems:
        before = problems[0]
    elif lost:
        before = "lost_multi_step_chain"
    else:
        before = None

    if result["stop_reason"] == "repair_failed":
        after = problems[-1]
    elif lost:
        after = "lost_multi_step_chain"
    else:
        after = None
    return before, after

def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    print("raw files go to:", os.path.abspath(RAW_DIR))

    attempts = []
    number = 0
    for case in agent.load_cases():
        for _ in range(ATTEMPTS_PER_CASE):
            number += 1
            seed = VERIFY_SEED + number
            options = {"seed": seed, "temperature": TEMPERATURE, "num_ctx": 8192}
            agent.log("attempt " + str(number) + " | case " + case["id"] + " | seed " + str(seed))
            result = agent.run_agent(case["prompt"], require_tool=True, options=options)
            before, after = classify(result, case)
            attempts.append({
                "attempt": number,
                "case_id": case["id"],
                "seed": seed,
                "tools_called": "|".join(c["name"] for c in result["tool_calls"]),
                "total_tool_calls": result["total_tool_calls"],
                "repairs_used": sum(1 for e in result["events"] if e["kind"] in PROBLEM_KINDS),
                "stop_reason": result["stop_reason"],
                "failure_before_repair": before,
                "failure_after_repair": after,
            })
    summary = []
    for stage, key in [("before repair", "failure_before_repair"),
        ("after repair", "failure_after_repair")]:
        failures = [a[key] for a in attempts]
        good = failures.count(None)
        row = {"stage": stage, "attempts": len(attempts), "well_formed": good,
               "rate_percent": round(100 * good / len(attempts), 1)}
        for kind in FAILURE_TYPES:
            row[kind] = failures.count(kind)
        summary.append(row)

    write_csv(os.path.join(RAW_DIR, "reliability_attempts.csv"), attempts)
    with open(os.path.join(RAW_DIR, "reliability_attempts.json"), "w", encoding="utf-8") as f:
        json.dump(attempts, f, indent=2)
    write_csv(os.path.join(RAW_DIR, "reliability_summary.csv"), summary)

    lines = [
        "| Stage | Attempts | Well-formed | Rate | Malformed args | Unknown tool "
        "| Text instead of tool | Lost chain |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in summary:
        lines.append("| " + r["stage"] + " | " + str(r["attempts"]) + " | " + str(r["well_formed"])
            + " | " + str(r["rate_percent"]) + "% | " + str(r["malformed_arguments"])
            + " | " + str(r["unknown_tool"]) + " | " + str(r["text_when_tool_required"])
            + " | " + str(r["lost_multi_step_chain"]) + " |")
    with open(os.path.join(RAW_DIR, "part2_tables.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    agent.log("\n" + "\n".join(lines))


if __name__ == "__main__":
    main()