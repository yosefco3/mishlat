"""Folders under the roots (default ~/Desktop), to find moved project folders and to list git
repositories that have no Claude session yet."""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass

from .transcripts import encode_path

SKIP = {"node_modules", "__pycache__", "venv", "build", "dist", "target", "site-packages"}


@dataclass(frozen=True)
class Folder:
    path: str
    is_repo: bool


class FolderIndex:
    def __init__(self, folders: list[Folder], roots: list[str]) -> None:
        self.folders = folders
        self.roots = [r.rstrip("/") for r in roots]
        self._by_path = {f.path: f for f in folders}
        self._by_encoding: dict[str, list[str]] = defaultdict(list)
        self._by_base: dict[str, list[str]] = defaultdict(list)
        for f in folders:
            self._by_encoding[encode_path(f.path)].append(f.path)
            self._by_base[encode_path(os.path.basename(f.path))].append(f.path)

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
                    folders.append(Folder(e.path, is_repo))
                    if not is_repo:
                        nxt.append(e.path)
            level = nxt
    return FolderIndex(folders, roots)
