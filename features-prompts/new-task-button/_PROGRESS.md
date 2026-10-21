# Progress — new-task-button

A visible "New task" button on every project card in the window, which starts a new Claude
session in that folder through the desktop app (the same `claude-desktop --os-entry=folder_verb`
route the right-click menu and the file-manager extension already use). Until now the action was
hidden behind the card's right-click menu.

## מטרת-על / High-level goal
- מתי / When: the user looks at a project card and wants to start work there.
- עיקרון / Principle: one click, no dialog; the app opens with a new session in that folder.
- The General card (sessions without a folder) has no button: there is no folder to start in.

## החלטות (מול המשתמש, 2026-10-21) / Decisions (with the user, 2026-10-21)
- Wording follows the user's own: "משימה חדשה" / "New task", also for the existing menu item,
  so the button and the menu say the same thing.
- The button sits at the end of the card's badge row, flat (no relief), so a card stays a card.
- Clicking the button never toggles the card: a `Gtk.Button` consumes the press.

## מבחן הצלחה / Acceptance test (בדיקות שהמשתמש מריץ בעצמו)
1. Open Mishlat ⇒ every card with a folder shows "+ משימה חדשה" at the end of its badge row;
   the "כללי" card does not.
2. Click it on a project ⇒ the Claude app comes up with a new session in that folder (its
   sidebar shows the folder); the card did not expand or collapse.
3. Right-click a card ⇒ the menu item reads "משימה חדשה כאן" and does the same.
4. `MISHLAT_LANG=en mishlat` ⇒ the button reads "+ New task".
5. `python3 -m pytest -q` ⇒ green.

## ✅ Pending (2/2 completed):
1. ✅ `01_button.md` — the button on the card, the renamed menu item, English strings; smoke test.
2. ✅ `02_release.md` — README, APP_OVERVIEW, version 0.1.4, plugin sync, graphs, local install.

> כל צעד עצמאי, נוגע ב-2-4 קבצים, עם טסטים, ו-commit נפרד.
> Each step is independent, touches 2–4 files, has tests, and its own commit.
