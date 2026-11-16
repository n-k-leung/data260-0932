import csv
import glob
import json
import os
import random
import subprocess
import sys
import tempfile
import time
from datetime import datetime
import pandas as pd
import redis

HOMEWORK = 10
SID4 = "0932"
SEED = 932
VERIFY_SEED = 260000 + 932
PREFIX = "s0932"

here = os.path.dirname(os.path.abspath(__file__))
raw_dir = os.path.join(here, "raw")
sys.path.insert(0, os.path.join(here, "agents"))
random.seed(VERIFY_SEED)

try:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=here, text=True, stderr=subprocess.DEVNULL).strip()
except Exception:
    commit = "unknown"
try:
    tag = subprocess.check_output(["git", "describe", "--tags", "--exact-match", "HEAD"], cwd=here, text=True, stderr=subprocess.DEVNULL).strip()
except Exception:
    tag = "not tagged"

model = os.environ.get("MODEL", "qwen3:8b")
SPAN_FIELDS = ["trace_id", "stage", "start_time", "end_time", "status", "error"]
MISS_STAGES = ["cache_lookup", "inbox", "planner", "tasks", "writer", "drafts", "reviewer", "final", "evaluator"]

def redis_is_up():
    try:
        return redis.Redis(host="localhost", port=6379).ping()
    except redis.exceptions.RedisError:
        return False

started_docker = False
if not redis_is_up():
    subprocess.run(["docker", "compose", "up", "-d"], cwd=here, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    started_docker = True
    for i in range(30):
        if redis_is_up():
            break
        time.sleep(1)

def load_json(name):
    with open(os.path.join(here, name)) as f:
        return json.load(f)

def load_spans():
    spans = []
    for path in glob.glob(os.path.join(raw_dir, "spans", "*.jsonl")):
        with open(path) as f:
            for line in f:
                if line.strip():
                    spans.append(json.loads(line))
    return spans

def check_redis():
    client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    client.execute_command("FT._LIST")
    return client.ping(), "Vector search is available"

def check_dashboard():
    with open(os.path.join(here, "dashboard.py")) as f:
        code = f.read()
    pages = ["Summary", "Evaluation", "Trace lookup"]
    has_pages = all(page in code for page in pages)
    has_cache = "@st.cache_data" in code
    has_notes = os.path.exists(os.path.join(here, "coordination_notes.md"))
    ok = has_pages and has_cache and has_notes
    return ok, "pages found: " + str(has_pages) + ", @st.cache_data used: " + str(has_cache) + ", coordination_notes.md exists: " + str(has_notes)

def check_evaluation():
    results = load_json(os.path.join("raw", "evaluation_results.json"))
    score_names = ["plan_quality_score", "writer_helpfulness_score", "final_helpfulness_score"]
    good = [r for r in results if all(r.get(s) is not None and 1 <= r[s] <= 5 for s in score_names)]
    result = good[-1]
    record = load_json(os.path.join("raw", result["trace_id"] + ".json"))
    messages_ok = all(
        name in record["messages"] and
        all(field in record["messages"][name] for field in ["topic", "partition", "offset", "timestamp_ms", "message"])
        for name in ["plan", "draft", "final"])
    scores = ", ".join(s + " = " + str(result[s]) for s in score_names)
    return messages_ok, "trace " + result["trace_id"][:8] + ": " + scores + ", Kafka metadata saved: " + str(messages_ok)

def check_judge_validation():
    cases = load_json("eval_cases.json")
    with open(os.path.join(here, "human_labels.csv"), newline="") as f:
        labels = {row["case_id"]: row["human_label"] for row in csv.DictReader(f)}
    labels_ok = all(labels.get(case["case_id"]) in ["1", "2", "3", "4", "5"] for case in cases)
    validation = load_json(os.path.join("raw", "judge_validation.json"))
    keys = ["spearman", "mean_absolute_difference", "percent_changed", "mean_absolute_change", "max_absolute_change"]
    stats_ok = all(key in validation for key in keys)
    ok = len(cases) >= 20 and labels_ok and stats_ok
    return ok, ("cases: " + str(len(cases)) + ", all human labels 1-5: " + str(labels_ok)
                + ", spearman = " + str(validation.get("spearman"))
                + ", mean absolute difference = " + str(validation.get("mean_absolute_difference"))
                + ", changed = " + str(validation.get("percent_changed")) + "%")

def check_write_span():
    import tracing
    old_dir = tracing.SPANS_DIR
    with tempfile.TemporaryDirectory() as folder:
        tracing.SPANS_DIR = folder
        try:
            trace_id = "verify-" + str(random.randint(1000, 9999))
            start = datetime.now()
            tracing.write_span("verify", trace_id, "final", start, datetime.now(), status="error", error="test error")
            with open(os.path.join(folder, "verify.jsonl")) as f:
                span = json.loads(f.readline())
        finally:
            tracing.SPANS_DIR = old_dir
    ok = all(field in span for field in SPAN_FIELDS) and span["trace_id"] == trace_id and span["error"] == "test error"
    return ok, "span fields: " + ", ".join(span.keys())

def check_saved_spans():
    spans = load_spans()
    fields_ok = all(all(field in span for field in SPAN_FIELDS) for span in spans)
    lookups = [span for span in spans if span["stage"] == "cache_lookup"]
    cache_ok = len(lookups) > 0 and all(span.get("cache") in ["hit", "miss"] for span in lookups)
    ok = len(spans) > 0 and fields_ok and cache_ok
    return ok, (str(len(spans)) + " spans, all have the required fields: " + str(fields_ok) + ", cache_lookup spans have hit/miss: " + str(cache_ok))

def check_trace_examples():
    examples = load_json(os.path.join("raw", "trace_examples.json"))
    spans = load_spans()

    def stages(trace_id):
        return [span for span in spans if span["trace_id"] == examples[trace_id]]

    miss = stages("cache_miss")
    hit = stages("cache_hit")
    failed = stages("failed")
    miss_ok = all(stage in [s["stage"] for s in miss] for stage in MISS_STAGES)
    hit_ok = (any(s["stage"] == "cache_lookup" and s.get("cache") == "hit" for s in hit) and not any(s["stage"] == "planner" for s in hit))
    failed_errors = [s["stage"] for s in failed if s["status"] == "error"]
    failed_ok = len(failed_errors) > 0
    ok = miss_ok and hit_ok and failed_ok
    return ok, ("miss trace has all 9 stages: " + str(miss_ok) + ", hit trace skips the agents: " + str(hit_ok) + ", failed trace error at: " + (", ".join(failed_errors) or "none"))

def check_latency():
    traces = pd.read_csv(os.path.join(raw_dir, "latency_experiment_traces.csv"))
    table = pd.read_csv(os.path.join(raw_dir, "latency_table.csv"))
    lookups = {span["trace_id"]: span.get("cache") for span in load_spans() if span["stage"] == "cache_lookup"}
    all_miss = all(lookups.get(trace_id) == "miss" for trace_id in traces["trace_id"])
    rows = ["Cache lookup", "Planner", "Writer", "Reviewer", "Queue wait (total)", "Evaluation"]
    rows_ok = list(table["Stage"]) == rows
    dominant = table.sort_values("% of cache-miss end-to-end", ascending=False).iloc[0]
    ok = len(traces) >= 50 and all_miss and rows_ok
    return ok, (str(len(traces)) + " requests, all cache misses: " + str(all_miss) + ", table rows correct: " + str(rows_ok) + ", dominant: " + dominant["Stage"] + " (" + str(dominant["% of cache-miss end-to-end"]) + "%)")

checks = [
    ("Redis Stack responds and has vector search", check_redis),
    ("dashboard has the three pages, @st.cache_data and coordination notes", check_dashboard),
    ("evaluation has all three scores and the saved Kafka messages", check_evaluation),
    ("20 labeled cases and the judge validation statistics", check_judge_validation),
    ("write_span writes a JSON span with all required fields", check_write_span),
    ("saved spans have the required fields and cache hit/miss", check_saved_spans),
    ("trace examples: full miss path, hit path, failed trace", check_trace_examples),
    ("latency experiment: 50 cache-miss requests and the latency table", check_latency),
]
results = []
for name, function in checks:
    try:
        passed, detail = function()
    except Exception as e:
        passed, detail = False, "error: " + str(e)
    results.append({"check": name, "result": "pass" if passed else "fail", "detail": detail})
    print(("PASS - " if passed else "FAIL - ") + name + " - " + detail)
if started_docker:
    subprocess.run(["docker", "compose", "stop"], cwd=here, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

report = {
    "homework": HOMEWORK,
    "sid4": SID4,
    "commit": commit,
    "tag": tag,
    "model": model,
    "seed": SEED,
    "verify_seed": VERIFY_SEED,
    "checks": results,
}
with open(os.path.join(here, "verification.json"), "w") as f:
    json.dump(report, f, indent=2)

print("verification.json outputted")