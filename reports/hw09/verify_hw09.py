import importlib.util
import json
import os
import random
import subprocess
import sys
import time
import redis
import yaml

HOMEWORK = 9
SID4 = "0932"
SEED = 932
VERIFY_SEED = 260000 + 932
PREFIX = "s0932"

here = os.path.dirname(os.path.abspath(__file__))
part4_dir = os.path.join(here, "part4_self_improve_agent")
sys.path.insert(0, here)
random.seed(VERIFY_SEED)

try:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=here, text=True).strip()
except Exception:
    commit = "unknown"
try:
    tag = subprocess.check_output(["git", "describe", "--tags", "--exact-match", "HEAD"],
                                  cwd=here, text=True, stderr=subprocess.DEVNULL).strip()
except Exception:
    tag = "not tagged"

model = os.environ.get("MODEL", "qwen3:8b")

def redis_is_up():
    try:
        return redis.Redis(host="localhost", port=6379).ping()
    except redis.exceptions.RedisError:
        return False
    
started_docker = False
if not redis_is_up():
    subprocess.run(["docker", "compose", "up", "-d"], cwd=here,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    started_docker = True
    for i in range(30):
        if redis_is_up():
            break
        time.sleep(1)


def load_module_from_file(name, path):
    folder = os.path.dirname(path)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def check_redis():
    client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    client.execute_command("FT._LIST")
    return client.ping(), "Redis answered PING and FT._LIST (vector search is available)"

def check_view_counter():
    from app.models import Vul
    from view_counter import VulnerabilityDatabaseWithCache
    counter = VulnerabilityDatabaseWithCache()
    try:
        vul = counter.db.query(Vul).order_by(Vul.id.asc()).first()
        counter.redis_client.delete(f"{PREFIX}:views:vulnerability:{vul.id}")
        for i in range(10):
            total = counter.increment_vulnerability_views(vul.id)
        counter.db.refresh(vul)
    finally:
        counter.close()
    ok = total == 10 and vul.view_count == 10
    return ok, "after 10 views: Redis count = " + str(total) + ", database view_count = " + str(vul.view_count)

def check_semantic_cache():
    from semantic_cache import SemanticResponseCache
    cache = SemanticResponseCache()
    question = "verify_hw09 test question " + str(random.randint(1000, 9999))
    embedding = cache.embed(question)
    key = cache.store(question, embedding, "verify answer")
    try:
        best, similarity = cache.find_most_similar(embedding)
    finally:
        cache.redis_client.delete(key)  #remove the test entry again
    ok = (best is not None and similarity >= 0.99 and best.answer == "verify answer"
          and best.data_version == cache.get_data_version())
    return ok, "same question similarity = " + str(round(similarity, 3)) + ", stored answer returned: " + str(best is not None and best.answer == "verify answer")

def check_cache_cases():
    with open(os.path.join(here, "cache_cases.yaml")) as f:
        data = yaml.safe_load(f)
    cases = data["cases"]
    expected_label = {"exact_duplicate": "hit", "paraphrase": "hit", "similar_different": "miss", "unrelated": "miss"}
    counts = {}
    labels_ok = True
    for case in cases:
        counts[case["category"]] = counts.get(case["category"], 0) + 1
        if case["expected"] != expected_label[case["category"]]:
            labels_ok = False
    ok = len(cases) == 40 and all(counts.get(group) == 10 for group in expected_label) and labels_ok
    return ok, "cases: " + str(len(cases)) + ", per group: " + str(counts) + ", labels correct: " + str(labels_ok)

def check_evaluator():
    agents = load_module_from_file("part4_agents", os.path.join(part4_dir, "part4_agents.py"))
    reference = agents.load_json("reference_data.json")
    record = reference[0]
    question = f"Which version of {record['package']} fixes {record['cve']}?"
    right = agents.evaluator_agent(question, f"Upgrade to {record['fixed_versions'][0]}.", reference)
    wrong = agents.evaluator_agent(question, "Upgrade to 0.0.0.", reference)
    off_topic = agents.evaluator_agent("What is the capital of Australia?", "Canberra.", reference)
    ok = (right["result"] == "PASS" and wrong["result"] == "REVISE" and bool(wrong["feedback"])
          and off_topic["result"] == "REVISE")
    return ok, "correct answer: " + right["result"] + ", wrong answer: " + wrong["result"] + ", off-topic answer: " + off_topic["result"]

def check_part4_files():
    only_questions = True
    for name in ["training_data.json", "validation_data.json", "test_data.json"]:
        with open(os.path.join(part4_dir, name)) as f:
            for item in json.load(f):
                if sorted(item.keys()) != ["id", "question"]:
                    only_questions = False
    with open(os.path.join(part4_dir, "lessons.json")) as f:
        lessons = json.load(f)
    required = ["lesson_id", "failure_pattern", "correction", "created_at", "use_count"]
    lessons_ok = len(lessons) > 0 and all(field in lesson for lesson in lessons for field in required)
    ok = only_questions and lessons_ok
    return ok, "input files have no expected answers: " + str(only_questions) + ", " + str(len(lessons)) + " lesson(s) with all required fields: " + str(lessons_ok)

checks = [
    ("Redis Stack responds and has vector search", check_redis),
    ("view counter syncs to the database every 10 views", check_view_counter),
    ("semantic cache returns a stored answer for the same question", check_semantic_cache),
    ("cache_cases.yaml has 40 cases, 10 per group, correct labels", check_cache_cases),
    ("Evaluator Agent passes a correct answer and revises wrong ones", check_evaluator),
    ("Part 4 input files have no answers and lessons.json has the required fields", check_part4_files),
]
results = []

for name, function in checks:
    try:
        passed, detail = function()
    except Exception as e:
        passed, detail = False, "error: " + str(e)
    results.append({"check": name, "result": "pass" if passed else "fail", "detail": detail})
    print(("PASS - " if passed else "FAIL - ") + name + " - " + detail)

if started_docker:
    subprocess.run(["docker", "compose", "stop"], cwd=here, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

report = {
    "homework": HOMEWORK,
    "sid4": SID4,
    "commit": commit,
    "tag": tag,
    "model": model,
    "seed": SEED,
    "verify_seed": VERIFY_SEED,
    "checks": results,
}
with open(os.path.join(here, "verification.json"), "w") as f:
    json.dump(report, f, indent=2)

print("verification.json outputted")
