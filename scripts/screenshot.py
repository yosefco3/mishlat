#!/usr/bin/env python3
"""Render the window offscreen on the demo home, in both languages, into docs/screenshots/.
No window appears on screen and nothing of the user's own data is read."""

from __future__ import annotations

import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "docs", "screenshots")
SHOTS = (("home", ""), ("search", "q:chapter"), ("cleanup", "m:cleanup"))


def main() -> int:
    sys.path.insert(0, REPO)
    home = subprocess.run([sys.executable, os.path.join(HERE, "demo_home.py")], capture_output=True, text=True,
                          check=True).stdout.strip()
    os.environ["MISHLAT_HOME"] = home
    os.environ["MISHLAT_PROC_ROOT"] = os.path.join(home, "_proc")
    os.makedirs(OUT, exist_ok=True)
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
    from mishlat.scan import Scanner
    from mishlat.strings import is_rtl, set_lang
    from mishlat.window import MishlatWindow, install_css

    index = Scanner(home).scan()
    for lang in ("en", "he"):
        os.environ["MISHLAT_LANG"] = lang
        set_lang(lang)
        Gtk.Widget.set_default_direction(Gtk.TextDirection.RTL if is_rtl() else Gtk.TextDirection.LTR)
        install_css(15)
        for name, mode in SHOTS:
            w = MishlatWindow(None, home)
            w.set_index(index)
            if mode.startswith("q:"):
                w.search.set_text(mode[2:])
                w.set_query(mode[2:])
            elif mode.startswith("m:"):
                w.set_mode(mode[2:])
            content = w.get_child()
            w.remove(content)
            content.set_size_request(1320, 760)
            off = Gtk.OffscreenWindow()
            off.add(content)
            off.show_all()
            w.focus_bar.set_visible(False)
            for _ in range(2):  # the search box reports its text late; show whatever a late render added
                end = time.time() + 0.5
                while time.time() < end:
                    while Gtk.events_pending():
                        Gtk.main_iteration_do(False)
                    time.sleep(0.02)
                off.show_all()
                w.focus_bar.set_visible(False)
            path = os.path.join(OUT, f"{name}-{lang}.png")
            off.get_pixbuf().savev(path, "png", [], [])
            off.destroy()
            w.destroy()
            print("wrote", os.path.relpath(path, REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
