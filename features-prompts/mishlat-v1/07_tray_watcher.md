# 07 — File monitors, scan thread, tray, notifications

## מטרה / Goal
Keep the index live with no polling of 750 MB: Gio file monitors on the sources start a scan
after 2 s of quiet, a 30 s timer covers the time-based states, and the scan runs in a worker
thread. The tray shows the attention count and notifies on each new attention entry.

## קבצים לשינוי / Files to change
- `mishlat/watcher.py` (new) — `Debouncer`, `ScanRunner` (thread, no overlap), `SourceMonitor`.
- `mishlat/tray.py` (new) — `Tray` (XApp.StatusIcon, menu), `Notifier` (libnotify).
- `mishlat/app.py` — wire the runner, the monitors, the tray and the notifier.
- `data/icons/` — the tray icons (moved here from step 09: the tray needs them).
- `tests/test_watcher.py`, `tests/test_tray.py`

## מצב נוכחי / Current state
Step 06 app with a manual scan.

## שינוי נדרש / Required change
- Monitors: the store folder, `~/.claude/sessions`, `~/.claude/projects` and each project folder
  in it (a new one gets a monitor when it appears).
- `ScanRunner.request()`: if a scan runs, mark "again"; the result goes back to the GTK loop with
  `GLib.idle_add`.
- First scan sets the baseline: no notification. Later: one notification per `entered` entry in
  the "waiting" or "review" state that is not dismissed, with actions "פתח" and "הסתר".
- Tray icon file per count (0, 1, 2, 3+); menu: the attention sections, the working sessions,
  then "פתח את משלט", "סרוק עכשיו", "יציאה".

## טסטים נדרשים / Tests required
- Debouncer with a fake clock: a burst gives one call. Runner: a request during a scan gives one
  more scan, not two. Tray: icon name per count; menu model (pure) per index; the baseline rule.

## קריטריון הצלחה / Success criteria
- A Claude session that ends with a question produces one notification within ~5 s.

## קומיט / Commit
`feat(tray): live monitors, scan thread, tray badge and notifications`
