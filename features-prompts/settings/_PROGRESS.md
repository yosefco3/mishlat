# Progress — settings

A settings dialog in the window (⚙ in the header, Ctrl+,) with the two settings the user asked
for: whether Mishlat sends desktop notifications, and after how many days a session counts as
old for the cleanup list. Behind it, a `notify` setting whose default stops the one notification
that annoyed: Mishlat used to notify about the session the user was looking at, which the Claude
app already announces itself.

## מטרת-על / High-level goal
- מתי / When: the user opens the dialog; every scan reads the saved values.
- עיקרון / Principle: settings live in `~/.config/mishlat/settings.json` as before; the dialog
  only writes keys, the scan and the notifier read them. No restart needed.
- Notifications off keeps the tray badge and the attention column; only the desktop banners stop.

## החלטות (מול המשתמש, 2026-10-19) / Decisions (with the user, 2026-10-19)
- `notify` has three values: `others` (default: every waiting / review session except the one
  the user last looked at), `all` (the old behaviour), `off`. Rejected: a boolean, because the
  focused-session skip is the fix for the actual complaint and `all` must stay available.
- "The session the user last looked at" = the record with the greatest `lastFocusedAt` in the
  app's session store. The app itself notifies about that session when its window is in the
  background, so Mishlat's banner for it was always a duplicate.
- The dialog holds notifications and the old-days threshold only; language and text size stay
  on their shortcuts (Ctrl+L, Ctrl+= / Ctrl+-), as documented.
- The old-days spin accepts 1–365; the saved value feeds `mark_cleanup` at the next scan.

## מבחן הצלחה / Acceptance test (בדיקות שהמשתמש מריץ בעצמו)
1. Open Mishlat, press Ctrl+, (or the ⚙ button) ⇒ a dialog "הגדרות" with a notifications
   choice and a days spin; choose "כבויות", save ⇒ `cat ~/.config/mishlat/settings.json` shows
   `"notify": "off"`, and a session that starts waiting produces no banner (the badge still counts it).
2. Set the days to 7, save ⇒ the "למחיקה" chip count grows and `mishlat cleanup` lists sessions
   with the reason "untouched for 7 days"; set it back to 30 ⇒ the count drops again.
3. With the default ("others"): end a turn in the session you are looking at in the Claude app ⇒
   no Mishlat banner; a turn that ends in another session you have not opened since ⇒ a banner.
4. `MISHLAT_LANG=en python3 -m mishlat` ⇒ the same dialog in English.
5. `python3 -m pytest -q` ⇒ green.

## ⏳ Pending (1/3 completed):
1. ✅ `01_notify.md` — `notify` setting, `lastFocusedAt` in the record, `focused_session`, `to_notify` modes; tests.
2. `02_dialog.md` — the settings dialog (⚙, Ctrl+,), `apply_settings`, English strings; smoke test.
3. `03_release.md` — README, APP_OVERVIEW, version 0.1.3, plugin sync, graphs, local install.

> כל צעד עצמאי, נוגע ב-2-4 קבצים, עם טסטים, ו-commit נפרד.
> Each step is independent, touches 2–4 files, has tests, and its own commit.
