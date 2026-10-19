"""Everything that leaves Mishlat: open a session in the Claude app, resume it in a terminal,
open a folder, start a new session. Each takes a `run` callable so tests check the argv."""

from __future__ import annotations

import glob
import os
import re
import shlex
import shutil
import subprocess

from . import paths
from .paths import version_key
from .strings import t

APP_ID = re.compile(r"^local_[A-Za-z0-9-]{1,64}$")           # the app's own check
CLI_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def spawn(argv: list[str]) -> None:
    """Start a program detached from Mishlat."""
    subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def session_url(session: dict) -> str | None:
    """The app's own routes (found in the app bundle, v2.42304.2):
    an app session opens with code/continue; a terminal-only session is imported with resume."""
    sid = session.get("id") or ""
    if APP_ID.match(sid):
        return f"claude://code/continue?session={sid}"
    cli = session.get("cli_id") or ""
    if CLI_ID.match(cli):
        return f"claude://resume?session={cli}"
    return None


def open_session(session: dict, run=spawn) -> bool:
    url = session_url(session)
    if url is None:
        return False
    run(["xdg-open", url])
    return True


def claude_cli(home: str, which=shutil.which) -> str | None:
    """`claude` on PATH, else the newest CLI bundled with the desktop app."""
    found = which("claude")
    if found:
        return found
    bundled = [p for p in glob.glob(os.path.join(home, paths.BUNDLED_CLI_GLOB)) if os.access(p, os.X_OK)]
    if not bundled:
        return None
    return max(bundled, key=lambda p: version_key(os.path.basename(os.path.dirname(os.path.dirname(p)))))


def terminal_command(cwd: str, cli: str, cli_id: str, which=shutil.which) -> list[str]:
    if which("gnome-terminal"):
        return ["gnome-terminal", f"--working-directory={cwd}", "--", cli, "--resume", cli_id]
    line = f"cd {shlex.quote(cwd)} && exec {shlex.quote(cli)} --resume {shlex.quote(cli_id)}"
    return ["x-terminal-emulator", "-e", "bash", "-lc", line]


def resume_in_terminal(session: dict, project_path: str | None, home: str, run=spawn,
                       which=shutil.which, isdir=os.path.isdir) -> str | None:
    """Resume in a terminal, in the folder where the transcript is now. Returns an error text or None."""
    cli_id = session.get("cli_id")
    if not cli_id:
        return t("לשיחה הזו אין מזהה של Claude Code")
    cli = claude_cli(home, which)
    if cli is None:
        return t("לא נמצא claude במחשב")
    for cwd in (project_path, session.get("cwd"), home):
        if cwd and isdir(cwd):
            break
    run(terminal_command(cwd, cli, cli_id, which))
    return None


def open_folder(path: str, run=spawn) -> None:
    run(["xdg-open", path])


def new_session_in(path: str, run=spawn) -> None:
    """The same call the app's own file-manager script makes."""
    run(["claude-desktop", "--os-entry=folder_verb", path])
