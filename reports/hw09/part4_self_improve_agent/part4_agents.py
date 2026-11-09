import json
import os
import re
import time
from datetime import date
import ollama

MODEL = "qwen3:8b"
SEED = 932
MAX_ATTEMPTS = 2  #so at most two answers per question
HERE = os.path.dirname(os.path.abspath(__file__))
LESSONS_FILE = os.path.join(HERE, "lessons.json")
REFUSAL = "I can only answer questions about open source package vulnerabilities."
ANSWERING_PROMPT = (
    "You are the Answering Agent for an open source package vulnerability team. "
    "Answer the question in 2 or 3 sentences."
)

#lesson per failure pattern
LESSON_TEMPLATES = {
    "unsupported_answer": (
        "The answer responds to a question that is not about open source package vulnerabilities.",
        f'If the question is not about an open source package vulnerability, do not answer it. Reply exactly: "{REFUSAL}"',
    ),
    "missing_fixed_version": (
        "The answer does not give the exact fixed version.",
        "When asked which version fixes a CVE, give one exact version number and say to upgrade to that version or later.",
    ),
    "missing_severity": (
        "The answer does not give the correct severity label.",
        "When asked about severity, state the CVSS v3 severity label: Critical, High, Medium or Low.",
    ),
    "missing_cvss_score": (
        "The answer does not give the CVSS score.",
        "When asked about the CVSS score, give the CVSS v3 base score as one number.",
    ),
    "missing_vulnerability_type": (
        "The answer does not name the vulnerability type.",
        "When asked about the vulnerability type, name the weakness category, for example prototype pollution or regular expression denial of service (ReDoS).",
    ),
}

def load_json(file_name):
    with open(os.path.join(HERE, file_name)) as f:
        return json.load(f)

def ask_llm(system_prompt, user_prompt):
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        options={"seed": SEED, "temperature": 0},
        think=False,
    )
    return response["message"]["content"].strip()

def find_cve(question):
    match = re.search(r"CVE-\d{4}-\d+", question)
    return match.group(0) if match else None

def question_topic(question):
    q = question.lower()
    if find_cve(question) is None:
        return "unrelated"
    if "cvss" in q or "score" in q:
        return "cvss_score"
    if "severity" in q:
        return "severity"
    if "type" in q or "kind" in q:
        return "vulnerability_type"
    return "fixed_version"

def load_lessons():
    if not os.path.exists(LESSONS_FILE):
        return []
    with open(LESSONS_FILE) as f:
        return json.load(f)

def save_lessons(lessons):
    with open(LESSONS_FILE, "w") as f:
        json.dump(lessons, f, indent=2)

def create_lesson(pattern, lessons):
    failure_pattern, correction = LESSON_TEMPLATES[pattern]
    lesson = {
        "lesson_id": f"L{len(lessons) + 1}",
        "failure_pattern": failure_pattern,
        "correction": correction,
        "created_at": date.today().isoformat(),
        "use_count": 0,
        "pattern": pattern,
        "topic": "unrelated" if pattern == "unsupported_answer" else pattern.replace("missing_", ""),
    }
    lessons.append(lesson)
    return lesson

def relevant_lessons(question, lessons):
    return [lesson for lesson in lessons if lesson["topic"] == question_topic(question)]

def answering_agent(question, lessons, previous_answer=None, feedback=None):
    system_prompt = ANSWERING_PROMPT
    if lessons:
        system_prompt += "\n\nLessons from earlier mistakes (follow them):\n"
        system_prompt += "\n".join(f"- {lesson['correction']}" for lesson in lessons)

    if feedback is None:
        user_prompt = question
    else:
        user_prompt = (f"Question: {question}\n\nYour previous answer: {previous_answer}\n\n"
                       f"Evaluator feedback: {feedback}\n\nWrite a corrected answer.")
    return ask_llm(system_prompt, user_prompt)

def evaluator_agent(question, answer, reference):
    cve = find_cve(question)
    record = next((r for r in reference if r["cve"] == cve), None)
    answer_lower = answer.lower()

    #so questions not about vulnerability in the reference dataset aren't answered
    if record is None:
        if REFUSAL.lower().rstrip(".") in answer_lower:
            return {"result": "PASS",
                    "explanation": "The question is not in the reference dataset and the answer correctly declines.",
                    "feedback": "", "failure_pattern": None}
        return {"result": "REVISE",
                "explanation": "The question is not about a vulnerability in the reference dataset, but the answer gives an unsupported answer.",
                "feedback": f'Do not answer this question. Reply exactly: "{REFUSAL}"',
                "failure_pattern": "unsupported_answer"}

    topic = question_topic(question)
    if topic == "fixed_version":
        label = "fixed version"
        expected = " or ".join(record["fixed_versions"])
        correct = any(version in answer for version in record["fixed_versions"])
    elif topic == "severity":
        label = "severity"
        expected = record["severity"]
        correct = re.search(rf"\b{record['severity'].lower()}\b", answer_lower) is not None
    elif topic == "cvss_score":
        label = "CVSS score"
        expected = str(record["cvss_score"])
        numbers = re.findall(r"\d+(?:\.\d+)?", answer)
        correct = any(float(number) == record["cvss_score"] for number in numbers)
    else:
        label = "vulnerability type"
        expected = record["vulnerability_type"]
        correct = any(keyword in answer_lower for keyword in record["type_keywords"])

    if correct:
        return {"result": "PASS",
                "explanation": f"The answer gives the correct {label} ({expected}) from the reference dataset.",
                "feedback": "", "failure_pattern": None}
    return {"result": "REVISE",
            "explanation": f"The answer does not give the correct {label}. The reference dataset says: {expected}.",
            "feedback": f"State the {label} of {record['cve']} in {record['package']}: {expected}.",
            "failure_pattern": f"missing_{topic}"}

def run_question(item, reference, use_repair, lessons, first_answer=None):
    question = item["question"]
    start = time.perf_counter()
    used = relevant_lessons(question, lessons)
    for lesson in used:
        lesson["use_count"] += 1

    if first_answer is not None:
        answer = first_answer
    else:
        answer = answering_agent(question, used)
    evaluation = evaluator_agent(question, answer, reference)
    attempts = [{"answer": answer, "evaluation": evaluation}]
    if use_repair and evaluation["result"] == "REVISE" and len(attempts) < MAX_ATTEMPTS:
        answer = answering_agent(question, used, previous_answer=answer, feedback=evaluation["feedback"])
        evaluation = evaluator_agent(question, answer, reference)
        attempts.append({"answer": answer, "evaluation": evaluation})
    return {
        "id": item["id"],
        "question": question,
        "lessons_used": [lesson["lesson_id"] for lesson in used],
        "attempts": attempts,
        "number_of_attempts": len(attempts),
        "final_result": evaluation["result"],
        "final_answer": answer,
        "first_failure_pattern": attempts[0]["evaluation"]["failure_pattern"],
        "latency_ms": round((time.perf_counter() - start) * 1000, 1),
    }


def print_run(run):
    print(f"\nQuestion ({run['id']}): {run['question']}")
    print(f"Lessons loaded: {', '.join(run['lessons_used']) if run['lessons_used'] else 'none'}")
    for number, attempt in enumerate(run["attempts"], start=1):
        evaluation = attempt["evaluation"]
        print(f"Attempt {number} answer: {attempt['answer']}")
        print(f"Evaluator result: {evaluation['result']}")
        print(f"Evaluator explanation: {evaluation['explanation']}")
        if evaluation["feedback"]:
            print(f"Evaluator feedback: {evaluation['feedback']}")
    print(f"Number of attempts: {run['number_of_attempts']}")
    print(f"Final evaluation: {run['final_result']}")
    print(f"Final response: {run['final_answer']}")
    print(f"Latency: {run['latency_ms']} ms")