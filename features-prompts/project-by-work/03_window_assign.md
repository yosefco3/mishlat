# 03 — Origin in the tooltip, "שייך לפרויקט…", docs, install

## מטרה / Goal
Show where a moved session started, and let the user assign any session to a project by hand.

## קבצים לשינוי / Files to change
- `mishlat/window.py` — tooltip line, menu items, the project picker dialog.
- `README.md`, `APP_OVERVIEW.md`
- `tests/test_window_smoke.py`

## שינוי נדרש / Required change
- Tooltip: "התחילה ב־ <start folder>" when `started_in` is set.
- Menu: "שייך לפרויקט…" opens a dialog with the project list (search box, newest first) and a
  folder chooser for a folder with no session yet; "החזר לשיוך האוטומטי" when assigned by hand.
- Both write `assignments.json` and request a scan.

## קומיט / Commit
`feat(window): show where a session started and assign it by hand`
