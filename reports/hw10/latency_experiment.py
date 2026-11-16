import glob
import json
import os
import time
import pandas as pd
from semantic_cache import SemanticResponseCache
from traced_request import HERE, make_evaluator, run_request

RAW_DIR = os.path.join(HERE, "raw")
SPANS_DIR = os.path.join(RAW_DIR, "spans")

PACKAGES = [
    ("lodash", "CVE-2021-23337"), ("lodash", "CVE-2019-10744"), ("lodash", "CVE-2020-28500"),
    ("requests", "CVE-2018-18074"), ("requests", "CVE-2023-32681"), ("log4j-core", "CVE-2021-44228"),
    ("log4j-core", "CVE-2021-45046"), ("axios", "CVE-2021-3749"), ("semver", "CVE-2022-25883"),
    ("minimist", "CVE-2020-7598"), ("jsonwebtoken", "CVE-2022-23529"), ("express", "CVE-2024-29041"),
    ("urllib3", "CVE-2023-43804"), ("Jinja2", "CVE-2024-22195"), ("PyYAML", "CVE-2020-14343"),
    ("Pillow", "CVE-2023-50447"), ("node-fetch", "CVE-2022-0235"), ("tar", "CVE-2021-32803"),
    ("moment", "CVE-2022-24785"), ("follow-redirects", "CVE-2022-0155"), ("ws", "CVE-2024-37890"),
    ("braces", "CVE-2024-4068"), ("cryptography", "CVE-2023-50782"), ("Django", "CVE-2024-27351"),
    ("Werkzeug", "CVE-2023-25577"),
]
QUESTIONS = ([f"Which version of {package} fixes {cve}?" for package, cve in PACKAGES] + [f"What type of vulnerability is {cve} in {package}?" for package, cve in PACKAGES])

TABLE_ROWS = [
    ("Cache lookup", ["cache_lookup"]),
    ("Planner", ["planner"]),
    ("Writer", ["writer"]),
    ("Reviewer", ["reviewer"]),
    ("Queue wait (total)", ["inbox", "tasks", "drafts", "final"]),
    ("Evaluation", ["evaluator"]),
]

def load_spans(trace_ids):
    rows = []
    for path in glob.glob(os.path.join(SPANS_DIR, "*.jsonl")):
        with open(path) as f:
            for line in f:
                if line.strip():
                    span = json.loads(line)
                    if span["trace_id"] in trace_ids:
                        rows.append(span)
    spans = pd.DataFrame(rows)
    spans["start_time"] = pd.to_datetime(spans["start_time"])
    spans["end_time"] = pd.to_datetime(spans["end_time"])
    return spans

def main():
    cache = SemanticResponseCache()
    cache.clear()
    evaluator = make_evaluator()

    results = []
    for number, question in enumerate(QUESTIONS, start=1):
        print(f"\nRequest {number} of {len(QUESTIONS)}")
        results.append(run_request(question, cache, evaluator, store_answer=False))

    time.sleep(2)
    trace_ids = [r["trace_id"] for r in results]
    spans = load_spans(trace_ids)
    lookups = spans[spans["stage"] == "cache_lookup"]
    misses = (lookups["cache"] == "miss").sum()
    failed_ids = set(spans[spans["status"] == "error"]["trace_id"]) | {r["trace_id"] for r in results if r["status"] != "ok"}
    print(f"\nConfirmed cache misses: {misses} of {len(results)} (hits: {(lookups['cache'] == 'hit').sum()})")
    print(f"Failed requests (left out of the latency numbers): {len(failed_ids)}")
    good = spans[~spans["trace_id"].isin(failed_ids) & spans["trace_id"].isin(lookups[lookups["cache"] == "miss"]["trace_id"])]
    per_trace = []
    for trace_id, trace in good.groupby("trace_id"):
        row = {"trace_id": trace_id}
        for stage, stage_spans in trace.groupby("stage"):
            row[stage] = stage_spans["duration_ms"].sum()
        row["end_to_end"] = (trace["end_time"].max() - trace["start_time"].min()).total_seconds() * 1000
        per_trace.append(row)
    per_trace = pd.DataFrame(per_trace).fillna(0)
    per_trace.to_csv(os.path.join(RAW_DIR, "latency_experiment_traces.csv"), index=False)
    
    table = []
    for name, stages in TABLE_ROWS:
        values = per_trace[[s for s in stages if s in per_trace.columns]].sum(axis=1)
        table.append({
            "Stage": name,
            "p50 (ms)": round(values.quantile(0.50), 1),
            "p95 (ms)": round(values.quantile(0.95), 1),
            "% of cache-miss end-to-end": round(values.mean() / per_trace["end_to_end"].mean() * 100, 1),
        })
    table = pd.DataFrame(table)
    table.to_csv(os.path.join(RAW_DIR, "latency_table.csv"), index=False)

    print(f"\nStage latency over {len(per_trace)} cache-miss requests")
    print(table.to_string(index=False))
    print(f"End-to-end: p50 {per_trace['end_to_end'].quantile(0.5):.1f} ms, p95 {per_trace['end_to_end'].quantile(0.95):.1f} ms")
    print(f"Time between spans (not in any stage): {100 - table['% of cache-miss end-to-end'].sum():.1f}% of end-to-end")
    dominant = table.sort_values("% of cache-miss end-to-end", ascending=False).iloc[0]
    print(f"Dominant contributor: {dominant['Stage']} ({dominant['% of cache-miss end-to-end']}% of end-to-end)")

if __name__ == "__main__":
    main()
