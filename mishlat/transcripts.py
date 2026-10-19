"""Claude Code transcripts: `~/.claude/projects/<encoded folder>/<cli session id>.jsonl`.

Indexed by file name (the cli session id), never by the folder: when a project folder moves, the
transcript folder moves with it but the app's record keeps the old path. Only top-level files are
sessions; `<session>/subagents/*.jsonl` are not. Reading is incremental: a file that grew is read
from the last complete line.
"""

from __future__ import annotations

import glob
import json
import os
import re
from datetime import datetime

from .paths import PROJECTS_DIR

# A line is parsed only when it holds one of these (most lines are large tool output).
INTERESTING = (b'"type":"user"', b'"type": "user"', b'"custom-title"', b'"agent-name"', b"update_plan", b"wrap_up",
               b"TodoWrite", b'"tool_use"')
STATUSES = ("pending", "in_progress", "completed")
PROMPT_CHARS = 200

# Where a session works: absolute paths in its tool calls, cut to PATH_PARTS components.
PATH_PARTS = 6
PATH_RE = re.compile(r"(?:~|/home/[^/\s'\"`]+)/[^\s'\"`;|&()<>,\\]+")  # a path ends at a quote or a JSON escape
TS_RE = re.compile(rb'"timestamp":"(\d{4}-\d\d-\d\dT[^"]{8,24})"')
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
WRITE_CMD = re.compile(r"(cat\s*>|>>|(?<![<>=&|0-9])>\s*[\w./~-]|\btee\b|\bcp\b|\bmv\b|\binstall\b|\bmkdir\b"
                       r"|sed\s+-i|git\s+(add|commit)|step_done)")


def encode_path(path: str) -> str:
    """Claude Code's folder name for a path: every non-alphanumeric character becomes '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def empty() -> dict:
    return {"title": None, "name": None, "first_prompt": None, "interrupted": False, "plan": [], "cwd": None,
            "writes": {}, "reads": {}, "local_writes": 0, "last_ts": 0}


def _parse_ts(text: str) -> int:
    """An ISO timestamp from a transcript line -> milliseconds since the epoch (0 when unreadable)."""
    try:
        return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp() * 1000)
    except ValueError:
        return 0


def _cut(path: str, home: str | None) -> str | None:
    """`~/a/b/c/d/e/f/g` -> `/home/u/a/b/c/d` (PATH_PARTS components); hidden top folders are dropped."""
    if path.startswith("~"):
        if not home:
            return None
        path = home + path[1:]
    path = os.path.normpath(path.rstrip(".:"))
    parts = path.split("/")
    if len(parts) < 4 or parts[1] != "home" or parts[3].startswith("."):  # /tmp, ~/.config, ~/.claude: not projects
        return None
    return "/".join(parts[: PATH_PARTS + 1])


def work_of(name: str, inp: dict, home: str | None = None) -> tuple[str, set[str]]:
    """("write" | "read" | "skip", the cut paths) of one tool call. ("write", set()) is a write with no
    path at all (in the session's own folder); a write that only touches places outside home is "skip"."""
    if name in WRITE_TOOLS:
        target = inp.get("file_path") or inp.get("notebook_path")
        cut = _cut(target, home) if isinstance(target, str) else None
        return ("write", {cut}) if cut else ("skip", set())
    text = json.dumps(inp, ensure_ascii=False)
    paths = {c for c in (_cut(m, home) for m in PATH_RE.findall(text)) if c}
    command = inp.get("command") if name == "Bash" and isinstance(inp.get("command"), str) else None
    if command is not None:
        cleaned = re.sub(r"\d?>\s*/dev/null|2>&1", " ", command)
        if WRITE_CMD.search(cleaned):
            if not paths and re.search(r"(?:^|[\s>=])[/~]", cleaned):
                return "skip", set()  # it writes to /tmp, ~/.cache and the like
            return "write", paths
    return "read", paths


def _text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def clean_prompt(text: str) -> str:
    text = re.sub(r"<pasted_content[^>]*>.*?</pasted_content[^>]*>", " … ", text, flags=re.S)
    return re.sub(r"\s+", " ", text).strip()[:PROMPT_CHARS]


# ── the task list ──
def _item(value: object) -> dict | None:
    if not isinstance(value, dict) or not _text(value.get("content")):
        return None
    status = value.get("status") if value.get("status") in STATUSES else "pending"
    return {"content": value["content"].strip(), "status": status}


def apply_op(items: list[dict], op: object) -> list[dict]:
    """One task-list call (update_plan input, or {"all_done": True} for wrap_up), applied in order."""
    if not isinstance(op, dict):
        return items
    if op.get("all_done") is True:
        return [{**i, "status": "completed"} for i in items]
    if isinstance(op.get("items"), list):
        new = [i for i in (_item(v) for v in op["items"]) if i is not None]
    else:
        new = [dict(i) for i in items]
    if isinstance(op.get("done"), list):
        for n in op["done"]:
            if isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= len(new):
                new[n - 1]["status"] = "completed"
    if op.get("advance") is True:
        cur = next((i for i in new if i["status"] == "in_progress"), None)
        if cur is not None:
            cur["status"] = "completed"
        nxt = next((i for i in new if i["status"] == "pending"), None)
        if nxt is not None:
            nxt["status"] = "in_progress"
    start = op.get("start")
    if isinstance(start, int) and not isinstance(start, bool) and 1 <= start <= len(new):
        new[start - 1]["status"] = "in_progress"
    return new


def plan_summary(plan: list[dict]) -> tuple[str | None, int, int]:
    """(the step in progress, else the next pending one), completed count, total."""
    done = sum(1 for i in plan if i["status"] == "completed")
    cur = next((i for i in plan if i["status"] == "in_progress"), None) or next(
        (i for i in plan if i["status"] == "pending"), None)
    return (cur["content"] if cur else None), done, len(plan)


def step_open(plan: list[dict]) -> bool:
    return any(i["status"] == "in_progress" for i in plan)


# ── one line ──
def _texts(content: object) -> list[str]:
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [b["text"] for b in content if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str)]
    return []


def _apply_user(data: dict, r: dict) -> None:
    if r.get("isMeta") is True:
        return
    msg = r.get("message")
    texts = [t.strip() for t in _texts(msg.get("content") if isinstance(msg, dict) else None) if t.strip()]
    if any(t.startswith("[Request interrupted") for t in texts):
        data["interrupted"] = True
        return
    real = [t for t in texts if not t.startswith("<")]  # <task-notification>, <command-name>, reminders
    if not real:
        return
    data["interrupted"] = False
    if data["first_prompt"] is None:
        data["first_prompt"] = clean_prompt("\n".join(real)) or None


def _apply_assistant(data: dict, r: dict, home: str | None = None) -> None:
    msg = r.get("message")
    content = msg.get("content") if isinstance(msg, dict) else None
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        name = block.get("name") if isinstance(block.get("name"), str) else ""
        inp = block.get("input") if isinstance(block.get("input"), dict) else {}
        kind, paths = work_of(name, inp, home)
        if kind == "skip":
            paths = set()
        elif kind == "write" and not paths:
            data["local_writes"] = data.get("local_writes", 0) + 1
        bucket = data.setdefault("writes" if kind != "read" else "reads", {})
        for p in paths:
            bucket[p] = bucket.get(p, 0) + 1
        if name.endswith("update_plan"):
            data["plan"] = apply_op(data["plan"], inp)
        elif name.endswith("wrap_up"):
            data["plan"] = apply_op(data["plan"], {"all_done": True})
        elif name == "TodoWrite" and isinstance(inp.get("todos"), list):
            data["plan"] = apply_op(data["plan"], {"items": inp["todos"]})


def apply_line(data: dict, raw: bytes, home: str | None = None) -> None:
    """Update `data` (see `empty()`) with one transcript line. Unknown or broken lines are ignored."""
    try:
        r = json.loads(raw)
    except ValueError:
        return
    if not isinstance(r, dict) or r.get("isSidechain") is True:
        return
    cwd = r.get("cwd")
    if isinstance(cwd, str) and cwd:
        data["cwd"] = cwd
    kind = r.get("type")
    if kind == "custom-title":
        title = _text(r.get("customTitle"))
        if title:
            data["title"] = title
    elif kind == "agent-name":
        name = _text(r.get("agentName"))
        if name:
            data["name"] = name
    elif kind == "user":
        _apply_user(data, r)
    elif kind == "assistant":
        _apply_assistant(data, r, home)


def _wanted(raw: bytes) -> bool:
    if not any(key in raw for key in INTERESTING):
        return False
    # A tool result can be megabytes of file content; it matters only as an interruption.
    is_result = b'"type":"tool_result"' in raw or b'"type": "tool_result"' in raw
    return not is_result or b"Request interrupted" in raw


def read_from(path: str, offset: int, data: dict, home: str | None = None) -> int:
    """Apply every complete line after `offset`; return the offset after the last complete line."""
    with open(path, "rb") as f:
        f.seek(offset)
        for raw in f:
            if not raw.endswith(b"\n"):
                break  # half-written: read it again on the next scan
            offset += len(raw)
            m = TS_RE.search(raw[:400])  # every line carries its time near the start; no JSON parse needed
            if m:
                data["last_ts"] = max(data.get("last_ts", 0), _parse_ts(m.group(1).decode("ascii", "replace")))
            if _wanted(raw):
                apply_line(data, raw, home)
    return offset


def index_transcripts(home: str, cache: dict) -> dict[str, dict]:
    """cli session id -> transcript facts. `cache` (path -> entry) is updated in place."""
    out: dict[str, dict] = {}
    seen = set()
    for path in glob.glob(os.path.join(home, PROJECTS_DIR, "*", "*.jsonl")):
        seen.add(path)
        try:
            st = os.stat(path)
        except OSError:
            continue
        prev = cache.get(path)
        if prev and (prev["size"], prev["mtime"], prev["ino"]) == (st.st_size, st.st_mtime, st.st_ino):
            data = prev["data"]
        else:
            grew = bool(prev) and prev["ino"] == st.st_ino and st.st_size >= prev["offset"]
            data = json.loads(json.dumps(prev["data"])) if grew else empty()
            try:
                offset = read_from(path, prev["offset"] if grew else 0, data, home)
            except OSError:
                continue
            cache[path] = {"size": st.st_size, "mtime": st.st_mtime, "ino": st.st_ino, "offset": offset, "data": data}
        cli_id = os.path.basename(path)[: -len(".jsonl")]
        # The file's mtime is a fallback only: a copy or a move of the folder resets it (122 of 175 transcripts
        # carried an mtime days after their last line on 2026-10-19), which made old sessions look recent.
        last_write = data.get("last_ts") or int(st.st_mtime * 1000)
        entry = dict(data, folder=os.path.basename(os.path.dirname(path)), last_write=last_write, path=path)
        if cli_id not in out or out[cli_id]["last_write"] < entry["last_write"]:
            out[cli_id] = entry
    for gone in set(cache) - seen:
        del cache[gone]
    return out
