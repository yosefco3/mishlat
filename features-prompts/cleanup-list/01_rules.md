# 01 — Rules, keep file, delete requests

## קבצים לשינוי / Files to change
- `mishlat/store.py` — `Record.turns` (`completedTurns`).
- `mishlat/model.py` — session row: `turns`, `writes`; `cleanup_reason(...)`; `index["cleanup"]`,
  `totals["cleanup"]`, `totals["cleanup_by"]`.
- `mishlat/index.py` — `load_keep`, `keep`, `unkeep`; `load_delete_requests`, `request_delete`,
  `prune_delete_requests`; `settings["old_days"]`.
- `mishlat/scan.py` — pass keep + settings; prune requests of sessions that no longer exist.
- Tests: `tests/test_store.py`, `tests/test_model_index.py`, `tests/test_index_io.py`, `tests/test_scan.py`.

## שינוי נדרש / Required change
`cleanup_reason(s, project, duplicates, now, old_days, kept)` returns the reason key or None, in
the priority order of `_PROGRESS.md`. `writes` on the row = sum of transcript writes + local
writes (0 without a transcript). Duplicates: same title (trimmed), the newer session wins; only
sessions with a transcript or an app record count. The request file holds ids approved for
deletion; `prune_delete_requests` drops ids that are no longer in the store (deleted).

## קומיט / Commit
`feat(model): the cleanup list, by rules, with keep and delete-request files`
