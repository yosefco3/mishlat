# Progress — general-project

Sessions whose folder no longer exists (deleted, or moved where Mishlat cannot follow) and the
app's temporary scratch sessions have no real project. Each lost folder used to get its own card
("התיקייה לא נמצאה"), and scratch got a "scratch" card. They now go together under one project,
**כללי** ("general"), shown last.

## מטרה-על / High-level goal
- One "כללי" card instead of one card per lost folder; the card lists the old folders it holds.
- A session there keeps its original folder (in the tooltip, and in search).

## החלטות (מול המשתמש, 2026-10-19) / Decisions (with the user, 2026-10-19)
- The user asked: "אם יש ספריות לא קיימות, שים את השיחות שלהן תחת כללי".
- Default taken: the app's scratch sessions also go to "כללי" (they have no project folder either).
- "כללי" sorts last, whatever its activity. A folder that `aliases.json` or a moved transcript can
  place still goes to its real project first.

## מבחן הצלחה / Acceptance test (בדיקות שהמשתמש מריץ בעצמו, במחשב הפיתוח)
1. `mishlat scan` ⇒ the project list has one `כללי` line (last) and no "(folder not found)" line.
2. Super+Shift+C ⇒ the last card is "כללי" with a note naming the old folders; no card says
   "התיקייה לא נמצאה".
3. Type `scheduler` in the search box ⇒ the "כללי" project is found (by its old folder).

## ✅ Pending (1/1 completed):
1. ✅ `01_general_project.md` — fold lost and scratch sessions into "כללי".

> כל צעד עצמאי, נוגע ב-2-4 קבצים, עם טסטים, ו-commit נפרד.
