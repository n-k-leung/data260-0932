import json
import os
from semantic_cache import SemanticResponseCache
from traced_request import HERE, make_evaluator, run_request

EXAMPLES_FILE = os.path.join(HERE, "raw", "trace_examples.json")
QUESTION = "Which version of lodash fixes CVE-2021-23337, and what should our team do about it?"
FAIL_QUESTION = "Which version of axios fixes CVE-2021-3749, and what should our team do about it?"
FAIL_TIMEOUT_SECONDS = 60


def main():
    cache = SemanticResponseCache()
    cache.clear()
    evaluator = make_evaluator()
    examples = {}

    print("\nTrace 1: cache miss (full agent path)")
    examples["cache_miss"] = run_request(QUESTION, cache, evaluator)["trace_id"]

    print("\nTrace 2: cache hit (same question)")
    examples["cache_hit"] = run_request(QUESTION, cache, evaluator)["trace_id"]

    input("\nTrace 3: stop the Reviewer now, then press Enter")
    cache.clear()
    result = run_request(FAIL_QUESTION, cache, evaluator, timeout=FAIL_TIMEOUT_SECONDS)
    examples["failed"] = result["trace_id"]
    print("Start the Reviewer again")

    with open(EXAMPLES_FILE, "w") as f:
        json.dump(examples, f, indent=2)
    print("\nSaved raw/trace_examples.json")
    for name, trace_id in examples.items():
        print(f"{name}: {trace_id}")


if __name__ == "__main__":
    main()
