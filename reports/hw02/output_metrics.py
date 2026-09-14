import csv 
from collections import defaultdict

groups=defaultdict(list)
with open("raw/schema_validation_runs.csv") as f:
    for row in csv.DictReader(f):
        groups[row["outcome"]].append(float(row["elapsed_ms"]))
        
lables = {
    "valid_first_attempt": "valid first attempt",
    "valid_after_1_retry": "valid after 1 retry",
    "valid_after_2plus_retries": "valid after 2+ retries",
    "abandoned_at_ceiling": "hit turn ceiling",
}

for key, label in lables.items():
    times = groups.get(key,[])
    count=len(times)
    mean_ms=round(sum(times)/count,1) if times else "N/A"
    print(f"{label} | {count} | {mean_ms}")