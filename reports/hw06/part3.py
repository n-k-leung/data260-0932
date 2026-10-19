import csv
import json
import os
import statistics
import time
from datetime import datetime
import requests
import yaml

URL = "http://localhost:8032/api/chat"
REPORT_DIR = os.getenv("REPORT_DIR", os.path.join(os.path.dirname(__file__)))
RAW_DIR = os.path.join(REPORT_DIR, "raw")
PROBE_FILE = os.path.join(REPORT_DIR, "memory_probes.yaml")
RUNS = [
    ("N4", 4, "none"),
    ("N12", 12, "none"),
    ("N30", 30, "none"),
    ("COMPRESS", 12, "compress"),
]
#facts planted at turns 1, 10, 18, 25 and 29
CONVERSATION = [
    "Hi, my name is test and I work at a bank called Northwind Bank as a security analyst.",
    "What does CVSS stand for?",
    "Explain SQL injection in two sentences.",
    "What is the difference between a vulnerability and an exploit?",
    "What is a CVE identifier?",
    "Give me one tip for validating user input.",
    "What does XSS stand for?",
    "Explain what a patch window is.",
    "What is a zero-day?",
    "The login service is owned by our team lead, Marcus Reed.",
    "What is the principle of least privilege?",
    "Explain two-factor authentication briefly.",
    "What is a dependency scanner?",
    "Why do we keep an audit log?",
    "What is a denial of service attack?",
    "Explain what hashing a password means.",
    "What is a security advisory?",
    "Our patch deadline for critical issues is 7 days.",
    "What does severity mean in a vulnerability report?",
    "Explain what a CORS policy does.",
    "What is rate limiting?",
    "Why should we avoid storing secrets in code?",
    "What is a penetration test?",
    "Explain session expiration in one paragraph.",
    "The vendor for our reports page is Acme Corp.",
    "What is an SBOM?",
    "Explain what a reverse proxy does.",
    "What is the difference between authentication and authorization?",
    "Please always answer me in bullet points from now on.",
    "Give me one last tip about reviewing logs.",
]
#pricing
INPUT_PRICE_PER_M = 1.0 # dollars per million tokens
OUTPUT_PRICE_PER_M = 5.0
CONVERSATIONS = 10000
TURNS = 30

def log(text):
    print(datetime.now().strftime("%H:%M:%S"), text, flush=True)

def send(user_id, session_id, message, n, policy, label):
    body = {"user_id": user_id, "session_id": session_id, "message": message,"short_term_n": n, "policy": policy, "run_label": label}
    r = requests.post(URL, json=body, timeout=900)
    if not r.ok:
        print(f"API ERROR: {r.status_code}")
        r.raise_for_status()
    return r.json()

def score_answer(answer, keywords):
    text = answer.lower()
    matched = 0
    for kw in keywords:
        options = kw.lower().split("|")
        if any(opt in text for opt in options):
            matched += 1
    return 1 + round(4 * matched / len(keywords)), matched

def run_one(label, n, policy, probes):
    stamp = int(time.time())
    #new user_id and session_id for every run sot that no mem carries over between runs
    user_id = "exp_" + label +"_"+ str(stamp)
    session_id = label + "-session-" + str(stamp)
    log(f" run {label}: SHORT_TERM_N={n}, policy={policy}")

    turn_rows = []
    for turn, message in enumerate(CONVERSATION, start=1):
        data = send(user_id, session_id, message, n, policy, label)
        m = data["metrics"]
        turn_rows.append({"run": label, "turn": turn, "short_term_n": n, "policy": policy, ** m})
        log(f"{label} turn {turn}/30 prompt={m['prompt_tokens']}"
            f"completion={m['completion_tokens']} latency={m['latency_ms']}ms")

    probe_results = []
    for p in probes: #5 probe questions are asked in the same session after the run
        data = send(user_id, session_id, p["question"], n, policy, label + "_probe")
        score, matched = score_answer(data["reply"], p["expected_keywords"])
        probe_results.append({"run": label, "probe_id": p["id"], "question": p["question"],
            "expected": p["expected_answer"], "answer": data["reply"],
            "matched_keywords": matched, "auto_score": score})
        log(f"{label} probe {p['id']} score={score}")

    summary={
        "setting": label, "short_term_n": n, "policy": policy,
        "mean_prompt_tokens": round(statistics.mean(r["prompt_tokens"] for r in turn_rows), 1),
        "mean_completion_tokens": round(statistics.mean(r["completion_tokens"] for r in turn_rows), 1),
        "mean_latency_ms": round(statistics.mean(r["latency_ms"] for r in turn_rows)),
        "probe_quality": round(statistics.mean(r["auto_score"] for r in probe_results), 2),
    }
    return turn_rows, probe_results, summary

def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows (rows)
        
def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    with open(PROBE_FILE, encoding="utf-8") as f:
        probes = yaml.safe_load(f)["probes"]

    all_turns, all_probes, summaries = [], [], []
    for label, n, policy in RUNS:
        turns, probe_results, summary = run_one(label, n, policy, probes)
        all_turns += turns
        all_probes += probe_results
        summaries.append (summary)

    write_csv(os.path.join(RAW_DIR, "turn_metrics.csv"), all_turns)
    with open(os.path.join(RAW_DIR, "probe_scores.json"), "w", encoding="utf-8") as f:
        json.dump(all_probes, f, indent=2)
    write_csv(os.path.join(RAW_DIR, "summary_results.csv"), summaries)

    #cost of 10,000 30-turn conversations
    cost_rows = []
    for s in summaries:
        input_tokens = s["mean_prompt_tokens"] * TURNS * CONVERSATIONS
        output_tokens = s["mean_completion_tokens"] * TURNS * CONVERSATIONS
        cost = input_tokens / 1e6 * INPUT_PRICE_PER_M + output_tokens / 1e6 * OUTPUT_PRICE_PER_M
        cost_rows.append({"setting": s["setting"], "probe_quality": s["probe_quality"],
            "input_tokens": int(input_tokens), "output_tokens": int(output_tokens),
            "cost_usd": round(cost, 2)})
    top_quality = max(r["probe_quality"] for r in cost_rows)
    good_enough = [r for r in cost_rows if r["probe_quality"] >= top_quality - 0.5]
    best = min(good_enough, key=lambda r: r["cost_usd"])["setting"]
    worst = max(cost_rows, key=lambda r: r["cost_usd"])["setting"]
    for r in cost_rows:
        r["role"] ="BEST" if r["setting"] == best else ("WORST" if r["setting"] == worst else "")
    write_csv(os.path.join(RAW_DIR, "cost_estimate.csv"), cost_rows)

    lines = ["| Setting | Mean prompt tokens/turn | Mean latency (ms) | Probe quality (1-5) |",
        "| --- | --- | --- | --- |"]
    for s in summaries:
        lines.append(f"| {s['setting']} | {s['mean_prompt_tokens']} | {s['mean_latency_ms']} | {s['probe_quality']} |")
    base = next(s for s in summaries if s["setting"] == "N12")
    comp = next(s for s in summaries if s["setting"] == "COMPRESS")
    saved = (base["mean_prompt_tokens"] - comp["mean_prompt_tokens"]) / base["mean_prompt_tokens"] * 100
    lines += ["", f"Compression vs N12: token savings = {saved :.1f}%,"
        f"probe quality change = {comp[ 'probe_quality'] - base['probe_quality']:+.2f}",
        "", f"Cost of {CONVERSATIONS} x {TURNS}-turn conversations"
        f"(input ${INPUT_PRICE_PER_M}/M, output ${OUTPUT_PRICE_PER_M}/M):",
        "| Setting | Probe quality | Input tokens | Output tokens | Cost (USD) | Role |",
        "| --- | --- | --- | --- | --- | --- |"]
    for r in cost_rows:
        lines.append(f"| {r['setting']} | {r['probe_quality']} | {r['input_tokens']:,} |"
            f"{r[ 'output_tokens']:,} | ${r['cost_usd']} | {r['role']} |")
    with open(os.path.join(RAW_DIR, "part3_tables.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log("\n"+ "\n".join(lines))

if __name__ == "__main__":
    main()
