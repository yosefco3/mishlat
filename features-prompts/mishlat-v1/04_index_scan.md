# 04 — Build the index, search, attention, persistence, scanner

## מטרה / Goal
One `scan()` call reads every source and writes `~/.cache/mishlat/index.json`, the single file
that the window, the tray and the Nemo extension read.

## קבצים לשינוי / Files to change
- `mishlat/model.py` — `build_index`, `search`, `attention`, `entered`, `stale_sessions`.
- `mishlat/index.py` (new) — atomic JSON writes (mode 0600), index/cache/aliases/dismissed/settings.
- `mishlat/scan.py` (new) — `Scanner.scan()`; each source guarded on its own.
- `tests/test_model_index.py`, `tests/test_index_io.py`, `tests/test_scan.py`

## מצב נוכחי / Current state
Steps 01–03 give records, live processes, transcripts, folders and the resolution and state rules.

## שינוי נדרש / Required change
- Sessions: every non-archived app record, plus every transcript whose cli id no record claims
  (archived records claim theirs too). Title: app title, else custom title, agent name, first
  prompt, else "(ללא כותרת)".
- Projects: one per resolved key, plus git repositories with no session. Counts: working, open,
  and the attention states counted only for sessions in the attention list.
- Attention: waiting, review or stopped; active in the last 14 days; not dismissed. A dismissal
  stores the time; it holds until the session has newer activity.
- `entered(old, new)`: attention entries whose (id, state) pair is new.
- Index fields as in `docs/plan.html` (shared claim), plus `version`, `roots`, `attention` ids,
  `scan_ms`, `app_version`, `errors`.
- Writes: temp file + `os.replace`, mode 0600, folder 0700.

## טסטים נדרשים / Tests required
- build_index on a fake home: an app session, a terminal-only session, an archived one, a moved
  folder, a repo with no session; counts and order.
- search fields; attention window and dismissal; entered.
- Atomic write leaves no temp file and mode 0600; a broken source becomes an `errors` line.

## קריטריון הצלחה / Success criteria
- Tests pass. `python3 -m mishlat.scan` on the real home writes the index with no errors.

## קומיט / Commit
`feat(scan): build and persist the index with search and attention`
