# 01 — Fold lost and scratch sessions into "כללי"

## מטרה / Goal
Every session whose project has no folder (`ref.path is None`: lost or scratch) belongs to one
project with key `general` and name `כללי`, sorted last.

## קבצים לשינוי / Files to change
- `mishlat/model.py` — `GENERAL`, the fold after the learned-alias pass, the sort, `totals["lost"]`.
- `mishlat/view.py` — `project_note` for the general card.
- `mishlat/window.py`, `mishlat/cli.py` — the path line and the summary line for it; the original
  folder in a session's tooltip.
- Tests: `tests/test_model_index.py`, `tests/test_view.py`, `tests/test_scan.py`.

## מצב נוכחי / Current state
`build_index` (model.py, the `for i, ref in enumerate(refs)` loop after `learned_aliases`) keeps a
lost folder as its own project keyed by the old path, and scratch as `scratch`.
`view.project_note` says "התיקייה לא נמצאה" or "תיקיות עבודה זמניות של האפליקציה".

## שינוי נדרש / Required change
- After the learned pass: `if ref.path is None: refs[i] = ProjectRef(GENERAL, None, ref.moved_from)`
  (scratch has no `moved_from`). The project dict gets `"general": True`, name `כללי`.
- Sort: `(p["key"] == GENERAL, -p["last_activity"], p["name"])`.
- `totals["lost"]` = the number of distinct old folders in "כללי".
- Note: "שיחות מתיקיות שכבר לא קיימות: <folders>" and "N שיחות זמניות של האפליקציה".

## טסטים נדרשים / Tests required
- A lost folder and a scratch session land in "כללי", which is last; its `moved_from` lists the
  lost folder; `totals["lost"] == 1`; a learned move still goes to the real project.
- The note text; the summary line.

## קריטריון הצלחה / Success criteria
- `mishlat scan` on the dev laptop shows one "כללי" line and no "(folder not found)".

## קומיט / Commit
`feat(model): put sessions of folders that no longer exist under "כללי"`
