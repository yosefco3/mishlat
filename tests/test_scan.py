import json
import os
import unittest

from mishlat import index as io
from mishlat.scan import Scanner, app_version
from tests.helpers import FakeHome, user


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.home = FakeHome()
        self.shedu = self.home.make_repo("Desktop/shedu")
        self.home.add_record("local_a", self.shedu, cli_id="c1", title="Plan", last=1_000,
                             status="blocked", question="Go?")
        self.home.add_transcript(self.shedu, "c1", [user("start", cwd=self.shedu)])
        self.home.add_transcript(self.shedu, "c2", [user("terminal work", cwd=self.shedu)])
        self.home.add_live(5, "c2", self.shedu, start="77")
        os.makedirs(self.home.path(".config/Claude/claude-code/2.1.280/a"))
        os.makedirs(self.home.path(".config/Claude/claude-code/2.1.299/b"))
        self.clock = lambda: 2_000

    def tearDown(self):
        self.home.cleanup()

    def scanner(self, **kw):
        return Scanner(self.home.root, proc_root=self.home.proc, clock=self.clock,
                       git_run=lambda *a, **k: __import__("subprocess").CompletedProcess(a, 0, "", ""), **kw)

    def test_end_to_end_writes_index_and_cache(self):
        index = self.scanner().scan()
        self.assertEqual(index["errors"], [])
        self.assertEqual(index["app_version"], "2.1.299")
        p = index["projects"][0]
        self.assertEqual((p["name"], p["branch"], p["dirty"], len(p["sessions"])), ("shedu", "main", False, 2))
        self.assertEqual({s["source"] for s in p["sessions"]}, {"app", "cli"})
        self.assertEqual(io.read_index(self.home.root)["attention"], ["local_a"])
        self.assertTrue(io.load_cache(self.home.root))

    def test_second_scan_uses_caches(self):
        s = self.scanner()
        s.scan()
        s.scan()
        self.assertEqual(s.store.parsed, 0)

    def test_broken_source_becomes_an_error_line(self):
        s = self.scanner()

        def boom(home):
            raise RuntimeError("disk on fire")
        s.store.read = boom
        index = s.scan()
        self.assertTrue(any("store: RuntimeError: disk on fire" in e for e in index["errors"]))
        # With no store, every transcript still shows, as a terminal session.
        self.assertEqual({s["source"] for s in index["projects"][0]["sessions"]}, {"cli"})
        self.assertEqual(index["totals"]["sessions"], 2)

    def test_app_version_missing(self):
        self.assertIsNone(app_version(self.home.path("nowhere")))


if __name__ == "__main__":
    unittest.main()


class CliTest(unittest.TestCase):
    def test_scan_command_prints_a_summary(self):
        import contextlib
        import io as stdio

        from mishlat import cli
        home = FakeHome()
        try:
            shedu = home.make_repo("Desktop/shedu")
            home.add_record("local_a", shedu, cli_id="c1", title="Plan it", status="blocked", question="Go?",
                            last=10**13)
            old = os.environ.get("MISHLAT_HOME")
            os.environ["MISHLAT_HOME"] = home.root
            out = stdio.StringIO()
            with contextlib.redirect_stdout(out):
                code = cli.main(["mishlat", "scan"])
            self.assertEqual(code, 0)
            text = out.getvalue()
            self.assertIn("projects 1 · sessions 1", text)
            self.assertIn("errors: none", text)
            self.assertIn("◐ shedu · Plan it — Go?", text)
            scratch = {"totals": dict.fromkeys(("projects", "sessions", "working", "open", "stale", "lost", "attention",
                                                "waiting", "review", "stopped"), 0),
                       "scanned_at": 0, "scan_ms": 1, "errors": [], "attention": [],
                       "projects": [{"name": "כללי", "path": None, "general": True, "sessions": [{"id": "x"}],
                                     "working": 0, "waiting": 0, "review": 0, "stopped": 0, "open": 0}]}
            self.assertIn("(sessions whose folder no longer exists, and app scratch sessions)",
                          cli.summary(scratch, home.root))
            with contextlib.redirect_stdout(stdio.StringIO()) as v:
                cli.main(["mishlat", "--version"])
            self.assertIn("mishlat 0.1.0", v.getvalue())
            # cleanup: nothing approved, then two approved
            from mishlat import index as io
            with contextlib.redirect_stdout(stdio.StringIO()) as c0:
                cli.main(["mishlat", "cleanup"])
            self.assertIn("No sessions approved", c0.getvalue())
            io.request_delete(home.root, [{"id": "local_a", "title": "Plan it", "cli_id": "c1"}], 5)
            with contextlib.redirect_stdout(stdio.StringIO()) as c1:
                cli.main(["mishlat", "cleanup"])
            self.assertIn("1 sessions approved", c1.getvalue())
            self.assertIn("local_a  Plan it", c1.getvalue())
            with contextlib.redirect_stdout(stdio.StringIO()) as c2:
                cli.main(["mishlat", "cleanup", "--json"])
            self.assertEqual(json.loads(c2.getvalue())["delete"][0]["id"], "local_a")
            with contextlib.redirect_stdout(stdio.StringIO()) as s2:  # a pruned request after the session is gone
                cli.main(["mishlat", "scan"])
            self.assertIn("cleanup", s2.getvalue())
        finally:
            if old is None:
                os.environ.pop("MISHLAT_HOME", None)
            else:
                os.environ["MISHLAT_HOME"] = old
            home.cleanup()
