# 02 — The list in the window, the summary, the command

## קבצים לשינוי / Files to change
- `mishlat/view.py` — `CLEANUP_LABEL`, `cleanup_list(index)`, `cleanup_counts(index)`.
- `mishlat/window.py` — chip "למחיקה (N)", mode `cleanup`: rows with מחק / השאר, footer with
  "אשר הכול (N)" and the approved count; approved rows leave the list.
- `mishlat/cli.py` — the Cleanup section in `mishlat scan`; `mishlat cleanup [--json]`.
- Tests: `tests/test_view.py`, `tests/test_window_smoke.py`, `tests/test_scan.py`.

## קומיט / Commit
`feat(window): the "למחיקה" list with keep, delete and approve-all`
