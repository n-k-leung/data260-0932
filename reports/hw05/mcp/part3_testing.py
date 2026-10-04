import csv
import os
import random
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__),"..", "backend"))
from app.database import SessionLocal
from app import models

VERIFY_SEED = 260932
CALLS_PER_RATE = 50
RATES = [0.0, 0.2, 0.5]
RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

def call_retry(operation, max_retries=3, base_delay=0.2, timeout=2):
    attempt = 0

    while True:
        attempt += 1
        start = time.time()
        try:
            result = operation()
            elapsed = time.time() - start
            if elapsed > timeout:
                raise TimeoutError("attempt took " + str(round(elapsed, 3)) + "s, timeout is " +str(timeout) + "s")
            return {"ok": True, "data": result, "error": None, "attempts": attempt}

        except Exception as e:
            if attempt > max_retries:
                return {"ok": False, "data": None, "error": str(e), "attempts": attempt}
            delay = base_delay * (2 ** (attempt - 1))
            time.sleep(delay)
            
def fail_sequence(seed, failure_rate, count):
    rng = random. Random(seed)
    return [rng.random() < failure_rate for _ in range(count)]

def make_operation(fail_flags):
    flags = list(fail_flags)

    class Operation:
        def __call__(self):
            should_fail = flags.pop(0)

            if should_fail:
                raise ConnectionError("storage failed")
            return "query result"
    return Operation()

print("Success on the first attempt")
print(call_retry(make_operation([False]), max_retries=3, base_delay=0.1))

print("\nFailure on the first attempt followed by success after a retry")
print(call_retry(make_operation([True, False]), max_retries=3, base_delay=0.1))

print("\nFailure after all allowed retries, returning a clean error result instead of crashing")
print(call_retry(make_operation([True, True, True, True]), max_retries=3, base_delay=0.1))

def make_db(fail_flags):
    class DatabaseOperation:
        def __call__(self):
            should_fail = fail_flags.pop(0) if fail_flags else False

            if should_fail:
                raise ConnectionError("database failed")
            db = SessionLocal()
            try:
                return db.query(models.Vul).filter(models.Vul.package_name =="nodejs").all()
            finally:
                db.close()

    return DatabaseOperation()

raw_rows = []
summary_rows = []

print(time.strftime("%Y-%m-%d %H:%M:%S"), "start fault-injection measurement, VERIFY_SEED =", VERIFY_SEED)

for rate in RATES:

    flags = fail_sequence(VERIFY_SEED, rate, CALLS_PER_RATE * 4)
    latencies = []
    successes = 0

    for call_number in range(1, CALLS_PER_RATE + 1):
        start = time.perf_counter()
        result = call_retry(make_db(flags), max_retries=3, base_delay=0.1, timeout=2)
        latency_ms = (time.perf_counter() - start) * 1000
        latencies.append(latency_ms)
        if result["ok"]:
            successes += 1
        raw_rows.append([rate, call_number, result["ok"], result["attempts"], round(latency_ms, 2)])

    success_rate = successes / CALLS_PER_RATE
    mean_latency = sum(latencies) / len(latencies)
    latencies_sorted = sorted(latencies)
    index = int(round(0.99 * (len(latencies_sorted) - 1)))
    p99_latency = latencies_sorted[index]
    summary_rows.append([rate, success_rate, round(mean_latency, 2), round(p99_latency, 2)])
    print(time.strftime("%Y-%m-%d %H:%M:%S"), "rate", rate, "success rate", success_rate, "mean ms",
    round(mean_latency, 2), "p99_ms", round(p99_latency, 2))

with open(os.path.join(RAW_DIR, "fault_injection_raw.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["injected failure rate", "call number", "success", "attempts", "latency ms"])
    w.writerows(raw_rows)

with open(os.path.join(RAW_DIR, "fault_injection_summary.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["injected failure rate", "success rate", "mean latency ms", "p99 latency ms"])
    w.writerows(summary_rows)