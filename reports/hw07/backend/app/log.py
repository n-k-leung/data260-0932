import csv
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

REPORT_DIR = os.getenv("REPORT_DIR", os.path.join(os.path.dirname(__file__), ".."))
RAW_DIR = os.path.join(REPORT_DIR, "raw")
LOG_FILE = os.path.join(RAW_DIR, "chat_usage.csv")

FIELDS = ["timestamp", "run_label", "policy", "short_term_n", "user_id", "session_id",
    "prompt_tokens", "completion_tokens",
    "system_primer_tokens_est", "long_term_summary_tokens_est",
    "short_term_tokens_est", "episodic_tokens_est", "latency_ms"]

def log_usage(row):
    os.makedirs(RAW_DIR, exist_ok=True)
    is_new_file = not os.path.exists(LOG_FILE)
    row["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new_file:
            writer.writeheader()
        writer.writerow(row)