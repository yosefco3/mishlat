"""One scan: read every source, build the index, write it. A failing source becomes one line in
`index["errors"]`; the scan itself never fails."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time

from . import agents
from . import index as io
from . import paths
from .paths import version_key
from .describe import ReadmeCache
from .folders import FolderIndex, find_by_identity, folder_index, identity
from .gitinfo import is_dirty, read_branch
from .live import read_live
from .model import build_index, mark_cleanup
from .store import StoreReader
from .transcripts import index_transcripts

FOLDERS_TTL_S = 30
DIRTY_TTL_S = 60


def app_version(home: str) -> str | None:
    """The newest Claude Code version bundled with the desktop app."""
    try:
        names = [n for n in os.listdir(os.path.join(home, paths.BUNDLED_CLI_DIR)) if re.match(r"^\d+(\.\d+)+$", n)]
    except OSError:
        return None
    return max(names, key=version_key) if names else None


class Scanner:
    """Keeps the caches between scans. Use one Scanner from one thread at a time."""

    def __init__(self, home: str, proc_root: str | None = None, clock=None, git_run=subprocess.run,
                 env=None) -> None:
        """`env` (default `os.environ`) carries the overrides: MISHLAT_PROC_ROOT (a fake /proc for the
        demo), MISHLAT_AGENTS_CMD (a command instead of the bundled CLI), MISHLAT_AGENTS_DISABLE=1."""
        self.home = home
        self.env = os.environ if env is None else env
        self.proc_root = proc_root or self.env.get("MISHLAT_PROC_ROOT") or "/proc"
        self.agents_timeout = agents.TIMEOUT_S
        self.clock = clock or (lambda: int(time.time() * 1000))
        self.git_run = git_run
        self.store = StoreReader()
        self.tx_cache = io.load_cache(home)
        self.readmes = ReadmeCache()
        self.folder_memory = io.load_folder_memory(home)
        self._folders: tuple[float, tuple, FolderIndex] | None = None
        self._dirty: dict[str, tuple[float, bool | None]] = {}

    def folders(self, roots: list[str]) -> FolderIndex:
        now = time.monotonic()
        if self._folders and self._folders[1] == tuple(roots) and now - self._folders[0] < FOLDERS_TTL_S:
            return self._folders[2]
        idx = folder_index(roots)
        self._folders = (now, tuple(roots), idx)
        return idx

    def remember(self, folders: FolderIndex, records) -> None:
        """Record the identity of every folder that exists now: the index, and each session's folder."""
        known = {f.path for f in folders.folders} | {r.cwd.rstrip("/") for r in records if r.cwd}
        changed = False
        for path in known:
            if not os.path.isdir(path):
                continue
            ident = identity(path)
            if ident is None:
                continue
            ident["seen"] = self.clock()
            old = self.folder_memory.get(path)
            if old is None or {k: old.get(k) for k in ("dev", "ino", "remote", "entries")} != \
                    {k: ident[k] for k in ("dev", "ino", "remote", "entries")}:
                self.folder_memory[path] = ident
                changed = True
            else:
                old["seen"] = ident["seen"]
        if changed:
            io.save_folder_memory(self.home, self.folder_memory)

    def find_moved(self, folders: FolderIndex, records, roots: list[str]) -> dict[str, str]:
        """old path -> where it is now, for every session folder that vanished but is remembered."""
        lost: dict[str, dict] = {}
        for r in records:
            if not r.cwd:
                continue
            path = r.cwd.rstrip("/")
            i = path.find("/.claude/worktrees/")
            if i >= 0:
                path = path[:i]
            if os.path.isdir(path) or path in lost:
                continue
            remembered = self.folder_memory.get(path)
            if remembered:
                lost[path] = remembered
        if not lost:
            return {}
        found = {}
        for old, w in lost.items():
            new = folders.by_identity(w)
            if new:
                found[old] = new
        missing = {old: w for old, w in lost.items() if old not in found}
        if missing:
            found.update(find_by_identity(roots, missing))  # a folder moved into a repository, or deeper
        return found

    def read_agents(self) -> dict | None:
        """`claude agents --json`, the primary live source; None when disabled. Any failure
        raises AgentsError, which the scan reports as one error line before falling back."""
        argv = agents.agents_command(self.home, self.env)
        return agents.read_agents(argv, self.agents_timeout) if argv else None

    def git(self, path: str) -> dict | None:
        branch = read_branch(path)
        if branch is None:
            return None
        now = time.monotonic()
        hit = self._dirty.get(path)
        if hit is None or now - hit[0] >= DIRTY_TTL_S:
            hit = (now, is_dirty(path, run=self.git_run))
            self._dirty[path] = hit
        return {"is_repo": True, "branch": branch, "dirty": hit[1]}

    def scan(self) -> dict:
        t0 = time.monotonic()
        now = self.clock()
        errors: list[str] = []

        def guarded(name, fn, default):
            try:
                return fn()
            except Exception as exc:  # one source must never stop the scan
                errors.append(f"{name}: {type(exc).__name__}: {exc}")
                return default

        settings = guarded("settings", lambda: io.load_settings(self.home),
                           {"roots": paths.default_roots(self.home), "old_days": 30})
        records, store_errors = guarded("store", lambda: self.store.read(self.home), ([], []))
        errors.extend(store_errors)
        live = guarded("agents", self.read_agents, None)
        live_source = "agents" if live is not None else "registry"
        if live is None:  # disabled, or the command failed: the registry + /proc, as before 0.1.2
            live = guarded("live", lambda: read_live(self.home, self.proc_root), {})
        before = {p: (e["size"], e["mtime"]) for p, e in self.tx_cache.items()}
        transcripts = guarded("transcripts", lambda: index_transcripts(self.home, self.tx_cache), {})
        folders = guarded("folders", lambda: self.folders(settings["roots"]), FolderIndex([], settings["roots"]))
        guarded("folder memory", lambda: self.remember(folders, records), None)
        found = guarded("find moved", lambda: self.find_moved(folders, records, settings["roots"]), {})
        aliases = guarded("aliases", lambda: io.load_aliases(self.home), {})
        dismissed = guarded("dismissed", lambda: io.load_dismissed(self.home), {})
        assignments = guarded("assignments", lambda: io.load_assignments(self.home), {})
        descriptions = guarded("descriptions", lambda: io.load_descriptions(self.home), {})
        index = guarded("model", lambda: build_index(records, transcripts, live, folders, now, aliases, dismissed,
                                                     self.git, assignments=assignments,
                                                     describe=self.readmes.purpose, descriptions=descriptions,
                                                     found=found), None)
        if index is None:
            index = build_index([], {}, {}, FolderIndex([], settings["roots"]), now)
        kept = guarded("keep", lambda: io.load_keep(self.home), {})
        guarded("cleanup", lambda: mark_cleanup(index, now, settings.get("old_days", 30), kept), None)
        ids = {s["id"] for p in index["projects"] for s in p["sessions"]}
        guarded("prune requests", lambda: io.prune_delete_requests(self.home, ids), 0)
        index["errors"] = errors
        index["live_source"] = live_source
        index["app_version"] = app_version(self.home)
        index["scan_ms"] = int((time.monotonic() - t0) * 1000)
        guarded("write index", lambda: io.write_index(self.home, index), None)
        if before != {p: (e["size"], e["mtime"]) for p, e in self.tx_cache.items()}:
            guarded("write cache", lambda: io.save_cache(self.home, self.tx_cache), None)
        return index


def main() -> int:
    index = Scanner(paths.default_home()).scan()
    t = index["totals"]
    print(f"projects {t['projects']} · sessions {t['sessions']} · attention {t['attention']} · "
          f"working {t['working']} · live source {index['live_source']} · scan {index['scan_ms']} ms · "
          f"errors {len(index['errors'])}")
    for e in index["errors"]:
        print("  error:", e, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
