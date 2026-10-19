# 08 — The Nemo extension

## מטרה / Goal
Marks in the file manager and on the desktop: an emblem on a project folder with attention or
work, a "Claude" column, and two menu items. The extension is one self-contained file that only
reads `~/.cache/mishlat/index.json`.

## קבצים לשינוי / Files to change
- `nemo/mishlat_nemo.py` (new)
- `tests/test_nemo.py`

## מצב נוכחי / Current state
`nemo-desktop` loads `libnemo-python.so` (checked 2026-10-19). Emblems that resolve in the
Mint-Y-Navy theme: `emblem-important`, `emblem-synchronizing`.

## שינוי נדרש / Required change
- `build_marks(index)`: one mark per project folder; each parent folder below a root sums the
  projects under it. Label `⁦8 · ◐1 ●1⁩` (left-to-right isolate so digits do not flip), and for a
  parent `… · 3 פרויקטים`.
- `IndexCache` re-reads only when the index mtime changes. `update_file_info` is one dict lookup.
- Every 5 s: if the index changed, `invalidate_extension_info()` on the files whose mark changed.
- Menu on a folder (and on the background of an open folder): "שיחות Claude של התיקייה (N)…"
  runs `~/.local/bin/mishlat --project <path>`; "סשן Claude חדש כאן" runs
  `claude-desktop --os-entry=folder_verb <path>`.

## טסטים נדרשים / Tests required
- build_marks: a project, a parent sum, a root itself is not marked, a missing folder is skipped;
  labels; the cache reloads only on change.

## הערה / Note (2026-10-19)
Creating a `Nemo.Column` in a plain Python process (outside Nemo) aborts at interpreter exit
("double free"); import and construction are fine. Inside Nemo the column is Nemo's, and a real
Nemo window loaded the extension, drew the emblems and did not crash. So tests load the module
with `MISHLAT_NEMO_NO_GI=1` and test the pure parts only.

## קריטריון הצלחה / Success criteria
- After install, `~/Desktop/shedu` shows the column value and an emblem when a session waits.

## קומיט / Commit
`feat(nemo): emblems, Claude column and folder menu in Nemo`
