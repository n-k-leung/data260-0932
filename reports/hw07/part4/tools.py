import ast
import re
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def make_result(success, data=None, error=None, source=None):
    return {
        "success": success,
        "data": data,
        "error": error,
        "source": source,
        "ts": now_iso(),
    }

MAX_ROWS_RETURNED = 20
SQL_CONTRACT = True
FORBIDDEN_WORDS = ["insert", "update", "delete", "drop", "alter", "create", "attach","detach", "pragma", "vacuum", "load_extension"]

def check_select_contract(sql):
    text = sql.strip()
    if text.endswith(";"):
        text = text[:-1].strip()
    if ";" in text:
        return "only ONE statement is allowed"
    if not text.lower().startswith("select"):
        return "only SELECT queries are allowed"
    if "--" in text or "/*" in text:
        return "SQL comments are not allowed"
    lowered = text.lower()
    for word in FORBIDDEN_WORDS:
        if re.search(r"\b" + word + r"\b", lowered):
            return "the word '" + word + "' is not allowed in a read-only query"
    return None

def csv_sql(conn, sql):
    if not isinstance(sql, str) or not sql.strip():
        return make_result(False, error="sql must be a non-empty string",
                           source="uploaded.csv")
    if SQL_CONTRACT:
        problem = check_select_contract(sql)
        if problem:
            return make_result(False, error=problem, source="uploaded.csv")
    try:
        cursor = conn.execute(sql)
        if cursor.description is None:
            conn.commit()
            return make_result(True, {"rows": [], "row_count": cursor.rowcount,
                                      "source": "uploaded.csv"}, source="uploaded.csv")
        names = [col[0] for col in cursor.description]
        all_rows = cursor.fetchall()
    except Exception as e:
        return make_result(False, error=str(e), source="uploaded.csv")

    rows = [dict(zip(names, row)) for row in all_rows[:MAX_ROWS_RETURNED]]
    data = {"rows": rows, "row_count": len(all_rows), "source": "uploaded.csv"}
    return make_result(True, data, source="uploaded.csv")

STOP_WORDS = {"the", "and", "for", "per", "with", "that", "this", "from"}
def fetch_page_text(url):
    reply = requests.get(url, timeout=20,
                         headers={"User-Agent": "Mozilla/5.0 (course project)"})
    reply.raise_for_status()
    soup = BeautifulSoup(reply.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    lines = [" ".join(line.split()) for line in soup.get_text("\n").splitlines()]
    return "\n".join(line for line in lines if line)


def split_into_snippets(page_text):
    snippets = []
    for line in page_text.splitlines():
        if len(line) <= 300:
            snippets.append(line)
        else:
            for sentence in re.split(r"(?<=[.!?])\s+", line):
                if sentence:
                    snippets.append(sentence[:300])
    return snippets

def policy_retriever(pages, url, query, k=8):
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return make_result(False, error="url must start with http:// or https://", source=str(url))
    try:
        if url not in pages:
            text = fetch_page_text(url)
            if len(text) < 200:
                return make_result(
                    False, source=url,
                    error="page text is too short (is the page built with JavaScript?)")
            pages[url] = (text, now_iso())
        page_text = pages[url][0]
    except Exception as e:
        return make_result(False, error="could not fetch page: " + str(e), source=url)

    k = max(1, min(int(k or 8), 10))
    keywords = [w for w in re.findall(r"[a-z]{3,}", query.lower())
                if w not in STOP_WORDS]
    keywords = [w[:-1] if w.endswith("s") and len(w) > 3 else w for w in keywords]
    keywords = list(dict.fromkeys(keywords))
    if not keywords:
        return make_result(False, error="query has no usable words", source=url)
    scored = []
    seen = set()
    for snippet in split_into_snippets(page_text):
        low = snippet.lower()
        hits = sum(1 for w in keywords if w in low)
        has_price = "$" in snippet
        if (hits == 0 and not has_price) or snippet in seen:
            continue
        seen.add(snippet)
        score = hits / len(keywords)
        if has_price:
            score += 0.25 if hits else 0.2
        scored.append({"text": snippet, "source": url, "score": round(min(score, 1.0), 2)})

    scored.sort(key=lambda p: p["score"], reverse=True)
    return make_result(True, {"passages": scored[:k]}, source=url)

ALLOWED_EXPRESSION = re.compile(r"^[0-9+\-*/().\s]+$")

def calc_node(node):
    if isinstance(node, ast.Expression):
        return calc_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = calc_node(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp):
        left, right = calc_node(node.left), calc_node(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
    raise ValueError("unsupported expression")

def calculator(expression, units=None):
    if not isinstance(expression, str) or not ALLOWED_EXPRESSION.match(expression):
        return make_result(False, error="expression may only contain digits and + - * / ( ) .",
                           source="calculator")
    try:
        value = calc_node(ast.parse(expression.strip(), mode="eval"))
    except ZeroDivisionError:
        return make_result(False, error="division by zero", source="calculator")
    except Exception as e:
        return make_result(False, error="bad expression: " + str(e), source="calculator")
    data = {"value": value}
    if units:
        data["units"] = units
    return make_result(True, data, source="calculator")

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "csv_sql",
        "description": "Run one read-only SELECT query on the uploaded trips table "
                       "called trips. Returns rows, row_count and source.",
        "parameters": {"type": "object",
                       "properties": {"sql": {"type": "string",
                                              "description": "a single SELECT statement"}},
                       "required": ["sql"]}}},
    {"type": "function", "function": {
        "name": "policy_retriever",
        "description": "Fetch the official pricing page and return short quotable "
                       "snippets (passages with text, source, score). Lines with a "
                       "dollar price are always included.",
        "parameters": {"type": "object",
                       "properties": {"url": {"type": "string"},
                                      "query": {"type": "string",
                                                "description": "words to look for"},
                                      "k": {"type": "integer",
                                            "description": "how many snippets (default 8, at most 10)"}},
                       "required": ["url", "query"]}}},
    {"type": "function", "function": {
        "name": "calculator",
        "description": "Safe arithmetic. Only digits and + - * / ( ) . are allowed.",
        "parameters": {"type": "object",
                       "properties": {"expression": {"type": "string"},
                                      "units": {"type": "string"}},
                       "required": ["expression"]}}},
]

PYTHON_TYPES = {"string": str, "integer": int}
def check_arguments(name, args):
    schema = None
    for item in TOOL_SCHEMAS:
        if item["function"]["name"] == name:
            schema = item["function"]["parameters"]
    if schema is None:
        return "unknown tool: " + str(name)
    if not isinstance(args, dict):
        return "arguments must be an object"
    for key in schema["required"]:
        if key not in args:
            return "missing argument: " + key
    for key, value in args.items():
        if key not in schema["properties"]:
            return "unexpected argument: " + key
        wanted = PYTHON_TYPES[schema["properties"][key]["type"]]
        if not isinstance(value, wanted) or isinstance(value, bool):
            return "argument " + key + " must be of type " + schema["properties"][key]["type"]
    return None

def execute_tool(name, args, ctx):
    problem = check_arguments(name, args)
    if problem:
        return make_result(False, error=problem, source=name)
    if name == "csv_sql":
        return csv_sql(ctx["conn"], args["sql"])
    if name == "policy_retriever":
        return policy_retriever(ctx["pages"], args["url"], args["query"], args.get("k", 8))
    return calculator(args["expression"], args.get("units"))