# Progress — agents-json

`claude agents --json` becomes the primary source of live-session state. Until now Mishlat knew
only whether a Claude Code *process* is alive (the registry `~/.claude/sessions/<pid>.json`
checked against `/proc`) and guessed "working" from a transcript write in the last 90 s. The
bundled CLI has a documented command that lists every live session with its `status`
(`busy` / `waiting` / `idle`) and what it waits for. Mishlat reads that first and keeps the
registry + `/proc` reader as the fallback, so nothing gets worse when the command is missing.

## מטרת-על / High-level goal
- מתי / When: every scan. The command costs ~0.15 s, starts no supervisor and writes nothing
  under `~/.claude` (checked on CLI 2.1.299, 2026-10-19).
- עיקרון / Principle: the CLI's listing is the one supported surface for live state
  (https://code.claude.com/docs/en/agent-view#list-sessions-as-json). When it succeeded, a
  session is live iff its id is listed; `busy` → working, `idle` → open, `waiting` → waiting
  (the `waitingFor` text is the row's question when the store has none). Review / stopped and
  the store's blocked / review_ready keep their rules and still win over open.
- Fallback: any failure (no CLI, non-zero exit, timeout, bad JSON) is one line in
  `index["errors"]` and the scan behaves exactly as before (registry + `/proc` + the 90 s
  heuristic). `index["live_source"]` says which source was used; `mishlat scan` prints it.
- Overrides: `MISHLAT_AGENTS_CMD` runs another command instead of the bundled CLI (tests, the
  demo home); `MISHLAT_AGENTS_DISABLE=1` forces the fallback.
- Rules kept: standard library only; nothing written into the app's files; every reader takes
  what it parses as an argument so tests run on a fake home.

## החלטות (מול המשתמש, 2026-10-19) / Decisions (with the user, 2026-10-19)
- Primary source = the CLI listing, fallback = the registry. Not the other way round: the
  listing is documented, the registry is not, and only the listing knows whether a turn runs.
- A session listed as `idle` is *open* even if its transcript was written seconds ago: the CLI
  knows better than the heuristic (a turn that ended with a prose question reads idle, and the
  store's post-turn summary then says waiting / review).
- A background session listed without a process (its process exited, state `working` /
  `blocked`) maps to `busy` / `waiting`; an unknown `status` value maps to none, so the old
  heuristic decides for that session and nothing breaks on a new CLI.
- `waitingFor` values are shown through the window's string table (five documented values:
  permission prompt, input needed, sandbox request, worker request, dialog open); the index
  keeps the CLI's raw text.
- The error line on failure is deliberate (the user sees why the fallback is in use); the
  deliberate `MISHLAT_AGENTS_DISABLE=1` adds no line.
- Version 0.1.2; no tag or GitHub release without the user's word.

## מבחן הצלחה / Acceptance test (בדיקות שהמשתמש מריץ בעצמו)
1. `~/.config/Claude/claude-code/*/*/claude agents --json` (the newest version) and
   `mishlat scan` ⇒ the summary's first line ends with `live source: agents`; every session the
   CLI lists `busy` shows `●` working in its project line, every `idle` one `○` open; sessions
   not listed are not working/open.
2. `MISHLAT_AGENTS_DISABLE=1 mishlat scan` ⇒ `live source: registry`, no error line, the same
   sessions still alive (working / open by the 90 s heuristic).
3. `MISHLAT_AGENTS_CMD=/nonexistent mishlat scan` ⇒ `live source: registry` and one error line
   `agents: AgentsError: …`; the scan still completes.
4. `H=$(python3 scripts/demo_home.py); MISHLAT_HOME=$H MISHLAT_AGENTS_CMD="cat $H/_agents.json"
   python3 -m mishlat scan` ⇒ `live source: agents`, shop-site shows `●1`, shop-api `○1` and
   the "Needs you" list has a row ending with `— permission prompt`.
5. `python3 -m pytest -q` ⇒ green; `python3 scripts/screenshot.py` ⇒ six PNGs rewritten.

## ⏳ Pending (1/5 completed):
1. ✅ `01_parse.md` — `mishlat/agents.py`: `LiveEntry`, `parse_agents_json`, `read_agents` with a hard timeout, the env overrides; fixture + tests.
2. `02_model.md` — `state_of` takes the CLI status; `waitingFor` as the row's question; `Live` carries status; tests.
3. `03_scan.md` — the scan reads the listing first and falls back to the registry; `index["live_source"]`; the summary prints it; end-to-end tests.
4. `04_demo.md` — the demo home fakes the listing (`_agents.json`), screenshots use it, the window translates `waitingFor`.
5. `05_release.md` — README, APP_OVERVIEW, plugin docs, version 0.1.2, plugin sync, graphs, local install and a check against the real CLI.

> כל צעד עצמאי, נוגע ב-2-4 קבצים, עם טסטים, ו-commit נפרד.
> Each step is independent, touches 2–4 files, has tests, and its own commit.
