"""The pure rules: which project a session belongs to, and which state it is in.

Nothing here reads the disk except through the `isdir` argument, so every rule is testable.
"""

from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass

from .folders import FolderIndex
from .transcripts import encode_path, plan_summary, step_open

WORKING_WINDOW_MS = 90_000
STATES = ("working", "stopped", "waiting", "review", "open", "idle")
ATTENTION_STATES = ("waiting", "review", "stopped")
SCRATCH = "scratch"
GENERAL = "general"        # one project for sessions with no folder: lost folders and scratch
GENERAL_NAME = "כללי"


@dataclass(frozen=True)
class ProjectRef:
    key: str                 # the folder path now; for a lost folder its old path; or "scratch"
    path: str | None         # where the folder is now (None when lost or scratch)
    moved_from: str | None   # the session's folder when it no longer exists
    ambiguous: bool = False  # several folders could be the moved one


def fold_worktree(path: str) -> str:
    """A worktree under <repo>/.claude/worktrees/<name> belongs to <repo>."""
    i = path.find("/.claude/worktrees/")
    return path[:i] if i >= 0 else path


def resolve_project(cwd: str, folders: FolderIndex, tx_folder: str | None = None,
                    aliases: dict[str, str] | None = None, isdir=os.path.isdir,
                    found: dict[str, str] | None = None) -> ProjectRef:
    """In order: scratch; the folder exists (unless its transcripts moved elsewhere); the folder found
    again by its remembered identity (`found`: old path -> new path, after a rename or a move); a
    user alias; the transcript folder's encoding; a unique folder with the same name; else lost."""
    path = fold_worktree(os.path.normpath(cwd)) if cwd else "/"
    if "/scratch-workspaces/" in path:
        return ProjectRef(SCRATCH, None, None)
    again = (found or {}).get(path)
    if not isdir(path) and again and isdir(again):
        return ProjectRef(again, again, path)
    if isdir(path):
        # The folder name may have been reused (an old project folder became a parent folder);
        # the transcript folder then still names where the session's history lives now.
        if tx_folder and tx_folder != encode_path(path):
            moved = sorted({p for p in folders.by_encoding(tx_folder) if isdir(p)})
            if len(moved) == 1 and moved[0] != path:
                return ProjectRef(moved[0], moved[0], path)
        return ProjectRef(path, path, None)
    target = (aliases or {}).get(path)
    if target and isdir(target):
        return ProjectRef(target, target, path)
    by_tx = sorted({p for p in folders.by_encoding(tx_folder) if isdir(p)}) if tx_folder else []
    if len(by_tx) == 1:
        return ProjectRef(by_tx[0], by_tx[0], path)
    by_name = sorted({p for p in folders.by_basename(path) if isdir(p)})
    if not by_tx and len(by_name) == 1:
        return ProjectRef(by_name[0], by_name[0], path)
    return ProjectRef(path, None, path, ambiguous=len(by_tx) > 1 or len(by_name) > 1)


# ── where a session worked ──
WORK_MIN = 15           # score a session needs in another project before it moves there
WRITE_WEIGHT = 3        # a write counts three reads


def owner_of(path: str, candidates: list[str], by_name: dict[str, list[str]],
             old_paths: dict[str, str] | None = None) -> str | None:
    """The project folder a path belongs to: the deepest candidate it lies in (an old path of a
    moved folder counts as its project); else the one candidate named like one of its first folders."""
    for c in candidates:  # deepest first
        if path == c or path.startswith(c + "/"):
            return (old_paths or {}).get(c, c)
    parts = path.split("/")[2:7]  # the folders below "/" and the first one (any home depth)
    for comp in reversed(parts):
        hits = by_name.get(encode_path(comp).lower(), [])
        if len(hits) == 1:
            return hits[0]
    return None


def work_project(tx: dict | None, own: str | None, candidates: list[str], by_name: dict[str, list[str]],
                 old_paths: dict[str, str] | None = None) -> str | None:
    """The project the session worked in, when it is not its own folder; else None."""
    if not tx:
        return None
    score: Counter = Counter()
    for kind, weight in (("writes", WRITE_WEIGHT), ("reads", 1)):
        for path, n in (tx.get(kind) or {}).items():
            project = owner_of(path, candidates, by_name, old_paths)
            if project:
                score[project] += weight * n
    if own:
        score[own] += WRITE_WEIGHT * tx.get("local_writes", 0)
    if not score:
        return None
    top, top_score = score.most_common(1)[0]
    if top == own or top_score < WORK_MIN or top_score <= 2 * score.get(own, 0):
        return None
    return top


def state_of(status: str | None, fresh: bool, alive: bool, tx: dict | None, now: int) -> str:
    """working > stopped > waiting > review > open > idle."""
    if alive and tx is not None and now - tx.get("last_write", 0) < WORKING_WINDOW_MS:
        return "working"
    if tx is not None and tx.get("interrupted") and step_open(tx.get("plan") or []):
        return "stopped"
    if fresh and status == "blocked":
        return "waiting"
    if fresh and status == "review_ready":
        return "review"
    return "open" if alive else "idle"


# ── the index ────────────────────────────────────────────────────────────────────────────
DAY_MS = 86_400_000
ATTENTION_DAYS = 14
STALE_DAYS = 30
OLD_DAYS = 30            # the "old" cleanup rule; settings.json "old_days" overrides it
EMPTY_DAYS = 7
EMPTY_TURNS = 2
CLEANUP_REASONS = ("gone", "no_transcript", "duplicate", "empty", "old")
UNTITLED = "(ללא כותרת)"
INDEX_VERSION = 1


def _project_name(ref: ProjectRef, roots: list[str]) -> str:
    if ref.key == GENERAL:
        return GENERAL_NAME
    if ref.key == SCRATCH:
        return SCRATCH
    path = ref.path or ref.key
    for root in roots:
        if path.startswith(root.rstrip("/") + "/"):
            return path[len(root.rstrip("/")) + 1:]
    return os.path.basename(path.rstrip("/")) or path


def _session(rec, cli_id: str | None, tx: dict | None, live_entry, now: int, dismissed: dict) -> dict:
    """One session row. `rec` is a store Record, or None for a terminal-only session."""
    alive = live_entry is not None
    status, fresh = (rec.status, rec.fresh) if rec else (None, True)
    state = state_of(status, fresh, alive, tx, now)
    last = max(rec.last_activity if rec else 0, tx["last_write"] if tx else 0)
    step, done, total = plan_summary(tx["plan"]) if tx else (None, 0, 0)
    title = (rec.title if rec else "") or (tx or {}).get("title") or (tx or {}).get("name") \
        or (tx or {}).get("first_prompt") or UNTITLED
    sid = rec.id if rec else cli_id
    is_dismissed = dismissed.get(sid, 0) >= last > 0
    writes = (sum((tx.get("writes") or {}).values()) + tx.get("local_writes", 0)) if tx else 0
    row = {
        "id": sid,
        "cli_id": cli_id,
        "turns": rec.turns if rec else None,
        "writes": writes,
        "source": "app" if rec else "cli",
        "title": title,
        "cwd": rec.cwd if rec else ((tx or {}).get("cwd") or ""),
        "project": None,
        "state": state,
        "question": (rec.question or rec.detail) if (rec and state == "waiting") else None,
        "detail": rec.detail if (rec and rec.fresh) else None,
        "step": step,
        "steps_done": done,
        "steps_total": total,
        "first_prompt": (tx or {}).get("first_prompt"),
        "transcript": tx is not None,
        "last_activity": last,
        "starred": bool(rec and rec.starred),
        "dismissed": is_dismissed,
        "pid": live_entry.pid if alive else None,
    }
    row["attention"] = (state in ATTENTION_STATES and not is_dismissed and now - last <= ATTENTION_DAYS * DAY_MS)
    return row


def build_index(records, transcripts: dict, live: dict, folders: FolderIndex, now: int,
                aliases: dict | None = None, dismissed: dict | None = None, git=None,
                isdir=os.path.isdir, assignments: dict | None = None, describe=None,
                descriptions: dict | None = None, found: dict | None = None) -> dict:
    """Every session and project, as the dict written to `~/.cache/mishlat/index.json`.
    `describe(path)` gives a folder's README purpose; `descriptions` the user's own lines;
    `found` maps the old path of a renamed or moved folder to where it is now."""
    aliases, dismissed, assignments = aliases or {}, dismissed or {}, assignments or {}
    descriptions = descriptions or {}
    describe = describe or (lambda path: None)
    git = git or (lambda path: None)
    claimed = {r.cli_id for r in records if r.cli_id}
    rows: list[tuple[dict, str | None]] = []  # (session row, transcript folder)
    for rec in records:
        if rec.archived:
            continue
        tx = transcripts.get(rec.cli_id) if rec.cli_id else None
        rows.append((_session(rec, rec.cli_id, tx, live.get(rec.cli_id or ""), now, dismissed),
                     tx["folder"] if tx else None))
    for cli_id, tx in transcripts.items():
        if cli_id not in claimed:
            rows.append((_session(None, cli_id, tx, live.get(cli_id), now, dismissed), tx["folder"]))

    # Resolve folders; a move found through one session's transcript also moves its siblings.
    refs = [resolve_project(row["cwd"], folders, folder, aliases, isdir, found) for row, folder in rows]
    learned: dict[str, set] = {}
    for ref, (_, folder) in zip(refs, rows):
        if ref.moved_from and ref.path and folder and ref.path in folders.by_encoding(folder):
            learned.setdefault(ref.moved_from, set()).add(ref.path)
    learned_aliases = {old: next(iter(new)) for old, new in learned.items() if len(new) == 1}
    merged = {**learned_aliases, **aliases}
    for i, ref in enumerate(refs):
        if ref.path is None and ref.key != SCRATCH and ref.moved_from in merged:
            refs[i] = resolve_project(rows[i][0]["cwd"], folders, rows[i][1], merged, isdir, found)
    # A session that still has no folder (the folder is gone, or an app scratch folder) goes to "כללי".
    for i, ref in enumerate(refs):
        if ref.path is None:
            refs[i] = ProjectRef(GENERAL, None, ref.moved_from if ref.key != SCRATCH else None)

    # A session belongs to the project it worked in (wrote, else read); a manual assignment wins.
    # Work under a folder's old path (before a move) counts for that folder's project.
    old_paths = {r.moved_from: r.path for r in refs if r.path and r.moved_from}
    candidates = sorted({r.path for r in refs if r.path} | {f.path for f in folders.repos()} | set(old_paths),
                        key=len, reverse=True)
    by_name: dict[str, list[str]] = {}
    for c in candidates:
        if c not in old_paths:
            by_name.setdefault(encode_path(os.path.basename(c)).lower(), []).append(c)
    started: list[str | None] = [None] * len(refs)
    for i, ref in enumerate(refs):
        row = rows[i][0]
        target = assignments.get(row["id"])
        if not (target and isdir(target)):
            target = work_project(transcripts.get(row["cli_id"] or ""), ref.path, candidates, by_name, old_paths)
        if target and target != ref.path:
            started[i] = ref.key
            refs[i] = ProjectRef(target, target, None)
        row["assigned"] = bool(assignments.get(row["id"]) and isdir(assignments[row["id"]]))

    projects: dict[str, dict] = {}

    def project(ref: ProjectRef) -> dict:
        p = projects.get(ref.key)
        if p is None:
            info = git(ref.path) if ref.path else None
            folder = folders.at(ref.path) if ref.path else None
            own = descriptions.get(ref.path) if ref.path else None
            readme = describe(ref.path) if (ref.path and not own) else None
            p = projects[ref.key] = {
                "key": ref.key, "name": _project_name(ref, folders.roots), "path": ref.path,
                "description": own or readme,
                "description_source": "user" if own else ("readme" if readme else None),
                "moved_from": [], "ambiguous": False,
                "is_repo": bool((info or {}).get("is_repo") or (folder and folder.is_repo)),
                "branch": (info or {}).get("branch"), "dirty": (info or {}).get("dirty"),
                "general": ref.key == GENERAL,
                "working": 0, "open": 0, "waiting": 0, "review": 0, "stopped": 0, "attention": 0,
                "last_activity": 0, "sessions": [],
            }
        return p

    for i, (ref, (row, _)) in enumerate(zip(refs, rows)):
        p = project(ref)
        row["project"] = ref.key
        row["started_in"] = started[i]
        p["sessions"].append(row)
        if ref.moved_from and ref.moved_from not in p["moved_from"]:
            p["moved_from"].append(ref.moved_from)
        p["ambiguous"] = p["ambiguous"] or ref.ambiguous
        if row["state"] in ("working", "open"):
            p[row["state"]] += 1
        if row["attention"]:
            p[row["state"]] += 1
            p["attention"] += 1
        p["last_activity"] = max(p["last_activity"], row["last_activity"])
    for folder in folders.repos():
        if folder.path not in projects:
            project(ProjectRef(folder.path, folder.path, None))

    ordered = sorted(projects.values(), key=lambda p: (p["general"], -p["last_activity"], p["name"]))
    for p in ordered:
        p["sessions"].sort(key=lambda s: -s["last_activity"])
        p["moved_from"].sort()
    sessions = [s for p in ordered for s in p["sessions"]]
    order = {"waiting": 0, "stopped": 1, "review": 2}
    attention = sorted((s for s in sessions if s["attention"]), key=lambda s: (order[s["state"]], -s["last_activity"]))
    with_sessions = [p for p in ordered if p["sessions"]]
    totals = {
        "projects": len(with_sessions),
        "repos": sum(1 for p in ordered if p["is_repo"]),
        "lost": len(projects[GENERAL]["moved_from"]) if GENERAL in projects else 0,
        "sessions": len(sessions),
        "working": sum(1 for s in sessions if s["state"] == "working"),
        "open": sum(1 for s in sessions if s["state"] == "open"),
        "waiting": sum(1 for s in attention if s["state"] == "waiting"),
        "review": sum(1 for s in attention if s["state"] == "review"),
        "stopped": sum(1 for s in attention if s["state"] == "stopped"),
        "attention": len(attention),
        "stale": sum(1 for s in sessions if is_stale(s, now)),
    }
    return {
        "version": INDEX_VERSION, "scanned_at": now, "scan_ms": 0, "app_version": None,
        "roots": list(folders.roots), "projects": ordered, "attention": [s["id"] for s in attention],
        "totals": totals, "errors": [],
    }


def cleanup_reason(s: dict, project: dict, newer_same_title: bool, now: int, old_days: int,
                   kept: dict | None = None, newest_in_project: bool = False) -> str | None:
    """Why a session is worth deleting, or None. Never for a starred, active, kept or hand-assigned
    one, and never for the newest session of a folder (a project always keeps its last conversation)."""
    if s["starred"] or s["state"] in ("working", "waiting", "review", "stopped") or s.get("assigned"):
        return None
    if kept and s["id"] in kept:
        return None
    if newest_in_project and not project.get("general"):
        return None
    if project.get("general"):
        return "gone"
    if not s["transcript"] and s["source"] == "app":
        return "no_transcript"
    if newer_same_title:
        return "duplicate"
    age = now - s["last_activity"]
    if (s["turns"] or 0) <= EMPTY_TURNS and s["writes"] == 0 and age >= EMPTY_DAYS * DAY_MS:
        return "empty"
    if age >= old_days * DAY_MS:
        return "old"
    return None


def mark_cleanup(index: dict, now: int, old_days: int = OLD_DAYS, kept: dict | None = None) -> None:
    """Sets `cleanup` on every session, and `index["cleanup"]` (ids, newest first) and the totals."""
    sessions = all_sessions(index)
    newest_by_title: dict[str, int] = {}
    for s in sessions:
        key = s["title"].strip()
        newest_by_title[key] = max(newest_by_title.get(key, 0), s["last_activity"])
    by_key = {p["key"]: p for p in index["projects"]}
    by_reason: dict[str, int] = {r: 0 for r in CLEANUP_REASONS}
    listed = []
    newest_id = {p["key"]: p["sessions"][0]["id"] for p in index["projects"] if p["sessions"]}  # sorted newest first
    for s in sessions:
        key = s["title"].strip()
        newer = key != "" and key != UNTITLED and newest_by_title.get(key, 0) > s["last_activity"]
        reason = cleanup_reason(s, by_key[s["project"]], newer, now, old_days, kept,
                                newest_in_project=newest_id.get(s["project"]) == s["id"])
        s["cleanup"] = reason
        if reason:
            by_reason[reason] += 1
            listed.append(s)
    listed.sort(key=lambda s: -s["last_activity"])
    index["cleanup"] = [s["id"] for s in listed]
    index["totals"]["cleanup"] = len(listed)
    index["totals"]["cleanup_by"] = by_reason


def cleanup_sessions(index: dict) -> list[dict]:
    by_id = {s["id"]: s for s in all_sessions(index)}
    return [by_id[i] for i in index.get("cleanup", []) if i in by_id]


def is_stale(session: dict, now: int, days: int = STALE_DAYS) -> bool:
    return session["state"] == "idle" and now - session["last_activity"] >= days * DAY_MS


def all_sessions(index: dict) -> list[dict]:
    return [s for p in index.get("projects", []) for s in p["sessions"]]


def attention_sessions(index: dict) -> list[dict]:
    by_id = {s["id"]: s for s in all_sessions(index)}
    return [by_id[i] for i in index.get("attention", []) if i in by_id]


def stale_sessions(index: dict, now: int, days: int = STALE_DAYS) -> list[dict]:
    return sorted((s for s in all_sessions(index) if is_stale(s, now, days)), key=lambda s: -s["last_activity"])


def entered(old: dict | None, new: dict) -> list[dict]:
    """Attention entries that are new since `old`: a new session, or a session in a new state."""
    before = {(s["id"], s["state"]) for s in attention_sessions(old)} if old else set()
    return [s for s in attention_sessions(new) if (s["id"], s["state"]) not in before]


def search(index: dict, query: str, limit: int = 60) -> tuple[list[dict], list[dict]]:
    """(projects, sessions) whose text holds `query`, case-insensitive."""
    q = query.strip().casefold()
    if not q:
        return [], []

    def hit(*fields) -> bool:
        return any(q in (f or "").casefold() for f in fields)

    projects = [p for p in index.get("projects", []) if hit(p["name"], p["path"], p["key"], *p["moved_from"])]
    names = {p["key"]: p["name"] for p in index.get("projects", [])}
    sessions = [s for s in all_sessions(index)
                if hit(s["title"], s["question"], s["detail"], s["step"], s["first_prompt"], s["cwd"],
                       names.get(s["project"]))]
    sessions.sort(key=lambda s: -s["last_activity"])
    return projects, sessions[:limit]
