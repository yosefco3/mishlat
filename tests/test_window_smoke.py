import os
import unittest

from tests.helpers import FakeHome
from tests.test_model_index import D, NOW, build, folders, rec, tx
from mishlat.live import Live
from mishlat.model import DAY_MS
from mishlat.transcripts import encode_path

HAS_DISPLAY = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def sample_index():
    book, shedu = f"{D}/book", f"{D}/shedu"
    working = [{"content": "a", "status": "completed"}, {"content": "Build it", "status": "in_progress"}]
    return build([rec("local_w", shedu, "c1", title="עבודה"),
                  rec("local_q", book, "c2", title="תיקון פרק 4", status="blocked", question="איזה פתיח?"),
                  rec("local_old", book, "c3", title="ישן", last=NOW - 60 * DAY_MS)],
                 {"c1": tx(encode_path(shedu), last_write=NOW - 500, plan=working)},
                 live={"c1": Live(1, "c1", "/w", None, None, 0)},
                 fi=folders(book, shedu), existing={book, shedu})


@unittest.skipUnless(HAS_DISPLAY, "needs a display")
class WindowSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
        import mishlat.window as window
        cls.Gtk, cls.window = Gtk, window
        window.now_ms = lambda: NOW
        Gtk.Widget.set_default_direction(Gtk.TextDirection.RTL)

    def setUp(self):
        self.home = FakeHome()
        self.w = self.window.MishlatWindow(None, self.home.root)
        self.index = sample_index()

    def tearDown(self):
        self.w.destroy()
        self.home.cleanup()

    def test_home_view_cards_and_attention_column(self):
        self.w.set_index(self.index)
        self.assertEqual(self.w.shown_cards, [f"{D}/shedu", f"{D}/book"])
        self.assertEqual(self.w.side_sessions, ["local_q", "local_w"])  # waiting, then working
        self.assertIn("נסרק", self.w.status.get_text())

    def test_new_task_button_on_folder_cards(self):
        general = build([rec("local_g", f"{D}/gone", "c9", title="ללא תיקייה")], existing=set())
        self.w.set_index(self.index)
        self.assertEqual(set(self.w.new_task_buttons), {f"{D}/shedu", f"{D}/book"})
        started = []
        self.window.actions.new_session_in = lambda path: started.append(path)
        self.w.new_task_buttons[f"{D}/book"].clicked()
        self.assertEqual(started, [f"{D}/book"])
        self.assertEqual(self.w.shown_cards, [f"{D}/shedu", f"{D}/book"])   # the click did not toggle the card
        self.w.set_index(general)
        self.assertEqual(self.w.new_task_buttons, {})                          # General has no folder

    def test_apply_settings_saves_and_rescans(self):
        import mishlat.index as io
        from mishlat.strings import EN
        from mishlat.window import NOTIFY_CHOICES

        class App:
            scans = 0

            def request_scan(self):
                self.scans += 1
        self.w.app = App()
        self.w.apply_settings({"notify": "off", "old_days": 7})
        saved = io.load_settings(self.home.root)
        self.assertEqual((saved["notify"], saved["old_days"]), ("off", 7))
        self.assertEqual(self.w.app.scans, 1)
        self.w.apply_settings({"notify": "off", "old_days": 7})   # nothing changed: no scan
        self.assertEqual(self.w.app.scans, 1)
        for _, text in NOTIFY_CHOICES:                              # every choice has English
            self.assertIn(text, EN)
        dialog, combo, days = self.w.settings_dialog({"notify": "all", "old_days": 45})
        self.assertEqual((combo.get_active_id(), days.get_value()), ("all", 45))
        dialog.destroy()

    def test_search_stale_focus_and_empty(self):
        self.w.set_index(self.index)
        self.w.set_query("פרק 4")
        self.assertEqual(self.w.shown_sessions[-1:], ["local_q"])
        self.w.set_query("")
        self.w.set_mode("stale")
        self.assertEqual(self.w.shown_sessions, ["local_old"])
        self.assertIn("(1)", self.w.chips["stale"].get_label())
        self.w.set_mode("all")
        self.w.show_project(f"{D}/book")
        self.assertEqual(self.w.shown_cards, [f"{D}/book"])
        self.assertIn(f"{D}/book", self.w.expanded)
        self.w.show_project(None)
        self.assertEqual(len(self.w.shown_cards), 2)
        self.w.set_index(None)
        self.assertEqual(self.w.shown_cards, [])

    def test_cleanup_mode_keep_and_delete(self):
        from mishlat import index as io
        from mishlat.model import mark_cleanup
        mark_cleanup(self.index, NOW, 30)
        self.w.set_index(self.index)
        self.w.set_mode("cleanup")
        self.assertEqual(self.w.shown_sessions, ["local_old"])          # the only old, non-newest session
        self.assertIn("(1)", self.w.chips["cleanup"].get_label())
        old = next(s for p in self.index["projects"] for s in p["sessions"] if s["id"] == "local_old")
        self.w._request_delete([old])
        self.assertEqual(list(io.load_delete_requests(self.home.root)), ["local_old"])
        self.assertEqual(self.w.shown_sessions, [])                     # approved rows leave the list
        self.w._keep(old)
        self.assertEqual(list(io.load_keep(self.home.root)), ["local_old"])

    def test_font_scale_is_saved(self):
        from mishlat import index as io
        self.w.set_index(self.index)
        self.w.set_font(self.w.font_px + 2)
        self.assertEqual(io.load_settings(self.home.root)["font_px"], io.FONT_DEFAULT + 2)
        self.w.set_font(io.FONT_MAX + 5)
        self.assertEqual(self.w.font_px, io.FONT_MAX)

    def test_describe_sets_text_and_writes_readme_once(self):
        from mishlat import index as io
        from mishlat.describe import readme_path
        folder = self.home.mkdir("Desktop/archive")
        self.w.set_index(self.index)
        self.w._set_description(folder, "ארכיון של האתר", True)
        self.assertEqual(io.load_descriptions(self.home.root), {folder: "ארכיון של האתר"})
        with open(readme_path(folder), encoding="utf-8") as f:
            self.assertIn("ארכיון של האתר", f.read())
        self.w._set_description(folder, "שינוי", True)             # README exists: not touched
        with open(readme_path(folder), encoding="utf-8") as f:
            self.assertNotIn("שינוי", f.read())
        self.w._set_description(folder, None, False)
        self.assertEqual(io.load_descriptions(self.home.root), {})
        p = dict(self.index["projects"][0], description="A purpose line", description_source="readme")
        menu = self.w._project_menu(p)
        self.assertIn("תאר את התיקייה…", [i.get_label() for i in menu.get_children() if i.get_label()])

    def test_menus_build(self):
        self.w.set_index(self.index)
        s = dict(self.index["projects"][1]["sessions"][0], started_in=f"{D}/shedu", assigned=True)
        menu = self.w._session_menu(s)  # keep it: a freed menu takes its items' labels with it
        labels = [i.get_label() for i in menu.get_children() if i.get_label()]
        self.assertIn("שייך לפרויקט…", labels)
        self.assertIn("החזר לשיוך האוטומטי", labels)
        self.assertIn("התחילה ב־", self.w._tooltip(s))
        self.assertIn("שויכה ידנית", self.w._tooltip(s))
        self.assertGreaterEqual(len(self.w._project_menu(self.index["projects"][0]).get_children()), 3)


if __name__ == "__main__":
    unittest.main()
