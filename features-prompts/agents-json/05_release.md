# 05 — Release 0.1.2

## קבצים לשינוי / Files to change
- `README.md` ("How it decides", "What it reads, what it writes", "Limits, honestly")
- `APP_OVERVIEW.md` (architecture diagram and table, lifecycle, a change-history row)
- `plugin/README.md`, `plugin/skills/projects/SKILL.md` (the listing is read too)
- version 0.1.2: `mishlat/__init__.py`, `plugin/.claude-plugin/plugin.json`, `tests/test_scan.py`
- `tests/test_plugin.py` (`agents` in the bundled set), `make plugin-sync`, `make check`

## קריטריון הצלחה / Success criteria
- `MISHLAT_NO_RESTART=1 ./install.sh`, then `mishlat scan` against `claude agents --json` run by
  hand: the same sessions, the same busy/idle → working/open.
- Pushed to origin main. No tag, no release (the user decides).

## קומיט / Commit
`chore(release): 0.1.2 — live state from claude agents --json`
