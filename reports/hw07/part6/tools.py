import difflib
import fnmatch
import glob
import os
import re
import subprocess

SANDBOX_ROOT = None
MAX_FILE_BYTES = 100000
MAX_RESULTS = 50
MAX_DIFF_LINES = 20
BLOCKED_NAMES = [".env", "id_rsa", "credentials"]
BLOCKED_ENDINGS = (".pem", ".key")

def set_sandbox(folder):
    global SANDBOX_ROOT
    SANDBOX_ROOT = os.path.realpath(folder)
    
def resolve_path(path):
    if SANDBOX_ROOT is None:
        return None, "sandbox folder is not set"
    if not isinstance(path, str) or not path.strip():
        return None, "path must be a non-empty string"
    full = os.path.realpath(os.path.join(SANDBOX_ROOT, path))
    if full != SANDBOX_ROOT and not full.startswith(SANDBOX_ROOT + os.sep):
        return None, "blocked: path is outside the sandbox"
    name = os.path.basename(full)
    if name in BLOCKED_NAMES or name.endswith(BLOCKED_ENDINGS):
        return None, "blocked: secret file"
    return full, None

def relative(full):
    return os.path.relpath(full, SANDBOX_ROOT)

def read_file(path, max_lines=None):
    full, problem = resolve_path(path)
    if problem:
        return {"ok": False, "error": problem}
    if not os.path.isfile(full):
        return {"ok": False, "error": "file not found: " + str(path)}
    if os.path.getsize(full) > MAX_FILE_BYTES:
        return {"ok": False, "error": "file is too big to read"}
    with open(full, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    shown = lines
    if max_lines is not None and max_lines > 0:
        shown = lines[:max_lines]
    return {"ok": True, "path": relative(full), "content": "\n".join(shown),
            "total_lines": len(lines), "truncated": len(shown) < len(lines)}

def write_file(path, content):
    full, problem = resolve_path(path)
    if problem:
        return {"ok": False, "error": problem}
    if not isinstance(content, str):
        return {"ok": False, "error": "content must be a string"}
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    return {"ok": True, "path": relative(full), "bytes": len(content.encode("utf-8"))}

def edit_file(path, old_text, new_text):
    full, problem = resolve_path(path)
    if problem:
        return {"ok": False, "error": problem}
    if not os.path.isfile(full):
        return {"ok": False, "error": "file not found: " + str(path)}
    with open(full, encoding="utf-8") as f:
        before = f.read()
    count = before.count(old_text) if old_text else 0
    if count == 0:
        return {"ok": False, "error": "old_text was not found"}
    if count > 1:
        return {"ok": False, "error": "old_text appears " + str(count) +
                " times; give more of the surrounding text"}
    after = before.replace(old_text, new_text)
    with open(full, "w", encoding="utf-8") as f:
        f.write(after)
    diff = list(difflib.unified_diff(before.splitlines(), after.splitlines(),
                                     "before", "after", lineterm="", n=1))
    return {"ok": True, "path": relative(full), "diff": "\n".join(diff[:MAX_DIFF_LINES])}

def glob_files(pattern):
    if SANDBOX_ROOT is None or not isinstance(pattern, str):
        return {"ok": False, "error": "bad pattern or sandbox not set"}
    found = []
    for match in glob.glob(os.path.join(SANDBOX_ROOT, pattern), recursive=True):
        full, problem = resolve_path(os.path.relpath(match, SANDBOX_ROOT))
        if problem is None and os.path.isfile(full):
            found.append(relative(full))
    return {"ok": True, "files": sorted(found)[:MAX_RESULTS]}

def search_in_files(text, file_pattern="*"):
    if SANDBOX_ROOT is None or not isinstance(text, str) or not text:
        return {"ok": False, "error": "text must be a non-empty string"}
    matches = []
    for folder, _, names in os.walk(SANDBOX_ROOT):
        for name in sorted(names):
            if not fnmatch.fnmatch(name, file_pattern):
                continue
            full, problem = resolve_path(os.path.relpath(os.path.join(folder, name), SANDBOX_ROOT))
            if problem or os.path.getsize(full) > MAX_FILE_BYTES:
                continue
            with open(full, encoding="utf-8", errors="replace") as f:
                for number, line in enumerate(f, start=1):
                    if text in line:
                        matches.append({"file": relative(full), "line": number,
                                        "text": line.strip()[:120]})
    return {"ok": True, "matches": matches[:MAX_RESULTS], "match_count": len(matches)}

SAFE_PREFIXES = ["ls", "pwd", "cat", "head", "tail", "grep", "echo", "wc", "git status", "git diff", "git log", "python --version"]
WRAPPERS = ["env", "nohup", "time", "xargs", "exec", "bash", "sh", "-c"]
PRIVILEGE_PROGRAMS = ["sudo", "su", "doas", "pkexec"]
PERMISSION_PROGRAMS = ["chmod", "chown", "chgrp", "setfacl"]
FILESYSTEM_PROGRAMS = ("mkfs", "mke2fs", "mkswap")

def split_command(command):
    pieces = re.split(r"&&|\|\||;|\||\n|`|\$\(|\)", command)
    return [p.strip() for p in pieces if p.strip()]

def has_recursive_flag(words):
    for word in words[1:]:
        if word == "--recursive":
            return True
        if word.startswith("-") and not word.startswith("--") and ("r" in word or "R" in word):
            return True
    return False

def is_destructive(command):
    if not isinstance(command, str):
        return True
    if re.search(r"(of=|>\s*)/dev/(sd|hd|vd|nvme|mmcblk|disk|rdisk)", command):
        return True
    if re.search(r">>?\s*/", command.replace("/dev/null", "")):
        return True
    for piece in split_command(command):
        words = piece.replace('"', " ").replace("'", " ").split()
        while words and os.path.basename(words[0]) in WRAPPERS:
            words = words[1:]
        if not words:
            continue
        program = os.path.basename(words[0])
        if program == "rm" and has_recursive_flag(words):
            return True
        if program == "find" and "-delete" in words:
            return True
        if program in PRIVILEGE_PROGRAMS:
            return True
        if program in PERMISSION_PROGRAMS:
            return True
        if program.startswith(FILESYSTEM_PROGRAMS):
            return True
    return False


def matches_safe_prefix(command):
    text = command.strip()
    if any(char in text for char in ";&|`<>$\n"):
        return False
    for prefix in SAFE_PREFIXES:
        if text == prefix or text.startswith(prefix + " "):
            return True
    return False

def confirm_bash(command, auto_approve=False, confirmed=False):
    if not isinstance(command, str) or not command.strip():
        return {"allowed": False, "reason": "empty command"}
    if is_destructive(command):
        if confirmed:
            return {"allowed": True, "reason": "destructive, but explicitly confirmed"}
        return {"allowed": False, "reason": "destructive command needs explicit confirmation"}
    if matches_safe_prefix(command):
        return {"allowed": True, "reason": "matches SAFE_PREFIXES"}
    if auto_approve:
        return {"allowed": True, "reason": "auto_approve is on"}
    return {"allowed": False, "reason": "not in SAFE_PREFIXES (needs approval)"}

def bash(command, auto_approve=False, confirmed=False):
    gate = confirm_bash(command, auto_approve, confirmed)
    if not gate["allowed"]:
        return {"ok": False, "error": "blocked: " + gate["reason"]}
    try:
        done = subprocess.run(command, shell=True, cwd=SANDBOX_ROOT, capture_output=True,
                              text=True, timeout=10)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "command took longer than 10 seconds"}
    return {"ok": done.returncode == 0, "returncode": done.returncode,
            "stdout": done.stdout[:2000], "stderr": done.stderr[:500]}

def schema(name, description, properties, required):
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties, "required": required}}}

TOOL_SCHEMAS = [
    schema("read_file", "Read a text file. Use max_lines to read only the first lines.",
        {"path": {"type": "string"}, "max_lines": {"type": "integer"}}, ["path"]),
    schema("write_file", "Create or overwrite a text file.",
        {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
    schema("edit_file", "Replace old_text with new_text once. Returns a short diff.",
        {"path": {"type": "string"}, "old_text": {"type": "string"},
        "new_text": {"type": "string"}}, ["path", "old_text", "new_text"]),
    schema("glob_files", "List files whose name matches a pattern such as *.py or **/*.py.",
        {"pattern": {"type": "string"}}, ["pattern"]),
    schema("search_in_files", "Find lines containing text. file_pattern limits the files, e.g. *.py.",
        {"text": {"type": "string"}, "file_pattern": {"type": "string"}}, ["text"]),
    schema("bash", "Run a shell command (only if the safety gate allows it).",
        {"command": {"type": "string"}}, ["command"]),
]
PYTHON_TYPES = {"string": str, "integer": int}

def check_arguments(name, args):
    wanted = None
    for item in TOOL_SCHEMAS:
        if item["function"]["name"] == name:
            wanted = item["function"]["parameters"]
    if wanted is None:
        return "unknown tool: " + str(name)
    if not isinstance(args, dict):
        return "arguments must be an object"
    for key in wanted["required"]:
        if key not in args:
            return "missing argument: " + key
    for key, value in args.items():
        if key not in wanted["properties"]:
            return "unexpected argument: " + key
        kind = wanted["properties"][key]["type"]
        if not isinstance(value, PYTHON_TYPES[kind]) or isinstance(value, bool):
            return "argument " + key + " must be of type " + kind
    return None

def execute_tool(name, args):
    problem = check_arguments(name, args)
    if problem:
        return {"ok": False, "error": problem}
    if name == "read_file":
        return read_file(args["path"], args.get("max_lines"))
    if name == "write_file":
        return write_file(args["path"], args["content"])
    if name == "edit_file":
        return edit_file(args["path"], args["old_text"], args["new_text"])
    if name == "glob_files":
        return glob_files(args["pattern"])
    if name == "search_in_files":
        return search_in_files(args["text"], args.get("file_pattern", "*"))
    return bash(args["command"])