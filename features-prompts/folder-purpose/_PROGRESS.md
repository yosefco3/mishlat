# Progress — folder-purpose

Every project card shows one line that says what the folder is for, so an archive, an export or a
scratch folder is not mistaken for a live project. The line comes from the folder's `README.md`
(its first heading and first paragraph), or from a purpose the user typed in the card's menu.

## החלטות (מול המשתמש, 2026-10-19) / Decisions (with the user, 2026-10-19)
- The user, about `site-archive` (the site's article export): "בתיקיות מהסוג הזה תרשום
  איכשהו את ייעוד התיקייה כדי שלא נתבלבל".
- Source order: the user's own text (`~/.config/mishlat/descriptions.json`) > `README.md` in the
  folder (first heading + first paragraph, 160 chars) > nothing.
- "תאר את התיקייה…" in the card's menu saves the text to `descriptions.json`; when the folder has
  no `README.md`, a checked box also writes a minimal one (`# <folder>` + the line), so the purpose
  travels with the folder. This is the only write Mishlat ever makes inside a project folder, and
  only on that click. An existing README is never changed.
- README files are read once per mtime (cached in the scanner).

## מבחן הצלחה / Acceptance test (במחשב הפיתוח)
1. Super+Shift+C ⇒ the card "web_site/site-archive" shows a dim line taken from its
   README: "ארכיון המאמרים — example.org · ייצוא מלא של 67 המאמרים…".
2. Right-click a card without a README (e.g. `tools/dev-kit-export`) ▸ "תאר את התיקייה…", type a
   purpose, keep the box checked, OK ⇒ the line appears on the card, and the folder now has a
   `README.md` with that line.
3. `mishlat scan --json | grep -c '"description"'` ⇒ at least the number of repos with a README.

## ✅ Pending (2/2 completed):
1. ✅ `01_purpose_source.md` — `describe.py` (README parsing, cache), `descriptions.json` IO, `project["description"]`.
2. ✅ `02_card_and_dialog.md` — the card line and tooltip, the "תאר את התיקייה…" dialog with the README box.
