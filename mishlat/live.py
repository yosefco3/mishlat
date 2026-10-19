"""Claude Code's live process registry: `~/.claude/sessions/<pid>.json`.

A file stays after its process ends, so a process counts as alive only when `/proc/<pid>/stat`
has the same start time (field 22) as the file's `procStart`. "Alive" means the session is open,
not that a turn runs (one process serves many turns).
"""

from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass

from .paths import LIVE_DIR


@dataclass(frozen=True)
class Live:
    pid: int
    cli_id: str
    cwd: str
    name: str | None
    entrypoint: str | None
    started_at: int


def parse_proc_start(stat_text: str) -> str | None:
    """Field 22 (start time) of /proc/<pid>/stat. The name field may hold spaces and ')'."""
    try:
        return stat_text.rsplit(")", 1)[1].split()[19]
    except IndexError:
        return None


def proc_start(pid: int, proc_root: str = "/proc") -> str | None:
    try:
        with open(os.path.join(proc_root, str(pid), "stat"), encoding="ascii", errors="replace") as f:
            return parse_proc_start(f.read())
    except OSError:
        return None


def read_live(home: str, proc_root: str = "/proc") -> dict[str, Live]:
    """cli session id -> the live process that owns it."""
    out: dict[str, Live] = {}
    for path in glob.glob(os.path.join(home, LIVE_DIR, "*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                r = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(r, dict):
            continue
        pid, sid, cwd = r.get("pid"), r.get("sessionId"), r.get("cwd")
        if not isinstance(pid, int) or not isinstance(sid, str) or not isinstance(cwd, str):
            continue
        if proc_start(pid, proc_root) != str(r.get("procStart")):
            continue
        started = r.get("startedAt") if isinstance(r.get("startedAt"), int) else 0
        prev = out.get(sid)
        if prev is not None and prev.started_at >= started:
            continue
        name = r.get("name") if isinstance(r.get("name"), str) else None
        entry = r.get("entrypoint") if isinstance(r.get("entrypoint"), str) else None
        out[sid] = Live(pid=pid, cli_id=sid, cwd=cwd, name=name, entrypoint=entry, started_at=started)
    return out
