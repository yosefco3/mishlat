# Progress — mishlat-v1

Mishlat (משלט, "control post") is a read-only desktop companion for the Claude desktop app on
the dev laptop (Linux Mint, Cinnamon, Nemo). It shows every project and its Claude Code
sessions in one window, marks the sessions that need the user (waiting, review, stopped), puts a
badge in the Cinnamon panel with a notification on each change, and marks project folders in
Nemo with an emblem, a "Claude" column and a right-click menu. The approved plan is
`docs/plan.html` (published as https://claude.ai/artifact/Qk7vudHXgSix1L5VHymp9S).

## מטרת-על / High-level goal
- מתי / When: always on; the tray process starts at login and rescans on every file change.
- עיקרון / Principle: **read-only towards Claude.** Nothing under `~/.config/Claude` or `~/.claude`
  is written. Mishlat writes only `~/.cache/mishlat/` (index, transcript cache) and
  `~/.config/mishlat/` (aliases, dismissed ids, settings).
- עיקרון / Principle: the window is never blank. It shows the last index at once, scans, and its
  status line always says how old the data is and what failed.
- עיקרון / Principle: every source is an undocumented app file. Each reader checks the fields it
  needs and reports a new shape as one line in `errors`, never as an empty list.

## החלטות (מול המשתמש, 2026-10-19) / Decisions (with the user, 2026-10-19)
- Python 3.12 + GTK 3 + XApp status icon + libnotify + nemo-python. No build step, no new
  dependency (all bindings are installed). Tests: `python3 -m pytest` over `unittest` tests.
- Terminal-only sessions (transcripts with no app record) are listed too.
- Hotkey Super+Shift+C toggles the window (checked free on 2026-10-19).
- Nemo gets emblems, a "Claude" column and a menu; a parent folder shows the sum of the
  projects under it.
- Six session states: working, open, waiting, review, stopped, idle. A session stays in the
  attention list for 14 days or until dismissed.
- The in-app pane mod (`~/.claude/mods/projects-dashboard`) was disabled on 2026-10-19.
- Build model: Claude Opus 5.5 (user's choice, 2026-10-19).
- Default taken while building (2026-10-19): notifications for "waiting" and "review" only; a
  "stopped" session shows in the badge and the lists but is not notified, because the user
  stopped it. The tray icons were drawn in step 07 (the tray needs them), not in step 09.

## ממצאים שנקבעו בבדיקה / Facts fixed in review (2026-10-19, verified on disk)
- Transcripts are found by file name (= `cliSessionId`), never by the record's folder: 110 of
  178 app sessions keep theirs under the folder's new name after the 2026-10-17 Desktop move.
- `~/.claude/sessions/<pid>.json` means "process alive", not "turn running". Working = alive and
  a transcript write in the last 90 s.
- No store record has an `error` field; "stopped" (interrupted with a step in progress) replaces
  "failed".
- Open a session from outside the app: `claude://code/continue?session=local_<id>` (the app's
  own jump-list route, validated `^local_[A-Za-z0-9-]{1,64}$`). A terminal-only session:
  `claude://resume?session=<cli uuid>` (the app imports it). Found in the app bundle
  v2.42304.2; the handler logs only on rejection, and a test link logged nothing.
- `claude` is not on PATH; the bundled CLI is `~/.config/Claude/claude-code/<ver>/<hash>/claude`.
- `nemo-desktop` loads `libnemo-python.so`, so desktop icons get the marks too.
- The app store is 42 MB: store records are cached by (mtime, size).

## מבחן הצלחה / Acceptance test (בדיקות שהמשתמש מריץ בעצמו, במחשב הפיתוח)
1. Terminal: `mishlat scan` ⇒ a summary with the project and session counts, the attention
   list, and `errors: none`; `shedu` is listed with its sessions.
2. Press Super+Shift+C ⇒ the "משלט" window opens: the attention column on the right
   (מחכים לך / לבדיקה / נעצרו באמצע / עובדים), project cards newest first, and a status line
   "נסרק לפני … שנ׳". Press it again ⇒ the window hides.
3. Type a word from a session title in the search box ⇒ the cards give way to results (projects,
   then sessions); clear the box ⇒ the cards return.
4. Click a session row ⇒ the Claude app comes to the front on that session.
5. The Cinnamon panel shows the Mishlat icon with a badge (the attention count); a click shows
   the menu. In another Claude session, end a turn with a question ⇒ within ~5 s a notification
   "<project> · <title>" with פתח / הסתר.
6. Nemo at `~/Desktop`, list view, View ▸ Visible Columns ▸ Claude ⇒ project folders show
   "N · ◐… ●…"; a folder with a waiting session has an emblem; right-click `shedu` ⇒
   "שיחות Claude של התיקייה (N)…" opens the window filtered to shedu.
7. Terminal: `make -C ~/Desktop/apps/mishlat check` ⇒ all tests pass and `TEST_GRAPH.md` is
   rewritten.

## נבדק על ידי Claude במחשב הפיתוח / Verified by Claude on the dev laptop (2026-10-19)
- Installed with `./install.sh`: the tray process owns `io.github.yosefco3.Mishlat` on D-Bus, the panel
  shows the icon with the "3+" badge, `custom-list` is `['mishlat']` with Super+Shift+C →
  `~/.local/bin/mishlat --toggle`.
- Check 1: `mishlat scan` → 15 projects, 168 sessions, attention 11, `errors: none`, 516 ms.
- Check 2 (command path of the hotkey): `mishlat --toggle` shows and focuses the window, a second
  one hides it; one process. Pressing the key itself is for the user.
- Check 6 (part): a Nemo window on `~/Desktop` loaded the extension and drew emblems on essays,
  audio, cookbook, shedu and trading; `nemo-desktop` loads `libnemo-python.so`.
- Check 7: `make check` → 79 passed, TEST_GRAPH.md 94% (only `__init__.py` unmapped), code graph
  41 files / 437 nodes.
- Left for the user: pressing the hotkey, clicking a session (the app jumps to it), a live
  notification, the Nemo column and menu.

## ✅ Pending (10/10 completed):
1. ✅ `01_store_live.md` — paths, app store reader (cached), live process registry.
2. ✅ `02_transcripts.md` — incremental transcript index: titles, first prompt, task list, interruptions.
3. ✅ `03_folders_resolve.md` — folder index, git info, project resolution, session state rule.
4. ✅ `04_index_scan.md` — build the index, search, attention, persistence, the scanner.
5. ✅ `05_actions_view.md` — open/resume/folder actions and the pure view model (Hebrew labels).
6. ✅ `06_window_app.md` — the GTK window, the single-instance app, `mishlat scan`.
7. ✅ `07_tray_watcher.md` — file monitors, scan thread, tray icon, notifications.
8. ✅ `08_nemo.md` — the Nemo extension: emblems, column, menu.
9. ✅ `09_install.md` — launcher, icons, desktop files, install/uninstall, hotkey.
10. ✅ `10_docs_acceptance.md` — README, overview, graphs, install on the dev laptop, acceptance run.

> כל צעד עצמאי, נוגע ב-2-4 קבצים, עם טסטים, ו-commit נפרד.
> Each step is independent, touches 2–4 files, has tests, and its own commit.
