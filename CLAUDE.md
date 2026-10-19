# Mishlat — project instructions

Mishlat (משלט) is a read-only desktop companion for the Claude desktop app on Linux (Cinnamon or
GNOME; Nemo or Nautilus): one window with every project and its Claude Code sessions, a tray badge
with notifications, marks on project folders, and a cleanup list. Python 3 + GTK 3. A `plugin/`
folder carries the scanner and slash commands into Claude Code itself.

## Rules of this codebase
- Read-only towards Claude: never write under `~/.config/Claude` or `~/.claude`. Mishlat writes
  only `~/.cache/mishlat/` and `~/.config/mishlat/`.
- Readers parse what they are given (dict, bytes, path) so tests run on a fake home; every function
  that touches the disk takes `home` as an argument.
- Every source is an undocumented app file: check the fields you need, report a new shape as one
  line in `index["errors"]`, never fail the whole scan.
- No new dependency: standard library + the GObject bindings already installed (Gtk 3, XApp,
  Notify, Nemo 3.0). Tests: `unittest` classes run by pytest.
- UI text goes through `strings.t()` (Hebrew source, English table); code, file names, commits
  and terminal output are English.

## Way of working (dev-kit)

This project follows the **dev-kit** method. Pillars:
- **Prompt library** — features are specced under `features-prompts/<feature>/`
  (`_PROGRESS.md` + numbered step files). See `~/.claude/skills/dev-kit`.
- **App overview** — `APP_OVERVIEW.md` is a living doc; keep it current.
- **Test graph** — `python3 scripts/test_graph.py` regenerates `TEST_GRAPH.md`.
- **Code graph** — `code-review-graph update` refreshes `.code-review-graph/`.

### Stack commands
- Run from the repo: `python3 -m mishlat` (window) · `python3 -m mishlat scan` (one scan, summary)
- Tests: `python3 -m pytest -q`
- Everything (tests + graphs): `make check`
- Install / uninstall (user scope, no sudo): `./install.sh` · `./uninstall.sh`

### Per-feature workflow
1. Spec the feature under `features-prompts/<slug>/` (small steps, 2–4 files each).
2. Execute one step at a time → run tests → one commit per step → tick `_PROGRESS.md`.
3. After each coding mission (source changed): `code-review-graph update`,
   `python3 scripts/test_graph.py`, and update `APP_OVERVIEW.md` if features/models/
   workflow/architecture changed.
