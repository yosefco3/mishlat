# 03 — Docs, version 0.1.3, install

## מטרה / Goal
Document the dialog and the `notify` key, bump the version, sync the plugin copy, refresh the
graphs, install locally.

## קבצים לשינוי / Files to change
- `README.md` — "What it does" bullet, the Use table row, the `settings.json` example.
- `APP_OVERVIEW.md` — settings in the files section; a change-history row.
- `mishlat/__init__.py`, `plugin/.claude-plugin/plugin.json` — 0.1.3; `make plugin-sync`.

## שינוי נדרש / Required change
README: `{"roots": [...], "old_days": 30, "font_px": 15, "lang": "en", "notify": "others"}` and a
sentence on the three values; Use table: `| Settings (notifications, old days) | ⚙ or Ctrl+, |`.
APP_OVERVIEW: the same, plus the history row. Then `make check`, `MISHLAT_NO_RESTART=1 ./install.sh`,
restart the tray.

## טסטים נדרשים / Tests required
- `make check` green; `mishlat scan` still reports `live source: agents`.

## קריטריון הצלחה / Success criteria
- The installed copy shows the ⚙ button; the docs describe the setting.

## קומיט / Commit
`chore(release): 0.1.3 — settings dialog`
