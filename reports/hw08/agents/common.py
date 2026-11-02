import json
from datetime import datetime
from ollama import AsyncClient

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
INBOX_TOPIC = "s0932_inbox"
TASKS_TOPIC = "s0932_tasks"
DRAFTS_TOPIC = "s0932_drafts"
FINAL_TOPIC = "s0932_final"
MODEL = "qwen3:8b"
SEED = 932

def log(text):
    print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} {text}", flush=True)
    
def to_bytes(message):
    return json.dumps(message).encode()

def from_bytes(raw):
    return json.loads(raw.decode())

#ask Ollama one question and return answer
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
