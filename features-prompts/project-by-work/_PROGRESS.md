# Progress — project-by-work

A session belonged to the folder it started in. But work moves: this very session started in
`~/Desktop/shedu` and built Mishlat in `~/Desktop/apps/mishlat`; the tradebot sessions started in the
old `~/Desktop/trading` folder and wrote tradebot. So "tradebot" and "mishlat" showed no sessions.
Now a session belongs to the project it **wrote** in (files written or edited, commands that write or
commit); a session with no writes is judged by what it read, with a higher bar; and the user can
assign a session by hand.

## מטרה-על / High-level goal
- The project of a session = where its work went, not where it started; its start folder stays in
  the tooltip ("התחילה ב־…").
- Measured on 158 sessions (2026-10-19): the write rule moves 4 (this one → apps/mishlat, three
  tradebot sessions → apps/tradebot); 12 sessions wrote in several projects and stay in their own.

## החלטות (מול המשתמש, 2026-10-19) / Decisions (with the user, 2026-10-19)
- The user: "למה אין שיחות לטריידבוט, משלט וכו" · "השיחה הזו למשל צריכה להיות שייכת למשלט".
- Defaults taken: writes decide (top project ≥ 5 writes and more than twice the start folder's);
  with no writes, reads decide (≥ 15 mentions and more than twice the start folder's); a write with
  no absolute path counts for the start folder. A manual assignment
  (`~/.config/mishlat/assignments.json`, from the window's "שייך לפרויקט…") always wins.
- A session is shown under one project only (no duplicates), so the counts stay true.

## מבחן הצלחה / Acceptance test (בדיקות שהמשתמש מריץ בעצמו, במחשב הפיתוח)
1. `mishlat scan` ⇒ `apps/mishlat` and `apps/tradebot` are listed with sessions.
2. Super+Shift+C, the card "apps/mishlat" ⇒ it holds "דשבורד פרויקטים וניהול משימות"; its tooltip
   says "התחילה ב־ ~/Desktop/shedu".
3. Right-click a session ▸ "שייך לפרויקט…" ▸ pick another project ⇒ within a few seconds the session
   moves there; right-click ▸ "החזר לשיוך האוטומטי" ⇒ it goes back.

## ✅ Pending (3/3 completed):
1. ✅ `01_transcript_work.md` — record written and read project paths per transcript, incrementally.
2. ✅ `02_assign_by_work.md` — the assignment rule in `build_index`, with `assignments.json` overriding.
3. ✅ `03_window_assign.md` — the origin in the tooltip, the "שייך לפרויקט…" dialog, docs, install.

> כל צעד עצמאי, נוגע ב-2-4 קבצים, עם טסטים, ו-commit נפרד.
