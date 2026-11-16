import glob
import json
import os
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(HERE, "raw")
SPANS_DIR = os.path.join(RAW_DIR, "spans")
NOTES_FILE = os.path.join(HERE, "coordination_notes.md")
STAGE_ORDER = ["cache_lookup", "inbox", "planner", "tasks", "writer", "drafts", "reviewer", "final", "evaluator"]


#Loading data

@st.cache_data(ttl=30)
def load_spans():
    rows = []
    for path in glob.glob(os.path.join(SPANS_DIR, "*.jsonl")):
        with open(path) as f:
            rows += [json.loads(line) for line in f if line.strip()]
    if not rows:
        return pd.DataFrame()
    spans = pd.DataFrame(rows)
    spans["start_time"] = pd.to_datetime(spans["start_time"])
    spans["end_time"] = pd.to_datetime(spans["end_time"])
    spans["duration_ms"] = (spans["end_time"] - spans["start_time"]).dt.total_seconds() * 1000
    return spans

@st.cache_data(ttl=30)
def load_json(file_name):
    path = os.path.join(RAW_DIR, file_name)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)

@st.cache_data(ttl=30)
def load_csv(file_name):
    path = os.path.join(RAW_DIR, file_name)
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)

def summarize_traces(spans):
    rows = []
    for trace_id, trace in spans.groupby("trace_id"):
        lookup = trace[trace["stage"] == "cache_lookup"]
        cache = lookup["cache"].iloc[0] if "cache" in trace and len(lookup) > 0 else "unknown"
        start = trace["start_time"].min()
        end = trace["end_time"].max()
        rows.append({
            "trace_id": trace_id,
            "start_time": start,
            "cache": cache,
            "failed": (trace["status"] == "error").any(),
            "total_ms": (end - start).total_seconds() * 1000,
        })
    return pd.DataFrame(rows)


#Summary

def summary_page():
    st.header("Summary")
    spans = load_spans()
    if spans.empty:
        st.info("No data yet: raw/spans/*.jsonl is written by the Part 4 tracing.")
        return

    #time window for every metric on this page
    window = st.sidebar.selectbox("Time window", ["All data", "Last 24 hours", "Last 1 hour"])
    if window == "Last 24 hours":
        spans = spans[spans["start_time"] >= datetime.now() - timedelta(hours=24)]
    elif window == "Last 1 hour":
        spans = spans[spans["start_time"] >= datetime.now() - timedelta(hours=1)]
    if spans.empty:
        st.info(f"No requests in the selected time window ({window}).")
        return

    traces = summarize_traces(spans)
    total = len(traces)
    hits = (traces["cache"] == "hit").sum()
    misses = (traces["cache"] == "miss").sum()
    failed = traces["failed"].sum()

    st.write(f"**Time window:** {window} — from {traces['start_time'].min():%Y-%m-%d %H:%M:%S} "
             f"to {traces['start_time'].max():%Y-%m-%d %H:%M:%S}")
    st.write("**Data source:** raw/spans/*.jsonl (one request = one trace_id)")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Requests", total)
    col1.caption("Count of trace_ids")
    col2.metric("Cache hit rate", f"{hits / total * 100:.1f}%")
    col2.caption(f"{hits} hits, {misses} misses (cache_lookup spans)")
    col3.metric("Error rate", f"{failed / total * 100:.1f}%")
    col3.caption(f"{failed} request(s) with a span status of error")
    col4.metric("End-to-end latency (p50)", f"{traces['total_ms'].median():.0f} ms")
    col4.caption("First span start to last span end")

    #cache hits and misses are kept separate
    st.subheader("End-to-end latency by cache path")
    latency = traces.groupby("cache")["total_ms"].agg(["count", "mean", "median"]).round(1)
    latency.columns = ["requests", "mean (ms)", "p50 (ms)"]
    st.table(latency)
    st.caption(f"Data source: raw/spans/*.jsonl, time window: {window}")

#Evaluation

def evaluation_page():
    st.header("Evaluation")
    st.subheader("Pipeline evaluation (Part 2)")
    results = load_json("evaluation_results.json")
    if results is None:
        st.info("No data yet: raw/evaluation_results.json is written by the Part 2 evaluator.")
    else:
        table = pd.DataFrame(results)
        st.write("Scores by case (1 = very poor, 5 = excellent)")
        st.dataframe(table)
        score_columns = [column for column in table.columns if column.endswith("_score")]
        if score_columns:
            st.write("Average score by pipeline stage")
            st.bar_chart(table[score_columns].mean())

    st.subheader("Judge validation (Part 3)")
    judge = load_json("judge_validation.json")
    if judge is None:
        st.info("No data yet: raw/judge_validation.json is written by the Part 3 judge validation.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Spearman correlation", judge.get("spearman"))
        col2.metric("Mean absolute difference", judge.get("mean_absolute_difference"))
        col3.metric("Scores that changed across 3 runs", f"{judge.get('percent_changed')}%")
        st.write(f"Repeatability: mean absolute change {judge.get('mean_absolute_change')}, "
                 f"max absolute change {judge.get('max_absolute_change')}")
        scores = load_csv("judge_scores.csv")
        if scores is not None:
            st.write("Raw per-case data (human label vs judge score)")
            st.dataframe(scores)
    st.subheader("What the scores suggest about coordination")
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE) as f:
            st.markdown(f.read())
    else:
        st.info("Write interpretation in coordination_notes.md.")

#Trace lookup

def trace_page():
    st.header("Trace lookup")
    spans = load_spans()
    if spans.empty:
        st.info("No data yet: raw/spans/*.jsonl is written by the Part 4 tracing.")
        return
    examples = load_json("trace_examples.json")
    if examples:
        st.write("Example traces (Part 4.2):")
        st.table(pd.DataFrame(list(examples.items()), columns=["example", "trace_id"]))
    trace_id = st.text_input("trace_id", value=examples.get("cache_hit", "") if examples else "")
    if not trace_id:
        return
    trace = spans[spans["trace_id"] == trace_id.strip()].copy()
    if trace.empty:
        st.warning(f"No spans found for trace_id {trace_id}")
        return

    #show if request was a cache hit or a cache miss
    lookup = trace[trace["stage"] == "cache_lookup"]
    cache = lookup["cache"].iloc[0] if "cache" in trace and len(lookup) > 0 else "unknown"
    if cache == "hit":
        st.success("Cache HIT path: answered from the Redis semantic cache, the agents were not called.")
    elif cache == "miss":
        st.warning("Cache MISS path: cache_lookup -> inbox -> Planner -> Writer -> Reviewer -> final.")
    if (trace["status"] == "error").any():
        failed_stage = trace[trace["status"] == "error"].iloc[0]
        st.error(f"Failed at stage {failed_stage['stage']}: {failed_stage.get('error')}")

    #show journey in pipeline stage order
    trace["order"] = trace["stage"].apply(lambda s: STAGE_ORDER.index(s) if s in STAGE_ORDER else len(STAGE_ORDER))
    trace = trace.sort_values(["order", "start_time"])
    columns = ["stage", "start_time", "end_time", "duration_ms", "status", "error"]
    st.dataframe(trace[[column for column in columns if column in trace.columns]], hide_index=True)
    st.write(f"Total: {(trace['end_time'].max() - trace['start_time'].min()).total_seconds() * 1000:.0f} ms")

#Main

st.title("s0932 Operations Dashboard")
page = st.sidebar.radio("Page", ["Summary", "Evaluation", "Trace lookup"])
if page == "Summary":
    summary_page()
elif page == "Evaluation":
    evaluation_page()
else:
    trace_page()
