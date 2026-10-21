# 01 — The New task button

## מטרה / Goal
A flat "+ משימה חדשה" button at the end of every folder card's badge row; it calls
`actions.new_session_in(path)`. The right-click item gets the same wording.

## קבצים לשינוי / Files to change
- `mishlat/window.py` — `_card` adds the button; `_project_menu` renames the item; `self.new_task_buttons` for tests.
- `mishlat/strings.py` — English for "משימה חדשה" and "משימה חדשה כאן".
- `tests/test_window_smoke.py` — cards with a path get a button, General does not; clicking calls the action.

## מצב נוכחי / Current state
`_card` (window.py) builds `badges = Gtk.Box(spacing=4)` and packs the state badges. `_project_menu`
has `t("סשן Claude חדש כאן")` → `actions.new_session_in(p["path"])`. `actions.new_session_in`
runs `claude-desktop --os-entry=folder_verb <path>`.

## שינוי נדרש / Required change
1. `window.py`: in `_card`, when `p["path"]`:
   `btn = Gtk.Button(label=t("+ משימה חדשה")); btn.set_relief(Gtk.ReliefStyle.NONE);`
   tooltip `t("פותח שיחת Claude חדשה בתיקייה הזו")`; `btn.connect("clicked", lambda *_: actions.new_session_in(p["path"]))`;
   `badges.pack_end(btn, False, False, 0)`; `self.new_task_buttons[p["key"]] = btn` (reset in `render`).
2. `_project_menu`: `t("משימה חדשה כאן")`.
3. `strings.py`: `"+ משימה חדשה": "+ New task"`, `"משימה חדשה כאן": "New task here"`, the tooltip.

## טסטים נדרשים / Tests required
- After `set_index(sample_index())`: `set(new_task_buttons) == {shedu, book}`; a General card has none.
- Monkeypatch `window.actions.new_session_in`; `btn.clicked()` ⇒ called with the card's path.

## קריטריון הצלחה / Success criteria
- The button shows on folder cards only and starts a session there; all existing tests pass.

## קומיט / Commit
`feat(window): a New task button on every project card`
