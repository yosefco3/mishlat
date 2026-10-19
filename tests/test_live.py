import os
import unittest

from mishlat.live import parse_proc_start, read_live
from tests.helpers import FakeHome


class LiveTest(unittest.TestCase):
    def setUp(self):
        self.home = FakeHome()

    def tearDown(self):
        self.home.cleanup()

    def test_parse_proc_start_with_spaces_and_parens_in_name(self):
        fields = ["S"] + [str(i) for i in range(1, 19)] + ["4242"] + ["0"] * 5
        self.assertEqual(parse_proc_start("7 (a (b) c) " + " ".join(fields)), "4242")
        self.assertIsNone(parse_proc_start("garbage"))

    def test_alive_only_when_start_time_matches(self):
        self.home.add_live(10, "c-alive", "/w", start="500")
        self.home.add_live(11, "c-gone", "/w", start="600", alive=False)
        self.home.add_live(12, "c-reused", "/w", start="700", alive=False)
        self.home.add_proc(12, "999")  # the pid now belongs to another process
        live = read_live(self.home.root, proc_root=self.home.proc)
        self.assertEqual(set(live), {"c-alive"})
        self.assertEqual(live["c-alive"].pid, 10)

    def test_newest_process_wins_and_broken_files_are_skipped(self):
        self.home.add_live(20, "c1", "/w", start="1", started_at=100)
        self.home.add_live(21, "c1", "/w", start="2", started_at=200)
        with open(self.home.path(".claude/sessions/99.json"), "w") as f:
            f.write("{nope")
        live = read_live(self.home.root, proc_root=self.home.proc)
        self.assertEqual(live["c1"].pid, 21)

    def test_no_registry(self):
        self.assertEqual(read_live(self.home.root, proc_root=self.home.proc), {})


if __name__ == "__main__":
    unittest.main()
