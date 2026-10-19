"""Keep the index live without polling 750 MB of transcripts: file monitors on the sources start
a scan, coalesced to at most one every 2 s, and each scan runs in a worker thread."""

from __future__ import annotations

import glob
import os
import threading

from . import paths


class Coalescer:
    """`poke()` many times; `fn` runs once, `delay_ms` after the first poke of a burst.
    (Not a trailing debounce: a session that writes every second still gets a scan every 2 s.)"""

    def __init__(self, fn, delay_ms: int, timeout_add=None) -> None:
        if timeout_add is None:
            from gi.repository import GLib
            timeout_add = GLib.timeout_add
        self.fn = fn
        self.delay_ms = delay_ms
        self._add = timeout_add
        self._pending = False

    def poke(self) -> None:
        if not self._pending:
            self._pending = True
            self._add(self.delay_ms, self._fire)

    def _fire(self) -> bool:
        self._pending = False
        self.fn()
        return False  # one-shot timer


class ScanRunner:
    """Runs `scan()` in a worker thread, one at a time. A request during a scan runs one more scan
    after it, not one per request. `on_done(result)` runs on the GTK loop; result may be an exception."""

    def __init__(self, scan, on_done, on_busy=None, start_thread=None, idle_add=None) -> None:
        if idle_add is None:
            from gi.repository import GLib
            idle_add = GLib.idle_add
        self.scan = scan
        self.on_done = on_done
        self.on_busy = on_busy or (lambda busy: None)
        self._start = start_thread or (lambda target: threading.Thread(target=target, name="mishlat-scan",
                                                                        daemon=True).start())
        self._idle_add = idle_add
        self.busy = False
        self._again = False
        self.count = 0

    def request(self) -> None:
        if self.busy:
            self._again = True
            return
        self.busy = True
        self.on_busy(True)
        self._start(self._work)

    def _work(self) -> None:
        try:
            result = self.scan()
        except Exception as exc:  # reported, never raised into the thread
            result = exc
        self._idle_add(self._finish, result)

    def _finish(self, result) -> bool:
        self.busy = False
        self.count += 1
        self.on_busy(False)
        self.on_done(result)
        if self._again:
            self._again = False
            self.request()
        return False


def watched_dirs(home: str) -> list[str]:
    """The folders whose changes can change the index."""
    out = [d for pattern in paths.STORE_GLOBS
           for d in glob.glob(os.path.join(home, os.path.dirname(pattern))) if os.path.isdir(d)]
    out.append(os.path.join(home, paths.LIVE_DIR))
    projects = os.path.join(home, paths.PROJECTS_DIR)
    out.append(projects)
    out += [d for d in glob.glob(os.path.join(projects, "*")) if os.path.isdir(d)]
    out.append(paths.config_dir(home))
    return out


class SourceMonitor:
    """Gio directory monitors on `watched_dirs`. A new project folder gets a monitor when it appears."""

    def __init__(self, home: str, on_change) -> None:
        self.home = home
        self.on_change = on_change
        self.projects = os.path.join(home, paths.PROJECTS_DIR)
        self._monitors: dict = {}

    def start(self) -> int:
        for d in watched_dirs(self.home):
            self.watch(d)
        return len(self._monitors)

    def watch(self, d: str) -> None:
        if d in self._monitors or not os.path.isdir(d):
            return
        from gi.repository import Gio
        monitor = Gio.File.new_for_path(d).monitor_directory(Gio.FileMonitorFlags.NONE, None)
        monitor.connect("changed", self._changed)
        self._monitors[d] = monitor

    def _changed(self, monitor, file, other, event) -> None:
        from gi.repository import Gio
        path = file.get_path() if file is not None else None
        if (event == Gio.FileMonitorEvent.CREATED and path and os.path.isdir(path)
                and os.path.dirname(path) == self.projects):
            self.watch(path)
        self.on_change()
