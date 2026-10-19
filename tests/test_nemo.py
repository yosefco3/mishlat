import importlib.util
import json
import os
import time
import unittest

from tests.helpers import FakeHome

os.environ["MISHLAT_FM_NO_GI"] = "1"
_spec = importlib.util.spec_from_file_location(
    "mishlat_fm", os.path.join(os.path.dirname(__file__), "..", "extension", "mishlat_fm.py"))
nemo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nemo)

D = "/h/Desktop"


def project(path, n=1, attention=0, working=0):
    return {"path": path, "sessions": [{}] * n, "attention": attention, "working": working}


class MarksTest(unittest.TestCase):
    def test_projects_parents_and_roots(self):
        marks = nemo.build_marks({"roots": [D], "projects": [
            project(f"{D}/shedu", 8, attention=1, working=1),
            project(f"{D}/trading/prop", 17, attention=2),
            project(f"{D}/trading/scalp", 4),
            project(None, 3),                       # a lost folder: no mark
            project(f"{D}/apps/appx", 0),       # a repo with no session: no mark
            project("/srv/other", 2),               # outside the roots: its own mark, no parents
        ]})
        self.assertEqual(marks[f"{D}/shedu"].label(), "⁦8 · ◐1 ●1⁩")
        self.assertEqual(marks[f"{D}/shedu"].emblem(), nemo.EMBLEM_ATTENTION)
        self.assertEqual(marks[f"{D}/trading"].label(), "⁦21 · ◐2⁩ · 2 פרויקטים")
        self.assertIsNone(marks[f"{D}/trading/scalp"].emblem())
        self.assertNotIn(D, marks)
        self.assertNotIn(f"{D}/apps", marks)
        self.assertIn("/srv/other", marks)
        self.assertNotIn("/srv", marks)

    def test_working_emblem_and_menu_labels(self):
        m = nemo.Mark(is_project=True)
        m.add(project("/x", 2, working=1))
        self.assertEqual(m.emblem(), nemo.EMBLEM_WORKING)
        self.assertEqual(nemo.menu_labels(m, "he")[0], "שיחות Claude של התיקייה (2)…")
        self.assertEqual(nemo.menu_labels(None, "en")[0], "Claude sessions of this folder (0)…")
        self.assertEqual(nemo.build_marks({"roots": ["/h"], "projects": [project("/h/a/b", 1), project("/h/a/c", 1)]}, "en")["/h/a"].label(),
                         "\u20662\u2069 · 2 projects")
        self.assertEqual(nemo.ui_lang("/nonexistent", {"LANG": "en_US.UTF-8"}), "en")
        self.assertEqual(nemo.ui_lang("/nonexistent", {"LANG": "he_IL.UTF-8"}), "he")


class CacheTest(unittest.TestCase):
    def test_reload_only_on_change_and_changed_paths(self):
        home = FakeHome()
        try:
            path = home.path("index.json")
            cache = nemo.IndexCache(path)
            self.assertEqual(cache.reload(), None)  # no file, nothing changed from "nothing"
            with open(path, "w") as f:
                json.dump({"roots": [D], "projects": [project(f"{D}/a", 1), project(f"{D}/b", 2)]}, f)
            self.assertEqual(cache.reload(), {f"{D}/a", f"{D}/b"})
            self.assertIsNone(cache.reload())
            with open(path, "w") as f:
                json.dump({"roots": [D], "projects": [project(f"{D}/a", 1, attention=1), project(f"{D}/b", 2)]}, f)
            os.utime(path, (time.time() + 5, time.time() + 5))
            self.assertEqual(cache.reload(), {f"{D}/a"})
            self.assertEqual(cache.get(f"{D}/a/").attention, 1)
            with open(path, "w") as f:
                f.write("{half")
            os.utime(path, (time.time() + 9, time.time() + 9))
            self.assertEqual(cache.reload(), set())  # a broken file keeps the old marks
            self.assertIsNotNone(cache.get(f"{D}/b"))
        finally:
            home.cleanup()


if __name__ == "__main__":
    unittest.main()
