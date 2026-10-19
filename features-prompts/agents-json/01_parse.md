# 01 — Parse `claude agents --json`

## מטרה / Goal
A pure parser over the CLI's text and a thin runner with a hard timeout. Nothing in the scan
changes yet.

## קבצים לשינוי / Files to change
- `mishlat/agents.py` (new)
- `tests/fixtures/agents.json` (new; shaped like the real output of CLI 2.1.299)
- `tests/test_agents.py` (new)

## מצב נוכחי / Current state
`mishlat/live.py` reads the registry and `/proc`; `mishlat/actions.py: claude_cli(home, which)`
finds `claude` on PATH or the newest bundled CLI. The real listing (2.1.299) is a JSON array of
objects: always `cwd`, `kind`, `startedAt`; `pid` + `status` (`busy`|`waiting`|`idle`) while the
process is alive; `waitingFor` when waiting; `sessionId` + `name` when set; `id` + `state`
(`working`|`blocked`|`done`|`failed`|`stopped`) for background sessions.

## שינוי נדרש / Required change
### 1. `mishlat/agents.py`
- `LiveEntry(pid, cwd, name, status, waiting_for, kind, started_at)` (frozen dataclass).
- `AgentsError(RuntimeError)`.
- `parse_agents_json(text) -> dict[cli_id, LiveEntry]`: bad JSON or a non-array raises
  `AgentsError`; entries that are not objects or have no `sessionId` are skipped; `pid` only when
  an int; `status` only when one of busy/waiting/idle, else derived from a background `state`
  (working → busy, blocked → waiting), else None; `waitingFor` only with status waiting; when one
  id appears twice the newer `startedAt` wins.
- `agents_command(home, env=os.environ, which=shutil.which) -> list[str] | None`: None when
  `MISHLAT_AGENTS_DISABLE=1`; `shlex.split(MISHLAT_AGENTS_CMD)` when set; else
  `[claude_cli(home), "agents", "--json"]`, raising `AgentsError` when no CLI is found.
- `read_agents(cli, timeout=5, run=subprocess.run)`: `cli` is a path (→ `agents --json`) or an
  argv list; stdin closed, output captured, `timeout` enforced; a missing program, a timeout, an
  OS error, a non-zero exit (with the last stderr line) all raise `AgentsError`.

## טסטים נדרשים / Tests required
- The fixture parses into three entries: two interactive (busy / idle with pid), one background
  (no pid, state working → busy); an entry without `sessionId` is skipped.
- Waiting: `waitingFor` kept; a `waitingFor` on a busy entry is dropped.
- Malformed text, a JSON object instead of an array → `AgentsError`; `[]` → `{}`.
- Missing fields: no `cwd`/`kind`/`startedAt`/`name` still yields an entry with defaults.
- `read_agents`: the real-shaped fixture through `cat`; a sleeping command with `timeout=0.2`
  → `AgentsError` mentioning the timeout; exit 3 → `AgentsError` with the stderr line;
  `/nonexistent` → `AgentsError`; `echo nope` → `AgentsError` (bad JSON).
- `agents_command`: disabled → None; the override is split; the bundled CLI is used; no CLI →
  `AgentsError`.

## קריטריון הצלחה / Success criteria
- `python3 -m pytest -q tests/test_agents.py` green; nothing else changes.

## קומיט / Commit
`feat(agents): parse claude agents --json into live entries`
