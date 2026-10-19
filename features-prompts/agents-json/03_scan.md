# 03 — The scan reads the listing first

## מטרה / Goal
`Scanner.scan` runs the listing; on success it is the live source, else the registry. The index
records which, and `mishlat scan` prints it.

## קבצים לשינוי / Files to change
- `mishlat/scan.py` — `Scanner(env=...)`, `read_agents`, the fallback, `index["live_source"]`
- `mishlat/cli.py` — the summary's first line ends with `live source: agents|registry`
- `tests/test_scan.py`, `tests/helpers.py` (`FakeHome.add_agents(entries) -> command`)
- `tests/test_plugin.py`, `tests/test_install.py` — the subprocess runs get `MISHLAT_AGENTS_DISABLE=1`

## מצב נוכחי / Current state
`scan.py` line 123: `live = guarded("live", lambda: read_live(self.home, self.proc_root), {})`.
`Scanner.__init__` reads `MISHLAT_PROC_ROOT` from `os.environ`.

## שינוי נדרש / Required change
### 1. `mishlat/scan.py`
- `__init__(..., env=None)`: `self.env = os.environ if env is None else env`; `MISHLAT_PROC_ROOT`
  comes from it.
- `read_agents(self)`: `argv = agents_command(self.home, self.env)`; None (disabled) → None;
  else `agents.read_agents(argv)`.
- In `scan`: `live = guarded("agents", self.read_agents, None)`; `source = "agents" if live is
  not None else "registry"`; when None, `live = guarded("live", read_live…, {})` as today.
  `index["live_source"] = source`.
### 2. `mishlat/cli.py`
First summary line: `… · Claude Code {ver} · live source: {index.get("live_source") or "?"}`.
`scan.main()` prints it too.

## טסטים נדרשים / Tests required
- End to end on the fake home with a fake listing (`cat …/_agents.json`): a record whose cli id is
  listed busy → working; listed idle with a fresh transcript → open; a registry+/proc session not
  listed → idle; `live_source == "agents"`; `errors == []`.
- Listing disabled → `live_source == "registry"`, the registry session working, no error.
- Listing fails (`/nonexistent`) → one `agents: AgentsError` line, `live_source == "registry"`,
  the registry session still working.
- `mishlat scan` prints `live source:`.

## קריטריון הצלחה / Success criteria
- All tests green; `MISHLAT_AGENTS_DISABLE=1 python3 -m mishlat scan` on the dev machine shows
  `live source: registry`; without it `live source: agents`.

## קומיט / Commit
`feat(scan): claude agents --json first, the registry as the fallback`
