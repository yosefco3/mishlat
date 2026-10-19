"""Command line. `mishlat scan` runs one scan with no GUI; anything else starts or reaches the app."""

from __future__ import annotations

import json
import sys
import time

from . import __version__, paths

USAGE = """usage: mishlat [--toggle | --project PATH | --tray | --quit]
       mishlat scan [--json]
       mishlat cleanup [--json]
       mishlat --version

  (no option)    show the Mishlat window
  --toggle       show or hide the window (the Super+Shift+C hotkey)
  --project PATH show one folder and the projects under it
  --tray         start in the tray only (used at login)
  --quit         stop the running Mishlat
  scan           scan once, write the index, print a summary (no GUI)
  cleanup        list the sessions approved for deletion in the window, for a Claude session to run
"""

CLEANUP_EN = {"gone": "folder gone", "no_transcript": "no transcript", "duplicate": "duplicate title",
              "empty": "empty", "old": "old"}

GLYPH = {"working": "●", "open": "○", "waiting": "◐", "review": "◑", "stopped": "◼", "idle": "·"}


def summary(index: dict, home: str) -> str:
    from .model import attention_sessions

    t = index["totals"]
    when = time.strftime("%Y-%m-%d %H:%M", time.localtime(index["scanned_at"] / 1000))
    lines = [
        f"Mishlat scan · {when} · {index['scan_ms']} ms · Claude Code {index.get('app_version') or '?'}",
        f"projects {t['projects']} · sessions {t['sessions']} · working {t['working']} · open {t['open']} · "
        f"stale {t['stale']} · gone folders (in כללי) {t['lost']}",
        f"attention {t['attention']}: waiting {t['waiting']} · review {t['review']} · stopped {t['stopped']} · "
        f"cleanup {t.get('cleanup', 0)}",
        "errors: " + ("none" if not index["errors"] else str(len(index["errors"]))),
    ]
    lines += [f"  ! {e}" for e in index["errors"]]
    lines.append("")
    lines.append("Projects (newest first):")
    for p in index["projects"]:
        if not p["sessions"]:
            continue
        marks = " ".join(f"{GLYPH[k]}{p[k]}" for k in ("working", "waiting", "review", "stopped", "open") if p[k])
        where = p["path"] or ("(sessions whose folder no longer exists, and app scratch sessions)"
                              if p.get("general") else "(folder not found)")
        if where.startswith(home):
            where = "~" + where[len(home):]
        lines.append(f"  {p['name'][:34]:34} {len(p['sessions']):4} sessions  {marks:12} {where}")
    attention = attention_sessions(index)
    if attention:
        lines.append("")
        lines.append("Needs you:")
        names = {p["key"]: p["name"] for p in index["projects"]}
        for s in attention:
            extra = s["question"] or s["detail"] or ""
            lines.append(f"  {GLYPH[s['state']]} {names.get(s['project'], '?')} · {s['title']}"
                         + (f" — {extra}" if extra else ""))
    by = (t.get("cleanup_by") or {})
    if t.get("cleanup"):
        lines.append("")
        lines.append("Cleanup (worth deleting, see the window's למחיקה list): " +
                     " · ".join(f"{CLEANUP_EN[k]} {n}" for k, n in by.items() if n))
    return "\n".join(lines)


def run_cleanup(home: str, args: list[str]) -> int:
    """The sessions the user approved for deletion in the window."""
    from . import index as io

    requests = io.load_delete_requests(home)
    if "--json" in args:
        print(json.dumps({"delete": [{"id": k, **v} for k, v in requests.items()]}, ensure_ascii=False, indent=1))
        return 0
    if not requests:
        print("No sessions approved for deletion. Approve some in the window: Super+Shift+C ▸ למחיקה.")
        return 0
    print(f"{len(requests)} sessions approved for deletion in Mishlat:")
    for sid, v in requests.items():
        print(f"  {sid}  {v.get('title', '')}")
    print()
    print("To run them, tell any Claude session: תמחק את השיחות שאישרתי במשלט")
    print("It deletes each one through the app (the app asks per session); the next scan drops them.")
    return 0


def run_scan(home: str, args: list[str]) -> int:
    from .scan import Scanner

    index = Scanner(home).scan()
    if "--json" in args:
        print(json.dumps(index, ensure_ascii=False, indent=1))
    else:
        print(summary(index, home))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    args = argv[1:]
    home = paths.default_home()
    if args[:1] == ["scan"]:
        return run_scan(home, args[1:])
    if args[:1] == ["cleanup"]:
        return run_cleanup(home, args[1:])
    if args[:1] in (["--version"], ["-V"]):
        print(f"mishlat {__version__}")
        return 0
    if args[:1] in (["--help"], ["-h"]):
        print(USAGE)
        return 0
    from .app import run_gui

    return run_gui(home, argv)
