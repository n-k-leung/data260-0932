import json 
from collections import defaultdict 
import yaml

def recall_at_k(technique, correct_answer, by_technique, k=3):
    hits=0
    total=0
    for question, correct in correct_answer.items():
        total+=1
        retrieved = [
            r["source_file"] for r in by_technique[technique]
            if r["query"] == question and r["rank"] <=3
        ]
        if any(f in retrieved for f in correct):
            hits+=1
    if total == 0:
        return 0.0
    return hits/total

def main():
    #getting correct answer for each query question
    questions = yaml.safe_load(open("questions.yaml"))
    correct_answer={}
    for q in questions:
        #if more than one correct answer for the file
        files=[f.strip() for f in q["expected_source_file"].split(",")]
        correct_answer[q["question"]] = files
    with open("raw/per_query_results.json", encoding="utf-8") as f:
        rows=[json.loads(line) for line in f if line.strip()]
    with open("raw/per_technique_results.json", encoding="utf-8") as f:
        technique=json.load(f)

    # group cosine scores by technique
    by_technique = defaultdict(list)
    for r in rows:
        by_technique[r["technique"]].append(r)

    lines = []
    lines.append("# METRICS.md\n")
    lines.append("## Retrieval quality summary\n")
    lines.append("| Technique | Chunks | Avg chunk length (chars) | Top-1 cosine | Mean@3 cosine | Recall@3 | Mean retrieval latency (ms) |")
    lines.append("|---|---|---|---|---|---|---|")

    for name in ["token", "semantic", "sentenceWindow"]:
        group = by_technique[name]
        top1 = [r["cosine_sim"] for r in group if r["rank"] == 1]
        all_cos = [r["cosine_sim"] for r in group]
        stats = technique[name]
        recall = recall_at_k(name, correct_answer,by_technique,k=3)
        lines.append(f"| {name} | {stats['num_chunks']} | {stats['avg_chunk_len']:.0f} | {sum(top1)/len(top1):.3f} | {sum(all_cos)/len(all_cos):.3f} | {recall:.3f} | {stats['mean_latency_ms']:.2f} |"
        )

    open("METRICS.md", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))
if __name__=="__main__":
    main()