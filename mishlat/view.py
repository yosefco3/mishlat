"""The pure view model: glyphs, colors, Hebrew labels, sections and filters. No GTK here."""

from __future__ import annotations

import os

from .model import DAY_MS, attention_sessions, cleanup_sessions, stale_sessions
from .strings import t

GLYPH = {"working": "●", "open": "○", "waiting": "◐", "review": "◑", "stopped": "◼", "idle": "·"}
COLOR = {"working": "#2e9e5b", "open": "#8a8578", "waiting": "#d4900f", "review": "#3a7bd5",
         "stopped": "#c0392b", "idle": "#8a8578"}
STATE_LABEL = {"working": "עובד עכשיו", "open": "פתוח באפליקציה", "waiting": "מחכה לך",
               "review": "לבדיקה", "stopped": "נעצר באמצע", "idle": "סגור"}
SECTIONS = (("waiting", "מחכים לך"), ("review", "לבדיקה"), ("stopped", "נעצרו באמצע"), ("working", "עובדים"))
WAITING_FOR = {  # what `claude agents --json` says a session waits for (its five documented values)
    "permission prompt": "מבקש אישור לפעולה",
    "input needed": "מחכה לקלט ממך",
    "sandbox request": "מבקש אישור ל-sandbox",
    "worker request": "מבקש אישור ל-worker",
    "dialog open": "חלון פתוח באפליקציה",
}
FILTERS = (("all", "הכול"), ("active", "פעילים"), ("week", "השבוע"), ("stale", "ישנים"), ("cleanup", "למחיקה"))
CLEANUP_LABEL = {
    "gone": "הפרויקט כבר לא קיים",
    "no_transcript": "ההיסטוריה כבר נמחקה, אין מה להמשיך",
    "duplicate": "כפולה של שיחה חדשה יותר באותו שם",
    "empty": "ריקה: עד שני תורות, בלי קבצים",
    "old": "ישנה: לא נגעו בה {days} יום",
}
WEEK_MS = 7 * DAY_MS


def _ago(n: int, one: str, two: str, many: str) -> str:
    return t(one) if n == 1 else t(two) if n == 2 else f"{n} {t(many)}"


def short_age(at: int, now: int) -> str:
    """עכשיו, 5 דק׳, שעה, שעתיים, 3 שע׳, אתמול, יומיים, 4 ימים, שבוע, 3 שבועות, חודש, שנה."""
    if at <= 0:
        return "—"
    minutes = max(0, now - at) // 60_000
    if minutes < 1:
        return t("עכשיו")
    if minutes < 60:
        return t("{n} דק׳").format(n=minutes)
    hours = minutes // 60
    if hours < 24:
        return _ago(hours, "שעה", "שעתיים", "שע׳")
    days = hours // 24
    if days < 7:
        return _ago(days, "אתמול", "יומיים", "ימים")
    if days < 30:
        return _ago(days // 7, "שבוע", "שבועיים", "שבועות")
    if days < 365:
        return _ago(days // 30, "חודש", "חודשיים", "חודשים")
    return _ago(days // 365, "שנה", "שנתיים", "שנים")


def format_age(at: int, now: int) -> str:
    """The same, as a phrase: "לפני שעה", "אתמול", "עכשיו"."""
    short = short_age(at, now)
    return short if short in (t("עכשיו"), t("אתמול"), "—") else t("לפני {x}").format(x=short)


def count_label(n: int) -> str:
    return t("אין שיחות") if n == 0 else t("שיחה אחת") if n == 1 else t("{n} שיחות").format(n=n)


def tilde(path: str, home: str) -> str:
    return "~" + path[len(home):] if path == home or path.startswith(home.rstrip("/") + "/") else path


def ltr(text: str) -> str:
    """Wrap left-to-right text (a path) in a direction isolate, so a right-to-left line keeps its order."""
    return "\u2066" + text + "\u2069"


def auto(text: str) -> str:
    """Wrap text of either direction (a step, a title) in a first-strong isolate."""
    return "\u2068" + text + "\u2069"


def _step(s: dict) -> str | None:
    if not s.get("step") or not s.get("steps_total"):
        return None
    current = min(s["steps_done"] + 1, s["steps_total"])
    return t("צעד {cur}/{total}: {step}").format(cur=current, total=s["steps_total"], step=auto(s["step"]))


def subline(s: dict) -> str:
    """The second line of a session row: what the user needs to know about it now (translated)."""
    state = s["state"]
    if state == "waiting":
        question = s.get("question")
        return t(WAITING_FOR[question]) if question in WAITING_FOR else (question or t("מחכה לתשובה שלך"))
    if state == "review":
        return s.get("detail") or t("סיים, מחכה לבדיקה")
    if state == "stopped":
        step = _step(s)
        return t("נעצר באמצע · {step}").format(step=step) if step else t("נעצר באמצע")
    if state in ("working", "open"):
        return _step(s) or t(STATE_LABEL[state])
    if s.get("steps_total") and s["steps_done"] >= s["steps_total"]:
        return t("{n}/{n} צעדים הושלמו").format(n=s["steps_total"])
    return s.get("detail") or s.get("first_prompt") or ""


def project_names(index: dict) -> dict[str, str]:
    return {p["key"]: p["name"] for p in index.get("projects", [])}


def project_edge(p: dict) -> str | None:
    """The state that colors a card's edge: attention first, then work."""
    for state in ("waiting", "stopped", "review", "working"):
        if p.get(state):
            return state
    return None


def project_badges(p: dict) -> list[tuple[str, str]]:
    """(text, state or "") pairs for a project card."""
    out = [(f"{GLYPH[k]} {p[k]}", k) for k in ("working", "waiting", "review", "stopped", "open") if p.get(k)]
    out.append((count_label(len(p["sessions"])), ""))
    if p.get("branch"):
        out.append((p["branch"] + (" ✎" if p.get("dirty") else ""), ""))
    elif p.get("is_repo"):
        out.append(("git", ""))
    return out


def project_note(p: dict, home: str) -> str | None:
    """A line for a card: where a moved folder was, what "כללי" holds, sessions without a transcript."""
    parts = []
    if p.get("general"):  # one fact per line; the full paths are in the tooltips and in search
        lines = []
        if p["moved_from"]:
            lines.append(t("מתיקיות שכבר לא קיימות: {folders}").format(
                folders=", ".join(ltr(os.path.basename(m)) for m in p["moved_from"])))
        scratch = sum(1 for s in p["sessions"] if "/scratch-workspaces/" in (s.get("cwd") or ""))
        if scratch:
            lines.append(t("{n} שיחות זמניות של האפליקציה").format(n=scratch))
        missing = sum(1 for s in p["sessions"] if not s["transcript"])
        if missing:
            lines.append(t("{n} בלי טרנסקריפט").format(n=missing))
        return "\n".join(lines) or None
    if p["moved_from"]:
        parts.append(t("הוזזה מ־{folders}").format(folders=", ".join(ltr(tilde(m, home)) for m in p["moved_from"])))
    missing = sum(1 for s in p["sessions"] if not s["transcript"])
    if missing:
        parts.append(t("{n} בלי טרנסקריפט").format(n=missing))
    return " · ".join(parts) or None


def filter_projects(index: dict, mode: str, now: int) -> list[dict]:
    projects = index.get("projects", [])
    if mode == "active":
        return [p for p in projects if p["working"] or p["open"] or p["attention"]]
    if mode == "week":
        return [p for p in projects if p["sessions"] and now - p["last_activity"] <= WEEK_MS]
    return list(projects)


def sections(index: dict) -> list[tuple[str, str, list[dict]]]:
    """The attention column: (state, title, sessions), only the non-empty ones."""
    attention = attention_sessions(index)
    working = [s for p in index.get("projects", []) for s in p["sessions"] if s["state"] == "working"]
    out = []
    for state, title in SECTIONS:
        rows = working if state == "working" else [s for s in attention if s["state"] == state]
        if rows:
            out.append((state, title, rows))
    return out


def assign_choices(index: dict) -> list[tuple[str, str]]:
    """(name, folder) of every project with a folder, newest first: the "שייך לפרויקט…" list."""
    return [(p["name"], p["path"]) for p in index.get("projects", []) if p.get("path")]


def started_line(s: dict, names: dict[str, str], home: str) -> str | None:
    """"התחילה ב־ <folder>" for a session that moved to the project it worked in."""
    start = s.get("started_in")
    if not start:
        return None
    if start == "general":
        return t("התחילה ב־כללי")
    return t("התחילה ב־ {folder}").format(folder=ltr(tilde(start, home)))


def cleanup_reason_text(s: dict, now: int) -> str:
    label = t(CLEANUP_LABEL.get(s.get("cleanup") or "", ""))
    return label.format(days=max(0, now - s["last_activity"]) // DAY_MS)


def cleanup_list(index: dict, requested: dict | None = None) -> list[dict]:
    """The sessions to show under "למחיקה": the index's list without the ones already approved."""
    requested = requested or {}
    return [s for s in cleanup_sessions(index) if s["id"] not in requested]


def cleanup_counts(index: dict) -> dict[str, int]:
    return dict((index.get("totals") or {}).get("cleanup_by") or {})


def stale_list(index: dict, now: int) -> list[dict]:
    return stale_sessions(index, now)


def status_text(index: dict | None, now: int, scanning: bool = False) -> str:
    if index is None:
        return t("סורק…") if scanning else t("אין עדיין נתונים")
    text = t("נסרק {age}").format(age=format_age(index["scanned_at"], now))
    if index.get("errors"):
        text += " · " + t("{n} שגיאות").format(n=len(index["errors"]))
    return text + (" · " + t("סורק…") if scanning else "")


def session_menu_label(s: dict, names: dict[str, str], now: int) -> str:
    """One row of the tray menu: glyph, project, title, age."""
    title = s["title"] if len(s["title"]) <= 40 else s["title"][:39] + "…"
    project = os.path.basename(names.get(s["project"], "") or "") or names.get(s["project"], "")
    return f"{GLYPH[s['state']]}  {project} · {title}  ({short_age(s['last_activity'], now)})"
