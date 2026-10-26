import json
import os
import re
from datetime import UTC, datetime, timedelta

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
AGENT_FILE = os.path.join(REPO_ROOT, "AGENT.md")
MEMORY_FILE = os.path.join(REPO_ROOT, "MEMORY.md")
ARCHIVE_FILE = os.path.join(REPO_ROOT, "MEMORY_archive.md")
MAX_MEMORY_LINES = 40
MAX_AGE_HOURS = 24
STAMP_PATTERN = re.compile(r"<!-- \s*last_consolidated: \s*(\S+)\s *-->")
FACT_PATTERN = re.compile(r"^- \[(.+?)\](.+) \((\d{4}-\d{2}-\d{2})\)\s*$")
RISKY_WORDS = [
    "only",
    "for now",
    "temporar",
    "just for",
    "this week",
    "today",
    "one-time",
    "this one",
]


def read_file(path):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_file(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def load_files():
    return read_file(AGENT_FILE), read_file(MEMORY_FILE)


def is_comment(line):
    return line.strip().startswith("<!--")


def build_system_prompt():
    agent_text, memory_text = load_files()
    # the timestamp comment is only for the program, so leave it out of the prompt
    memory_for_prompt = "\n".join(
        l for l in memory_text.splitlines() if not is_comment(l)
    )
    return agent_text + "\n\n# Long-term memory (from MEMORY.md)\n" + memory_for_prompt


def get_last_consolidated(text):
    match = STAMP_PATTERN.search(text)
    if not match:
        return None
    try:
        when = datetime.fromisoformat(match.group(1))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return when


def make_stamp_line(now):
    return "<!-- last_consolidated: " + now.isoformat() + " -->"


def count_memory_lines(text):
    return sum(1 for line in text.splitlines() if line.strip() and not is_comment(line))


def needs_consolidation(text, now=None):
    now = now or datetime.now(UTC)
    count = count_memory_lines(text)
    if count > MAX_MEMORY_LINES:
        return True, f"{count} non-empty, non-comment lines (limit {MAX_MEMORY_LINES})"
    last = get_last_consolidated(text)
    if last is None:
        return True, "no last-consolidated timestamp is recorded"
    age = now - last
    if age > timedelta(hours=MAX_AGE_HOURS):
        return (
            True,
            f"last consolidated {age.total_seconds() / 3600:.1f} hours ago (limit {MAX_AGE_HOURS})",
        )
    return (
        False,
        f"{count} lines, consolidated {age.total_seconds() / 3600: .1f} hours ago",
    )


def parse_memory(text):
    facts = []
    notes = []
    for line in text.splitlines():
        line = line.strip()
        if not line or is_comment(line) or line.startswith("#"):
            continue
        match = FACT_PATTERN.match(line)
        if match:
            facts.append(
                {
                    "topic": match.group(1).strip(),
                    "text": match.group(2).strip(),
                    "date": match.group(3),
                }
            )
        else:
            notes.append(line)
    return facts, notes


def normalize(text):
    text = re.sub(r"[^a-z0-9 ]", "", text.lower())
    return " ".join(text.split())


def looks_temporary(text):
    lowered = text.lower()
    return any(word in lowered for word in RISKY_WORDS)


def consolidate_text(text, now=None):
    now = now or datetime.now(UTC)
    facts, notes = parse_memory(text)

    kept = {}
    order = []
    duplicates = []
    resolutions = []

    for fact in facts:
        key = fact["topic"].lower()
        if key not in kept:
            kept[key] = fact
            order.append(key)
            continue
        old = kept[key]
        if normalize(old["text"]) == normalize(fact["text"]):
            # keep only one of the dumplicates
            newest_date = max(old["date"], fact["date"])
            kept[key] = {
                "topic": old["topic"],
                "text": old["text"],
                "date": newest_date,
            }
            duplicates.append(
                {"topic": fact["topic"], "dropped": fact, "kept": kept[key]}
            )
        else:
            if fact["date"] >= old["date"]:
                winner, loser = fact, old
            else:
                winner, loser = old, fact
            kept[key] = winner
            resolutions.append(
                {
                    "topic": winner["topic"],
                    "kept": winner,
                    "dropped": loser,
                    "suspect": looks_temporary(winner["text"]),
                }
            )

    lines = [make_stamp_line(now), "# MEMORY", ""]
    for key in order:
        f = kept[key]
        lines.append(f"- [{f['topic']}] {f['text']} ({f['date']})")
    if notes:
        lines += ["", "## Other notes"] + notes
    new_text = "\n".join(lines) + "\n"
    archive_lines = []
    for d in duplicates:
        x = d["dropped"]
        archive_lines.append(
            f'- MERGED_DUPLICATE [{d["topic"]}] "{x["text"]}" ({x["date"]}) '
            f" | same as kept fact dated {d['kept']['date']}"
        )
    for r in resolutions:
        k, x = r["kept"], r["dropped"]
        line = (
            f'- SUPERSEDED [{r["topic"]}] "{x["text"]}" ({x["date"]})'
            f'| replaced by "{k["text"]}" ({k["date"]}) | rule: newest date wins'
        )
        if r["suspect"]:
            line += (
                " | CHECK: newer fact sounds temporary, this may be the WRONG choice"
            )
        archive_lines.append(line)
    if archive_lines:
        archive_lines.insert(0, " <!-- consolidation at " + now.isoformat() + " -->")

    report = {
        "facts_before": len(facts),
        "facts_after": len(kept),
        "duplicates": duplicates,
        "resolutions": resolutions,
        "suspect_resolutions": [r for r in resolutions if r["suspect"]],
        "archive_lines": archive_lines,
    }
    return new_text, report


def consolidate_file(memory_path=MEMORY_FILE, archive_path=ARCHIVE_FILE):
    old_text = read_file(memory_path)
    new_text, report = consolidate_text(old_text)
    if report["archive_lines"]:
        with open(archive_path, "a", encoding="utf-8") as f:
            f.write("\n".join(report["archive_lines"]) + "\n")
    write_file(memory_path, new_text)
    report["lines_before"] = count_memory_lines(old_text)
    report["lines_after"] = count_memory_lines(new_text)
    report["total_lines_before"] = len(old_text.splitlines())
    report["total_lines_after"] = len(new_text.splitlines())
    return report


def help_text():
    return (
        "Available commands: \n"
        "/memory show the current file-based memory (AGENT.md and MEMORY.md) \n"
        "/ compact consolidate MEMORY.md and compress the chat history; shows counts before and after\n"
        "/dream find useful long-term facts in the recent conversation and add them to MEMORY.md\n"
        "/help show this list\n"
        "/exit quit"
    )


def show_memory():
    agent_text, memory_text = load_files()
    needed, reason = needs_consolidation(memory_text)
    return (
        "AGENT.md\n"
        + agent_text
        + "\n\n MEMORY.md \n"
        + memory_text
        + f"\n\n[status] {count_memory_lines(memory_text)} memory lines | "
        f"consolidation needed: {needed} ({reason})"
    )


def compact_history(messages, keep_last=4):
    from . import llm_adapter

    if len(messages) <= keep_last + 2:
        return messages
    old_part = messages[1:-keep_last]
    transcript = "\n".join(m["role"] + ": " + m["content"] for m in old_part)
    prompt = "Summarize this conversation in 3 short bullet points: \n\n" + transcript
    summary, _, _ = llm_adapter.chat([{"role": "user", "content": prompt}])
    summary_message = {
        "role": "user",
        "content": "(Summary of the earlier chat) " + summary,
    }
    return [messages[0], summary_message] + messages[-keep_last:]


def run_compact(messages):
    report = consolidate_file()
    before_msgs = len(messages)
    new_messages = compact_history(messages)
    new_messages[0] = {"role": "system", "content": build_system_prompt()}
    text = (
        f"[/compact] MEMORY.md lines: {report['lines_before']} -> {report['lines_after']}"
        f"(duplicates merged: {len(report['duplicates'])}, "
        f"contradictions resolved: {len(report['resolutions'])})\n"
        f"[/compact] Conversation messages: {before_msgs} -> {len(new_messages)}"
    )
    for r in report["suspect_resolutions"]:
        text += f"\n[/compact] CHECK [{r['topic']}]: newest-wins may be wrong, see {os.path.basename(ARCHIVE_FILE)}"
    return new_messages, text


# reload memory


def run_dream(recent_messages):
    from . import llm_adapter

    transcript = "\n".join(
        m["role"] + ": " + m["content"]
        for m in recent_messages
        if m["role"] != "system"
    )
    if not transcript.strip():
        return []
    prompt = (
        "Read the conversation below. List up to 5 long-term facts worth remembering "
        "(user details, project decisions, preferences). Reply with ONLY a JSON list like "
        '[{"topic": "user.name", "fact": "The user is named test"}].'
        "topic is a short lowercase label with dots. If there is nothing, reply [].\n\n"
        + transcript
    )
    reply, _, _ = llm_adapter.chat([{"role": "user", "content": prompt}])
    start, end = reply.find("["), reply.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        items = json.loads(reply[start : end + 1])
    except json.JSONDecodeError:
        return []

    existing, _ = parse_memory(read_file(MEMORY_FILE))
    seen = {(f["topic"].lower(), normalize(f["text"])) for f in existing}
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    added = []
    for item in items[:5]:
        if not isinstance(item, dict) or not item.get("topic") or not item.get("fact"):
            continue
        topic = str(item["topic"]).strip()
        fact = str(item["fact"]).strip()
        if (topic.lower(), normalize(fact)) in seen:
            continue
        added.append(f"- [{topic}] {fact} ({today})")
        seen.add((topic.lower(), normalize(fact)))
    if added:
        text = read_file(MEMORY_FILE)
        if text and not text.endswith("\n"):
            text += "\n"
        write_file(MEMORY_FILE, text + "\n".join(added) + "\n")
    return added


def review_code(code_text):
    from . import llm_adapter

    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": code_text},
    ]
    reply, _, _ = llm_adapter.chat(messages)
    return reply


INTRO_WORDS = [
    "here are",
    "here is",
    "sure",
    "certainly",
    "i found",
    "below",
    "let me",
    "the following",
]
SUMMARY_WORDS = [
    "in summary",
    "summary",
    "overall",
    "in conclusion",
    "to summarize",
    "to sum up",
]


def check_reply_follows_agent_md(reply, expect_no_issue=False):
    lines = [l.strip() for l in reply.splitlines() if l.strip()]
    bullets = [l[2:].strip() if l[:2] in ("- ", "* ", "• ") else None for l in lines]
    results = []
    bad = [l for l, b in zip(lines, bullets) if b is None]
    results.append(
        (
            "only bullet points",
            len(lines) > 0 and not bad,
            "all lines are bullets" if not bad else "not a bullet: " + bad[0][:40],
        )
    )

    texts = [b for b in bullets if b is not None]
    starts = [t.lower() for t in texts]
    intro = any(s.startswith(w) for s in starts[:1] for w in INTRO_WORDS)
    summary = any(s.startswith(w) for s in starts[-1:] for w in SUMMARY_WORDS)
    results.append(
        (
            "no introduction or summary",
            not intro and not summary,
            "none found" if not (intro or summary) else "intro or summary bullet found",
        )
    )
    too_long = [t for t in texts if len(t.split()) > 35 in t]
    results.append(
        (
            "one issue per bullet",
            not too_long,
            "every bullet is short and one sentence"
            if not too_long
            else "long bullet: " + too_long[0][:40],
        )
    )
    normal = [normalize(t) for t in texts]
    results.append(
        (
            "no repeated bullets",
            len(normal) == len(set(normal)),
            "all bullets are different"
            if len(normal) == len(set(normal))
            else "a bullet is repeated",
        )
    )
    has_code = "```" in reply or "`" in reply
    results.append(
        (
            "no code shown",
            not has_code,
            "no backticks found" if not has_code else "backticks found",
        )
    )
    if expect_no_issue:
        ok = len(texts) == 1 and normalize(texts[0]) == normalize(
            "There are no errors in the code"
        )
        results.append(
            (
                "no-issue reply",
                ok,
                "exact sentence used"
                if ok
                else "expected: There are no errors in the code",
            )
        )
    return results
