# 01 — Paths, app store reader, live process registry

## מטרה / Goal
Read the two app-side sources that need no transcript: the desktop app's session records and the
live process registry of Claude Code. Pure parsing functions plus thin readers; no UI yet.

## קבצים לשינוי / Files to change
- `mishlat/paths.py` (new) — every path Mishlat reads or writes, all relative to a `home` argument.
- `mishlat/store.py` (new) — `parse_record(obj) -> Record | None`, `StoreReader.read(home)` with an
  (mtime, size) cache.
- `mishlat/live.py` (new) — `parse_proc_start(stat)`, `read_live(home, proc_root)`.
- `tests/test_store.py`, `tests/test_live.py`, `tests/helpers.py` (fake home builder).

## מצב נוכחי / Current state
Empty repository. Record shape (verified 2026-10-19 on 178 records): `sessionId` (`local_…`),
`cliSessionId`, `cwd`, `originCwd`, `title`, `lastActivityAt` (ms), `createdAt`, `isArchived`,
`isStarred`, `lastAssistantUuid`, `postTurnSummary{status_category, status_detail, needs_action,
summarizes_uuid}`. Registry `~/.claude/sessions/<pid>.json`: `pid`, `sessionId` (= cli id),
`cwd`, `procStart`, `name`, `entrypoint`; alive iff `/proc/<pid>/stat` field 22 == `procStart`.

## שינוי נדרש / Required change
- `Record` dataclass: id, cli_id, title, cwd, last_activity, archived, starred, status, question,
  detail, fresh. `fresh` is True when the summary's `summarizes_uuid` equals `lastAssistantUuid`
  or either is missing (the in-app pane rule, plus the missing-uuid case).
- `parse_record` rejects anything without a `local_…` id and a `cwd`.
- `StoreReader` keeps `{path: (mtime, size, Record)}` and re-parses only changed files (the store
  is 42 MB); unreadable files count into one error line.
- `read_live` keeps a process only when the start time matches; two live files for one session:
  the newest `startedAt` wins.

## טסטים נדרשים / Tests required
- parse: a waiting record, a stale summary (other uuid), a missing uuid, a bad id, an archived one.
- StoreReader: a second read with no change does not parse again; a changed file does.
- live: a matching start time, a reused pid with another start time, a missing /proc entry,
  a broken JSON file.

## קריטריון הצלחה / Success criteria
- `python3 -m pytest -q` passes. `python3 -c "from mishlat.store import StoreReader; …"` on the
  real home returns 178 records and no errors.

## קומיט / Commit
`feat(sources): read the app session store and the live process registry`
