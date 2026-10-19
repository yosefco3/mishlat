# 04 — Demo home, screenshots, the waitingFor labels

## מטרה / Goal
The demo and the screenshots work with the new source; the window shows a documented
`waitingFor` value in the UI language.

## קבצים לשינוי / Files to change
- `scripts/demo_home.py` — `session(..., alive, live_status, waiting_for)` records a listing
  entry; `build` writes `<home>/_agents.json`; one open (idle) and one waiting (permission
  prompt) session added; the docstring shows `MISHLAT_AGENTS_CMD="cat $H/_agents.json"`
- `scripts/screenshot.py` — sets `MISHLAT_AGENTS_CMD` before the scan
- `mishlat/view.py`, `mishlat/strings.py` — `WAITING_FOR` map (five values) used by `subline`
- `tests/test_view.py`

## שינוי נדרש / Required change
The transcript of an alive demo session is touched (written "now") only when its live status is
busy, so the fallback path still shows it working and the listing path shows idle ones open.

## טסטים נדרשים / Tests required
- `subline` of a waiting row with `question == "permission prompt"` → the Hebrew label; in
  English → "asks you to approve an action"; an unknown text is shown as is.
- The demo home builds and its `_agents.json` parses with `parse_agents_json` into the alive
  sessions (a small test that imports `scripts/demo_home.py`).

## קריטריון הצלחה / Success criteria
- Acceptance test 4 of `_PROGRESS.md`; `python3 scripts/screenshot.py` rewrites the six PNGs.

## קומיט / Commit
`feat(demo): the demo home fakes the listing; waitingFor labels in the window`
