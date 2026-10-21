# 02 — Docs, version 0.1.4, install

## מטרה / Goal
Document the button, bump the version, sync the plugin copy, refresh the graphs, install locally.

## קבצים לשינוי / Files to change
- `README.md` — the "Click a row" bullet and a Use-table row.
- `APP_OVERVIEW.md` — a change-history row.
- `mishlat/__init__.py`, `plugin/.claude-plugin/plugin.json`, `tests/test_scan.py` — 0.1.4.

## טסטים נדרשים / Tests required
- `make check` green; `mishlat scan` still reports `live source: agents`.

## קריטריון הצלחה / Success criteria
- The installed copy shows the button; the docs describe it.

## קומיט / Commit
`chore(release): 0.1.4 — New task button`
