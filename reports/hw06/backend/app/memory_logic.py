import json
import math
import os
from datetime import UTC, datetime

from dotenv import load_dotenv

from . import llm_adapter
from .mongo import get_episodes_col, get_messages_col, get_summaries_col

load_dotenv()

SHORT_TERM_N = int(os.getenv("SHORT_TERM_N", "12"))
SUMMARIZE_EVERY_USER_MSGS = int(os.getenv("SUMMARIZE_EVERY_USER_MSGS", "5"))
TOP_K = int(os.getenv("TOP_K", "3"))
CONDENSE_EVERY_N_SUMMARIES = int(os.getenv("CONDENSE_EVERY_N_SUMMARIES", "2"))

SYSTEM_PRIMER = "You are a helpful assistant for a vulnerability management app. Use the memory provided below when it is relevant. Keep answers short."


def now_utc():
    return datetime.now(UTC)


def save_message(user_id, session_id, role, content):
    get_messages_col().insert_one(
        {
            "user_id": user_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": now_utc(),
        }
    )


def get_short_term(user_id, session_id, n):
    rows = list(
        get_messages_col()
        .find(
            {"user_id": user_id, "session_id": session_id},
            {"_id": 0, "role": 1, "content": 1},
        )
        .sort([("created_at", -1), ("_id", -1)])
        .limit(n)
    )
    rows.reverse()
    return rows


def get_latest_summary(user_id, scope, session_id=None):
    query = {"user_id": user_id, "scope": scope}
    if scope == "session":
        query["session_id"] = session_id
    doc = get_summaries_col().find_one(
        query, {"_id": 0}, sort=[("created_at", -1), ("_id", -1)]
    )
    return doc["text"] if doc else None


def save_summary(user_id, session_id, scope, text):
    get_summaries_col().insert_one(
        {
            "user_id": user_id,
            "session_id": session_id,
            "scope": scope,
            "text": text,
            "created_at": now_utc(),
        }
    )


def maybe_summarize(user_id, session_id):
    user_msg_count = get_messages_col().count_documents(
        {"user_id": user_id, "session_id": session_id, "role": "user"}
    )
    if user_msg_count == 0 or user_msg_count % SUMMARIZE_EVERY_USER_MSGS != 0:
        return False

    recent = get_short_term(user_id, session_id, SUMMARIZE_EVERY_USER_MSGS * 2)
    transcript = "\n".join(m["role"] + ": " + m["content"] for m in recent)
    prompt = (
        "Summarize this conversation into 3-5 concise bullet points."
        "Keep names, numbers and decisions. \n\n" + transcript
    )
    text, _, _ = llm_adapter.chat([{"role": "user", "content": prompt}])
    save_summary(user_id, session_id, "session", text)
    session_summary_count = get_summaries_col().count_documents(
        {"user_id": user_id, "scope": "session"}
    )
    if session_summary_count % CONDENSE_EVERY_N_SUMMARIES == 0:
        condense_lifetime(user_id)
    return True


def condense_lifetime(user_id):
    rows = list(
        get_summaries_col()
        .find({"user_id": user_id, "scope": "session"}, {"_id": 0, "text": 1})
        .sort([("created_at", -1), ("_id", -1)])
        .limit(CONDENSE_EVERY_N_SUMMARIES)
    )
    rows.reverse()
    old_lifetime = get_latest_summary(user_id, "user")
    parts = []
    if old_lifetime:
        parts.append("Previous lifetime summary:\n" + old_lifetime)
    for r in rows:
        parts.append("Session summary: \n" + r["text"])
    prompt = (
        "Merge the summaries below into one short lifetime summary"
        "(max 6 bullet points) about this user.\n\n" + "\n\n".join(parts)
    )
    text, _, _ = llm_adapter.chat([{"role": "user", "content": prompt}])
    save_summary(user_id, None, "user", text)


def extract_facts(user_message):
    prompt = (
        "Extract up to 3 short facts worth remembering from the user message below."
        'Reply with ONLY a JSON list like [{"fact": " ... ", "importance": 0.7}].'
        "importance is a number from 0 to 1."
        "If nothing is worth remembering reply with [].\n\n"
        "User message: " + user_message
    )
    text, _, _ = llm_adapter.chat([{"role": "user", "content": prompt}])
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        items = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []

    facts = []
    for item in items[:3]:
        if not isinstance(item, dict) or not item.get("fact"):
            continue
        try:
            importance = float(item.get("importance", 0.5))
        except (TypeError, ValueError):
            importance = 0.5
        importance = max(0.0, min(1.0, importance))
        facts.append({"fact": str(item["fact"])[:200], "importance": importance})
    return facts


def save_episodes(user_id, session_id, facts):
    docs = []
    for f in facts:
        docs.append(
            {
                "user_id": user_id,
                "session_id": session_id,
                "fact": f["fact"],
                "importance": f["importance"],
                "embedding": llm_adapter.embed(f["fact"]),
                "created_at": now_utc(),
            }
        )
    if docs:
        get_episodes_col().insert_many(docs)


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    len_a = math.sqrt(sum(x * x for x in a))
    len_b = math.sqrt(sum(y * y for y in b))
    if len_a == 0 or len_b == 0:
        return 0.0
    return dot / (len_a * len_b)


def retrieve_episodes(user_id, message, k=TOP_K):
    episodes = list(get_episodes_col().find({"user_id": user_id}))
    if not episodes:
        return []
    query_vec = llm_adapter.embed(message)
    scored = []
    for ep in episodes:
        score = cosine_similarity(query_vec, ep["embedding"])
        scored.append(
            {
                "fact": ep["fact"],
                "importance": ep["importance"],
                "score": round(score, 4),
            }
        )
    scored.sort(key=lambda e: e["score"], reverse=True)  # best match first
    return scored[:k]


def build_prompt(session_summary, lifetime_summary, window, message, facts):
    system_text = SYSTEM_PRIMER
    if lifetime_summary:
        system_text += "\n\nLifetime summary of this user: \n" + lifetime_summary
    if session_summary:
        system_text += "\n\nSummary of this session so far: \n" + session_summary
    messages = [{"role": "system", "content": system_text}]
    messages.extend(window)
    final = message
    if facts:
        final += "\n\n(Relevant remembered facts: \n"
        final += "\n".join("- " + f["fact"] for f in facts) + ")"
    messages.append({"role": "user", "content": final})
    return messages


def estimate_tokens(text):
    return len(text) // 4


def compress_window(window):
    result = []
    cutoff = len(window) - 4
    for i, m in enumerate(window):
        content = m["content"]
        if m["role"] == "assistant" and i < cutoff and len(content) > 150:
            content = content[:150] + " .."
        result.append({"role": m["role"], "content": content})
    return result
