import csv, json, os, re,subprocess, sys, time, statistics
from collections import Counter

inputFile = "../reports/hw01/cases/nondeterminism_input.json"
outputFile = "../reports/hw01/raw"

def run(title,content, email,temp):
    cmd = ["python", "agents_demo.py", "--title", title, "--content", content, "--email", email, "--temperature", str(temp), "--strict"]
    start =time.time()
    result=subprocess.run(cmd,capture_output=True, text=True)
    latency_ms=int((time.time()-start)*1000)
    # use regex to get finalized outputs data correctly
    match = re.search(r"Finalized Output\s*\n(\{.*?\n\})\s*\n\s*Publish Package", result.stdout, re.DOTALL)
    tags=[]
    if match:
        try:
            tags=json.loads(match.group(1))["data"]["tags"]
        except Exception:
            pass
    return result.stdout, tags, latency_ms    

def get_metrics(runs):
    tag_sets=[tuple(sorted(r["tags"])) for r in runs]
    count = Counter()
    for tags in tag_sets:
        for tag in set(tags):
            count[tag]+=1
    
    times=sorted(r["latency_ms"] for r in runs)
    p=statistics.quantiles(times,n=100)
    return {
        "distinct_tag_sets":len(set(tag_sets)),
        "tags_in_all_runs": sorted(tag for tag, c in count.items()if c==20),
        "tags_in_exactly_one_run": sorted(tag for tag, c in count.items() if c==1),
        "latency_p50": statistics.median(times),
        # go one lower than percentile number actually want for right value
        "latency_p95": p[94],
        "latency_p99": p[98],
    }

    
def main():
    with open(inputFile) as f:
        case = json.load(f)
    os.makedirs(outputFile, exist_ok=True)
    summary={}
    for temp in [0.7,0.0]:
        label=str(temp).replace(".","_")
        runs=[]
        for i in range(1,21):
            print(f"temp={temp} run={i}/20", file=sys.stderr)
            output, tags, latency = run(case["title"], case["content"], case["email"], temp)
        
            with open(os.path.join(outputFile, f"run_temp{label}_{i:02d}.txt"),"w") as f:
                f.write(output)
            runs.append({"run":i,"tags": tags, "latency_ms":latency})
        # save every run as a json and csv
        with open(os.path.join(outputFile, f"nondeterminism_temp_{label}.json"),"w") as f:
            json.dump(runs,f,indent=2)
        with open(os.path.join(outputFile, f"nondeterminism_temp_{label}.csv"), "w", newline="") as f:
            w= csv.writer(f)
            w.writerow(["run","tag_1", "tag_2", "tag_3", "latency_ms"])
            for r in runs:
                tags=(r["tags"]+["","",""])[:3]
                w.writerow([r["run"], *tags, r["latency_ms"]])
        summary[label] = get_metrics(runs)
        
        
        # print out table with all the runs to compare tags and stuff
        # formatting is off but still readable
    print("\nMetrics table")
    print(f"'Metric' | 'Temp 0.7' | 'Temp 0.0'")
    
    metrics = [("Distinct tag sets", "distinct_tag_sets"), ("Tags in all 20 runs", "tags_in_all_runs"),("Tags in exactly 1 run", "tags_in_exactly_one_run"), ("Latency p50 (ms)", "latency_p50"), ("Latency p95 (ms)", "latency_p95"), ("Latency p99 (ms)", "latency_p99")]
    for name, key in metrics:
        print(f"{name} | {str(summary['0_7'][key])} | {summary['0_0'][key]}")
    
    with open(os.path.join(outputFile, "nondeterminism_all.json"), "w") as f:
        json.dump(summary,f,indent=2)
    print("Done")
        
if __name__ == "__main__":
    main()
    