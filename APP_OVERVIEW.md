# APP_OVERVIEW — Mishlat

> עדכון אחרון / Last updated: 2026-10-19
> מסמך חי. עדכן אותו אחרי כל שינוי שנוגע בפיצ'רים/מודלים/workflow/ארכיטקטורה.

## מה זה / What it is
Mishlat (משלט, "control post") is a read-only desktop companion for the Claude desktop app on
Linux (built on Linux Mint 22 / Cinnamon 6.6 / Nemo 6.6; GNOME / Nautilus supported, untested). It finds every project the user worked on
with Claude Code, shows each session's state and its open question or current step, and brings
the sessions that need the user to the front: in its window, in a tray badge with notifications,
and as marks on project folders in Nemo and on the desktop.

## סטאק / Stack
- Python 3.12, GTK 3 (PyGObject), XApp status icon, libnotify, nemo-python. No other dependency.
- הרצה / Run: installed `mishlat` (Super+Shift+C) · from the repo `python3 -m mishlat` · one scan
  `mishlat scan`
- טסטים / Tests: `python3 -m pytest -q` (unittest classes; fake home in `tests/helpers.py`)

## ארכיטקטורה / Architecture
One process per login session (`Gtk.Application`, id `io.github.yosefco3.Mishlat`) owns the scanner, the
tray, the notifications and the window. A second launch hands its arguments over D-Bus and exits.
The Nemo extension runs inside Nemo and only reads the index file.

```
sources (read-only)                 mishlat process                       readers
───────────────────                 ───────────────                       ───────
app store  local_*.json ──┐   SourceMonitor (Gio) → Coalescer (2 s) ┐
transcripts *.jsonl ──────┼──▶  ScanRunner (worker thread) ─ Scanner.scan()
claude agents --json ─────┤        store · agents (else live registry + /proc) · transcripts · folders · git
live registry + /proc ────┤        model.build_index ─▶ ~/.cache/mishlat/index.json ──▶ Nemo extension
~/Desktop folders ────────┘
                                   on the GTK loop:  Tray (badge, menu) · Notifier · MishlatWindow
```

| Module | Responsibility |
|---|---|
| `paths.py` | every path, relative to a `home` argument; `version_key` |
| `store.py` | the app's session records → `Record`; (mtime, size) cache (the store is 42 MB) |
| `agents.py` | `claude agents --json` (the bundled CLI, found by `actions.claude_cli`) → `LiveEntry` per cli session id: pid, status busy/waiting/idle, `waitingFor`; a 5 s timeout; every failure is an `AgentsError`; `MISHLAT_AGENTS_CMD` / `MISHLAT_AGENTS_DISABLE` |
| `live.py` | the fallback: `~/.claude/sessions/<pid>.json` + `/proc/<pid>/stat` start time → live processes |
| `transcripts.py` | transcripts by session id, read incrementally: titles, first prompt, task list, interruption |
| `folders.py`, `gitinfo.py` | folders under the roots (encoding, name and identity lookups), a folder's identity (inode, git remote, entry names), the deep search for moved folders; branch, dirty state, remote URL |
| `model.py` | project resolution (moved folders), the six states, `build_index`, search, attention, `entered` |
| `index.py` | atomic private JSON files: index, cache, aliases, dismissed, settings |
| `scan.py` | `Scanner`: one guarded scan; each failing source becomes one line in `errors` |
| `actions.py` | open in the app (`claude://code/continue`, `claude://resume`), terminal resume, folder, new session |
| `view.py` | Hebrew labels, glyphs, ages, sublines, sections, filters (pure) |
| `window.py` | the GTK window: attention column, project cards, search, stale list, folder focus, menus |
| `watcher.py` | `Coalescer`, `ScanRunner`, `SourceMonitor` |
| `tray.py` | `Tray` (XApp.StatusIcon, else AyatanaAppIndicator3), `Notifier` (libnotify), pure menu/notification rules |
| `strings.py` | `t()`: Hebrew source text → English table; the language from `settings.lang`, the locale, or `MISHLAT_LANG` |
| `describe.py` | a folder's purpose from its README (first heading + paragraph, cached by mtime); `write_readme` once |
| `app.py`, `cli.py` | the single-instance app; `mishlat scan / --toggle / --project / --tray / --quit` |
| `extension/mishlat_fm.py` | Nemo and Nautilus: emblems, the "Claude" column, parent sums, two menu items (self-contained) |

## מודלים / Data models
`~/.cache/mishlat/index.json` (version 1): `scanned_at`, `scan_ms`, `app_version`, `live_source`
(`agents` when the CLI's listing was read, `registry` otherwise), `roots`, `projects[]`,
`attention[]` (session ids in order), `totals`, `errors[]`.
- Project: `key` (folder path now, or `general` for "כללי"), `name` (path below the root, or
  `כללי`), `path`, `moved_from[]` (for "כללי": the folders that no longer exist), `ambiguous`,
  `is_repo`, `branch`, `dirty`, `general`, counts
  (`working`, `open`, and the attention-only `waiting`, `review`, `stopped`, `attention`),
  `last_activity`, `sessions[]` (newest first).
- Session: `id` (`local_…`, or the cli id for a terminal-only session), `cli_id`, `source`
  (`app`/`cli`), `title`, `cwd`, `project`, `state`, `question`, `detail`, `step`, `steps_done`,
  `steps_total`, `first_prompt`, `transcript`, `last_activity`, `starred`, `dismissed`, `attention`,
  `waiting_for` (what the CLI says a waiting session waits for, else null), `pid`,
  `started_in` (the start project when the work moved it), `assigned` (moved by hand),
  `turns`, `writes`, `cleanup` (the reason key or null). Index: `cleanup[]` ids newest first,
  `totals.cleanup`, `totals.cleanup_by`.

## Workflow / Lifecycle
- Live source: `claude agents --json` first (a session is live iff listed; its `status` says
  whether a turn runs). When the command is missing or fails: one error line, and the registry +
  `/proc` as before 0.1.2. `index["live_source"]` records which; `mishlat scan` prints it.
- Session state: working (listed `busy`; in the fallback: alive and a transcript write in the
  last 90 s) > stopped (interrupted with a task step in progress) > waiting (listed `waiting`,
  with `waitingFor` as the question when the store has none; or the app's post-turn summary for
  the last turn is `blocked`) > review (`review_ready`) > open (alive: listed `idle`, or a live
  process in the fallback) > idle.
- Project of a session: scratch folding; the folder exists (unless the transcript folder says the
  history moved: a reused name); the folder found again by its remembered identity
  (`~/.cache/mishlat/folders.json`: inode + git remote + entry names, recorded at every scan; an
  inode match needs agreeing remotes and a shared entry name, so a recycled inode does not fool
  it; a deep search covers a folder moved into a repository); `aliases.json`; the transcript
  folder's encoding; a unique folder with the same name; a move learned from sibling sessions;
  else "כללי" (a folder that no longer exists, or an app scratch folder). "כללי" is always the
  last card.
- Then the work decides: score = 3 × writes + reads per project (paths in the tool calls, recorded
  incrementally by `transcripts.work_of`; a write with no path counts for the start folder). The top
  project wins with ≥ 15 and more than twice the start folder's score; `started_in` keeps the start.
  `~/.config/mishlat/assignments.json` (the window's "שייך לפרויקט…") wins over both.
- Attention: waiting / review / stopped, active in the last 14 days, not dismissed. Notifications
  for new waiting / review entries only, never on the first scan after start.
- Refresh: file monitors (coalesced to one scan per 2 s), a 30 s timer for the time-based states,
  the Nemo extension re-reads the index every 5 s when its mtime changed.
- Cleanup list (`model.mark_cleanup`, every scan): reason in priority order gone > no_transcript >
  duplicate > empty > old (30 days, `settings.old_days`, set in the ⚙ dialog); exempt: starred, active states, assigned,
  kept (`keep.json`), the newest session of each folder. "מחק" writes `delete-requests.json`; a
  Claude session runs `mishlat cleanup --json` and deletes through the app; the scan prunes
  requests of sessions that are gone.

## היסטוריית שינויים משמעותיים / Significant change history
| תאריך / Date | שינוי / Change | קבצים עיקריים / Key files |
|---|---|---|
| 2026-10-19 | Initial overview, dev-kit bootstrap, spec mishlat-v1 | `features-prompts/mishlat-v1/` |
| 2026-10-19 | v1: scanner, index, window, tray, notifications, Nemo marks, installer | `mishlat/`, `nemo/`, `install.sh` |
| 2026-10-19 | Sessions of folders that no longer exist, and scratch sessions, go under "כללי" | `mishlat/model.py`, `mishlat/view.py` |
| 2026-10-19 | A session belongs to the project it worked in; "שייך לפרויקט…" by hand | `mishlat/transcripts.py`, `mishlat/model.py`, `mishlat/window.py` |
| 2026-10-19 | Review fixes: session time from transcript line timestamps (not file mtime); old folder paths count for their project | `mishlat/transcripts.py`, `mishlat/model.py` |
| 2026-10-19 | Cleanup list: rules at every scan, keep / delete-request files, "למחיקה" view, `mishlat cleanup` | `mishlat/model.py`, `mishlat/window.py`, `mishlat/cli.py` |
| 2026-10-19 | UI polish: session rows are links (hand cursor, underline, "פתח ↗"), base font 15 px with Ctrl+=/−/0 saved as `settings.font_px`, card edge colored by state | `mishlat/window.py`, `mishlat/index.py` |
| 2026-10-19 | Folder purpose line on cards: README first heading + paragraph, or the user's text (`descriptions.json`); "תאר את התיקייה…" can write a README once | `mishlat/describe.py`, `mishlat/window.py` |
| 2026-10-19 | Open source: English UI with a Hebrew switch (`strings.py`, Ctrl+L), Nemo + Nautilus extension, AppIndicator fallback, GNOME hotkey, demo home + screenshots, scrubbed specs, MIT | `mishlat/strings.py`, `extension/`, `install.sh`, `scripts/` |
| 2026-10-19 | 0.1.1: folder identity memory; a renamed or moved folder (also into a repository) keeps its sessions; a deleted one stays "gone" | `mishlat/folders.py`, `mishlat/gitinfo.py`, `mishlat/scan.py`, `mishlat/model.py` |
| 2026-10-21 | 0.1.4: a "+ New task" button on every folder card (`actions.new_session_in`, the `claude-desktop --os-entry=folder_verb` route); the menu item says the same | `mishlat/window.py`, `mishlat/strings.py` |
| 2026-10-19 | 0.1.3: settings dialog (⚙, Ctrl+,) for notifications and the old-days threshold; `settings.notify` = others (default: never about the session the user looks at, by `lastFocusedAt`) / all / off | `mishlat/window.py`, `mishlat/tray.py`, `mishlat/model.py`, `mishlat/store.py`, `mishlat/index.py` |
| 2026-10-19 | 0.1.2: `claude agents --json` is the primary live source (busy / waiting / idle → working / waiting / open, `waitingFor` shown); the registry + `/proc` reader is the fallback; `index.live_source`; the demo home fakes the listing | `mishlat/agents.py`, `mishlat/scan.py`, `mishlat/model.py`, `mishlat/view.py`, `scripts/demo_home.py` |
