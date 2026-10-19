# 05 — Actions and the view model

## מטרה / Goal
The commands that leave Mishlat (open a session in the app, resume it in a terminal, open a folder,
start a new session) and every label the UI shows, as pure functions that tests can check
without a display.

## קבצים לשינוי / Files to change
- `mishlat/actions.py` (new)
- `mishlat/view.py` (new)
- `tests/test_actions.py`, `tests/test_view.py`

## מצב נוכחי / Current state
The index from step 04. Link routes verified in the app bundle (see `_PROGRESS.md`).

## שינוי נדרש / Required change
- `session_url(s)`: `claude://code/continue?session=<local id>` for app sessions,
  `claude://resume?session=<cli id>` for terminal-only ones. `open_session` runs `xdg-open`.
- `claude_cli(home, which)`: `claude` on PATH, else the newest bundled CLI by version number.
- `terminal_command(cwd, cli, cli_id)`: `gnome-terminal --working-directory=<cwd> -- <cli> --resume <id>`.
- `open_folder(path)`: `xdg-open`; `new_session_in(path)`: `claude-desktop --os-entry=folder_verb <path>`
  (the call the app's own file-manager script makes).
- view: glyphs and colors per state, Hebrew state labels and section titles, `format_age`,
  `subline(session)`, `count_label`, project badges, `filter_projects(mode)`, `sections(index)`.

## טסטים נדרשים / Tests required
- URLs for both kinds; the newest bundled CLI wins; the terminal command shape; the runner is
  called with the expected argv (injected).
- Ages (now, minutes, hours, "אתמול", weeks, months); sublines per state; filters; sections order.

## קריטריון הצלחה / Success criteria
- Tests pass with no display.

## קומיט / Commit
`feat(view): session actions and the Hebrew view model`
