import csv
import json
import os
import pandas as pd
from deepeval.metrics import GEval
from deepeval.metrics.g_eval import Rubric
from deepeval.models import OllamaModel
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(HERE, "raw")
JUDGE_MODEL = "qwen3:8b"
JUDGE_SEED = 932
JUDGE_TIMEOUT_SECONDS = 180
RUNS = 3

RUBRIC = [
    Rubric(score_range=(1, 1), expected_outcome="Very poor"),
    Rubric(score_range=(2, 2), expected_outcome="Poor"),
    Rubric(score_range=(3, 3), expected_outcome="Average"),
    Rubric(score_range=(4, 4), expected_outcome="Good"),
    Rubric(score_range=(5, 5), expected_outcome="Excellent"),
]
HELPFULNESS_STEPS = [
    "Check that the answer directly answers the user's question",
    "Check that the facts (CVE, package, versions, severity) are accurate",
    "Check that the advice is useful and actionable for a software team",
    "Penalize missing key facts, wrong facts or unrelated content",
]

def make_judge():
    judge = OllamaModel(model=JUDGE_MODEL, base_url="http://localhost:11434", temperature=0, generation_kwargs={"seed": JUDGE_SEED}, timeout=JUDGE_TIMEOUT_SECONDS)
    return GEval(name="Writer Helpfulness", evaluation_steps=HELPFULNESS_STEPS,
                 evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
                 rubric=RUBRIC, model=judge, async_mode=False)

def judge_score(metric, question, draft):
    try:
        metric.measure(LLMTestCase(input=question, actual_output=draft))
        return round(1 + 4 * metric.score, 2)
    except Exception as error:
        print(f"  judge error: {error!r}")
        return None

def load_inputs():
    with open(os.path.join(HERE, "eval_cases.json")) as f:
        cases = json.load(f)
    labels = {}
    with open(os.path.join(HERE, "human_labels.csv"), newline="") as f:
        for row in csv.DictReader(f):
            labels[row["case_id"]] = row["human_label"].strip()
    return cases, labels

def main():
    cases, labels = load_inputs()
    missing = [case["case_id"] for case in cases if labels.get(case["case_id"]) not in ["1", "2", "3", "4", "5"]]
    if missing:
        print(f"Fill in a human label from 1 to 5 for: {missing}")
        return
    metric = make_judge()
    rows = []
    for case in cases:
        rows.append({"case_id": case["case_id"], "trace_id": case["trace_id"],
                     "human_label": int(labels[case["case_id"]])})
    for run in range(1, RUNS + 1):
        print(f"\nJudge run {run} of {RUNS}")
        for case, row in zip(cases, rows):
            row[f"judge_run{run}"] = judge_score(metric, case["question"], case["draft"])
            print(f"{case['case_id']}: human {row['human_label']}, judge {row[f'judge_run{run}']}")

    table = pd.DataFrame(rows)
    run_columns = [f"judge_run{run}" for run in range(1, RUNS + 1)]
    table["change"] = table[run_columns].max(axis=1) - table[run_columns].min(axis=1)
    complete = table.dropna(subset=run_columns)
    failed = len(table) - len(complete)
    spearman = complete["human_label"].corr(complete["judge_run1"], method="spearman")
    mean_abs_diff = (complete["human_label"] - complete["judge_run1"]).abs().mean()
    changed = (complete["change"] > 0).sum()
    percent_changed = changed / len(complete) * 100
    validation = {
        "cases": len(table),
        "cases_used": len(complete),
        "judge_failures": failed,
        "spearman": round(float(spearman), 3),
        "mean_absolute_difference": round(float(mean_abs_diff), 3),
        "cases_changed": int(changed),
        "percent_changed": round(float(percent_changed), 1),
        "mean_absolute_change": round(float(complete["change"].mean()), 3),
        "max_absolute_change": round(float(complete["change"].max()), 3),
        "judge_settings": f"{JUDGE_MODEL} through Ollama, GEval Writer Helpfulness, 1-5 rubric, "
                          f"temperature 0, seed {JUDGE_SEED}, {RUNS} runs, same inputs",
        "compared_with_humans": "judge run 1",
    }

    os.makedirs(RAW_DIR, exist_ok=True)
    table.to_csv(os.path.join(RAW_DIR, "judge_scores.csv"), index=False)
    with open(os.path.join(RAW_DIR, "judge_validation.json"), "w") as f:
        json.dump(validation, f, indent=2)
    print("\nJudge vs human labels (run 1)")
    print(f"Spearman rank correlation: {validation['spearman']}")
    print(f"Mean absolute difference: {validation['mean_absolute_difference']}")
    print("\nRepeatability (3 runs)")
    print(f"Cases whose score changed: {changed} of {len(complete)} ({validation['percent_changed']}%)")
    print(f"Mean absolute change: {validation['mean_absolute_change']}")
    print(f"Max absolute change: {validation['max_absolute_change']}")
    if failed:
        print(f"Judge failed on {failed} case(s); they are left out of the statistics.")

if __name__ == "__main__":
    main()
