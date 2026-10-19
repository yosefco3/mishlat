"""The panel icon (XApp.StatusIcon, native to Cinnamon), its menu, and the notifications."""

from __future__ import annotations

import os

from . import view
from .model import attention_sessions, focused_session
from .strings import t

MENU_ROWS = 8
NOTIFY_STATES = ("waiting", "review")  # "stopped" is not notified: the user stopped it


def icons_dir(home: str) -> str:
    installed = os.path.join(home, ".local", "share", "mishlat", "icons")
    if os.path.isdir(installed):
        return installed
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "icons"))


def icon_file(directory: str, count: int) -> str:
    return os.path.join(directory, f"mishlat-{min(max(count, 0), 3)}.svg")


def badge_count(index: dict | None) -> int:
    return len((index or {}).get("attention", []))


def tooltip(index: dict | None) -> str:
    if not index:
        return t("משלט · סורק…")
    tot = index["totals"]
    parts = [t("{n} מחכים לך").format(n=tot["waiting"])] if tot["waiting"] else []
    if tot["review"]:
        parts.append(t("{n} לבדיקה").format(n=tot["review"]))
    if tot["stopped"]:
        parts.append(t("{n} נעצרו").format(n=tot["stopped"]))
    if tot["working"]:
        parts.append(t("{n} עובדים").format(n=tot["working"]))
    return t("משלט") + " · " + (" · ".join(parts) if parts else t("אין שיחות שמחכות לך"))


def menu_model(index: dict | None, now: int) -> list[tuple]:
    """("header", text) · ("session", session, label) · ("more", text) · ("sep",) · ("action", key, text)."""
    out: list[tuple] = []
    if index:
        names = view.project_names(index)
        for state, title, rows in view.sections(index):
            if out:
                out.append(("sep",))
            out.append(("header", f"{t(title)} · {len(rows)}"))
            for s in rows[:MENU_ROWS]:
                out.append(("session", s, view.session_menu_label(s, names, now)))
            if len(rows) > MENU_ROWS:
                out.append(("more", t("ועוד {n}…").format(n=len(rows) - MENU_ROWS)))
    if not out:
        out.append(("header", t("אין שיחות שמחכות לך") if index else t("סורק…")))
    out += [("sep",), ("action", "open", t("פתח את משלט")), ("action", "scan", t("סרוק עכשיו")), ("action", "quit", t("יציאה"))]
    return out


def notification_text(s: dict, names: dict[str, str]) -> tuple[str, str]:
    project = os.path.basename(names.get(s["project"], "")) or names.get(s["project"], "") or "Claude"
    title = f"{project} · {s['title']}"
    if s["state"] == "waiting":
        body = t("מחכה לתשובה") + (f": {s['question']}" if s.get("question") else "")
    elif s["state"] == "review":
        body = t("סיים, מחכה לבדיקה") + (f": {s['detail']}" if s.get("detail") else "")
    else:
        body = view.subline(s)
    return title, body


def to_notify(previous: dict | None, index: dict, mode: str = "others") -> list[dict]:
    """The sessions to notify about: new attention entries in a notified state. None before the first
    scan: the first index is the baseline (no burst of old questions at login). `mode` is the
    `notify` setting: "off" sends nothing; "others" skips the session the user is looking at in the
    app (the app announces that one itself); "all" keeps it."""
    from .model import entered
    if previous is None or mode == "off":
        return []
    skip = focused_session(index) if mode == "others" else None
    return [s for s in entered(previous, index)
            if s["state"] in NOTIFY_STATES and not s.get("dismissed") and s["id"] != skip]


class _XAppIcon:
    """Cinnamon / Linux Mint: XApp.StatusIcon (a native panel icon with a tooltip)."""

    def __init__(self) -> None:
        import gi
        gi.require_version("XApp", "1.0")
        from gi.repository import XApp
        self.icon = XApp.StatusIcon()
        self.icon.set_name("mishlat")

    def set(self, icon_path: str, tip: str, menu) -> None:
        self.icon.set_primary_menu(menu)
        self.icon.set_secondary_menu(menu)
        self.icon.set_icon_name(icon_path)
        self.icon.set_tooltip_text(tip)


class _AppIndicator:
    """GNOME (with the AppIndicator extension), KDE, XFCE, MATE: AyatanaAppIndicator3."""

    def __init__(self, icons: str) -> None:
        import gi
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AI
        self.AI = AI
        self.icon = AI.Indicator.new("mishlat", "mishlat-0", AI.IndicatorCategory.APPLICATION_STATUS)
        self.icon.set_icon_theme_path(icons)
        self.icon.set_status(AI.IndicatorStatus.ACTIVE)

    def set(self, icon_path: str, tip: str, menu) -> None:
        self.icon.set_menu(menu)
        self.icon.set_icon_full(os.path.splitext(os.path.basename(icon_path))[0], tip)
        self.icon.set_title(tip)


def make_icon(icons: str):
    """The first panel-icon backend that loads; raises when none does (the window still works)."""
    errors = []
    for build in (lambda: _XAppIcon(), lambda: _AppIndicator(icons)):
        try:
            return build()
        except Exception as exc:  # a missing binding or no panel host
            errors.append(f"{type(exc).__name__}: {exc}")
    raise RuntimeError("no tray backend: " + " · ".join(errors))


class Tray:
    def __init__(self, home: str, on_action, on_session) -> None:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
        self.Gtk = Gtk
        self.icons = icons_dir(home)
        self.on_action = on_action
        self.on_session = on_session
        self.backend = make_icon(self.icons)
        self.menu = None
        self.update(None, 0)

    def update(self, index: dict | None, now: int) -> None:
        Gtk = self.Gtk
        menu = Gtk.Menu()
        for entry in menu_model(index, now):
            kind = entry[0]
            if kind == "sep":
                menu.append(Gtk.SeparatorMenuItem())
                continue
            item = Gtk.MenuItem(label=entry[2] if kind in ("session", "action") else entry[1])
            if kind == "session":
                item.connect("activate", lambda _i, s=entry[1]: self.on_session(s))
            elif kind == "action":
                item.connect("activate", lambda _i, key=entry[1]: self.on_action(key))
            else:
                item.set_sensitive(False)
            menu.append(item)
        menu.show_all()
        self.menu = menu
        self.backend.set(icon_file(self.icons, badge_count(index)), tooltip(index), menu)


class Notifier:
    def __init__(self, icon: str | None = None) -> None:
        import gi
        gi.require_version("Notify", "0.7")
        from gi.repository import Notify
        Notify.init("Mishlat")
        self.Notify = Notify
        self.icon = icon
        self.has_actions = "actions" in (Notify.get_server_caps() or [])
        self._alive: list = []  # a notification with actions must stay referenced

    def notify(self, title: str, body: str, actions: list[tuple]) -> None:
        n = self.Notify.Notification.new(title, body, self.icon)
        if self.has_actions:
            for key, label, callback in actions:
                n.add_action(key, label, lambda _n, _a, *_rest, cb=callback: cb(), None)
        n.connect("closed", lambda notif: notif in self._alive and self._alive.remove(notif))
        self._alive = self._alive[-20:] + [n]
        try:
            n.show()
        except Exception:  # no notification daemon: the tray badge still tells
            pass
