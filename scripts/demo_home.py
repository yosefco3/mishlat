#!/usr/bin/env python3
"""Build a fake home with made-up projects and Claude sessions, for screenshots and trials.

    H=$(python3 scripts/demo_home.py)
    MISHLAT_HOME=$H MISHLAT_AGENTS_CMD="cat $H/_agents.json" mishlat scan
    MISHLAT_HOME=$H MISHLAT_AGENTS_CMD="cat $H/_agents.json" mishlat

Prints the home's path. Nothing is personal: the projects, titles and prompts are invented.
The live sessions are faked twice: `_agents.json` is what `claude agents --json` would print
(the primary source), and `.claude/sessions` + `_proc` feed the registry fallback
(`MISHLAT_AGENTS_DISABLE=1 MISHLAT_PROC_ROOT=$H/_proc` shows that path instead).
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time

DAY = 86_400_000
NOW = int(time.time() * 1000)


def encode(path: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", path)


class Demo:
    def __init__(self, root: str) -> None:
        self.root = root
        self.store = os.path.join(root, ".config/Claude/claude-code-sessions/org/ws")
        self.proc = os.path.join(root, "_proc")
        os.makedirs(self.store)
        os.makedirs(self.proc)
        os.makedirs(os.path.join(root, ".claude/sessions"))
        self.n = 0
        self.agents: list[dict] = []  # what `claude agents --json` prints for the alive sessions

    def repo(self, rel: str, readme: str | None = None, branch: str = "main") -> str:
        path = os.path.join(self.root, "Desktop", rel)
        os.makedirs(os.path.join(path, ".git"), exist_ok=True)
        with open(os.path.join(path, ".git", "HEAD"), "w") as f:
            f.write(f"ref: refs/heads/{branch}\n")
        if readme:
            with open(os.path.join(path, "README.md"), "w", encoding="utf-8") as f:
                f.write(readme)
        return path

    def session(self, cwd: str, title: str, ago_days: float, turns: int = 6, status: str | None = None,
                question: str = "", detail: str = "", writes: int = 3, prompt: str = "", plan=None,
                interrupted: bool = False, alive: bool = False, transcript: bool = True, starred: bool = False,
                live_status: str = "busy", waiting_for: str | None = None) -> str:
        """`alive`: a live Claude Code process; `live_status` is what the CLI's listing says of it
        (busy / waiting / idle) and `waiting_for` what a waiting one waits for."""
        self.n += 1
        sid, cli = f"local_demo{self.n:04d}", f"0000{self.n:04d}-0000-4000-8000-{self.n:012d}"
        last = NOW - int(ago_days * DAY)
        rec = {"sessionId": sid, "cliSessionId": cli, "cwd": cwd, "originCwd": cwd, "title": title,
               "lastActivityAt": last, "createdAt": last - DAY, "isArchived": False, "isStarred": starred,
               "completedTurns": turns, "lastAssistantUuid": "u1", "model": "claude-opus-5-5"}
        if status:
            rec["postTurnSummary"] = {"status_category": status, "status_detail": detail or question,
                                      "needs_action": question, "summarizes_uuid": "u1"}
        with open(os.path.join(self.store, f"{sid}.json"), "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False)
        if transcript:
            d = os.path.join(self.root, ".claude/projects", encode(cwd))
            os.makedirs(d, exist_ok=True)
            ts = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(last / 1000))
            lines = [{"type": "user", "timestamp": ts, "cwd": cwd, "message": {"role": "user", "content": prompt or title}}]
            for _ in range(writes):
                lines.append({"type": "assistant", "timestamp": ts, "cwd": cwd, "message": {"role": "assistant", "content": [
                    {"type": "tool_use", "id": "t", "name": "Edit", "input": {"file_path": f"{cwd}/src/main.py"}}]}})
            if plan:
                lines.append({"type": "assistant", "timestamp": ts, "cwd": cwd, "message": {"role": "assistant", "content": [
                    {"type": "tool_use", "id": "t", "name": "mcp__ccd_turn__update_plan", "input": {"items": plan}}]}})
            if interrupted:
                lines.append({"type": "user", "timestamp": ts, "cwd": cwd,
                              "message": {"role": "user", "content": [{"type": "text", "text": "[Request interrupted by user]"}]}})
            with open(os.path.join(d, f"{cli}.jsonl"), "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(json.dumps(line, ensure_ascii=False) + "\n")
            os.utime(os.path.join(d, f"{cli}.jsonl"), (last / 1000, last / 1000))
        if alive:
            pid = 40000 + self.n
            with open(os.path.join(self.root, ".claude/sessions", f"{pid}.json"), "w") as f:
                json.dump({"pid": pid, "sessionId": cli, "cwd": cwd, "procStart": "777", "startedAt": last}, f)
            os.makedirs(os.path.join(self.proc, str(pid)))
            fields = ["S"] + [str(i) for i in range(1, 19)] + ["777"] + ["0"] * 10
            with open(os.path.join(self.proc, str(pid), "stat"), "w") as f:
                f.write(f"{pid} (claude) " + " ".join(fields) + "\n")
            entry = {"pid": pid, "cwd": cwd, "kind": "interactive", "startedAt": last, "sessionId": cli,
                     "name": title, "status": live_status}
            if waiting_for:
                entry["waitingFor"] = waiting_for
            self.agents.append(entry)
        if alive and live_status == "busy":  # a turn runs: the transcript is being written
            d = os.path.join(self.root, ".claude/projects", encode(cwd), f"{cli}.jsonl")
            os.utime(d, None)  # written just now: working
            with open(d, "a", encoding="utf-8") as f:
                f.write(json.dumps({"type": "assistant", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                                    "cwd": cwd, "message": {"role": "assistant", "content": [{"type": "text", "text": "…"}]}}) + "\n")
        return sid


def build(root: str) -> None:
    d = Demo(root)
    shop = d.repo("shop-site", "# Shop site\n\nThe online shop: Next.js front end, Stripe checkout, admin panel.\n")
    api = d.repo("apps/shop-api", "# shop-api\n\nThe shop's REST API (FastAPI + Postgres).\n", "develop")
    book = d.repo("writing/cookbook", "# Cookbook\n\nA cookbook manuscript: 40 recipes, photos, a chapter per season.\n")
    archive = d.repo("writing/cookbook-photos", "# Cookbook photos\n\nAn archive: the raw photos shot for the cookbook, nothing else.\n")
    tools = d.repo("tools/backup-scripts")
    d.session(shop, "Fix the checkout redirect after 3-D Secure", 0.05, turns=9, alive=True, writes=12,
              plan=[{"content": "Reproduce the redirect loop", "status": "completed"},
                    {"content": "Patch the return URL", "status": "in_progress"},
                    {"content": "Add a regression test", "status": "pending"}])
    d.session(shop, "Admin panel: bulk price update", 0.3, turns=14, status="blocked",
              question="Apply the 10% change to all 240 products, or only the summer category?")
    d.session(shop, "Lighthouse pass on the product page", 2, turns=7, status="review_ready",
              detail="Images lazy-loaded, LCP down from 4.1 s to 1.9 s; please check the gallery on mobile")
    d.session(shop, "Migrate the newsletter form", 9, turns=5)
    d.session(api, "Rate limiting for the search endpoint", 1, turns=11, writes=8, starred=True, alive=True,
              live_status="idle")
    d.session(api, "Add the audit log table", 0.02, turns=4, alive=True, live_status="waiting",
              waiting_for="permission prompt")
    d.session(api, "Stripe webhook retries", 4, turns=8, status="blocked", question="Keep the 24 h retry window or extend it to 72 h?")
    d.session(api, "Postgres 16 upgrade notes", 33, turns=4, writes=0)
    d.session(book, "Chapter 3: spring soups", 0.5, turns=12, interrupted=True,
              plan=[{"content": "Draft the asparagus recipe", "status": "in_progress"},
                    {"content": "Photos list for the chapter", "status": "pending"}])
    d.session(book, "Edit the introduction", 6, turns=3)
    d.session(book, "Edit the introduction", 20, turns=2, writes=0)          # a duplicate title, older
    d.session(book, "Convert recipes to metric", 45, turns=10)
    d.session(tools, "Nightly backup to the NAS", 12, turns=6)
    d.session(tools, "Why did the restore fail?", 70, turns=2, writes=0)
    d.session(os.path.join(root, "Desktop", "old-landing-page"), "Landing page copy", 90, turns=5, transcript=False)
    d.session(os.path.join(root, "Desktop", "old-landing-page"), "Hero image ideas", 95, turns=1, writes=0)
    with open(os.path.join(root, "_agents.json"), "w", encoding="utf-8") as f:
        json.dump(d.agents, f, ensure_ascii=False, indent=2)


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="mishlat-demo-")
    os.makedirs(root, exist_ok=True)
    build(root)
    print(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
