import json
import os
from part4_agents import HERE, load_json, load_lessons, run_question, save_lessons

RAW_DIR = os.path.join(HERE, "..", "raw")

def main():
    reference = load_json("reference_data.json")
    test = load_json("test_data.json")
    lessons = load_lessons()
    validated = [lesson for lesson in lessons if lesson.get("validated")]
    variants = [
        ("Baseline", False, []),
        ("Evaluator Repair", True, []),
        ("Lesson Memory", True, lessons),
        ("Validated Improvement", True, validated),
    ]
    rows = []
    all_runs = {}
    for name, use_repair, variant_lessons in variants:
        print(f"\nRunning {name} ({len(variant_lessons)} lesson(s))")
        runs = [run_question(item, reference, use_repair, variant_lessons) for item in test]
        for run in runs:
            print(f"{run['id']}: {run['final_result']} in {run['number_of_attempts']} attempt(s), lessons {run['lessons_used']}")
        correct = sum(1 for run in runs if run["final_result"] == "PASS")
        rows.append({
            "variant": name,
            "correct": correct,
            "incorrect": len(runs) - correct,
            "average_attempts": round(sum(run["number_of_attempts"] for run in runs) / len(runs), 2),
            "average_latency_ms": round(sum(run["latency_ms"] for run in runs) / len(runs), 1),
        })
        all_runs[name] = runs

    save_lessons(lessons)
    os.makedirs(RAW_DIR, exist_ok=True)
    with open(os.path.join(RAW_DIR, "part4_test_results.json"), "w") as f:
        json.dump({"table": rows, "runs": all_runs}, f, indent=2)
    print(f"\nResults on test_data.json ({len(test)} questions)")
    for row in rows:
        print(f"{row['variant']}: correct {row['correct']}, incorrect {row['incorrect']}, "
              f"average attempts {row['average_attempts']}, average latency {row['average_latency_ms']} ms")
    print("\nSaved raw/part4_test_results.json")

if __name__ == "__main__":
    main()
