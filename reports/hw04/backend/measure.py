import csv
import os
import time
import requests

BASE = "http://localhost:8032"
SIZES = [10, 50, 200]
def percentile(values, p):
    values = sorted(values)
    index = int(round((p / 100) * (len(values) - 1)))
    return values [index]

s = requests.Session()
login_data = {"email": "measure@example.com", "password": "measure1234"}
s.post(BASE + "/auth/register", json={"name": "Measure User", ** login_data})
s.post(BASE + "/auth/login", json=login_data)

os.makedirs("../raw", exist_ok=True)
raw_rows = []
summary_rows = []

print(time.strftime("%Y-%m-%d %H:%M:%S"), "start measuring")
for size in SIZES:
    for version in ["naive", "fixed"]:
        times = []
        counts = []
        for n in range(1, 31):
            start = time.perf_counter()
            r = s.get(BASE + "/vuls/" + version, params={"limit": size})
            ms = (time.perf_counter() - start) * 1000
            sql_count = int (r.headers["X-SQL-Count"])
            times.append (ms)
            counts.append(sql_count)
            raw_rows.append([size, version, n, r.status_code, sql_count, round(ms, 2)])

        p50, p95, p99 = percentile(times, 50), percentile(times, 95), percentile(times, 99)
        summary_rows.append([size, version, round(p50, 2), round(p95, 2), round(p99, 2), counts[0                                               ]])
        print(time.strftime("%Y-%m-%d %H:%M:%S"), "size", size, version, "p50", round(p50, 2), "p95", round(p95, 2), "p99", round(p99, 2), "stmts/req", counts[0])

with open("../raw/n_plus_one_raw.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["page_size", "version", "request_no", "status", "sql_statements", "latency_ms"])
    w.writerows(raw_rows)

with open("../raw/n_plus_one_summary.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["page_size", "version", "p50_ms", "p95_ms", "p99_ms", "stmts_per_req"])
    w.writerows(summary_rows)

print(time.strftime("%Y-%m-%d %H:%M:%S"), "done, saved", len(raw_rows), "requests to .. /raw/")
