import json
import os
import sys
import unittest
from unittest import mock

from mishlat import index as io
from mishlat.scan import Scanner, app_version
from tests.helpers import FakeHome, agent, user

REGISTRY_ONLY = {"MISHLAT_AGENTS_DISABLE": "1"}


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

    def scanner(self, env=REGISTRY_ONLY, **kw):
        return Scanner(self.home.root, proc_root=self.home.proc, clock=self.clock, env=env,
                       git_run=lambda *a, **k: __import__("subprocess").CompletedProcess(a, 0, "", ""), **kw)

    def states(self, index) -> dict:
        return {s["id"]: s["state"] for p in index["projects"] for s in p["sessions"]}

    def test_end_to_end_writes_index_and_cache(self):
        index = self.scanner().scan()
        self.assertEqual(index["errors"], [])
        self.assertEqual(index["app_version"], "2.1.299")
        self.assertEqual(index["live_source"], "registry")
        self.assertEqual(self.states(index), {"local_a": "waiting", "c2": "working"})  # c2: alive, written now
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

    # ── the live source: `claude agents --json` first, the registry as the fallback ──
    def test_listing_decides_live_state(self):
        self.home.add_transcript(self.shedu, "c3", [user("quiet one", cwd=self.shedu)])
        self.home.add_transcript(self.shedu, "c4", [user("asks", cwd=self.shedu)])
        cmd = self.home.add_agents(agent("c1", self.shedu, status="busy", pid=11),
                                   agent("c3", self.shedu, status="idle", pid=12),
                                   agent("c4", self.shedu, status="waiting", pid=13, waiting_for="permission prompt"))
        index = self.scanner(env={"MISHLAT_AGENTS_CMD": cmd}).scan()
        self.assertEqual(index["errors"], [])
        self.assertEqual(index["live_source"], "agents")
        # c1: busy beats the store's blocked; c2: alive in the registry only, so not live; c3: idle,
        # though its transcript was written just now; c4: waiting on a permission prompt.
        self.assertEqual(self.states(index), {"local_a": "working", "c2": "idle", "c3": "open", "c4": "waiting"})
        rows = {s["id"]: s for p in index["projects"] for s in p["sessions"]}
        self.assertEqual((rows["local_a"]["pid"], rows["c3"]["pid"], rows["c2"]["pid"]), (11, 12, None))
        self.assertEqual(rows["c4"]["question"], "permission prompt")
        self.assertEqual(index["attention"], ["c4"])

    def test_listing_disabled_keeps_the_registry_without_an_error(self):
        cmd = self.home.add_agents(agent("c1", self.shedu))
        index = self.scanner(env={"MISHLAT_AGENTS_CMD": cmd, "MISHLAT_AGENTS_DISABLE": "1"}).scan()
        self.assertEqual((index["live_source"], index["errors"]), ("registry", []))
        self.assertEqual(self.states(index), {"local_a": "waiting", "c2": "working"})

    def test_listing_failure_is_one_error_line_and_the_registry_takes_over(self):
        for cmd, text in (("/nonexistent/claude", "not found"), ("false", "exited 1"), ("echo nope", "bad JSON"),
                          (f"{sys.executable} -c 'import time; time.sleep(3)'", "timed out")):
            s = self.scanner(env={"MISHLAT_AGENTS_CMD": cmd})
            s.agents_timeout = 0.2
            index = s.scan()
            self.assertEqual(index["live_source"], "registry", cmd)
            self.assertEqual(len(index["errors"]), 1, index["errors"])
            self.assertTrue(index["errors"][0].startswith("agents: AgentsError: "), index["errors"][0])
            self.assertIn(text, index["errors"][0])
            self.assertEqual(self.states(index), {"local_a": "waiting", "c2": "working"}, cmd)
        # No CLI at all (not on PATH, none bundled under the fake home): the same, in words.
        with mock.patch("mishlat.actions.shutil.which", lambda n: None):
            index = self.scanner(env={}).scan()
        self.assertEqual(index["live_source"], "registry")
        self.assertIn("agents: AgentsError: no claude CLI", index["errors"][0])


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
            old = {k: os.environ.get(k) for k in ("MISHLAT_HOME", "MISHLAT_AGENTS_CMD", "MISHLAT_AGENTS_DISABLE")}
            os.environ["MISHLAT_HOME"] = home.root
            os.environ.pop("MISHLAT_AGENTS_DISABLE", None)
            os.environ["MISHLAT_AGENTS_CMD"] = home.add_agents(agent("c1", shedu, status="busy"))
            out = stdio.StringIO()
            with contextlib.redirect_stdout(out):
                code = cli.main(["mishlat", "scan"])
            self.assertEqual(code, 0)
            text = out.getvalue()
            self.assertIn("projects 1 · sessions 1 · working 1", text)
            self.assertIn("· live source: agents", text)
            self.assertIn("errors: none", text)
            os.environ["MISHLAT_AGENTS_DISABLE"] = "1"
            with contextlib.redirect_stdout(stdio.StringIO()) as reg:
                cli.main(["mishlat", "scan"])
            self.assertIn("· live source: registry", reg.getvalue())
            self.assertIn("working 0", reg.getvalue())
            os.environ.pop("MISHLAT_AGENTS_DISABLE", None)
            self.assertNotIn("◐ shedu · Plan it", text)  # busy: working, not waiting
            os.environ["MISHLAT_AGENTS_CMD"] = home.add_agents(agent("c1", shedu, status="idle"))
            with contextlib.redirect_stdout(stdio.StringIO()) as idle:
                cli.main(["mishlat", "scan"])
            self.assertIn("◐ shedu · Plan it — Go?", idle.getvalue())  # idle: the store's question wins over open
            scratch = {"totals": dict.fromkeys(("projects", "sessions", "working", "open", "stale", "lost", "attention",
                                                "waiting", "review", "stopped"), 0),
                       "scanned_at": 0, "scan_ms": 1, "errors": [], "attention": [],
                       "projects": [{"name": "כללי", "path": None, "general": True, "sessions": [{"id": "x"}],
                                     "working": 0, "waiting": 0, "review": 0, "stopped": 0, "open": 0}]}
            self.assertIn("(sessions whose folder no longer exists, and app scratch sessions)",
                          cli.summary(scratch, home.root))
            with contextlib.redirect_stdout(stdio.StringIO()) as v:
                cli.main(["mishlat", "--version"])
            self.assertIn("mishlat 0.1.3", v.getvalue())
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
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            home.cleanup()
