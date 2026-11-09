import asyncio
import csv
import json
import os
import time
import yaml
from semantic_cache import SemanticResponseCache, ask_agents, log

THRESHOLDS = [0.75, 0.80, 0.85, 0.90, 0.95]
MISS_COST = 1
FALSE_HIT_COST = 10
HERE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(HERE, "raw")
ANSWERS_FILE = os.path.join(RAW_DIR, "part3_agent_answers.json")

def load_cases():
    with open(os.path.join(HERE, "cache_cases.yaml")) as f:
        data = yaml.safe_load(f)
    return data["seed_queries"], data["cases"]

def get_agent_answers(questions):
    os.makedirs(RAW_DIR, exist_ok=True)
    answers = {}
    if os.path.exists(ANSWERS_FILE):
        with open(ANSWERS_FILE) as f:
            answers = json.load(f)
    for number, question in enumerate(questions, start=1):
        if question in answers:
            continue
        log(f"Agent run {number} of {len(questions)}: {question}")
        start = time.perf_counter()
        result = asyncio.run(ask_agents(question))
        agent_ms = (time.perf_counter() - start) * 1000
        answers[question] = {"answer": result["answer"], "agent_ms": round(agent_ms, 1)}
        #save after every answer so nothing is lost if the run stops
        with open(ANSWERS_FILE, "w") as f:
            json.dump(answers, f, indent=2)
    return answers

def main():
    seeds, cases = load_cases()
    questions = []
    for question in seeds + [case["query"] for case in cases]:
        if question not in questions:
            questions.append(question)
    answers = get_agent_answers(questions)
    
    #10 seed answers in an empty cache
    cache = SemanticResponseCache()
    cache.clear()
    for seed in seeds:
        cache.store(seed, cache.embed(seed), answers[seed]["answer"])
    log(f"Stored {len(seeds)} seed answers in the cache")

    #run the 40 cases for each threshold
    rows = []
    false_hits_list = []
    for threshold in THRESHOLDS:
        hits = 0
        false_hits = 0
        latencies = []
        for case in cases:
            start = time.perf_counter()
            best, similarity = cache.find_most_similar(cache.embed(case["query"]))
            lookup_ms = (time.perf_counter() - start) * 1000
            if best is not None and similarity >= threshold:
                hits += 1
                latencies.append(lookup_ms)
                correct = case["expected"] == "hit" and best.query == case.get("seed")
                if not correct:
                    false_hits += 1
                    false_hits_list.append({
                        "threshold": threshold,
                        "case_id": case["id"],
                        "category": case["category"],
                        "incoming_query": case["query"],
                        "cached_query": best.query,
                        "similarity": round(similarity, 3),
                        "cached_answer_returned": best.answer,
                        "correct_answer": answers[case["query"]]["answer"],
                    })
            else:
                latencies.append(lookup_ms + answers[case["query"]]["agent_ms"])

        misses = len(cases) - hits
        rows.append({
            "threshold": threshold,
            "hits": hits,
            "false_hits": false_hits,
            "hit_rate_%": round(hits / len(cases) * 100, 1),
            "false_hit_rate_%": round(false_hits / len(cases) * 100, 1),
            "mean_latency_ms": round(sum(latencies) / len(latencies), 1),
            "total_cost": misses * MISS_COST + false_hits * FALSE_HIT_COST,
        })
    print(f"\nCost model: total cost = misses x {MISS_COST} + false hits x {FALSE_HIT_COST}")
    print("\nResults")
    for r in rows:
        print(f"Threshold {r['threshold']}: hits {r['hits']}, false hits {r['false_hits']}, "
              f"hit rate {r['hit_rate_%']}%, false-hit rate {r['false_hit_rate_%']}%, "
              f"mean latency {r['mean_latency_ms']} ms, total cost {r['total_cost']}")
    best_row = min(rows, key=lambda r: (r["total_cost"], -r["threshold"]))
    print(f"\nLowest total cost: threshold {best_row['threshold']} (cost {best_row['total_cost']})")

    with open(os.path.join(RAW_DIR, "threshold_sweep.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with open(os.path.join(RAW_DIR, "part3_false_hits.json"), "w") as f:
        json.dump(false_hits_list, f, indent=2)

    #one false hit
    for threshold in reversed(THRESHOLDS):
        at_threshold = [fh for fh in false_hits_list if fh["threshold"] == threshold]
        if at_threshold:
            print(f"\nOne false hit in full (threshold {threshold})")
            false_hit = at_threshold[0]
            print(f"Incoming query: {false_hit['incoming_query']}")
            print(f"Cached query it matched: {false_hit['cached_query']}")
            print(f"Similarity: {false_hit['similarity']}")
            print(f"Cached answer returned: {false_hit['cached_answer_returned']}")
            print(f"Correct answer: {false_hit['correct_answer']}")
            break
    else:
        print("\nNo false hits at any threshold.")

    print("\nSaved raw/threshold_sweep.csv, raw/part3_false_hits.json, raw/part3_agent_answers.json")

if __name__ == "__main__":
    main()
