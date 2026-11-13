"""Settings and helpers shared by planner.py, writer.py, reviewer.py and send_question.py."""
import json
import os
from datetime import datetime

from ollama import AsyncClient

# The agents run on your laptop, so they use Kafka's localhost listener
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

INBOX_TOPIC = "s0932_inbox"
TASKS_TOPIC = "s0932_tasks"
DRAFTS_TOPIC = "s0932_drafts"
FINAL_TOPIC = "s0932_final"
DEAD_LETTER_TOPIC = "s0932_dead_letter"

MODEL = "qwen3:8b"
SEED = 932
VERIFY_SEED = 260932  # 260000 + SID4, used by the ordering test

# reports/hw08/raw – where the experiment CSV files are saved
RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "raw")


# Print a log line with the current time so the order of events is easy to follow
def log(text):
    print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} {text}", flush=True)


# Turn a Python dict into bytes for Kafka, and bytes back into a dict
def to_bytes(message):
    return json.dumps(message).encode()


def from_bytes(raw):
    return json.loads(raw.decode())


# Ask the local Ollama model one question and return its text answer.
# AsyncClient is used so a slow answer does not freeze the Kafka consumer.
async def ask_llm(system_prompt, user_prompt):
    response = await AsyncClient().chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        options={"seed": SEED, "temperature": 0},
        think=False,
    )
    return response["message"]["content"].strip()
