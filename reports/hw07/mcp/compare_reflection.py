import csv
import json
import os
import sys
import time
import agent
import reflexion
import tool_part4

VERIFY_SEED = 260932
RUNS_PER_TASK = 5
TEMPERATURE = 0.7
RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raw")

def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

def average(rows, key):
    return round(sum(r[key] for r in rows) / len(rows), 1)

def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    print("raw files go to:", os.path.abspath(RAW_DIR))

    rows = []
    details = []
    number = 0
    for case in agent.load_cases():
        expected = reflexion.load_expected(case)
        for _ in range(RUNS_PER_TASK):
            number += 1
            seed = VERIFY_SEED + number
            options = {"seed": seed, "temperature": TEMPERATURE, "num_ctx": 8192}
            agent.log("run " + str(number) + " | task " + case["id"] + " | seed " + str(seed))

            # ---- original loop (Part 2)
            start = time.perf_counter()
            original = agent.run_agent(case["prompt"], require_tool=True, options=options)
            original_ms = round((time.perf_counter() - start) * 1000)
            rejected = bool(reflexion.verify(case, original))
            correct = reflexion.is_correct(case, original, expected)
            rows.append({
                "loop": "original", "task": case["id"], "run": number, "seed": seed,
                "success": int(correct),
                "unsupported_claims": len(reflexion.find_unsupported_claims(original)),
                "retried": int(any(e["kind"] in reflexion.PROBLEM_KINDS
                                   for e in original["events"])),
                "tool_calls": original["total_tool_calls"],
                "tokens": original["total_tokens"], "latency_ms": original_ms,
                "false_rejections": int(rejected and correct),
                "stop_reason": original["stop_reason"],
            })
            refl = reflexion.run_reflexion(
                case, "student", "run" + str(number), options=options,
                first_result=original, first_latency_ms=original_ms)
            final = refl["final_result"]
            false_rejections = sum(
                1 for a in refl["attempts"]
                if a["verifier_problems"] and reflexion.is_correct(case, a["result"], expected))
            rows.append({
                "loop": "reflexion", "task": case["id"], "run": number, "seed": seed,
                "success": int(reflexion.is_correct(case, final, expected)),
                "unsupported_claims": len(reflexion.find_unsupported_claims(final)),
                "retried": int(refl["retries"] > 0),
                "tool_calls": refl["tool_calls"], "tokens": refl["tokens"],
                "latency_ms": refl["latency_ms"], "false_rejections": false_rejections,
                "stop_reason": refl["stop_reason"],
            })
            details.append({
                "task": case["id"], "run": number, "seed": seed,
                "original": {"final_answer": original["final_answer"],
                    "verifier_problems": reflexion.verify(case, original)},
                "reflexion": {"stop_reason": refl["stop_reason"],
                    "attempts": [{k: v for k, v in a.items() if k != "result"}
                                for a in refl["attempts"]]},
            })

    table = ["| Metric | Original loop | Reflexion loop |", "|---|---|---|"]
    per_loop = {name: [r for r in rows if r["loop"] == name] for name in ["original", "reflexion"]}

    def cell(name, metric):
        part = per_loop[name]
        total = len(part)
        if metric == "Task success":
            wins = sum(r["success"] for r in part)
            return str(wins) + "/" + str(total) + " (" + str(round(100 * wins / total)) + "%)"
        if metric == "Unsupported claims":
            return str(sum(r["unsupported_claims"] for r in part)) + " total"
        if metric == "Retry rate":
            return str(round(100 * sum(r["retried"] for r in part) / total)) + "% of runs"
        if metric == "Tool calls":
            return str(average(part, "tool_calls")) + " per run"
        if metric == "Tokens":
            return str(average(part, "tokens")) + " per run"
        if metric == "Latency (ms)":
            return str(average(part, "latency_ms")) + " per run"
        return str(sum(r["false_rejections"] for r in part)) 

    for metric in ["Task success", "Unsupported claims", "Retry rate", "Tool calls",
            "Tokens", "Latency (ms)", "Verifier false rejections"]:
        table.append("| " + metric + " | " + cell("original", metric)
            + " | " + cell("reflexion", metric) + " |")
    stops = [r["stop_reason"] for r in per_loop["reflexion"]]
    table.append("")
    table.append("Reflexion stop reasons: success=" + str(stops.count("success"))
        + ", budget_exhausted=" + str(stops.count("budget_exhausted"))
        + ", human_review=" + str(stops.count("human_review")))

    write_csv(os.path.join(RAW_DIR, "reflexion_runs.csv"), rows)
    with open(os.path.join(RAW_DIR, "reflexion_runs.json"), "w", encoding="utf-8") as f:
        json.dump(details, f, indent=2)
    stored = [item for items in reflexion.REFLECTION_STORE.values() for item in items]
    with open(os.path.join(RAW_DIR, "reflections.json"), "w", encoding="utf-8") as f:
        json.dump(stored, f, indent=2)
    with open(os.path.join(RAW_DIR, "part3_table.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(table))
    agent.log("\n" + "\n".join(table))
    print("reflections stored:", len(stored))
    print("rejected answers to read for the false-rejection note:")
    for r in rows:
        if r["false_rejections"]:
            print("  loop=" + r["loop"] + " task=" + r["task"] + " run=" + str(r["run"]))

def demo():
    rows = [
        {"id": 1, "package_name": "nodejs", "severity": "high",
         "vul_code": "CVE-2026-0001", "vendor_id": 1},
        {"id": 2, "package_name": "nodejs", "severity": "low",
         "vul_code": "CVE-2026-0002", "vendor_id": 1},
        {"id": 3, "package_name": "nodejs", "severity": "critical",
         "vul_code": "CVE-2026-0003", "vendor_id": 2},
    ]

    def fake_tool(name, inputs):
        if name == "search_vulnerabilities":
            data = rows
        else:
            data = [r for r in rows if r["id"] == inputs["vuln_id"]][0]
        return json.dumps({"ok": True, "data": data, "error": None})

    tool_part4.execute_tool = fake_tool

    def call(name, arguments):
        return {"content": "", "tool_calls": [{"name": name, "arguments": arguments}]}

    def text(words):
        return {"content": words, "tool_calls": []}

    replies = [
        #not getting first result
        call("search_vulnerabilities", {"package_name": "nodejs"}),
        call("get_vulnerability", {"vuln_id": 3}),
        text("The record is CVE-2026-0003 and its severity is critical."),
        #wiith reflection
        call("search_vulnerabilities", {"package_name": "nodejs"}),
        call("get_vulnerability", {"vuln_id": 1}),
        text("The first result is CVE-2026-0001 and its severity is high."),
    ]

    def scripted_model(messages):
        return replies.pop(0)

    def scripted_reflection(prompt):
        return ("I fetched id 3, but the task asked for the first search result (id 1)."
                " Next time call get_vulnerability with the id of the first result."), 0

    case = agent.load_cases()[0]
    outcome = reflexion.run_reflexion(
        case, "demo-user", "demo-run", model_fn=scripted_model,
        reflect_fn=scripted_reflection)
    stored = reflexion.get_reflections("demo-user", "demo-run")
    print("\nstop_reason:", outcome["stop_reason"], "| attempts:", len(outcome["attempts"]))
    print("\nSTORED REFLECTION WITH ITS EVIDENCE:")
    print(json.dumps(stored, indent=2))
    print("\nanother user sees:", reflexion.get_reflections("other-user", "demo-run"))
    os.makedirs(RAW_DIR, exist_ok=True)
    with open(os.path.join(RAW_DIR, "reflections_demo.json"), "w", encoding="utf-8") as f:
        json.dump(stored, f, indent=2)

if __name__ == "__main__":
    if "demo" in sys.argv:
        demo()
    else:
        main()