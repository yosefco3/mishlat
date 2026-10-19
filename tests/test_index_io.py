import os
import stat
import unittest

from mishlat import index as io
from mishlat import paths
from tests.helpers import FakeHome


class IndexIoTest(unittest.TestCase):
    def setUp(self):
        self.home = FakeHome()
        self.h = self.home.root

    def tearDown(self):
        self.home.cleanup()

    def test_atomic_private_write_and_version_check(self):
        io.write_index(self.h, {"version": 1, "projects": []})
        p = paths.index_path(self.h)
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.dirname(p)).st_mode), 0o700)
        self.assertEqual(os.listdir(os.path.dirname(p)), ["index.json"])
        self.assertEqual(io.read_index(self.h), {"version": 1, "projects": []})
        io.write_json(p, {"version": 99})
        self.assertIsNone(io.read_index(self.h))

    def test_cache_round_trip_and_bad_cache(self):
        io.save_cache(self.h, {"/a.jsonl": {"size": 1}})
        self.assertEqual(io.load_cache(self.h), {"/a.jsonl": {"size": 1}})
        io.write_json(paths.transcript_cache_path(self.h), {"version": 0, "files": {"x": 1}})
        self.assertEqual(io.load_cache(self.h), {})

    def test_assignments(self):
        io.assign(self.h, "local_a", "~/Desktop/apps/mishlat/")
        home = os.path.expanduser("~")
        self.assertEqual(io.load_assignments(self.h), {"local_a": f"{home}/Desktop/apps/mishlat"})
        io.assign(self.h, "local_a", None)
        self.assertEqual(io.load_assignments(self.h), {})
        self.assertEqual(stat.S_IMODE(os.stat(paths.assignments_path(self.h)).st_mode), 0o600)

    def test_aliases_dismissed_settings(self):
        io.write_json(paths.aliases_path(self.h), {"~/Desktop/old": "~/Desktop/new/", "bad": 3})
        home = os.path.expanduser("~")
        self.assertEqual(io.load_aliases(self.h), {f"{home}/Desktop/old": f"{home}/Desktop/new"})
        io.dismiss(self.h, "local_a", 123)
        io.dismiss(self.h, "local_b", 456)
        self.assertEqual(io.load_dismissed(self.h), {"local_a": 123, "local_b": 456})
        self.assertEqual(io.load_settings(self.h)["roots"], [os.path.join(self.h, "Desktop")])
        io.write_json(paths.settings_path(self.h), {"roots": ["/srv/projects/"]})
        self.assertEqual(io.load_settings(self.h)["roots"], ["/srv/projects"])
        self.assertEqual(io.load_settings(self.h)["notify"], "others")        # the default
        io.save_setting(self.h, "notify", "off")
        self.assertEqual(io.load_settings(self.h)["notify"], "off")
        io.save_setting(self.h, "notify", "loud")
        self.assertEqual(io.load_settings(self.h)["notify"], "others")        # unknown → default


if __name__ == "__main__":
    unittest.main()


class CleanupFilesTest(unittest.TestCase):
    def setUp(self):
        self.home = FakeHome()
        self.h = self.home.root

    def tearDown(self):
        self.home.cleanup()

    def test_descriptions(self):
        io.describe(self.h, "~/Desktop/x/", "An archive")
        home = os.path.expanduser("~")
        self.assertEqual(io.load_descriptions(self.h), {f"{home}/Desktop/x": "An archive"})
        io.describe(self.h, "~/Desktop/x", None)
        self.assertEqual(io.load_descriptions(self.h), {})

    def test_keep_and_requests(self):
        io.keep(self.h, "local_a", 5)
        self.assertEqual(io.load_keep(self.h), {"local_a": 5})
        io.unkeep(self.h, "local_a")
        self.assertEqual(io.load_keep(self.h), {})
        io.request_delete(self.h, [{"id": "local_x", "title": "X", "cli_id": "c1"}, {"id": "local_y", "title": "Y"}], 9)
        self.assertEqual(set(io.load_delete_requests(self.h)), {"local_x", "local_y"})
        self.assertEqual(io.prune_delete_requests(self.h, {"local_y"}), 1)   # x was deleted in the app
        self.assertEqual(list(io.load_delete_requests(self.h)), ["local_y"])
        io.write_json(paths.settings_path(self.h), {"old_days": 60})
        self.assertEqual(io.load_settings(self.h)["old_days"], 60)
        io.write_json(paths.settings_path(self.h), {"old_days": "x"})
        self.assertEqual(io.load_settings(self.h)["old_days"], 30)
        self.assertEqual(io.load_settings(self.h)["font_px"], io.FONT_DEFAULT)
        io.save_setting(self.h, "font_px", 18)
        self.assertEqual(io.load_settings(self.h),
                         {"roots": [os.path.join(self.h, "Desktop")], "old_days": 30, "font_px": 18, "lang": "he",
                          "notify": "others"})
        io.save_setting(self.h, "lang", "en")
        self.assertEqual(io.load_settings(self.h)["lang"], "en")
        io.save_setting(self.h, "lang", "xx")
        self.assertEqual(io.load_settings(self.h)["lang"], "he")  # unknown: from the locale (pinned to Hebrew here)
        os.environ["MISHLAT_LANG"] = "en"
        try:
            self.assertEqual(io.load_settings(self.h)["lang"], "en")
        finally:
            del os.environ["MISHLAT_LANG"]
        io.save_setting(self.h, "font_px", 99)
        self.assertEqual(io.load_settings(self.h)["font_px"], io.FONT_DEFAULT)  # out of range: the default
