"""Claude Code's own listing of live sessions: `claude agents --json`.

Documented at https://code.claude.com/docs/en/agent-view#list-sessions-as-json (checked against
CLI 2.1.299 on 2026-10-19). It prints a JSON array, one object per live session: always `cwd`,
`kind` (interactive / background) and `startedAt`; `pid` and `status` (busy / waiting / idle)
while the process is alive; `waitingFor` when waiting; `sessionId` and `name` when set; `id`
and `state` for background sessions. It is the primary live source since 0.1.2; `live.py` (the
registry + /proc) is the fallback when the command is missing or fails.

The command costs ~0.15 s, starts no supervisor and writes nothing under `~/.claude`.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass

from .actions import claude_cli

STATUSES = ("busy", "waiting", "idle")
BACKGROUND_STATUS = {"working": "busy", "blocked": "waiting"}  # a background session after its process exited
TIMEOUT_S = 5.0
DISABLE_VAR = "MISHLAT_AGENTS_DISABLE"   # "1": never run the command (the registry is the source)
COMMAND_VAR = "MISHLAT_AGENTS_CMD"       # a command to run instead of `<cli> agents --json` (tests, the demo)


class AgentsError(RuntimeError):
    """The listing could not be read: no CLI, a non-zero exit, a timeout, or bad JSON."""


@dataclass(frozen=True)
class LiveEntry:
    pid: int | None            # None for a background session whose process exited
    cwd: str
    name: str | None
    status: str | None         # busy / waiting / idle; None when the CLI gave none (or a new value)
    waiting_for: str | None    # "permission prompt", "input needed", … when status is waiting
    kind: str                  # interactive / background
    started_at: int            # ms since the epoch


def parse_agents_json(text: str | bytes) -> dict[str, LiveEntry]:
    """cli session id -> entry. Raises AgentsError on text that is not a JSON array; skips
    entries that are not objects or have no `sessionId`; the newer entry wins a repeated id."""
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise AgentsError(f"bad JSON: {exc}") from None
    if not isinstance(data, list):
        raise AgentsError(f"expected a JSON array, got {type(data).__name__}")
    out: dict[str, LiveEntry] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        sid = item.get("sessionId")
        if not isinstance(sid, str) or not sid:
            continue
        pid = item.get("pid")
        pid = pid if isinstance(pid, int) and not isinstance(pid, bool) else None
        status = item.get("status")
        if status not in STATUSES:
            status = BACKGROUND_STATUS.get(item.get("state")) if isinstance(item.get("state"), str) else None
        waiting_for = item.get("waitingFor") if status == "waiting" else None
        started = item.get("startedAt")
        started = started if isinstance(started, int) and not isinstance(started, bool) else 0
        prev = out.get(sid)
        if prev is not None and prev.started_at >= started:
            continue
        out[sid] = LiveEntry(
            pid=pid,
            cwd=item.get("cwd") if isinstance(item.get("cwd"), str) else "",
            name=item.get("name") if isinstance(item.get("name"), str) else None,
            status=status,
            waiting_for=waiting_for if isinstance(waiting_for, str) and waiting_for else None,
            kind=item.get("kind") if isinstance(item.get("kind"), str) else "",
            started_at=started,
        )
    return out


def agents_command(home: str, env=None, which=shutil.which) -> list[str] | None:
    """The command that lists live sessions: None when disabled, the override when set, else the
    bundled CLI's `agents --json`. Raises AgentsError when no CLI is found."""
    env = os.environ if env is None else env
    if env.get(DISABLE_VAR) == "1":
        return None
    custom = env.get(COMMAND_VAR)
    if custom:
        return shlex.split(custom)
    cli = claude_cli(home, which)
    if cli is None:
        raise AgentsError("no claude CLI: not on PATH and none bundled with the desktop app")
    return [cli, "agents", "--json"]


def read_agents(cli: str | list[str], timeout: float = TIMEOUT_S, run=subprocess.run) -> dict[str, LiveEntry]:
    """Run the listing and parse it. `cli` is the CLI's path, or a whole argv. Every failure is an
    AgentsError (the scan reports it as one error line and falls back to the registry)."""
    argv = [cli, "agents", "--json"] if isinstance(cli, str) else list(cli)
    if not argv:
        raise AgentsError("empty command")
    try:
        proc = run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        raise AgentsError(f"not found: {argv[0]}") from None
    except subprocess.TimeoutExpired:
        raise AgentsError(f"{argv[0]} timed out after {timeout:g} s") from None
    except OSError as exc:
        raise AgentsError(f"{argv[0]}: {exc}") from None
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace") if isinstance(proc.stderr, bytes) else (proc.stderr or "")
        last = err.strip().splitlines()[-1] if err.strip() else ""
        raise AgentsError(f"{argv[0]} exited {proc.returncode}" + (f": {last}" if last else ""))
    return parse_agents_json(proc.stdout)
