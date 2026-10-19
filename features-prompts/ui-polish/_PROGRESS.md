# Progress — ui-polish

Every session row is visibly a link to its conversation, and the window reads larger: bigger type,
more air, wider cards, state color on the card's edge. A font scale the user can change with
Ctrl + / Ctrl − (saved in settings).

## החלטות (מול המשתמש, 2026-10-19) / Decisions (with the user, 2026-10-19)
- The user: "אני רוצה שכל שורה תהיה קישור לשיחה. אני גם רוצה גרפיקה טובה יותר, אותיות גדולות
  יותר גם אם זה טיפה יאריך את העמוד."
- Verified 2026-10-19 20:45: `claude://code/continue?session=<local id>` focuses the session in
  the running app (its `lastFocusedAt` changed for another session and back). A left click on any
  session row already called it; the rows now look like links: hand cursor, title underlined on
  hover, a small "פתח ↗" hint, link color.
- Defaults taken: base font 15 px (was the theme's ~13 px), titles 16 px, project names 19 px,
  rows 8 px padding, cards 360 px wide, the card's edge colored by its attention state. Ctrl+= /
  Ctrl+- change the base font by 1 px (12–24), Ctrl+0 resets; saved as `settings.json` `font_px`.

## מבחן הצלחה / Acceptance test (במחשב הפיתוח)
1. Super+Shift+C ⇒ the text is clearly larger; hovering a session row shows a hand cursor and the
   title underlined with "פתח ↗"; a click brings the Claude app to that session.
2. Ctrl+= three times ⇒ everything grows; close and reopen the window ⇒ the size stays; Ctrl+0 ⇒
   back to the default.
3. A card of a project with a waiting session has an amber edge; a working one green.

## ✅ Pending (1/1 completed):
1. ✅ `01_polish.md` — CSS, sizes, link rows, cursor, font scale with persistence.
