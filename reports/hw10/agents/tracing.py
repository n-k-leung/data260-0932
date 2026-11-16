import json
import os
from datetime import datetime

SPANS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raw", "spans")

def now():
    return datetime.now()

def kafka_time(msg):
    return datetime.fromtimestamp(msg.timestamp / 1000)

def write_span(component, trace_id, stage, start, end, status="ok", error=None, **extra):
    span = {
        "trace_id": trace_id,
        "stage": stage,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "duration_ms": round((end - start).total_seconds() * 1000, 1),
        "status": status,
        "error": error,
    }
    span.update(extra)
    os.makedirs(SPANS_DIR, exist_ok=True)
    with open(os.path.join(SPANS_DIR, f"{component}.jsonl"), "a") as f:
        f.write(json.dumps(span) + "\n")
