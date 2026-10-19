# 06 — The window, the single-instance app, `mishlat scan`

## מטרה / Goal
The "משלט" window and the process that owns it. One process per login session: a second launch
(the hotkey, the Nemo menu, the menu entry) reaches the first through `Gtk.Application`.

## קבצים לשינוי / Files to change
- `mishlat/window.py` (new) — `MishlatWindow`.
- `mishlat/app.py` (new) — `MishlatApp(Gtk.Application)`, `main(argv)`.
- `mishlat/__main__.py` (new) — `python3 -m mishlat`.
- `tests/test_window_smoke.py`

## מצב נוכחי / Current state
Steps 01–05: index, actions, view model.

## שינוי נדרש / Required change
- Window (RTL): a search entry, filter chips (הכול / פעילים / השבוע / ישנים), a status line; on
  the right the attention column in sections; on the left the project cards in a flow box,
  newest first. A card unfolds on click; a session row opens the session; a right-click menu
  offers app / terminal / folder / copy id / dismiss. Search and the "ישנים" chip replace the
  cards with lists. `show_project(path)` filters to one folder and the projects under it.
- App: `HANDLES_COMMAND_LINE`; arguments `--toggle`, `--project PATH`, `--tray`, `--quit`;
  default shows the window. The app holds itself so the tray keeps running with no window.
  On start it shows the last index from disk at once, then scans (in a thread, step 07 wires the
  monitors).
- `mishlat scan [--json]` runs one scan without GTK and prints an English summary.

## טסטים נדרשים / Tests required
- With a display: build the window from a fake index, search, filter, project focus; no exception.
  Skipped without `DISPLAY`.
- `mishlat scan` on a fake home prints the summary and exits 0.

## קריטריון הצלחה / Success criteria
- `python3 -m mishlat` opens the window on the dev laptop with real data.

## קומיט / Commit
`feat(window): the Mishlat window and single-instance app`
