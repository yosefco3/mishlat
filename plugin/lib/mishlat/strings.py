"""UI language. Hebrew is the source text; `t()` maps it to English when the language is "en".
Templates keep their `{name}` placeholders, so `t("…{n}…").format(n=…)` works in both languages."""

from __future__ import annotations

import os

LANGS = ("he", "en")
_lang = "he"

EN: dict[str, str] = {
    # names and headers
    "משלט": "Mishlat",
    "שיחות Claude לפי פרויקט": "Claude sessions by project",
    "כללי": "General",
    "(ללא כותרת)": "(untitled)",
    "פתח ↗": "open ↗",
    # states and sections
    "עובד עכשיו": "working now", "פתוח באפליקציה": "open in the app", "מחכה לך": "waiting for you",
    "לבדיקה": "to review", "נעצר באמצע": "stopped midway", "סגור": "closed",
    "מחכים לך": "Waiting for you", "נעצרו באמצע": "Stopped midway", "עובדים": "Working",
    "הכול": "All", "פעילים": "Active", "השבוע": "This week", "ישנים": "Stale", "למחיקה": "To delete",
    "ישנים ({n})": "Stale ({n})", "למחיקה ({n})": "To delete ({n})",
    # cleanup reasons
    "הפרויקט כבר לא קיים": "the project folder no longer exists",
    "ההיסטוריה כבר נמחקה, אין מה להמשיך": "its history was deleted; nothing to resume",
    "כפולה של שיחה חדשה יותר באותו שם": "a duplicate of a newer session with the same title",
    "ריקה: עד שני תורות, בלי קבצים": "empty: two turns or fewer, no files written",
    "ישנה: לא נגעו בה {days} יום": "stale: untouched for {days} days",
    # ages
    "עכשיו": "now", "{n} דק׳": "{n} min", "שעה": "an hour", "שעתיים": "2 hours", "שע׳": "hours",
    "אתמול": "yesterday", "יומיים": "2 days", "ימים": "days", "שבוע": "a week", "שבועיים": "2 weeks",
    "שבועות": "weeks", "חודש": "a month", "חודשיים": "2 months", "חודשים": "months", "שנה": "a year",
    "שנתיים": "2 years", "שנים": "years", "לפני {x}": "{x} ago",
    "אין שיחות": "no sessions", "שיחה אחת": "1 session", "{n} שיחות": "{n} sessions",
    # sublines and notes
    "צעד {cur}/{total}: {step}": "step {cur}/{total}: {step}",
    "מחכה לתשובה שלך": "waiting for your answer", "סיים, מחכה לבדיקה": "done, waiting for your review",
    "נעצר באמצע · {step}": "stopped midway · {step}", "{n}/{n} צעדים הושלמו": "{n}/{n} steps done",
    "מתיקיות שכבר לא קיימות: {folders}": "from folders that no longer exist: {folders}",
    "{n} שיחות זמניות של האפליקציה": "{n} temporary app sessions", "{n} בלי טרנסקריפט": "{n} without a transcript",
    "הוזזה מ־{folders}": "moved from {folders}", "התחילה ב־כללי": "started in General",
    "התחילה ב־ {folder}": "started in {folder}",
    "סורק…": "scanning…", "אין עדיין נתונים": "no data yet", "נסרק {age}": "scanned {age}", "{n} שגיאות": "{n} errors",
    # window
    "סרוק עכשיו (Ctrl+R)": "Scan now (Ctrl+R)", "חיפוש פרויקט, שיחה או שאלה פתוחה…": "Search a project, a session or an open question…",
    "הצג את כל הפרויקטים": "Show all projects", "פרויקט: כללי": "Project: General", "תיקייה: {folder}": "Folder: {folder}",
    "סורק את השיחות בפעם הראשונה…": "Scanning the sessions for the first time…",
    "שיחות שלא נגעו בהן 30 יום ומעלה · {n}": "Sessions untouched for 30 days or more · {n}",
    "מומלץ למחיקה · {n}": "Worth deleting · {n}",
    "הרשימה מחושבת מחדש בכל סריקה. \"השאר\" מוציא שיחה מהרשימה לתמיד; \"מחק\" מאשר מחיקה, שסשן Claude מבצע באפליקציה.":
        "Recomputed at every scan. \"Keep\" removes a session from this list for good; \"Delete\" approves a deletion, which a Claude session runs in the app.",
    "אשר הכול ({n})": "Approve all ({n})", "מאושרות למחיקה, ממתינות לביצוע: {n}": "approved, waiting to be run: {n}",
    "איך מבצעים?": "How to run them?",
    "בכל סשן Claude כתוב: \"תמחק את השיחות שאישרתי במשלט\".\nהסשן מריץ `mishlat cleanup --json` ומוחק כל שיחה דרך האפליקציה, שמבקשת אישור לכל אחת.\nבסריקה הבאה השיחות שנמחקו יוצאות מהרשימה.":
        "In any Claude session write: \"delete the sessions I approved in Mishlat\".\nIt runs `mishlat cleanup --json` and deletes each one through the app, which asks per session.\nThe next scan drops the deleted ones from the list.",
    "מחק": "Delete", "השאר": "Keep", "אין כרגע שיחות שמחכות לך": "Nothing is waiting for you right now",
    "פרויקטים · {n}": "Projects · {n}", "שיחות · {n}": "Sessions · {n}", "אין פרויקטים להצגה": "No projects to show",
    "שיחות בלי תיקייה קיימת": "sessions without an existing folder",
    "לחיצה פותחת או מקפלת את רשימת השיחות · לחיצה ימנית לעוד פעולות": "Click to unfold or fold the sessions · right-click for more",
    " (מתוך README)": " (from README)", "עוד {n} שיחות…": "{n} more sessions…", "קפל": "fold",
    "תיקייה מקורית: {folder}": "original folder: {folder}", " · שויכה ידנית": " · assigned by hand",
    " · שויכה לפי העבודה בה": " · assigned by the work in it", "שויכה ידנית": "assigned by hand",
    "לחיצה פותחת באפליקציה · לחיצה ימנית לעוד פעולות": "Click to open in the app · right-click for more",
    # menus and dialogs
    "פתח באפליקציה": "Open in the app", "המשך בטרמינל": "Resume in a terminal", "פתח את התיקייה": "Open the folder",
    "העתק את מזהה השיחה": "Copy the session id", "שייך לפרויקט…": "Assign to a project…",
    "החזר לשיוך האוטומטי": "Back to automatic assignment", "הסתר מרשימת \"מחכים לך\"": "Hide from \"Waiting for you\"",
    "סשן Claude חדש כאן": "New Claude session here", "העתק את הנתיב": "Copy the path",
    "הצג רק את הפרויקט הזה": "Show only this project", "תאר את התיקייה…": "Describe the folder…",
    "מחק את התיאור שלי": "Remove my description", "ייעוד התיקייה": "What the folder is for",
    "ביטול": "Cancel", "שמור": "Save", "מה יש בתיקייה {folder}?": "What is in {folder}?",
    "למשל: ארכיון המאמרים של האתר, ייצוא מ-17.10, בלי קוד": "e.g. the site's article archive, exported in October, no code",
    "כתוב גם README.md בתיקייה, כדי שהייעוד יישאר איתה": "Also write a README.md in the folder, so the purpose travels with it",
    "לתיקייה כבר יש README; משלט לא משנה אותו": "The folder already has a README; Mishlat never changes it",
    "לא הצלחתי לכתוב README.md בתיקייה: {err}": "Could not write README.md in the folder: {err}",
    "שייך לפרויקט": "Assign to a project", "שייך": "Assign",
    "לאיזה פרויקט שייכת השיחה \"{title}\"?": "Which project does \"{title}\" belong to?",
    "בחר תיקייה": "Choose a folder", "בחר": "Choose", "תיקייה אחרת…": "Another folder…",
    # tray and notifications
    "משלט · סורק…": "Mishlat · scanning…", "{n} מחכים לך": "{n} waiting for you", "{n} לבדיקה": "{n} to review",
    "{n} נעצרו": "{n} stopped", "{n} עובדים": "{n} working", "אין שיחות שמחכות לך": "nothing is waiting for you",
    "ועוד {n}…": "{n} more…", "פתח את משלט": "Open Mishlat", "סרוק עכשיו": "Scan now", "יציאה": "Quit",
    "מחכה לתשובה": "waiting for an answer", "פתח": "Open", "הסתר": "Hide",
    # actions
    "לשיחה הזו אין מזהה של Claude Code": "This session has no Claude Code id",
    "לא נמצא claude במחשב": "claude was not found on this computer",
    # nemo
    "{n} פרויקטים": "{n} projects", "שיחות Claude של התיקייה ({n})…": "Claude sessions of this folder ({n})…",
    "שיחות Claude בתיקייה (משלט)": "Claude sessions in the folder (Mishlat)",
    "פותח את משלט על התיקייה הזו": "Opens Mishlat on this folder",
    "פותח שיחת Claude Code חדשה בתיקייה": "Starts a new Claude Code session in the folder",
}


def set_lang(lang: str) -> None:
    global _lang
    _lang = lang if lang in LANGS else "he"


def lang() -> str:
    return _lang


def is_rtl() -> bool:
    return _lang == "he"


def t(text: str) -> str:
    """The text in the current language. An unknown key stays Hebrew."""
    return EN.get(text, text) if _lang == "en" else text


def locale_lang(environ=os.environ) -> str:
    """"he" when the locale is Hebrew, else "en"."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = environ.get(var) or ""
        if value:
            return "he" if value.lower().startswith("he") else "en"
    return "en"
