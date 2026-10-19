"""Folders under the roots (default ~/Desktop), to find moved project folders and to list git
repositories that have no Claude session yet."""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass

from .gitinfo import remote_url
from .transcripts import encode_path

SKIP = {"node_modules", "__pycache__", "venv", "build", "dist", "target", "site-packages"}
SAMPLE = 8  # top-level entry names remembered per folder, to tell a renamed folder from a recycled inode


@dataclass(frozen=True)
class Folder:
    path: str
    is_repo: bool
    dev: int = 0
    ino: int = 0


def identity(path: str) -> dict | None:
    """What stays the same when a folder is renamed or moved: its device+inode, its git remote,
    and a sample of its top-level entry names. None when the folder cannot be read."""
    try:
        st = os.stat(path)
        with os.scandir(path) as it:
            names = sorted(e.name for e in it if not e.name.startswith("."))[:SAMPLE]
    except OSError:
        return None
    return {"dev": st.st_dev, "ino": st.st_ino, "remote": remote_url(path), "entries": names}


def same_folder(remembered: dict, candidate: str) -> bool:
    """Is `candidate` the folder `remembered` describes, after a rename or a move?"""
    now = identity(candidate)
    if now is None:
        return False
    if remembered.get("remote") and now.get("remote") and remembered["remote"] != now["remote"]:
        return False
    if (now["dev"], now["ino"]) == (remembered.get("dev"), remembered.get("ino")):
        old = set(remembered.get("entries") or [])
        if not old:
            return True
        return bool(old & set(now["entries"]))  # a recycled inode holds other files
    return bool(remembered.get("remote")) and remembered["remote"] == now.get("remote")


class FolderIndex:
    def __init__(self, folders: list[Folder], roots: list[str]) -> None:
        self.folders = folders
        self.roots = [r.rstrip("/") for r in roots]
        self._by_path = {f.path: f for f in folders}
        self._by_encoding: dict[str, list[str]] = defaultdict(list)
        self._by_base: dict[str, list[str]] = defaultdict(list)
        self._by_ino: dict[tuple, list[str]] = defaultdict(list)
        for f in folders:
            self._by_encoding[encode_path(f.path)].append(f.path)
            self._by_base[encode_path(os.path.basename(f.path))].append(f.path)
            if f.ino:
                self._by_ino[(f.dev, f.ino)].append(f.path)

    def by_identity(self, remembered: dict) -> str | None:
        """The one indexed folder that is the remembered one, by inode (guarded) or by remote."""
        hits = [p for p in self._by_ino.get((remembered.get("dev"), remembered.get("ino")), []) if same_folder(remembered, p)]
        if not hits and remembered.get("remote"):
            hits = [f.path for f in self.folders if f.is_repo and remote_url(f.path) == remembered["remote"]]
        return hits[0] if len(hits) == 1 else None

    def at(self, path: str) -> Folder | None:
        return self._by_path.get(path)

    def by_encoding(self, folder_name: str) -> list[str]:
        """Folders whose Claude Code transcript folder would be `folder_name`."""
        return list(self._by_encoding.get(folder_name, []))

    def by_basename(self, old_path: str) -> list[str]:
        """Folders whose name matches the old folder's name (`_` and `-` count as equal)."""
        return list(self._by_base.get(encode_path(os.path.basename(old_path.rstrip("/"))), []))

    def repos(self) -> list[Folder]:
        return [f for f in self.folders if f.is_repo]


def find_by_identity(roots: list[str], wanted: dict[str, dict], depth: int = 6) -> dict[str, str]:
    """old path -> new path for the remembered folders found under the roots, descending into
    repositories too (where the index does not). Used only while some remembered folder is lost."""
    by_ino = {(w.get("dev"), w.get("ino")): old for old, w in wanted.items()}
    remotes = {w["remote"]: old for old, w in wanted.items() if w.get("remote")}
    found: dict[str, str] = {}
    level = [r for r in roots if os.path.isdir(r)]
    for _ in range(depth):
        nxt: list[str] = []
        for d in level:
            try:
                entries = list(os.scandir(d))
            except OSError:
                continue
            for e in entries:
                try:
                    if not e.is_dir(follow_symlinks=False) or e.name.startswith(".") or e.name in SKIP:
                        continue
                    st = e.stat(follow_symlinks=False)
                except OSError:
                    continue
                old = by_ino.get((st.st_dev, st.st_ino))
                if old and old not in found and same_folder(wanted[old], e.path):
                    found[old] = e.path
                elif remotes and os.path.exists(os.path.join(e.path, ".git")):
                    old = remotes.get(remote_url(e.path) or "")
                    if old and old not in found and same_folder(wanted[old], e.path):
                        found[old] = e.path
                nxt.append(e.path)
        level = nxt
        if len(found) == len(wanted):
            break
    return found


def folder_index(roots: list[str], depth: int = 3) -> FolderIndex:
    """Breadth-first to `depth` levels. A git repository is recorded and not descended into."""
    folders: list[Folder] = []
    for root in roots:
        level = [root]
        for _ in range(depth):
            nxt: list[str] = []
            for d in level:
                try:
                    entries = sorted(os.scandir(d), key=lambda e: e.name)
                except OSError:
                    continue
                for e in entries:
                    try:
                        is_dir = e.is_dir(follow_symlinks=False)
                    except OSError:
                        continue
                    if not is_dir or e.name.startswith(".") or e.name in SKIP:
                        continue
                    is_repo = os.path.exists(os.path.join(e.path, ".git"))
                    try:
                        st = e.stat(follow_symlinks=False)
                        folders.append(Folder(e.path, is_repo, st.st_dev, st.st_ino))
                    except OSError:
                        folders.append(Folder(e.path, is_repo))
                    if not is_repo:
                        nxt.append(e.path)
            level = nxt
    return FolderIndex(folders, roots)
