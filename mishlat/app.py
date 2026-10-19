"""The Mishlat process: one per login session. It owns the scanner, the tray, the notifications
and the window. A second launch (the hotkey, the Nemo menu, the menu entry) hands its arguments to
the first through Gtk.Application and exits."""

from __future__ import annotations

import os
import sys
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from . import actions, view  # noqa: E402
from . import index as io  # noqa: E402
from .scan import Scanner  # noqa: E402
from .strings import is_rtl, set_lang, t  # noqa: E402
from .tray import Notifier, Tray, icon_file, icons_dir, notification_text, to_notify  # noqa: E402
from .watcher import Coalescer, ScanRunner, SourceMonitor  # noqa: E402
from .window import MishlatWindow, install_css  # noqa: E402

APP_ID = "io.github.yosefco3.Mishlat"
COALESCE_MS = 2000
PERIODIC_S = 30  # "working" ends 90 s after the last write, with no file event to say so


def now_ms() -> int:
    return int(time.time() * 1000)


def warn(text: str) -> None:
    print(f"mishlat: {text}", file=sys.stderr)


class MishlatApp(Gtk.Application):
    def __init__(self, home: str) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.home = home
        self.index: dict | None = None
        self.previous: dict | None = None
        self.window: MishlatWindow | None = None
        self.runner: ScanRunner | None = None
        self.tray: Tray | None = None
        self.notifier: Notifier | None = None
        self.monitor: SourceMonitor | None = None

    # ── lifecycle ──
    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        settings = io.load_settings(self.home)
        set_lang(settings["lang"])
        Gtk.Widget.set_default_direction(Gtk.TextDirection.RTL if is_rtl() else Gtk.TextDirection.LTR)
        install_css(settings["font_px"])
        self.hold()  # keep running with no window: the tray
        self.index = io.read_index(self.home)  # show the last data at once
        scanner = Scanner(self.home)
        self.runner = ScanRunner(scanner.scan, self._on_scan, self._on_busy)
        try:
            self.tray = Tray(self.home, self._on_tray_action, self._open_session)
            self.tray.update(self.index, now_ms())
        except Exception as exc:  # no status-icon support: the window still works
            warn(f"no tray icon: {exc}")
        try:
            self.notifier = Notifier(icon_file(icons_dir(self.home), 0))
        except Exception as exc:
            warn(f"no notifications: {exc}")
        coalescer = Coalescer(self.runner.request, COALESCE_MS)
        self.monitor = SourceMonitor(self.home, coalescer.poke)
        try:
            self.monitor.start()
        except Exception as exc:
            warn(f"no file monitors, scanning every {PERIODIC_S} s only: {exc}")
        GLib.timeout_add_seconds(PERIODIC_S, lambda: self.runner.request() or True)
        self.runner.request()

    def do_command_line(self, cmd: Gio.ApplicationCommandLine) -> int:
        args = cmd.get_arguments()[1:]
        if "--quit" in args:
            self.quit()
        elif "--tray" in args:
            pass
        elif "--toggle" in args:
            self.toggle_window()
        elif "--project" in args:
            i = args.index("--project")
            path = args[i + 1] if i + 1 < len(args) else None
            if path and not os.path.isabs(path):
                path = os.path.join(cmd.get_cwd() or self.home, path)
            self.show_window()
            self.window.show_project(path)
        else:
            self.show_window()
        return 0

    # ── the window ──
    def show_window(self) -> None:
        if self.window is None:
            self.window = MishlatWindow(self, self.home)
            self.window.set_index(self.index)
            self.window.set_scanning(bool(self.runner and self.runner.busy))
        self.window.present()

    def toggle_window(self) -> None:
        if self.window is not None and self.window.get_visible() and self.window.is_active():
            self.window.hide()
        else:
            self.show_window()

    def request_scan(self) -> None:
        if self.runner is not None:
            self.runner.request()

    # ── scans ──
    def _on_busy(self, busy: bool) -> None:
        if self.window is not None:
            self.window.set_scanning(busy)

    def _on_scan(self, result) -> None:
        if isinstance(result, Exception):
            warn(f"scan failed: {result}")
            return
        index = result
        notify = to_notify(self.previous, index)
        self.previous = self.index = index
        if self.tray is not None:
            self.tray.update(index, now_ms())
        if self.window is not None:
            self.window.set_index(index)
        if self.notifier is not None:
            names = view.project_names(index)
            for s in notify:
                title, body = notification_text(s, names)
                self.notifier.notify(title, body, [
                    ("default", t("פתח"), lambda s=s: self._open_session(s)),
                    ("open", t("פתח"), lambda s=s: self._open_session(s)),
                    ("dismiss", t("הסתר"), lambda s=s: self._dismiss(s)),
                ])

    # ── tray and notification actions ──
    def _open_session(self, s: dict) -> None:
        actions.open_session(s)

    def _dismiss(self, s: dict) -> None:
        io.dismiss(self.home, s["id"], s["last_activity"])
        self.request_scan()

    def _on_tray_action(self, key: str) -> None:
        if key == "open":
            self.show_window()
        elif key == "scan":
            self.request_scan()
        elif key == "quit":
            self.quit()


def run_gui(home: str, argv: list[str]) -> int:
    return MishlatApp(home).run(argv)
