# 01 — The `notify` setting and the focused-session skip

## מטרה / Goal
Add `notify` (`others` | `all` | `off`, default `others`) to settings.json and make the notifier
honour it: `off` sends nothing, `others` skips the session the user last looked at. No UI yet.

## קבצים לשינוי / Files to change
- `mishlat/index.py` — `load_settings` validates `notify`.
- `mishlat/store.py` — `Record.last_focused` from `lastFocusedAt`.
- `mishlat/model.py` — the row carries `last_focused`; `focused_session(index)`.
- `mishlat/tray.py` — `to_notify(previous, index, mode)`; `mishlat/app.py` passes the saved mode.
- tests: `tests/test_index_io.py`, `tests/test_store.py`, `tests/test_tray.py`.

## מצב נוכחי / Current state
`load_settings` (index.py 178-196) returns roots / old_days / font_px / lang. `parse_record`
(store.py 43-69) ignores `lastFocusedAt`. `to_notify` (tray.py 75-81) returns every new attention
entry in `NOTIFY_STATES`; `app._on_scan` (app.py 125) calls it with no mode.

## שינוי נדרש / Required change
1. `index.py`: `NOTIFY_MODES = ("others", "all", "off")`; `notify = obj.get("notify") if in NOTIFY_MODES else "others"`; returned in the dict.
2. `store.py`: `last_focused: int = 0` on `Record`, `_ms(obj.get("lastFocusedAt"))` in `parse_record`.
3. `model.py`: `row["last_focused"]`; `focused_session(index) -> str | None` = the id with the greatest positive `last_focused` over `all_sessions`.
4. `tray.py`: `to_notify(previous, index, mode="others")`: `off` → `[]`; `others` → drop `focused_session(index)`.
5. `app.py`: `mode = io.load_settings(self.home)["notify"]` in `_on_scan`.

## טסטים נדרשים / Tests required
- `load_settings`: missing / bad value → `others`; `"off"` kept.
- `parse_record`: `lastFocusedAt` → `last_focused`; absent → 0.
- `to_notify`: `off` → nothing; `others` skips the focused session but keeps another; `all` keeps both.

## קריטריון הצלחה / Success criteria
- The saved mode decides what the tray notifies; the default no longer notifies about the focused session.
- All existing tests still pass.

## קומיט / Commit
`feat(notify): a notify setting; never notify about the session the user is looking at`
