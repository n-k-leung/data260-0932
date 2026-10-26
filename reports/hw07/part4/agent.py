import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import pandas as pd
import tools

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(HERE, "..", "raw")

SEED = 932
OPTIONS = {"seed": SEED, "temperature": 0, "num_ctx": 8192}
MAX_STEPS = 8
MAX_REPAIRS = 2
REQUIRED_COLUMNS = ["start_time", "duration_sec"]

MEMBER = "Buy Monthly Membership"
PAY = "Pay Per Ride/Minute"
RATE_KEYS = ["pay_unlock_fee", "pay_free_minutes", "pay_per_minute", "member_price",
             "member_free_minutes", "member_extra_per_minute"]

def build_system_prompt(columns):
    return (
        "You are a cost advisor for the Bay Wheels bike share (San Francisco Bay Area). "
        "Decide between '" + MEMBER + "' and '" + PAY + "' for the rider whose "
        "trips are in the table trips.\n"
        "Tools:\n"
        "- csv_sql: one SELECT on the table trips. Columns: " + ", ".join(columns) + ". "
        "duration_sec is the ride length in seconds. start_time is text like "
        "2017-10-05 08:14:00.\n"
        "- policy_retriever: reads the official pricing page and returns short snippets.\n"
        "- calculator: does arithmetic. Never calculate in your head.\n"
        "Work in this order:\n"
        "1. Call csv_sql to get the number of rides, the average ride length in minutes "
        "and the number of distinct months (use substr(start_time, 1, 7)).\n"
        "2. Call policy_retriever to find the monthly membership price, the minutes "
        "included in every member ride, the extra price per minute after that, and for "
        "paying per ride: the single-ride price (or unlock fee), the minutes it includes "
        "and the price per extra minute. If several pricing URLs are given, call "
        "policy_retriever once for each URL. Use a query with many price words, for example "
        "'unlock per minute month membership free minutes single ride' and set k to 10.\n"
        "3. Use calculator to estimate both totals: pay-per-use = rides x (single-ride "
        "price + extra-minute price x average minutes beyond the included minutes); "
        "membership = price x months + extra minutes.\n"
        "4. Reply with ONE JSON object and nothing else. Keys: "
        "pay_unlock_fee (single-ride price or unlock fee), pay_free_minutes (minutes "
        "included in it, 0 if none), pay_per_minute, member_price, member_free_minutes, "
        "member_extra_per_minute (numbers copied from the snippets), "
        "decision ('" + MEMBER + "' or '" + PAY + "'), "
        "justification (3 to 6 sentences with numbers; put at least one short quote from a "
        "snippet inside double quotes), "
        "citations (list of 1 to 3 snippet texts copied exactly from policy_retriever), "
        "assumptions (list of short strings).\n"
        "Use only prices that appear in the snippets. For pay-per-use use the single-ride "
        "numbers only (not the day pass or annual plans); pay_free_minutes is 0 when a "
        "single ride is just an unlock fee plus a per-minute price. If a price is missing, use 0 and "
        "say so in assumptions. The program will recompute the exact costs from your "
        "six numbers and check your decision."
    )

def strip_thinking(text):
    if "</think>" in text:
        text = text.split("</think>")[-1]
    return text.strip()


def make_ollama_model_fn():
    sys.path.insert(0, os.path.join(HERE, "..", "backend"))
    from app.llm_adapter import client
    def ask(messages):
        return client.complete(messages, tools=tools.TOOL_SCHEMAS, options=OPTIONS)
    return ask


def normalize_trips(df):
    df = df.copy()
    df.columns = [str(c).strip().replace(" ", "_") for c in df.columns]
    notes = []
    if "start_time" not in df.columns and "started_at" in df.columns:
        df = df.rename(columns={"started_at": "start_time", "ended_at": "end_time"})
    if "duration_sec" not in df.columns and "start_time" in df.columns \
            and "end_time" in df.columns:
        start = pd.to_datetime(df["start_time"], errors="coerce")
        end = pd.to_datetime(df["end_time"], errors="coerce")
        df["duration_sec"] = (end - start).dt.total_seconds()
        notes.append("duration_sec was computed as end time minus start time.")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("the CSV needs these columns: " + ", ".join(missing))
    df["start_time"] = df["start_time"].astype(str)
    df["duration_sec"] = pd.to_numeric(df["duration_sec"], errors="coerce")
    before = len(df)
    df = df[df["duration_sec"] > 0]
    if len(df) < before:
        notes.append(str(before - len(df)) + " rows with a missing or non-positive "
                     "duration were removed.")
    return df, notes


def load_trips(df):
    df, notes = normalize_trips(df)
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    df.to_sql("trips", conn, index=False)
    return conn, list(df.columns), notes


def short(value, limit=500):
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + " ..."


def parse_final_json(text):
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None, "the reply has no JSON object"
    try:
        return json.loads(text[start:end + 1]), None
    except json.JSONDecodeError:
        return None, "the JSON could not be parsed"

def numbers_in(text):
    return {float(n) for n in re.findall(r"\d+(?:\.\d+)?|\.\d+", text)}

def check_answer(answer, ctx):
    tools_used = {t["tool"] for t in ctx["timeline"] if t["success"]}
    for needed in ["csv_sql", "policy_retriever"]:
        if needed not in tools_used:
            return "call " + needed + " successfully before you answer", None
    if not isinstance(answer, dict):
        return "the answer must be a JSON object", None
    rates = {}
    retrieved = ctx["retrieved"]
    known_numbers = numbers_in(" ".join(p["text"] for p in retrieved))
    for key in RATE_KEYS:
        try:
            rates[key] = float(answer[key])
        except (KeyError, TypeError, ValueError):
            return "key " + key + " must be a number", None
        if rates[key] < 0:
            return "key " + key + " cannot be negative", None
        if rates[key] != 0 and rates[key] not in known_numbers:
            return (key + "=" + str(rates[key]) + " does not appear in the snippets "
                    "from policy_retriever. Call policy_retriever again with a query like "
                    "'unlock per minute month free minutes' and k=10, then copy prices "
                    "from the snippets"), None

    decision = str(answer.get("decision", ""))
    if "member" in decision.lower():
        decision = MEMBER
    elif "pay" in decision.lower():
        decision = PAY
    else:
        return "decision must be '" + MEMBER + "' or '" + PAY + "'", None

    justification = str(answer.get("justification", "")).strip()
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", justification) if s.strip()]
    if not 3 <= len(sentences) <= 6:
        return "justification must have 3 to 6 sentences (it has " + str(len(sentences)) + ")", None

    quotes = re.findall(r'["\u201c]([^"\u201d]{8,})["\u201d]', justification)
    pool = " ".join(p["text"] for p in retrieved).lower()
    if not any(" ".join(q.split()).lower() in pool for q in quotes):
        return ("the justification must contain a short quote from a snippet, in double "
                "quotes, copied exactly"), None
    good = []
    for quote in answer.get("citations") or []:
        quote = " ".join(str(quote).split())
        for passage in retrieved:
            if quote and (quote in passage["text"] or passage["text"] in quote):
                if passage not in good:
                    good.append(passage)
    if not good:
        return "citations must be snippets copied exactly from policy_retriever", None

    assumptions = [str(a) for a in (answer.get("assumptions") or [])]
    return None, {"rates": rates, "decision": decision, "justification": justification,
                  "citations": good, "assumptions": assumptions}

def run_tool(ctx, name, args, by):
    started = time.time()
    result = tools.execute_tool(name, args, ctx)
    if name == "policy_retriever" and result["success"]:
        for passage in result["data"]["passages"]:
            if passage not in ctx["retrieved"]:
                ctx["retrieved"].append(passage)
    ctx["timeline"].append({
        "step": len(ctx["timeline"]) + 1,
        "by": by,
        "tool": name,
        "input": short(args, 300),
        "success": result["success"],
        "observation": short(result["data"] if result["success"] else result["error"]),
        "ms": round((time.time() - started) * 1000),
    })
    return result

def first_value(result, key):
    if not result["success"] or not result["data"]["rows"]:
        raise ValueError("a program query failed: " + str(result["error"]))
    return result["data"]["rows"][0][key]

def calc(ctx, expression):
    result = run_tool(ctx, "calculator", {"expression": expression}, "program")
    if not result["success"]:
        raise ValueError("calculator failed: " + str(result["error"]))
    return result["data"]["value"]

def pay_cost_sql(rates):
    m = "(duration_sec / 60.0)"
    f = str(rates["pay_free_minutes"])
    return ("(" + str(rates["pay_unlock_fee"]) + " + " + str(rates["pay_per_minute"]) +
        " * CASE WHEN " + m + " > " + f + " THEN " + m + " - " + f + " ELSE 0 END)")

def compute_costs(ctx, rates):
    pay_sql = pay_cost_sql(rates)
    price, free, extra = (rates["member_price"], rates["member_free_minutes"],
                          rates["member_extra_per_minute"])

    row = run_tool(ctx, "csv_sql", {"sql":
        "SELECT COUNT(*) AS rides, "
        "COUNT(DISTINCT substr(start_time, 1, 7)) AS months, "
        "SUM(duration_sec) / 60.0 AS total_minutes, "
        "SUM(" + pay_sql + ") AS pay_total, "
        "SUM(CASE WHEN duration_sec / 60.0 > " + str(free) + " THEN (duration_sec / 60.0 - "
        + str(free) + ") * " + str(extra) + " ELSE 0 END) AS extra_total "
        "FROM trips"}, "program")
    rides = first_value(row, "rides")
    months = first_value(row, "months")
    minutes = first_value(row, "total_minutes")
    pay_total = round(first_value(row, "pay_total"), 2)
    extra_total = round(first_value(row, "extra_total"), 2)
    member_total = round(calc(ctx, str(price) + " * " + str(months) + " + " + str(extra_total)), 2)
    saving = round(calc(ctx, "(" + str(pay_total) + ") - (" + str(member_total) + ")"), 2)
    rides_per_month = round(calc(ctx, str(rides) + " / " + str(months)), 1)
    minutes_per_ride = round(calc(ctx, str(minutes) + " / " + str(rides)), 1)
    pay_per_ride = calc(ctx, str(pay_total) + " / " + str(rides))
    extra_per_ride = calc(ctx, str(extra_total) + " / " + str(rides))
    gap = pay_per_ride - extra_per_ride
    break_even = None
    if gap > 0:
        break_even = round(calc(ctx, str(price) + " / " + "(" + str(round(gap, 6)) + ")"), 1)

    minutes_per_month = round(calc(ctx, str(minutes) + " / " + str(months)), 1)
    break_even_minutes = None
    if break_even is not None:
        break_even_minutes = round(calc(ctx, str(break_even) + " * " + str(minutes_per_ride)), 1)
    weekly = run_tool(ctx, "csv_sql", {"sql":
        "SELECT strftime('%Y-W%W', start_time) AS week, COUNT(*) AS rides, "
        "ROUND(AVG(duration_sec) / 60.0, 1) AS avg_minutes, "
        "ROUND(SUM(" + pay_sql + "), 2) AS spend "
        "FROM trips GROUP BY week ORDER BY week LIMIT 12"}, "program")
    weeks_total = run_tool(ctx, "csv_sql", {"sql":
        "SELECT COUNT(DISTINCT strftime('%Y-W%W', start_time)) AS weeks FROM trips"}, "program")
    return {
        "rides": rides, "months": months, "avg_minutes_per_ride": minutes_per_ride,
        "pay_total": pay_total, "member_price": price, "extra_charges": extra_total,
        "member_total": member_total, "saving_with_cheaper_option": abs(saving),
        "actual_rides_per_month": rides_per_month,
        "break_even_rides_per_month": break_even,
        "break_even_minutes_per_month": break_even_minutes,
        "actual_minutes_per_month": minutes_per_month,
        "weekly": weekly["data"]["rows"] if weekly["success"] else [],
        "weeks_total": first_value(weeks_total, "weeks"),
    }


def dataset_assumptions(columns):
    notes = [
        "The whole file is treated as the trips of ONE rider (the file has no rider id).",
        "A month is a calendar month that has at least one trip; a membership is bought "
        "for every such month.",
        "Pay-per-use is charged as the single-ride price (or unlock fee) for every ride, "
        "plus the per-minute price for the minutes beyond the included minutes.",
        "The weekly table uses SQLite weeks (%W, weeks start on Monday) and shows the "
        "first 12 weeks; spend is the pay-per-use cost.",
    ]
    if any("rideable" in c or "bike_type" in c for c in columns):
        notes.append("The file has a bike-type column, but e-bike surcharges are not "
                     "modelled: every ride is priced as a classic bike.")
    else:
        notes.append("No bike-type column (classic or electric), so every ride is "
                     "treated as a classic bike.")
    return notes

def save_snapshot(ctx, scenario, raw_dir):
    if not ctx["pages"]:
        return None
    parts, pages = [], []
    for url, (text, captured_at) in ctx["pages"].items():
        parts.append("### SOURCE: " + url + "\n" + text)
        pages.append({"url": url, "captured_at": captured_at,
                      "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
    data = "\n\n".join(parts).encode("utf-8")
    sha = hashlib.sha256(data).hexdigest()
    os.makedirs(raw_dir, exist_ok=True)
    text_file = "pricing_snapshot_" + scenario + ".txt"
    with open(os.path.join(raw_dir, text_file), "wb") as f:
        f.write(data)
    meta = {"scenario": scenario, "pages": pages, "access_date": pages[0]["captured_at"],
            "sha256": sha, "snapshot_file": text_file}
    with open(os.path.join(raw_dir, "pricing_snapshot_" + scenario + ".json"), "w",
              encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta

def run_agent(df, pricing_url, scenario="run", model_fn=None, raw_dir=RAW_DIR):
    started = time.time()
    conn, columns, load_notes = load_trips(df)
    ctx = {"conn": conn, "pages": {}, "timeline": [], "retrieved": []}
    model_fn = model_fn or make_ollama_model_fn()

    messages = [
        {"role": "system", "content": build_system_prompt(columns)},
        {"role": "user", "content": "Pricing page URL(s): " + pricing_url + "\nAnalyse the uploaded trips and decide."},
    ]
    stop_reason, final, problem_text = "max_steps_reached", None, None
    costs, costs_rates = None, None
    repairs = 0

    for turn in range(1, MAX_STEPS + 1):
        reply = model_fn(messages)
        text = strip_thinking(reply.get("content") or "")
        calls = reply.get("tool_calls") or []

        if calls:
            for call in calls:
                name, args = call.get("name"), call.get("arguments") or {}
                result = run_tool(ctx, str(name), args, "model")
                messages.append({"role": "assistant",
                                 "content": "Action: " + str(name) + " " + json.dumps(args)})
                messages.append({"role": "tool", "content":
                                 "Result of " + str(name) + ": " + short(result, 3000)})
            continue

        answer, problem = parse_final_json(text)
        checked = None
        if problem is None:
            problem, checked = check_answer(answer, ctx)
        if problem is None:
            if costs_rates != checked["rates"]:
                try:
                    costs = compute_costs(ctx, checked["rates"])
                except ValueError as e:
                    stop_reason, problem_text = "error", str(e)
                    break
                costs_rates = checked["rates"]
            expected = MEMBER if costs["member_total"] < costs["pay_total"] else PAY
            if checked["decision"] != expected:
                problem = ("your decision is " + checked["decision"] + " but the exact costs "
                           "from your numbers are pay-per-use $" + str(costs["pay_total"]) +
                           " and membership $" + str(costs["member_total"]) +
                           ", so the cheaper option is " + expected)
        if problem is None:
            final, stop_reason = checked, "final_answer"
            break
        repairs += 1
        if repairs > MAX_REPAIRS:
            stop_reason, problem_text = "repair_failed", problem
            break
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content": "Problem: " + problem +
                         ". Fix only this and answer again with the JSON object."})
    if final:
        ctx["timeline"].append({"step": len(ctx["timeline"]) + 1, "by": "model",
                                "tool": "final_answer", "input": "", "success": True,
                                "observation": short(final["justification"], 600), "ms": 0})
    snapshot = save_snapshot(ctx, scenario, raw_dir)
    result = {
        "scenario": scenario,
        "decision": final["decision"] if final else None,
        "justification": final["justification"] if final else None,
        "error": problem_text,
        "rates": final["rates"] if final else None,
        "costs": costs if final else None,
        "assumptions": (dataset_assumptions(columns) + load_notes + final["assumptions"]) if final else [],
        "citations": [{"text": p["text"], "source": p["source"]} for p in final["citations"]]
                     if final else [],
        "pricing_url": pricing_url,
        "pages": snapshot["pages"] if snapshot else [],
        "sha256": snapshot["sha256"] if snapshot else None,
        "snapshot_file": snapshot["snapshot_file"] if snapshot else None,
        "timeline": ctx["timeline"],
        "metrics": {"steps": len(ctx["timeline"]),
                    "total_time_s": round(time.time() - started, 2),
                    "stop_reason": stop_reason},
    }
    os.makedirs(raw_dir, exist_ok=True)
    with open(os.path.join(raw_dir, "run_" + scenario + ".json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    return result