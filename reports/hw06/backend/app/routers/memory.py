import uuid
from fastapi import APIRouter, HTTPException
from pymongo.errors import PyMongoError

from ..memory_schema import ChatRequest
from ..memory_logic import SHORT_TERM_N
from ..mongo import get_messages_col, get_summaries_col, get_episodes_col
from .. import memory_logic as mem
from .. import llm_adapter

router = APIRouter(prefix="/api", tags=["Memory (MongoDB)"])

@router.post("/chat")
def chat(payload: ChatRequest):
    user_id = payload.user_id
    session_id = payload.session_id or str(uuid.uuid4())

    try:
        mem.save_message(user_id, session_id, "user", payload.message)
        window = mem.get_short_term(user_id, session_id, SHORT_TERM_N + 1)[ :- 1]
        session_summary = mem.get_latest_summary(user_id, "session", session_id)
        lifetime_summary = mem.get_latest_summary(user_id, "user")
        facts = mem.retrieve_episodes(user_id, payload.message)
        prompt = mem.build_prompt(session_summary, lifetime_summary,
        window, payload.message, facts)
        reply, prompt_tokens, completion_tokens = llm_adapter.chat(prompt)
        mem.save_message(user_id, session_id, "assistant", reply)
        summary_created = mem.maybe_summarize(user_id, session_id)
        mem.save_episodes(user_id, session_id, mem.extract_facts(payload.message))

    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except PyMongoError:
        raise HTTPException(status_code=500, detail="Database error in chat")

    return {
        "reply": reply,
        "session_id": session_id,
        "memory_used": {
            "short_term_count": len(window),
            "short_term_messages": window,
            "session_summary": session_summary,
            "lifetime_summary": lifetime_summary,
            "episodic_facts": facts,
            "new_summary_created": summary_created,
        },
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
    }

@router.get("/memory/{user_id}")
def get_memory(user_id: str):
    try:
        msgs = list(get_messages_col().find({"user_id": user_id},{"_id": 0})
        .sort([("created_at", -1), ("_id", -1)]).limit(16))
        msgs.reverse()
        #latest session summ with latest lifetime summ
        session_doc = get_summaries_col().find_one(
        {"user_id": user_id, "scope": "session"}, {"_id": 0},
        sort=[("created_at", -1),("_id", -1)])
        lifetime_doc = get_summaries_col().find_one(
        {"user_id": user_id, "scope": "user"}, {"_id": 0},
        sort=[("created_at", -1),("_id", -1)])
        #last episodic facts
        episodes = list(get_episodes_col().find({"user_id": user_id}, {"_id": 0, "embedding": 0})
        .sort([("created_at",-1),("_id",-1)]).limit(20))
    except PyMongoError:
        raise HTTPException(status_code=500, detail="Database error while reading memory")
    return {"user_id": user_id, "messages": msgs,
        "latest_session_summary": session_doc,
        "latest_lifetime_summary": lifetime_doc,
        "episodic_facts": episodes}

@router.get("/aggregate/{user_id}")
def get_aggregate(user_id: str):
    try:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
        daily = [{"date": r["_id"], "count": r["count"]} for r in get_messages_col().aggregate(pipeline)]
        #small list of the most recent summaries
        recent = list(get_summaries_col().find({"user_id": user_id}, {"_id": 0})
    .sort([("created_at",-1),("_id",-1)]).limit(5))
    except PyMongoError:
        raise HTTPException(status_code=500, detail="Database error while aggregating")
    return {"user_id": user_id, "daily_message_counts": daily, "recent_summaries": recent}

