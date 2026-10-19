# 09 — Launcher, icons, desktop files, install and uninstall

## מטרה / Goal
One command installs everything at user scope (no sudo) and one removes it.

## קבצים לשינוי / Files to change
- `bin/mishlat` (new) — the launcher.
- `data/` (new) — `mishlat.desktop.in`, `mishlat-autostart.desktop.in` (the icons came in step 07).
- `install.sh`, `uninstall.sh` (new); `Makefile` targets.
- `tests/test_install.py`

## מצב נוכחי / Current state
`~/.local/bin` is on PATH. No custom keybinding exists. No Nemo window was open on 2026-10-19.

## שינוי נדרש / Required change
- install: package → `~/.local/share/mishlat/lib/mishlat` (rsync --delete), launcher →
  `~/.local/bin/mishlat`, icons → `~/.local/share/mishlat/icons`, menu entry →
  `~/.local/share/applications/mishlat.desktop`, autostart → `~/.config/autostart/mishlat.desktop`
  (`--tray`), Nemo extension → `~/.local/share/nemo-python/extensions/`, hotkey via gsettings
  (append `mishlat` to `custom-list`, never replace it). Then `nemo -q`, restart `nemo-desktop`,
  restart the tray. `MISHLAT_NO_RESTART=1` and `MISHLAT_NO_KEYBINDING=1` skip those parts.
- uninstall: the reverse, and `custom-list` loses only `mishlat`. The cache and config stay
  unless `--purge`.

Found while building (2026-10-19): `gsettings` writes through the user's dconf service even under
a temporary HOME, so the uninstaller also honors `MISHLAT_NO_KEYBINDING=1`; without it every test run
would remove the real hotkey.

## טסטים נדרשים / Tests required
- install into a temp HOME with both skips: every file in place, the launcher runs
  `mishlat scan` on that temp HOME; uninstall removes them.

## קריטריון הצלחה / Success criteria
- `./install.sh` on the dev laptop: the tray icon appears, Super+Shift+C opens the window.

## קומיט / Commit
`feat(install): user-scope installer, launcher, icons and hotkey`
