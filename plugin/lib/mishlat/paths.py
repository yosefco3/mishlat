"""Every path Mishlat reads or writes. Each function takes `home`, so tests use a fake home."""

from __future__ import annotations

import os
import re

# Read-only sources (owned by the Claude desktop app and Claude Code).
STORE_GLOB = ".config/Claude/claude-code-sessions/*/*/local_*.json"                    # Linux
STORE_GLOBS = (STORE_GLOB, "Library/Application Support/Claude/claude-code-sessions/*/*/local_*.json")  # + macOS
PROJECTS_DIR = ".claude/projects"
LIVE_DIR = ".claude/sessions"
BUNDLED_CLI_GLOB = ".config/Claude/claude-code/*/*/claude"
BUNDLED_CLI_DIR = ".config/Claude/claude-code"


def default_home() -> str:
    """The home to scan. `MISHLAT_HOME` overrides it for tests and trials."""
    return os.environ.get("MISHLAT_HOME") or os.path.expanduser("~")


# Mishlat's own files: the only places it writes.
def cache_dir(home: str) -> str:
    return os.path.join(home, ".cache", "mishlat")


def config_dir(home: str) -> str:
    return os.path.join(home, ".config", "mishlat")


def index_path(home: str) -> str:
    return os.path.join(cache_dir(home), "index.json")


def transcript_cache_path(home: str) -> str:
    return os.path.join(cache_dir(home), "transcripts.json")


def aliases_path(home: str) -> str:
    """Old folder path -> new folder path, written by the user for folders Mishlat cannot find."""
    return os.path.join(config_dir(home), "aliases.json")


def dismissed_path(home: str) -> str:
    return os.path.join(config_dir(home), "dismissed.json")


def assignments_path(home: str) -> str:
    """{session id: project folder}, written by the window's "שייך לפרויקט…"."""
    return os.path.join(config_dir(home), "assignments.json")


def descriptions_path(home: str) -> str:
    """{folder: purpose}: what a folder is for, in the user's words (wins over its README)."""
    return os.path.join(config_dir(home), "descriptions.json")


def keep_path(home: str) -> str:
    """{session id: time}: sessions the user keeps out of the cleanup list."""
    return os.path.join(config_dir(home), "keep.json")


def delete_requests_path(home: str) -> str:
    """{session id: {title, at}}: approved for deletion; a Claude session runs them through the app."""
    return os.path.join(config_dir(home), "delete-requests.json")


def settings_path(home: str) -> str:
    return os.path.join(config_dir(home), "settings.json")


def default_roots(home: str) -> list[str]:
    return [os.path.join(home, "Desktop")]


def install_dir(home: str) -> str:
    return os.path.join(home, ".local", "share", "mishlat")


def launcher_path(home: str) -> str:
    return os.path.join(home, ".local", "bin", "mishlat")


def version_key(name: str) -> tuple:
    """"2.1.299" -> (2, 1, 299), so versions sort as numbers."""
    return tuple(int(n) for n in re.findall(r"\d+", name))
