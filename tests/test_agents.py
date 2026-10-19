import os
import subprocess
import sys
import unittest

from mishlat.agents import AgentsError, LiveEntry, agents_command, parse_agents_json, read_agents
from tests.helpers import FakeHome

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "agents.json")
PY = sys.executable


class ParseTest(unittest.TestCase):
    def test_fixture_shaped_like_the_real_listing(self):
        with open(FIXTURE, encoding="utf-8") as f:
            live = parse_agents_json(f.read())
        self.assertEqual(len(live), 4)  # the entry without a sessionId is skipped
        idle = live["39796263-6d18-4539-b26a-13e3cedf3666"]
        self.assertEqual(idle, LiveEntry(pid=20043, cwd="/home/u/Desktop/book", name="Chapter three", status="idle",
                                         waiting_for=None, kind="interactive", started_at=1792427112819))
        self.assertEqual(live["a6c8cd08-d60c-4284-85cf-c65c0b0bf3ab"].status, "busy")
        waiting = live["0b2d6a0e-2b1c-4f0e-9a3e-5d2c1b7e8f90"]
        self.assertEqual((waiting.status, waiting.waiting_for), ("waiting", "permission prompt"))
        bg = live["5c1e2f3a-4b5c-4d6e-8f70-1a2b3c4d5e6f"]
        self.assertEqual((bg.pid, bg.kind, bg.status), (None, "background", "busy"))

    def test_background_states_and_unknown_status(self):
        live = parse_agents_json('[{"sessionId": "a", "kind": "background", "state": "blocked"},'
                                 ' {"sessionId": "b", "kind": "background", "state": "done"},'
                                 ' {"sessionId": "c", "pid": 1, "status": "dreaming", "waitingFor": "x"},'
                                 ' {"sessionId": "d", "pid": 2, "status": "busy", "waitingFor": "stale"}]')
        self.assertEqual(live["a"].status, "waiting")
        self.assertIsNone(live["b"].status)
        self.assertEqual((live["c"].status, live["c"].waiting_for), (None, None))
        self.assertEqual((live["d"].status, live["d"].waiting_for), ("busy", None))  # only with waiting

    def test_malformed_empty_and_missing_fields(self):
        with self.assertRaises(AgentsError):
            parse_agents_json("{nope")
        with self.assertRaises(AgentsError):
            parse_agents_json('{"sessions": []}')
        self.assertEqual(parse_agents_json("[]"), {})
        self.assertEqual(parse_agents_json(b"[]"), {})
        live = parse_agents_json('[{"sessionId": "s"}, 7, "x", {"pid": 3}, {"sessionId": ""}]')
        self.assertEqual(live, {"s": LiveEntry(None, "", None, None, None, "", 0)})
        live = parse_agents_json('[{"sessionId": "s", "pid": true, "startedAt": 1.5, "name": 3, "cwd": null}]')
        self.assertEqual((live["s"].pid, live["s"].started_at, live["s"].name, live["s"].cwd), (None, 0, None, ""))

    def test_newest_entry_wins_a_repeated_id(self):
        live = parse_agents_json('[{"sessionId": "s", "pid": 1, "startedAt": 200, "status": "idle"},'
                                 ' {"sessionId": "s", "pid": 2, "startedAt": 100, "status": "busy"}]')
        self.assertEqual((live["s"].pid, live["s"].status), (1, "idle"))


class CommandTest(unittest.TestCase):
    def setUp(self):
        self.home = FakeHome()

    def tearDown(self):
        self.home.cleanup()

    def cli(self, version: str) -> str:
        p = self.home.path(".config/Claude/claude-code", version, "h", "claude")
        os.makedirs(os.path.dirname(p))
        with open(p, "w") as f:
            f.write("#!/bin/sh\n")
        os.chmod(p, 0o755)
        return p

    def test_disabled_override_and_bundled(self):
        none = lambda n: None
        self.assertIsNone(agents_command(self.home.root, {"MISHLAT_AGENTS_DISABLE": "1"}, none))
        self.assertEqual(agents_command(self.home.root, {"MISHLAT_AGENTS_CMD": "cat '/a dir/x.json'"}, none),
                         ["cat", "/a dir/x.json"])
        with self.assertRaises(AgentsError):
            agents_command(self.home.root, {}, none)
        newest = self.cli("2.1.299")
        self.cli("2.1.30")
        self.assertEqual(agents_command(self.home.root, {}, none), [newest, "agents", "--json"])
        self.assertEqual(agents_command(self.home.root, {}, lambda n: "/usr/bin/claude"),
                         ["/usr/bin/claude", "agents", "--json"])


class ReadTest(unittest.TestCase):
    def test_runs_the_command_and_parses(self):
        live = read_agents(["cat", FIXTURE])
        self.assertEqual(live["a6c8cd08-d60c-4284-85cf-c65c0b0bf3ab"].status, "busy")

    def test_a_cli_path_becomes_agents_json(self):
        calls = []

        def run(argv, **kw):
            calls.append((argv, kw["timeout"], kw["stdin"]))
            return subprocess.CompletedProcess(argv, 0, b"[]", b"")
        self.assertEqual(read_agents("/opt/claude", timeout=2, run=run), {})
        self.assertEqual(calls, [(["/opt/claude", "agents", "--json"], 2, subprocess.DEVNULL)])

    def test_every_failure_is_an_agents_error(self):
        with self.assertRaises(AgentsError) as e:
            read_agents([PY, "-c", "import time; time.sleep(5)"], timeout=0.2)
        self.assertIn("timed out after 0.2 s", str(e.exception))
        with self.assertRaises(AgentsError) as e:
            read_agents([PY, "-c", "import sys; print('boom', file=sys.stderr); sys.exit(3)"])
        self.assertIn("exited 3: boom", str(e.exception))
        with self.assertRaises(AgentsError) as e:
            read_agents("/nonexistent/claude")
        self.assertIn("not found", str(e.exception))
        with self.assertRaises(AgentsError) as e:
            read_agents(["echo", "nope"])
        self.assertIn("bad JSON", str(e.exception))
        with self.assertRaises(AgentsError):
            read_agents([])


if __name__ == "__main__":
    unittest.main()
