import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()
SRC_PATH = os.getenv("HW1_SRC_PATH", os.path.join(os.path.dirname(__file__), "..", "..", "..", "..","src"))
sys.path.insert(0, SRC_PATH)
from model_client import ModelClient
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("SMOL_MODEL", "qwen3:8b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

client = ModelClient(model=MODEL, base_url=OLLAMA_URL)


def chat(messages) :
    try:
        result = client.complete(messages,options={"seed": 932, "temperature": 0})
    except Exception as e:
        raise RuntimeError("Model service error: " + str(e))
    text = result["content"]
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    return text, result["input_tokens"], result["output_tokens"]

def embed(text):
    try:
        r = requests.post(
            OLLAMA_URL + "/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["embedding"]
    except requests.RequestException as e:
        raise RuntimeError("Embedding service error: " + str(e))
