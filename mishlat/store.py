"""The Claude desktop app's session records: `<store>/<org>/<workspace>/local_<id>.json`.

Read-only. The store holds 40+ MB of records, so `StoreReader` re-parses a file only when its
(mtime, size) changed.
"""

from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass

from .paths import STORE_GLOBS


@dataclass(frozen=True)
class Record:
    id: str                  # local_<uuid>
    cli_id: str | None       # the Claude Code session id = the transcript file name
    title: str
    cwd: str
    last_activity: int       # ms since the epoch
    archived: bool
    starred: bool
    status: str | None       # post-turn summary: completed / blocked / review_ready
    question: str | None     # needs_action
    detail: str | None       # status_detail
    fresh: bool              # the summary belongs to the last turn
    turns: int | None = None  # completedTurns, when the app recorded it


def _text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _ms(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


def parse_record(obj: object) -> Record | None:
    """One record, or None when the shape is not a desktop session record."""
    if not isinstance(obj, dict):
        return None
    sid, cwd = obj.get("sessionId"), obj.get("cwd")
    if not isinstance(sid, str) or not sid.startswith("local_") or not isinstance(cwd, str) or not cwd:
        return None
    summary = obj.get("postTurnSummary")
    summary = summary if isinstance(summary, dict) else {}
    last_uuid = _text(obj.get("lastAssistantUuid"))
    summarized = _text(summary.get("summarizes_uuid"))
    fresh = last_uuid is None or summarized is None or last_uuid == summarized
    return Record(
        id=sid,
        cli_id=_text(obj.get("cliSessionId")),
        title=_text(obj.get("title")) or "",
        cwd=cwd,
        last_activity=_ms(obj.get("lastActivityAt")) or _ms(obj.get("createdAt")),
        archived=obj.get("isArchived") is True,
        starred=obj.get("isStarred") is True,
        status=_text(summary.get("status_category")),
        question=_text(summary.get("needs_action")),
        detail=_text(summary.get("status_detail")),
        fresh=fresh,
        turns=obj.get("completedTurns") if isinstance(obj.get("completedTurns"), int)
        and not isinstance(obj.get("completedTurns"), bool) else None,
    )


class StoreReader:
    """Reads every record; unchanged files come from the in-memory cache."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, int, Record | None]] = {}
        self.parsed = 0  # files parsed by the last read (for tests and diagnostics)

    def read(self, home: str) -> tuple[list[Record], list[str]]:
        paths = [p for pattern in STORE_GLOBS for p in glob.glob(os.path.join(home, pattern))]
        records: list[Record] = []
        bad = 0
        self.parsed = 0
        seen = set()
        for path in paths:
            seen.add(path)
            try:
                st = os.stat(path)
            except OSError:
                continue
            hit = self._cache.get(path)
            if hit is not None and hit[0] == st.st_mtime and hit[1] == st.st_size:
                record = hit[2]
            else:
                record = None
                try:
                    with open(path, encoding="utf-8") as f:
                        record = parse_record(json.load(f))
                except (OSError, ValueError):
                    record = None
                self.parsed += 1
                self._cache[path] = (st.st_mtime, st.st_size, record)
            if record is None:
                bad += 1
            else:
                records.append(record)
        for gone in set(self._cache) - seen:
            del self._cache[gone]
        errors = []
        if not paths:
            errors.append("store: no session records found under ~/.config/Claude (is the Claude app installed?)")
        elif bad:
            errors.append(f"store: {bad} of {len(paths)} session records have an unknown shape")
        return records, errors
