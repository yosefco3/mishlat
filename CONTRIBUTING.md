# Contributing

Thanks for looking. Mishlat is small on purpose: Python 3.10+, GTK 3, no dependencies beyond the
GObject bindings a Linux desktop already has. Please keep it that way.

## Run it from the checkout

```bash
python3 -m pytest -q                 # 100+ tests, no display needed (the window smoke test skips)
python3 -m mishlat scan              # one scan of your own sessions, English summary
MISHLAT_HOME=$(python3 scripts/demo_home.py) python3 -m mishlat   # the window on made-up data
```

## How the code is organized

See `APP_OVERVIEW.md` for the module map and the rules (session states, project resolution,
the cleanup list). Every rule is a pure function over plain data, so it has a unit test with a
fake home (`tests/helpers.py`). Everything that touches the disk takes `home` as an argument.

## The way of working

This repository uses the dev-kit method: a feature is a folder under `features-prompts/` with a
`_PROGRESS.md` (goal, decisions with their dates, a user-runnable acceptance test, a checklist) and
one numbered step file per commit. Small steps, tests with each step, one commit per step,
`make check` at the end (tests + `TEST_GRAPH.md`). You do not have to follow it for a one-line
fix, but a feature without a `_PROGRESS.md` will be asked for one.

## Things that need care

- **Read-only toward Claude.** Nothing under `~/.config/Claude` or `~/.claude` is ever written.
  Mishlat writes only `~/.cache/mishlat` and `~/.config/mishlat` (and a `README.md` into a project
  folder, once, when the user asks for it from the card's menu).
- **The sources are undocumented app files.** A reader must check the fields it needs and report
  a new shape as a line in `index["errors"]`, never fail the scan.
- **No windows on the user's screen in tests.** Render offscreen (`scripts/screenshot.py` shows how).
- **Hebrew and English.** Every string that reaches the screen goes through `strings.t()`; add the
  English form to the table in `mishlat/strings.py`, with the same `{placeholders}`.

## Reporting a problem

`mishlat scan` prints the errors the scanner saw. Attach that output (it holds your session titles;
trim what you do not want to share) and your desktop (`echo $XDG_CURRENT_DESKTOP`).
