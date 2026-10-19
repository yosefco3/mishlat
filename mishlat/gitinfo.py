"""Branch and dirty state of a project repository."""

from __future__ import annotations

import os
import subprocess


def git_dir(repo: str) -> str | None:
    p = os.path.join(repo, ".git")
    if os.path.isdir(p):
        return p
    if os.path.isfile(p):  # a worktree or submodule: "gitdir: <path>"
        try:
            with open(p, encoding="utf-8") as f:
                line = f.read().strip()
        except OSError:
            return None
        if line.startswith("gitdir:"):
            target = line.split(":", 1)[1].strip()
            return target if os.path.isabs(target) else os.path.normpath(os.path.join(repo, target))
    return None


def read_branch(repo: str) -> str | None:
    """The branch name, a short commit id when detached, or None."""
    gd = git_dir(repo)
    if gd is None:
        return None
    try:
        with open(os.path.join(gd, "HEAD"), encoding="utf-8") as f:
            head = f.read().strip()
    except OSError:
        return None
    if head.startswith("ref:"):
        ref = head.split(":", 1)[1].strip()
        return ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref
    return head[:7] or None


def is_dirty(repo: str, run=subprocess.run, timeout: float = 3) -> bool | None:
    """True when tracked files changed; None when git cannot tell."""
    try:
        proc = run(["git", "-C", repo, "status", "--porcelain", "--untracked-files=no"],
                   capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return bool(proc.stdout.strip())
