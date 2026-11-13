import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from deepeval.metrics import GEval
from deepeval.metrics.g_eval import Rubric
from deepeval.models import OllamaModel
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "agents"))
from common import (DRAFTS_TOPIC, FINAL_TOPIC, INBOX_TOPIC, KAFKA_BOOTSTRAP_SERVERS, TASKS_TOPIC, from_bytes, log, to_bytes)

RAW_DIR = os.path.join(HERE, "raw")
MESSAGES_DIR = os.path.join(RAW_DIR, "pipeline_messages")
RESULTS_FILE = os.path.join(RAW_DIR, "evaluation_results.json")
DEFAULT_QUESTION = "Which version of lodash fixes CVE-2021-23337, and what should our team do about it?"
JUDGE_MODEL = "qwen3:8b"
JUDGE_SEED = 932
COLLECT_TIMEOUT_SECONDS = 300
JUDGE_TIMEOUT_SECONDS = 180
RUBRIC = [
    Rubric(score_range=(1, 1), expected_outcome="Very poor"),
    Rubric(score_range=(2, 2), expected_outcome="Poor"),
    Rubric(score_range=(3, 3), expected_outcome="Average"),
    Rubric(score_range=(4, 4), expected_outcome="Good"),
    Rubric(score_range=(5, 5), expected_outcome="Excellent"),
]

async def send_and_collect(question):
    correlation_id = str(uuid.uuid4())
    topic_names = {TASKS_TOPIC: "plan", DRAFTS_TOPIC: "draft", FINAL_TOPIC: "final"}
    found = {}
    consumer = AIOKafkaConsumer(TASKS_TOPIC, DRAFTS_TOPIC, FINAL_TOPIC, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS, auto_offset_reset="earliest")
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await consumer.start()
    await producer.start()
    async def read_until_complete():
        async for msg in consumer:
            try:
                message = from_bytes(msg.value)
            except Exception as error:
                log(f"Skipped a malformed message on {msg.topic} offset {msg.offset}: {error!r}")
                continue
            if message.get("correlation_id") != correlation_id:
                continue
            name = topic_names[msg.topic]
            found[name] = {
                "topic": msg.topic,
                "partition": msg.partition,
                "offset": msg.offset,
                "timestamp_ms": msg.timestamp,
                "message": message,
            }
            log(f"Got the {name} from {msg.topic} (partition {msg.partition}, offset {msg.offset})")
            if len(found) == 3:
                return
    try:
        await producer.send_and_wait(INBOX_TOPIC, to_bytes({"correlation_id": correlation_id, "question": question}))
        log(f"Sent the question to {INBOX_TOPIC} (trace_id {correlation_id})")
        await asyncio.wait_for(read_until_complete(), timeout=COLLECT_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        log(f"Timed out after {COLLECT_TIMEOUT_SECONDS} s, only got: {list(found)}")
    finally:
        await consumer.stop()
        await producer.stop()
    return {"trace_id": correlation_id, "question": question,
            "collected_at": datetime.now().isoformat(), "messages": found}

def save_messages(record):
    os.makedirs(RAW_DIR, exist_ok=True)
    path = os.path.join(RAW_DIR, f"{record['trace_id']}.json")
    with open(path, "w") as f:
        json.dump(record, f, indent=2)
    return path

def make_metrics():
    judge = OllamaModel(model=JUDGE_MODEL, base_url="http://localhost:11434", temperature=0, generation_kwargs={"seed": JUDGE_SEED}, timeout=JUDGE_TIMEOUT_SECONDS)
    plan_quality = GEval(
        name="Plan Quality",
        evaluation_steps=[
            "Check that the plan's steps address the user's question about an open source package vulnerability",
            "Check that the steps are clear, specific and in a sensible order",
            "Penalize steps that are vague, off-topic or factually wrong",
        ],
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        rubric=RUBRIC,
        model=judge,
        async_mode=False,
    )
    helpfulness_steps = [
        "Check that the answer directly answers the user's question",
        "Check that the facts (CVE, package, versions, severity) are accurate",
        "Check that the advice is useful and actionable for a software team",
        "Penalize missing key facts, wrong facts or unrelated content",
    ]
    writer_helpfulness = GEval(name="Writer Helpfulness", evaluation_steps=helpfulness_steps,
                               evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
                               rubric=RUBRIC, model=judge, async_mode=False)
    final_helpfulness = GEval(name="Final Answer Helpfulness", evaluation_steps=helpfulness_steps,
                              evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
                              rubric=RUBRIC, model=judge, async_mode=False)
    return plan_quality, writer_helpfulness, final_helpfulness


def judge_score(metric, question, output):
    try:
        metric.measure(LLMTestCase(input=question, actual_output=output))
        return round(1 + 4 * metric.score, 2), metric.reason
    except Exception as error:
        return None, f"judge error: {error!r}"

def evaluate(record):
    messages = record["messages"]
    missing = [name for name in ["plan", "draft", "final"] if name not in messages]
    if missing:
        log(f"Cannot evaluate trace {record['trace_id']}: missing {missing}")
        return None

    question = record["question"]
    plan = messages["plan"]["message"]["plan"]
    draft = messages["draft"]["message"]["draft"]
    final = messages["final"]["message"]
    final_answer = final["answer"]
    plan_quality, writer_helpfulness, final_helpfulness = make_metrics()
    log("Judging Plan Quality...")
    plan_score, plan_reason = judge_score(plan_quality, question, plan)
    log("Judging Writer Helpfulness...")
    draft_score, draft_reason = judge_score(writer_helpfulness, question, draft)
    log("Judging Final Answer Helpfulness...")
    final_score, final_reason = judge_score(final_helpfulness, question, final_answer)
    same_text = final_answer.strip() == draft.strip()
    if draft_score is None or final_score is None:
        difference = None
        interpretation = "Could not compare: the judge failed on the draft or the final answer."
    else:
        difference = round(final_score - draft_score, 2)
        if difference > 0:
            interpretation = "The final answer scored higher than the draft."
        elif difference < 0:
            interpretation = "The final answer scored lower than the draft."
        else:
            interpretation = "The final answer scored the same as the draft."
        if same_text:
            interpretation += (f" The final answer text is the same as the draft: the Reviewer only marked it "
                               f"'{final.get('status')}' and did not rewrite it, so no improvement is expected.")

    return {
        "trace_id": record["trace_id"],
        "question": question,
        "judge_model": f"{JUDGE_MODEL} (Ollama, temperature 0, seed {JUDGE_SEED})",
        "evaluated_at": datetime.now().isoformat(),
        "plan_quality_score": plan_score,
        "plan_quality_reason": plan_reason,
        "writer_helpfulness_score": draft_score,
        "writer_helpfulness_reason": draft_reason,
        "final_helpfulness_score": final_score,
        "final_helpfulness_reason": final_reason,
        "final_answer": final_answer,
        "review_status": final.get("status"),
        "final_same_as_draft": same_text,
        "score_difference": difference,
        "interpretation": interpretation,
    }

def save_result(result):
    results = []
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE) as f:
            results = json.load(f)
    results.append(result)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)

def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--load":
        with open(sys.argv[2]) as f:
            record = json.load(f)
        log(f"Loaded saved messages for trace {record['trace_id']}")
    else:
        question = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUESTION
        record = asyncio.run(send_and_collect(question))
        log(f"Saved the messages in {save_messages(record)}")

    result = evaluate(record)
    if result is None:
        return
    save_result(result)
    print(f"\ntrace_id: {result['trace_id']}")
    print(f"question: {result['question']}")
    print(f"judge: {result['judge_model']}")
    print(f"Plan Quality: {result['plan_quality_score']} - {result['plan_quality_reason']}")
    print(f"Writer Helpfulness: {result['writer_helpfulness_score']} - {result['writer_helpfulness_reason']}")
    print(f"Final Answer Helpfulness: {result['final_helpfulness_score']} - {result['final_helpfulness_reason']}")
    print(f"Final answer: {result['final_answer']}")
    print(f"Final vs draft: draft {result['writer_helpfulness_score']}, final {result['final_helpfulness_score']}, "
          f"difference {result['score_difference']}")
    print(f"Interpretation: {result['interpretation']}")

if __name__ == "__main__":
    main()
