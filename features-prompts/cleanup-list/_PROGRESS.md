# Progress — cleanup-list (מומלץ למחיקה)

A standing list in the window of sessions that are worth deleting, computed by rules at every
scan, with a reason per row. The user keeps a session ("השאר") or approves its deletion ("מחק");
approved ids wait in a request file, and a Claude session deletes them through the app, which asks
once per session. Deleted sessions leave the index at the next scan, so the list shrinks by itself.

## מטרת-על / High-level goal
- Always there, no manual export or model pass: the rules run inside `build_index`.
- The first run may propose about 100 of 168 sessions; the next runs much fewer.
- Mishlat still writes nothing under `~/.config/Claude` or `~/.claude`: deletion is the app's.

## החלטות (מול המשתמש, 2026-10-19) / Decisions (with the user, 2026-10-19)
- The user: "תמיד יש המלצה על שיחות לא רלוונטיות שכדאי למחוק: שיחות ישנות, פרויקטים שכבר לא
  קיימים ועוד. עכשיו זה יכול להיות מאה שיחות, בפעם הבאה הרבה פחות." Threshold for "old": 30 days.
- From the triage plan: deletion, not archiving (the app confirms each one); a Claude Code session
  runs the deletions; no display names (a project is its folder name).
- Rules, in priority order (the first that matches is the reason shown):
  1. `gone` — the project folder no longer exists (the session sits in "כללי").
  2. `no_transcript` — the transcript was deleted by Claude Code's retention; nothing to resume.
  3. `duplicate` — another session has the same title and is newer.
  4. `empty` — two turns or fewer, no file written, older than 7 days.
  5. `old` — no activity for 30 days or more (`settings.json` `old_days`).
- Never listed: starred; working, waiting, review or stopped; assigned by hand; kept by the user;
  and **the newest session of every folder** (the user, 2026-10-19: "גם אם עברו 30 יום, השיחה
  האחרונה בתיקייה לא נמחקת"). "כללי" has no folder, so there the rule does not apply.
- Default taken: "השאר" keeps a session out of the list for good (until the user removes it
  from `keep.json`); a kept session that gets new activity stays kept.

## מבחן הצלחה / Acceptance test (בדיקות שהמשתמש מריץ בעצמו, במחשב הפיתוח)
1. `mishlat scan` ⇒ the second line ends with `cleanup N` (about 100 today), and the summary ends
   with a "Cleanup" section: the count per reason.
2. Super+Shift+C ▸ chip "למחיקה (N)" ⇒ a list, newest first, each row with its project tag and the
   reason; "השאר" removes the row at once; "מחק" marks it "מאושר למחיקה" and removes it from the
   list; "אשר הכול" marks every remaining row.
3. `mishlat cleanup` ⇒ the approved sessions, one per line with id and title, and the sentence
   that tells a Claude session what to do.
4. In any Claude session: "תמחק את השיחות שאישרתי במשלט" ⇒ it runs `mishlat cleanup --json`,
   deletes each session through the app (the app asks per session), and the next scan shows them
   gone and the list smaller.

## ✅ Pending (3/3 completed):
1. ✅ `01_rules.md` — turns and writes on the session row; the rules; keep and delete-request files; pruning.
2. ✅ `02_window.md` — the "למחיקה" view with מחק / השאר / אשר הכול; the scan summary; `mishlat cleanup`.
3. ✅ `03_docs.md` — README, overview, the executor note; install; verify on the dev laptop; graphs.

> כל צעד עצמאי, נוגע ב-2-4 קבצים, עם טסטים, ו-commit נפרד.
