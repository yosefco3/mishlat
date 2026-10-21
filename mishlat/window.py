"""The Mishlat window (GTK 3, right to left): the attention column, the project cards, search."""

from __future__ import annotations

import json
import os
import time

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk, Pango  # noqa: E402

from . import actions, view  # noqa: E402
from . import index as io  # noqa: E402
from .describe import readme_path, write_readme  # noqa: E402
from .strings import is_rtl, lang, set_lang, t  # noqa: E402
from .model import search  # noqa: E402

CSS = b"""
.mishlat-window { font-size: %(font)dpx; }
.mishlat-card { border: 1px solid alpha(@theme_fg_color, 0.16); border-radius: 12px; padding: 14px 16px;
                background-color: @theme_base_color; border-%(edge)s-width: 5px; }
.mishlat-card:hover { border-color: alpha(@theme_fg_color, 0.38); }
.mishlat-edge-waiting { border-%(edge)s-color: #d4900f; }
.mishlat-edge-stopped { border-%(edge)s-color: #c0392b; }
.mishlat-edge-review { border-%(edge)s-color: #3a7bd5; }
.mishlat-edge-working { border-%(edge)s-color: #2e9e5b; }
.mishlat-row { border-radius: 9px; padding: 8px 10px; background-color: alpha(@theme_fg_color, 0.03);
               border: 1px solid alpha(@theme_fg_color, 0.07); }
.mishlat-row:hover, .mishlat-line:hover { background-color: alpha(@theme_selected_bg_color, 0.16); }
.mishlat-line { border-radius: 7px; padding: 4px 6px; }
.mishlat-row:hover .mishlat-link, .mishlat-line:hover .mishlat-link { text-decoration: underline;
    color: @link_color; }
.mishlat-row:hover .mishlat-open, .mishlat-line:hover .mishlat-open { opacity: 0.9; }
.mishlat-open { opacity: 0; color: @link_color; font-size: 0.85em; }
.mishlat-side { background-color: alpha(@theme_fg_color, 0.035); }
.mishlat-section { font-weight: bold; font-size: 1.05em; opacity: 0.78; }
.mishlat-name { font-weight: bold; font-size: 1.28em; }
.mishlat-title { font-size: 1.06em; }
.mishlat-dim { opacity: 0.66; font-size: 0.92em; }
.mishlat-question { color: #c98a10; }
.mishlat-warn { color: #c98a10; font-size: 0.92em; }
.mishlat-newtask { padding: 0 8px; min-height: 0; border-radius: 7px; color: @theme_selected_bg_color; font-weight: bold; }
.mishlat-badge { background-color: alpha(@theme_fg_color, 0.08); border-radius: 7px; padding: 2px 9px;
                 font-size: 0.92em; }
.mishlat-tag { background-color: alpha(@theme_fg_color, 0.09); border-radius: 6px; padding: 1px 7px;
               font-size: 0.85em; }
.mishlat-glyph { font-size: 1.15em; }
.mishlat-purpose { opacity: 0.8; font-style: italic; }
"""

CARD_ROWS = 3          # session lines on a folded card
CARD_WIDTH = 360
CARD_CHARS = 32        # label width cap inside a card
ROW_CHARS = 40         # label width cap in the attention column
RERENDER_S = 60        # re-draw at least this often, so the ages stay true
FONT_STEP = 1


def now_ms() -> int:
    return int(time.time() * 1000)


_provider: Gtk.CssProvider | None = None


def install_css(font_px: int = io.FONT_DEFAULT) -> None:
    """Install (or re-install, on a font change) the window's CSS."""
    global _provider
    screen = Gdk.Screen.get_default()
    if screen is None:
        return
    if _provider is not None:
        Gtk.StyleContext.remove_provider_for_screen(screen, _provider)
    _provider = Gtk.CssProvider()
    _provider.load_from_data(CSS % {b"font": font_px, b"edge": b"right" if is_rtl() else b"left"})
    Gtk.StyleContext.add_provider_for_screen(screen, _provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def _label(text: str = "", css: tuple = (), markup: str | None = None, ellipsize: bool = False,
           wrap: bool = False, max_chars: int = 0) -> Gtk.Label:
    lab = Gtk.Label()
    if markup is not None:
        lab.set_markup(markup)
    else:
        lab.set_text(text)
    lab.set_halign(Gtk.Align.START)
    lab.set_xalign(0.0)
    if ellipsize:
        lab.set_ellipsize(Pango.EllipsizeMode.END)
    if wrap:
        lab.set_line_wrap(True)
        lab.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    if max_chars:
        lab.set_max_width_chars(max_chars)  # else a long title sets the natural width of its card
    for c in css:
        lab.get_style_context().add_class(c)
    return lab


def _glyph(state: str) -> Gtk.Label:
    return _label(markup=f'<span foreground="{view.COLOR[state]}">{view.GLYPH[state]}</span>', css=("mishlat-glyph",))


def _hover(widget: Gtk.Widget, hand: bool = False) -> Gtk.Widget:
    """Prelight on hover; with `hand`, a pointer cursor too, so the row reads as a link."""
    widget.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK |
                      Gdk.EventMask.BUTTON_PRESS_MASK)

    def enter(w, e):
        w.set_state_flags(Gtk.StateFlags.PRELIGHT, False)
        if hand and w.get_window() is not None:
            w.get_window().set_cursor(Gdk.Cursor.new_from_name(w.get_display(), "pointer"))

    def leave(w, e):
        w.unset_state_flags(Gtk.StateFlags.PRELIGHT)
        if hand and w.get_window() is not None:
            w.get_window().set_cursor(None)
    widget.connect("enter-notify-event", enter)
    widget.connect("leave-notify-event", leave)
    return widget


def _open_hint() -> Gtk.Label:
    return _label(t("פתח ↗"), css=("mishlat-open",))


def _clear(box: Gtk.Container) -> None:
    for child in box.get_children():
        box.remove(child)
        child.destroy()


NOTIFY_CHOICES = (("others", "על כל שיחה שמחכה לך, חוץ מזו שאתה מסתכל בה"),
                  ("all", "על כל שיחה שמחכה לך"),
                  ("off", "כבויות (הסימון בפאנל נשאר)"))


class MishlatWindow(Gtk.ApplicationWindow):
    def __init__(self, app, home: str) -> None:
        super().__init__(application=app, title=t("משלט"))
        self.get_style_context().add_class("mishlat-window")
        self.app = app
        self.home = home
        settings = io.load_settings(home)
        self.font_px = settings["font_px"]
        set_lang(settings["lang"])
        Gtk.Widget.set_default_direction(Gtk.TextDirection.RTL if is_rtl() else Gtk.TextDirection.LTR)
        install_css(self.font_px)
        self.index: dict | None = None
        self.mode = "all"
        self.query = ""
        self.focus: str | None = None
        self.expanded: set[str] = set()
        self.scanning = False
        self._signature = None
        self._rendered_at = 0.0
        # What the last render drew (for tests and diagnostics).
        self.shown_cards: list[str] = []
        self.shown_sessions: list[str] = []
        self.side_sessions: list[str] = []
        self.new_task_buttons: dict[str, Gtk.Button] = {}  # project key → its "+ New task" button

        self.set_default_size(1320, 840)
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title(t("משלט"))
        header.set_subtitle(t("שיחות Claude לפי פרויקט"))
        rescan = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        rescan.set_tooltip_text(t("סרוק עכשיו (Ctrl+R)"))
        rescan.connect("clicked", lambda *_: self._request_scan())
        header.pack_end(rescan)
        gear = Gtk.Button.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.BUTTON)
        gear.set_tooltip_text(t("הגדרות (Ctrl+,)"))
        gear.connect("clicked", lambda *_: self._settings())
        header.pack_end(gear)
        self.set_titlebar(header)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bar = Gtk.Box(spacing=8, margin=10)
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text(t("חיפוש פרויקט, שיחה או שאלה פתוחה…"))
        self.search.connect("search-changed", lambda e: self.set_query(e.get_text()))
        bar.pack_start(self.search, True, True, 0)
        self.chips: dict[str, Gtk.RadioButton] = {}
        group = None
        for mode, title in view.FILTERS:
            chip = Gtk.RadioButton.new_with_label_from_widget(group, t(title))
            chip.set_mode(False)
            chip.connect("toggled", self._on_chip, mode)
            group = group or chip
            self.chips[mode] = chip
            bar.pack_start(chip, False, False, 0)
        self.focus_bar = Gtk.Box(spacing=4)
        self.focus_label = _label(css=("mishlat-tag",))
        clear = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.BUTTON)
        clear.set_relief(Gtk.ReliefStyle.NONE)
        clear.set_tooltip_text(t("הצג את כל הפרויקטים"))
        clear.connect("clicked", lambda *_: self.show_project(None))
        self.focus_bar.pack_start(self.focus_label, False, False, 0)
        self.focus_bar.pack_start(clear, False, False, 0)
        bar.pack_start(self.focus_bar, False, False, 0)
        self.status = _label(css=("mishlat-dim",))
        bar.pack_end(self.status, False, False, 0)
        root.pack_start(bar, False, False, 0)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        side_scroll = Gtk.ScrolledWindow()
        side_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        side_scroll.set_size_request(400, -1)
        side_scroll.get_style_context().add_class("mishlat-side")
        self.side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin=12)
        side_scroll.add(self.side)
        self.main_scroll = Gtk.ScrolledWindow()
        self.main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=14)
        self.main_scroll.add(self.main)
        paned.pack1(side_scroll, False, False)
        paned.pack2(self.main_scroll, True, False)
        root.pack_start(paned, True, True, 0)
        self.add(root)

        self.connect("key-press-event", self._on_key)
        self.connect("delete-event", lambda *_: self.hide() or True)  # the tray keeps running
        GLib.timeout_add_seconds(RERENDER_S, self._tick)

    # ── state from the app ──
    def set_index(self, index: dict | None) -> None:
        self.index = index
        self.render()

    def set_scanning(self, on: bool) -> None:
        self.scanning = on
        self._update_status()

    def set_query(self, text: str) -> None:
        self.query = text.strip()
        self.render(force=True)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        if not self.chips[mode].get_active():
            self.chips[mode].set_active(True)
        self.render(force=True)

    def show_project(self, path: str | None) -> None:
        """Show one folder and the projects under it (the Nemo menu), or everything (None)."""
        self.focus = os.path.normpath(path) if path else None
        if self.focus:
            self.search.set_text("")
            self.query = ""
            for p in self._focused():
                self.expanded.add(p["key"])
        self.render(force=True)

    def set_font(self, px: int) -> None:
        """Ctrl+= / Ctrl+- / Ctrl+0: the base font, saved in settings.json."""
        px = max(io.FONT_MIN, min(io.FONT_MAX, px))
        if px == self.font_px:
            return
        self.font_px = px
        install_css(px)
        io.save_setting(self.home, "font_px", px)
        self.render(force=True)

    def set_language(self, code: str) -> None:
        """Ctrl+L: Hebrew or English, with the matching direction; saved in settings.json."""
        if code == lang():
            return
        set_lang(code)
        io.save_setting(self.home, "lang", code)
        Gtk.Widget.set_default_direction(Gtk.TextDirection.RTL if is_rtl() else Gtk.TextDirection.LTR)
        install_css(self.font_px)
        self.set_title(t("משלט"))
        bar = self.get_titlebar()
        if isinstance(bar, Gtk.HeaderBar):
            bar.set_title(t("משלט"))
            bar.set_subtitle(t("שיחות Claude לפי פרויקט"))
        self.search.set_placeholder_text(t("חיפוש פרויקט, שיחה או שאלה פתוחה…"))
        for mode, title in view.FILTERS:
            self.chips[mode].set_label(t(title))
        self.render(force=True)

    def _settings(self) -> None:
        """Ctrl+, / ⚙: notifications and the old-days threshold, saved in settings.json."""
        dialog, combo, days = self.settings_dialog(io.load_settings(self.home))
        dialog.show_all()
        answer = dialog.run()
        values = {"notify": combo.get_active_id() or "others", "old_days": int(days.get_value())}
        dialog.destroy()
        if answer == Gtk.ResponseType.OK:
            self.apply_settings(values)

    def settings_dialog(self, current: dict):
        """The dialog and its two inputs, not yet shown: (dialog, notify combo, days spin)."""
        dialog = Gtk.Dialog(title=t("הגדרות"), transient_for=self, modal=True)
        dialog.add_buttons(t("ביטול"), Gtk.ResponseType.CANCEL, t("שמור"), Gtk.ResponseType.OK)
        dialog.set_default_size(560, -1)
        grid = Gtk.Grid(row_spacing=10, column_spacing=12, border_width=12)
        grid.attach(_label(t("התראות על המסך")), 0, 0, 1, 1)
        combo = Gtk.ComboBoxText()
        for key, text in NOTIFY_CHOICES:
            combo.append(key, t(text))
        combo.set_active_id(current["notify"])
        combo.set_hexpand(True)
        grid.attach(combo, 1, 0, 1, 1)
        grid.attach(_label(t("שיחה נחשבת ישנה אחרי (ימים)")), 0, 1, 1, 1)
        days = Gtk.SpinButton.new_with_range(1, 365, 1)
        days.set_value(current["old_days"])
        days.set_activates_default(True)
        grid.attach(days, 1, 1, 1, 1)
        grid.attach(_label(t("ישנה = מועמדת למחיקה, חוץ מהשיחה האחרונה בכל תיקייה"), css=("mishlat-dim",), wrap=True),
                    0, 2, 2, 1)
        dialog.get_content_area().pack_start(grid, False, False, 0)
        dialog.set_default_response(Gtk.ResponseType.OK)
        return dialog, combo, days

    def apply_settings(self, values: dict) -> None:
        """Save the keys that changed and rescan, so the cleanup list and the notifier use them at once."""
        current = io.load_settings(self.home)
        changed = False
        for key, value in values.items():
            if current.get(key) != value:
                io.save_setting(self.home, key, value)
                changed = True
        if changed:
            self._request_scan()

    # ── drawing ──
    def _tick(self) -> bool:
        self.render()
        return True

    def _focused(self) -> list[dict]:
        if not self.index or not self.focus:
            return []
        f = self.focus
        return [p for p in self.index["projects"]
                if (p["path"] or p["key"]) == f or (p["path"] or p["key"]).startswith(f + "/")
                or f in p["moved_from"]]

    def render(self, force: bool = False) -> None:
        sig = json.dumps([self.index and {k: v for k, v in self.index.items() if k not in ("scanned_at", "scan_ms")},
                          self.mode, self.query, self.focus, sorted(self.expanded)], sort_keys=True, default=str)
        if not force and sig == self._signature and time.monotonic() - self._rendered_at < RERENDER_S - 1:
            self._update_status()
            return
        self._signature, self._rendered_at = sig, time.monotonic()
        vadj = self.main_scroll.get_vadjustment()
        keep = vadj.get_value()
        self.shown_cards, self.shown_sessions, self.side_sessions = [], [], []
        self.new_task_buttons = {}
        _clear(self.side)
        _clear(self.main)
        self._update_status()
        stale = len(view.stale_list(self.index, now_ms())) if self.index else 0
        self.chips["stale"].set_label(t("ישנים ({n})").format(n=stale) if stale else t("ישנים"))
        cleanup = len(view.cleanup_list(self.index, io.load_delete_requests(self.home))) if self.index else 0
        self.chips["cleanup"].set_label(t("למחיקה ({n})").format(n=cleanup) if cleanup else t("למחיקה"))
        self.focus_bar.set_visible(bool(self.focus))
        if self.focus:
            self.focus_label.set_text(t("פרויקט: כללי") if self.focus == "general"
                                      else t("תיקייה: {folder}").format(folder=view.ltr(view.tilde(self.focus, self.home))))
        if self.index is None:
            self.main.pack_start(_label(t("סורק את השיחות בפעם הראשונה…"), css=("mishlat-dim",)), False, False, 0)
            self.show_all()
            self.focus_bar.set_visible(bool(self.focus))
            return
        self._render_side()
        if self.query:
            self._render_search()
        elif self.focus:
            self._render_cards(self._focused(), title=None, expand_all=True)
        elif self.mode == "stale":
            rows = view.stale_list(self.index, now_ms())
            self._section(self.main, t("שיחות שלא נגעו בהן 30 יום ומעלה · {n}").format(n=len(rows)))
            for s in rows:
                self.main.pack_start(self._session_row(s, True, self.shown_sessions), False, False, 0)
        elif self.mode == "cleanup":
            self._render_cleanup()
        else:
            self._render_cards(view.filter_projects(self.index, self.mode, now_ms()))
        self.show_all()
        self.focus_bar.set_visible(bool(self.focus))
        GLib.idle_add(lambda: vadj.set_value(min(keep, max(0, vadj.get_upper() - vadj.get_page_size()))) and False)

    def _render_cleanup(self) -> None:
        requested = io.load_delete_requests(self.home)
        rows = view.cleanup_list(self.index, requested)
        counts = view.cleanup_counts(self.index)
        parts = " · ".join(f"{t(view.CLEANUP_LABEL[k]).split(':')[0].split(',')[0]} {n}" for k, n in counts.items() if n)
        self._section(self.main, t("מומלץ למחיקה · {n}").format(n=len(rows)) + (f"   ({parts})" if parts else ""))
        self.main.pack_start(_label(t("הרשימה מחושבת מחדש בכל סריקה. \"השאר\" מוציא שיחה מהרשימה לתמיד; "
                                      "\"מחק\" מאשר מחיקה, שסשן Claude מבצע באפליקציה."), css=("mishlat-dim",), wrap=True),
                             False, False, 0)
        bar = Gtk.Box(spacing=8)
        approve_all = Gtk.Button(label=t("אשר הכול ({n})").format(n=len(rows)))
        approve_all.set_sensitive(bool(rows))
        approve_all.connect("clicked", lambda *_: self._request_delete(rows))
        bar.pack_start(approve_all, False, False, 0)
        bar.pack_start(_label(t("מאושרות למחיקה, ממתינות לביצוע: {n}").format(n=len(requested)), css=("mishlat-dim",)),
                       False, False, 0)
        if requested:
            how = Gtk.Button(label=t("איך מבצעים?"))
            how.connect("clicked", lambda *_: self._message(
                t("בכל סשן Claude כתוב: \"תמחק את השיחות שאישרתי במשלט\".\n"
                  "הסשן מריץ `mishlat cleanup --json` ומוחק כל שיחה דרך האפליקציה, שמבקשת אישור לכל אחת.\n"
                  "בסריקה הבאה השיחות שנמחקו יוצאות מהרשימה.")))
            bar.pack_start(how, False, False, 0)
        self.main.pack_start(bar, False, False, 4)
        for s in rows:
            self.main.pack_start(self._cleanup_row(s), False, False, 0)

    def _cleanup_row(self, s: dict) -> Gtk.Widget:
        ev = _hover(Gtk.EventBox(), hand=True)
        ev.get_style_context().add_class("mishlat-row")
        grid = Gtk.Grid(column_spacing=8, row_spacing=2)
        grid.attach(_glyph(s["state"]), 0, 0, 1, 1)
        title = _label(view.auto(s["title"]), css=("mishlat-link", "mishlat-title"), ellipsize=True, max_chars=48)
        title.set_hexpand(True)
        grid.attach(title, 1, 0, 1, 1)
        age = Gtk.Box(spacing=6)
        age.pack_start(_open_hint(), False, False, 0)
        age.pack_start(_label(view.format_age(s["last_activity"], now_ms()), css=("mishlat-dim",)), False, False, 0)
        grid.attach(age, 2, 0, 1, 1)
        btns = Gtk.Box(spacing=4)
        delete = Gtk.Button(label=t("מחק"))
        delete.connect("clicked", lambda *_: self._request_delete([s]))
        keep = Gtk.Button(label=t("השאר"))
        keep.connect("clicked", lambda *_: self._keep(s))
        btns.pack_start(delete, False, False, 0)
        btns.pack_start(keep, False, False, 0)
        grid.attach(btns, 3, 0, 1, 2)
        line = Gtk.Box(spacing=6)
        name = view.project_names(self.index).get(s["project"], "")
        line.pack_start(_label(os.path.basename(name) or name, css=("mishlat-tag",)), False, False, 0)
        line.pack_start(_label(view.cleanup_reason_text(s, now_ms()), css=("mishlat-warn",), ellipsize=True), True, True, 0)
        grid.attach(line, 1, 1, 2, 1)
        ev.add(grid)
        ev.set_tooltip_text(self._tooltip(s))
        ev.connect("button-press-event", self._on_session_press, s)
        self.shown_sessions.append(s["id"])
        return ev

    def _request_delete(self, sessions: list[dict]) -> None:
        io.request_delete(self.home, sessions, now_ms())
        self.render(force=True)

    def _keep(self, s: dict) -> None:
        io.keep(self.home, s["id"], now_ms())
        self._request_scan()
        self.render(force=True)

    def _update_status(self) -> None:
        self.status.set_text(view.status_text(self.index, now_ms(), self.scanning))
        errors = (self.index or {}).get("errors") or []
        self.status.set_tooltip_text("\n".join(errors) if errors else None)

    def _section(self, box: Gtk.Box, text: str) -> None:
        box.pack_start(_label(text, css=("mishlat-section",)), False, False, 4)

    def _render_side(self) -> None:
        secs = view.sections(self.index)
        if not secs:
            self.side.pack_start(_label(t("אין כרגע שיחות שמחכות לך"), css=("mishlat-dim",)), False, False, 0)
        for state, title, rows in secs:
            self._section(self.side, f"{t(title)} · {len(rows)}")
            for s in rows:
                self.side.pack_start(self._session_row(s, True, self.side_sessions), False, False, 0)

    def _render_search(self) -> None:
        projects, sessions = search(self.index, self.query)
        self._render_cards(projects[:12], title=t("פרויקטים · {n}").format(n=len(projects)), expand_all=True)
        self._section(self.main, t("שיחות · {n}").format(n=len(sessions)))
        for s in sessions:
            self.main.pack_start(self._session_row(s, True, self.shown_sessions), False, False, 0)

    def _render_cards(self, projects: list[dict], title: str | None = None, expand_all: bool = False) -> None:
        if title:
            self._section(self.main, title)
        if not projects:
            self.main.pack_start(_label(t("אין פרויקטים להצגה"), css=("mishlat-dim",)), False, False, 0)
            return
        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(False)
        flow.set_max_children_per_line(6)
        flow.set_min_children_per_line(1)
        flow.set_column_spacing(14)
        flow.set_row_spacing(14)
        flow.set_valign(Gtk.Align.START)
        for p in projects:
            flow.add(self._card(p, expand_all or p["key"] in self.expanded))
            self.shown_cards.append(p["key"])
        self.main.pack_start(flow, False, False, 0)

    def _card(self, p: dict, expanded: bool) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box.set_size_request(CARD_WIDTH, -1)
        head = _hover(Gtk.EventBox())
        head_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        head_box.pack_start(_label(t(p["name"]) if p.get("general") else p["name"], css=("mishlat-name",), ellipsize=True,
                                   max_chars=CARD_CHARS),
                            False, False, 0)
        where = p["path"] or p["key"]
        where_text = t("שיחות בלי תיקייה קיימת") if p.get("general") else view.ltr(view.tilde(where, self.home))
        head_box.pack_start(_label(where_text, css=("mishlat-dim",), ellipsize=True, max_chars=CARD_CHARS),
                            False, False, 0)
        if p.get("description"):
            head_box.pack_start(_label(view.auto(p["description"]), css=("mishlat-purpose",), wrap=True,
                                       max_chars=CARD_CHARS), False, False, 2)
        note = view.project_note(p, self.home)
        if note:
            note_label = _label(note, css=("mishlat-warn",), wrap=True, max_chars=CARD_CHARS)
            head_box.pack_start(note_label, False, False, 0)
        badges = Gtk.Box(spacing=4)
        for text, state in view.project_badges(p):
            lab = _label(markup=(f'<span foreground="{view.COLOR[state]}">{GLib.markup_escape_text(text)}</span>'
                                 if state else GLib.markup_escape_text(text)), css=("mishlat-badge",))
            badges.pack_start(lab, False, False, 0)
        if p["path"]:
            new_task = Gtk.Button(label=t("+ משימה חדשה"))
            new_task.set_relief(Gtk.ReliefStyle.NONE)
            new_task.get_style_context().add_class("mishlat-newtask")
            new_task.set_tooltip_text(t("פותח שיחת Claude חדשה בתיקייה הזו, באפליקציה"))
            new_task.connect("clicked", lambda *_, path=p["path"]: actions.new_session_in(path))
            badges.pack_end(new_task, False, False, 0)
            self.new_task_buttons[p["key"]] = new_task
        head_box.pack_start(badges, False, False, 2)
        head.add(head_box)
        tip = [t("לחיצה פותחת או מקפלת את רשימת השיחות · לחיצה ימנית לעוד פעולות")]
        if p.get("description"):
            tip.insert(0, p["description"] + (t(" (מתוך README)") if p.get("description_source") == "readme" else ""))
        head.set_tooltip_text("\n".join(tip))
        head.connect("button-press-event", self._on_card_press, p)
        box.pack_start(head, False, False, 0)
        rows = p["sessions"] if expanded else p["sessions"][:CARD_ROWS]
        for s in rows:
            box.pack_start(self._session_line(s, detailed=expanded), False, False, 0)
        more = len(p["sessions"]) - len(rows)
        if more > 0 or (expanded and len(p["sessions"]) > CARD_ROWS):
            toggle = _hover(Gtk.EventBox())
            toggle.add(_label(t("עוד {n} שיחות…").format(n=more) if more > 0 else t("קפל"), css=("mishlat-dim",)))
            toggle.connect("button-press-event", lambda w, e, key=p["key"]: self._toggle(key) or True)
            box.pack_start(toggle, False, False, 0)
        card = Gtk.EventBox()
        card.get_style_context().add_class("mishlat-card")
        edge = view.project_edge(p)
        if edge:
            card.get_style_context().add_class(f"mishlat-edge-{edge}")
        _hover(card)
        card.add(box)
        return card

    def _session_line(self, s: dict, detailed: bool) -> Gtk.Widget:
        """A compact row inside a card: a link to the conversation."""
        ev = _hover(Gtk.EventBox(), hand=True)
        ev.get_style_context().add_class("mishlat-line")
        grid = Gtk.Grid(column_spacing=6, row_spacing=1)
        grid.attach(_glyph(s["state"]), 0, 0, 1, 1)
        title = _label(view.auto(s["title"]), css=("mishlat-link", "mishlat-title"), ellipsize=True, max_chars=CARD_CHARS)
        title.set_hexpand(True)
        grid.attach(title, 1, 0, 1, 1)
        age = Gtk.Box(spacing=6)
        age.pack_start(_open_hint(), False, False, 0)
        age.pack_start(_label(view.short_age(s["last_activity"], now_ms()), css=("mishlat-dim",)), False, False, 0)
        grid.attach(age, 2, 0, 1, 1)
        sub = view.subline(s)
        if sub and (detailed or s["state"] != "idle"):
            css = ("mishlat-question",) if s["state"] == "waiting" else ("mishlat-dim",)
            grid.attach(_label(sub, css=css, ellipsize=True, max_chars=CARD_CHARS), 1, 1, 2, 1)
        ev.add(grid)
        ev.set_tooltip_text(self._tooltip(s))
        ev.connect("button-press-event", self._on_session_press, s)
        self.shown_sessions.append(s["id"])
        return ev

    def _session_row(self, s: dict, show_project: bool, record: list) -> Gtk.Widget:
        """A full row: the attention column, search results, the stale list. A link to the conversation."""
        ev = _hover(Gtk.EventBox(), hand=True)
        ev.get_style_context().add_class("mishlat-row")
        grid = Gtk.Grid(column_spacing=8, row_spacing=2)
        grid.attach(_glyph(s["state"]), 0, 0, 1, 1)
        title = _label(view.auto(s["title"]), css=("mishlat-link", "mishlat-title"), ellipsize=True, max_chars=ROW_CHARS)
        title.set_hexpand(True)
        grid.attach(title, 1, 0, 1, 1)
        age = Gtk.Box(spacing=6)
        age.pack_start(_open_hint(), False, False, 0)
        age.pack_start(_label(view.format_age(s["last_activity"], now_ms()), css=("mishlat-dim",)), False, False, 0)
        grid.attach(age, 2, 0, 1, 1)
        line = Gtk.Box(spacing=6)
        if show_project:
            name = view.project_names(self.index).get(s["project"], "")
            line.pack_start(_label(os.path.basename(name) or name, css=("mishlat-tag",)), False, False, 0)
        css = ("mishlat-question",) if s["state"] == "waiting" else ("mishlat-dim",)
        line.pack_start(_label(view.auto(view.subline(s)), css=css, ellipsize=True, max_chars=ROW_CHARS),
                        True, True, 0)
        grid.attach(line, 1, 1, 2, 1)
        ev.add(grid)
        ev.set_tooltip_text(self._tooltip(s))
        ev.connect("button-press-event", self._on_session_press, s)
        record.append(s["id"])
        return ev

    def _tooltip(self, s: dict) -> str:
        parts = [s["title"], t(view.STATE_LABEL[s["state"]])]
        sub = view.subline(s)
        if sub:
            parts.append(sub)
        if s.get("project") == "general" and s.get("cwd"):
            parts.append(t("תיקייה מקורית: {folder}").format(folder=view.ltr(view.tilde(s["cwd"], self.home))))
        started = view.started_line(s, view.project_names(self.index or {}), self.home)
        if started:
            parts.append(started + (t(" · שויכה ידנית") if s.get("assigned") else t(" · שויכה לפי העבודה בה")))
        elif s.get("assigned"):
            parts.append(t("שויכה ידנית"))
        parts.append(t("לחיצה פותחת באפליקציה · לחיצה ימנית לעוד פעולות"))
        return "\n".join(parts)

    # ── events ──
    def _toggle(self, key: str) -> None:
        self.expanded.symmetric_difference_update({key})
        self.render(force=True)

    def _on_chip(self, chip: Gtk.RadioButton, mode: str) -> None:
        if chip.get_active() and mode != self.mode:
            self.mode = mode
            self.render(force=True)

    def _on_card_press(self, widget, event, p: dict) -> bool:
        if event.type != Gdk.EventType.BUTTON_PRESS:
            return True
        if event.button == 3:
            self._popup(self._project_menu(p), event)
        elif event.button == 1:
            self._toggle(p["key"])
        return True

    def _on_session_press(self, widget, event, s: dict) -> bool:
        if event.type != Gdk.EventType.BUTTON_PRESS:
            return True
        if event.button == 3:
            self._popup(self._session_menu(s), event)
        elif event.button == 1:
            actions.open_session(s)
        return True

    def _on_key(self, widget, event) -> bool:
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        if ctrl and event.keyval in (Gdk.KEY_f, Gdk.KEY_F):
            self.search.grab_focus()
            return True
        if ctrl and event.keyval in (Gdk.KEY_r, Gdk.KEY_R):
            self._request_scan()
            return True
        if ctrl and event.keyval in (Gdk.KEY_plus, Gdk.KEY_equal, Gdk.KEY_KP_Add):
            self.set_font(self.font_px + FONT_STEP)
            return True
        if ctrl and event.keyval in (Gdk.KEY_minus, Gdk.KEY_KP_Subtract):
            self.set_font(self.font_px - FONT_STEP)
            return True
        if ctrl and event.keyval in (Gdk.KEY_0, Gdk.KEY_KP_0):
            self.set_font(io.FONT_DEFAULT)
            return True
        if ctrl and event.keyval == Gdk.KEY_comma:
            self._settings()
            return True
        if ctrl and event.keyval in (Gdk.KEY_l, Gdk.KEY_L):
            self.set_language("en" if lang() == "he" else "he")
            return True
        if event.keyval == Gdk.KEY_Escape:
            if self.search.get_text():
                self.search.set_text("")
            elif self.focus:
                self.show_project(None)
            else:
                self.hide()
            return True
        return False

    def _popup(self, menu: Gtk.Menu, event) -> None:
        menu.attach_to_widget(self, None)
        menu.show_all()
        menu.popup_at_pointer(event)

    def _item(self, menu: Gtk.Menu, text: str, fn) -> None:
        item = Gtk.MenuItem(label=text)
        item.connect("activate", lambda *_: fn())
        menu.append(item)

    def _project_path(self, s: dict) -> str | None:
        p = next((p for p in self.index["projects"] if p["key"] == s["project"]), None)
        return p["path"] if p else None

    def _session_menu(self, s: dict) -> Gtk.Menu:
        menu = Gtk.Menu()
        self._item(menu, t("פתח באפליקציה"), lambda: actions.open_session(s))
        if s.get("cli_id"):
            self._item(menu, t("המשך בטרמינל"), lambda: self._resume(s))
        path = self._project_path(s)
        if path:
            self._item(menu, t("פתח את התיקייה"), lambda: actions.open_folder(path))
        self._item(menu, t("העתק את מזהה השיחה"), lambda: self._copy(s["cli_id"] or s["id"]))
        menu.append(Gtk.SeparatorMenuItem())
        self._item(menu, t("שייך לפרויקט…"), lambda: self._assign(s))
        if s.get("assigned"):
            self._item(menu, t("החזר לשיוך האוטומטי"), lambda: self._unassign(s))
        if s.get("attention"):
            menu.append(Gtk.SeparatorMenuItem())
            self._item(menu, t("הסתר מרשימת \"מחכים לך\""), lambda: self._dismiss(s))
        return menu

    def _project_menu(self, p: dict) -> Gtk.Menu:
        menu = Gtk.Menu()
        if p["path"]:
            self._item(menu, t("פתח את התיקייה"), lambda: actions.open_folder(p["path"]))
            self._item(menu, t("משימה חדשה כאן"), lambda: actions.new_session_in(p["path"]))
            self._item(menu, t("העתק את הנתיב"), lambda: self._copy(p["path"]))
        self._item(menu, t("הצג רק את הפרויקט הזה"), lambda: self.show_project(p["path"] or p["key"]))
        if p["path"]:
            menu.append(Gtk.SeparatorMenuItem())
            self._item(menu, t("תאר את התיקייה…"), lambda: self._describe(p))
            if p.get("description_source") == "user":
                self._item(menu, t("מחק את התיאור שלי"), lambda: self._set_description(p["path"], None, False))
        return menu

    def _describe(self, p: dict) -> None:
        """A dialog: one line that says what the folder is for; optionally written as its README.md."""
        dialog = Gtk.Dialog(title=t("ייעוד התיקייה"), transient_for=self, modal=True)
        dialog.add_buttons(t("ביטול"), Gtk.ResponseType.CANCEL, t("שמור"), Gtk.ResponseType.OK)
        dialog.set_default_size(520, -1)
        box = dialog.get_content_area()
        box.set_spacing(8)
        box.set_border_width(12)
        box.pack_start(_label(t("מה יש בתיקייה {folder}?").format(folder=view.ltr(view.tilde(p["path"], self.home))), wrap=True),
                       False, False, 0)
        entry = Gtk.Entry()
        entry.set_text(p.get("description") or "")
        entry.set_placeholder_text(t("למשל: ארכיון המאמרים של האתר, ייצוא מ-17.10, בלי קוד"))
        entry.set_activates_default(True)
        box.pack_start(entry, False, False, 0)
        has_readme = readme_path(p["path"]) is not None
        check = Gtk.CheckButton(label=t("כתוב גם README.md בתיקייה, כדי שהייעוד יישאר איתה"))
        check.set_active(not has_readme)
        check.set_sensitive(not has_readme)
        if has_readme:
            check.set_tooltip_text(t("לתיקייה כבר יש README; משלט לא משנה אותו"))
        box.pack_start(check, False, False, 0)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()
        answer = dialog.run()
        text, write = entry.get_text().strip(), check.get_active() and not has_readme
        dialog.destroy()
        if answer == Gtk.ResponseType.OK:
            self._set_description(p["path"], text or None, write)

    def _set_description(self, path: str, text: str | None, write_file: bool) -> None:
        io.describe(self.home, path, text)
        if text and write_file:
            try:
                write_readme(path, text)
            except OSError as exc:
                self._message(t("לא הצלחתי לכתוב README.md בתיקייה: {err}").format(err=exc))
        self._request_scan()

    def _resume(self, s: dict) -> None:
        err = actions.resume_in_terminal(s, self._project_path(s), self.home)
        if err:
            self._message(err)

    def _copy(self, text: str) -> None:
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(text, -1)

    def _assign(self, s: dict) -> None:
        path = self._pick_project(s)
        if path:
            io.assign(self.home, s["id"], path)
            self._request_scan()

    def _unassign(self, s: dict) -> None:
        io.assign(self.home, s["id"], None)
        self._request_scan()

    def _pick_project(self, s: dict) -> str | None:
        """A dialog: the project list (with a filter box), or any folder through a chooser."""
        choices = view.assign_choices(self.index or {})
        dialog = Gtk.Dialog(title=t("שייך לפרויקט"), transient_for=self, modal=True)
        dialog.add_buttons(t("ביטול"), Gtk.ResponseType.CANCEL, t("שייך"), Gtk.ResponseType.OK)
        dialog.set_default_size(460, 520)
        box = dialog.get_content_area()
        box.set_spacing(6)
        box.set_border_width(10)
        box.pack_start(_label(t("לאיזה פרויקט שייכת השיחה \"{title}\"?").format(title=s["title"]), wrap=True, max_chars=50),
                       False, False, 0)
        entry = Gtk.SearchEntry()
        box.pack_start(entry, False, False, 0)
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        for name, path in choices:
            row = Gtk.ListBoxRow()
            line = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1, margin=4)
            line.pack_start(_label(name, css=("mishlat-name",)), False, False, 0)
            line.pack_start(_label(view.ltr(view.tilde(path, self.home)), css=("mishlat-dim",)), False, False, 0)
            row.add(line)
            listbox.add(row)
        texts = [f"{n} {p}".casefold() for n, p in choices]
        listbox.set_filter_func(lambda row: entry.get_text().casefold() in texts[row.get_index()])
        entry.connect("search-changed", lambda *_: listbox.invalidate_filter())
        listbox.connect("row-activated", lambda *_: dialog.response(Gtk.ResponseType.OK))
        scroll = Gtk.ScrolledWindow()
        scroll.add(listbox)
        box.pack_start(scroll, True, True, 0)
        chosen: list[str] = []

        def other_folder(*_):
            chooser = Gtk.FileChooserDialog(title=t("בחר תיקייה"), transient_for=dialog,
                                            action=Gtk.FileChooserAction.SELECT_FOLDER)
            chooser.add_buttons(t("ביטול"), Gtk.ResponseType.CANCEL, t("בחר"), Gtk.ResponseType.OK)
            chooser.set_current_folder(os.path.join(self.home, "Desktop"))
            if chooser.run() == Gtk.ResponseType.OK and chooser.get_filename():
                chosen.append(chooser.get_filename())
                dialog.response(Gtk.ResponseType.OK)
            chooser.destroy()
        other = Gtk.Button(label=t("תיקייה אחרת…"))
        other.connect("clicked", other_folder)
        box.pack_start(other, False, False, 0)
        dialog.show_all()
        answer = dialog.run()
        row = listbox.get_selected_row()
        path = chosen[0] if chosen else (choices[row.get_index()][1] if row is not None else None)
        dialog.destroy()
        return path if answer == Gtk.ResponseType.OK else None

    def _dismiss(self, s: dict) -> None:
        io.dismiss(self.home, s["id"], s["last_activity"])
        self._request_scan()

    def _message(self, text: str) -> None:
        dialog = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.WARNING,
                                   buttons=Gtk.ButtonsType.OK, text=text)
        dialog.run()
        dialog.destroy()

    def _request_scan(self) -> None:
        if self.app is not None and hasattr(self.app, "request_scan"):
            self.app.request_scan()
