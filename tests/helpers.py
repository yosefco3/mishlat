"""A fake home with the same file shapes as the real Claude desktop app (checked 2026-10-19)."""

from __future__ import annotations

import json
import os
import re
import tempfile

ORG, WS = "org1", "ws1"


def encode(path: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", path)


class FakeHome:
    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.proc = os.path.join(self.root, "_proc")
        os.makedirs(self.proc)

    def cleanup(self) -> None:
        self._tmp.cleanup()

    def path(self, *parts: str) -> str:
        return os.path.join(self.root, *parts)

    def mkdir(self, rel: str) -> str:
        p = self.path(rel)
        os.makedirs(p, exist_ok=True)
        return p

    def make_repo(self, rel: str, branch: str = "main") -> str:
        p = self.mkdir(rel)
        os.makedirs(os.path.join(p, ".git"), exist_ok=True)
        with open(os.path.join(p, ".git", "HEAD"), "w") as f:
            f.write(f"ref: refs/heads/{branch}\n")
        return p

    # ── app store ──
    def add_record(self, sid: str, cwd: str, cli_id: str | None = None, title: str = "a title",
                   last: int = 1_000, archived: bool = False, status: str | None = None,
                   question: str = "", detail: str = "", summarizes: str | None = "u1",
                   last_uuid: str | None = "u1", **extra) -> str:
        rec = {"sessionId": sid, "cwd": cwd, "originCwd": cwd, "title": title,
               "lastActivityAt": last, "createdAt": last - 10, "isArchived": archived,
               "model": "claude-opus-5-5", "permissionMode": "auto"}
        if cli_id is not None:
            rec["cliSessionId"] = cli_id
        if last_uuid is not None:
            rec["lastAssistantUuid"] = last_uuid
        if status is not None:
            rec["postTurnSummary"] = {"status_category": status, "status_detail": detail,
                                      "needs_action": question, "summarizes_uuid": summarizes}
            rec["postTurnSummaryFor"] = summarizes
        rec.update(extra)
        d = self.path(".config/Claude/claude-code-sessions", ORG, WS)
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"{sid}.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False)
        return p

    # ── transcripts ──
    def transcript_path(self, cwd: str, cli_id: str, folder: str | None = None) -> str:
        d = self.path(".claude/projects", folder or encode(cwd))
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, f"{cli_id}.jsonl")

    def add_transcript(self, cwd: str, cli_id: str, lines: list, folder: str | None = None) -> str:
        p = self.transcript_path(cwd, cli_id, folder)
        with open(p, "ab") as f:
            for line in lines:
                f.write(line if isinstance(line, bytes) else (json.dumps(line, ensure_ascii=False, separators=(",", ":")) + "\n").encode())
        return p

    # ── live registry + fake /proc ──
    def add_live(self, pid: int, cli_id: str, cwd: str, start: str = "1000", alive: bool = True,
                 started_at: int = 0) -> None:
        d = self.path(".claude/sessions")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{pid}.json"), "w") as f:
            json.dump({"pid": pid, "sessionId": cli_id, "cwd": cwd, "procStart": start,
                       "startedAt": started_at, "kind": "interactive", "entrypoint": "claude-desktop",
                       "name": "n"}, f)
        if alive:
            self.add_proc(pid, start)

    def add_proc(self, pid: int, start: str) -> None:
        d = os.path.join(self.proc, str(pid))
        os.makedirs(d, exist_ok=True)
        fields = ["S"] + [str(i) for i in range(1, 19)] + [start] + ["0"] * 10
        with open(os.path.join(d, "stat"), "w") as f:
            f.write(f"{pid} (claude (x)) " + " ".join(fields) + "\n")


def user(text, **extra) -> dict:
    return {"type": "user", "message": {"role": "user", "content": text}, "cwd": extra.pop("cwd", "/w"), **extra}


def user_blocks(*texts, **extra) -> dict:
    return {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": t} for t in texts]},
            "cwd": extra.pop("cwd", "/w"), **extra}


def tool_result(text="ok") -> dict:
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": text}]}, "cwd": "/w"}


def tool_use(name: str, inp: dict) -> dict:
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "t1", "name": name, "input": inp}]}, "cwd": "/w"}
