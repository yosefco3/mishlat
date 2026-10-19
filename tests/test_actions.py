import os
import stat
import unittest

from mishlat import actions
from tests.helpers import FakeHome

UUID = "b164962f-7357-4be8-96ac-52ec933ad049"


class ActionsTest(unittest.TestCase):
    def setUp(self):
        self.home = FakeHome()
        self.calls = []
        self.run = self.calls.append

    def tearDown(self):
        self.home.cleanup()

    def cli(self, version):
        p = self.home.path(f".config/Claude/claude-code/{version}/abc/claude")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write("#!/bin/sh\n")
        os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR)
        return p

    def test_urls(self):
        self.assertEqual(actions.session_url({"id": "local_f819f009-3c6f", "cli_id": UUID}),
                         "claude://code/continue?session=local_f819f009-3c6f")
        self.assertEqual(actions.session_url({"id": UUID, "cli_id": UUID}), f"claude://resume?session={UUID}")
        self.assertIsNone(actions.session_url({"id": "local_bad id!", "cli_id": "nope"}))

    def test_open_session_runs_xdg_open(self):
        self.assertTrue(actions.open_session({"id": "local_a1"}, run=self.run))
        self.assertEqual(self.calls, [["xdg-open", "claude://code/continue?session=local_a1"]])
        self.assertFalse(actions.open_session({"id": "x"}, run=self.run))

    def test_newest_bundled_cli_unless_on_path(self):
        self.cli("2.1.280")
        newest = self.cli("2.1.299")
        self.cli("2.1.30")  # 30 < 299 as numbers, though not as text
        self.assertEqual(actions.claude_cli(self.home.root, which=lambda n: None), newest)
        self.assertEqual(actions.claude_cli(self.home.root, which=lambda n: "/usr/bin/claude"), "/usr/bin/claude")
        self.assertIsNone(actions.claude_cli(self.home.path("empty"), which=lambda n: None))

    def test_resume_in_terminal_uses_the_current_folder(self):
        cli = self.cli("2.1.299")
        has_gnome = lambda n: "/usr/bin/gnome-terminal" if n == "gnome-terminal" else None
        err = actions.resume_in_terminal({"cli_id": UUID, "cwd": "/old/gone"}, "/new/place", self.home.root,
                                         run=self.run, which=has_gnome, isdir=lambda p: p == "/new/place")
        self.assertIsNone(err)
        self.assertEqual(self.calls[-1], ["gnome-terminal", "--working-directory=/new/place", "--", cli, "--resume", UUID])
        err = actions.resume_in_terminal({"cli_id": None}, None, self.home.root, run=self.run)
        self.assertIn("מזהה", err)

    def test_fallback_terminal_quotes(self):
        argv = actions.terminal_command("/a b", "/c/claude", UUID, which=lambda n: None)
        self.assertEqual(argv[:4], ["x-terminal-emulator", "-e", "bash", "-lc"])
        self.assertIn("cd '/a b' && exec /c/claude --resume", argv[4])

    def test_folder_and_new_session(self):
        actions.open_folder("/p", run=self.run)
        actions.new_session_in("/p", run=self.run)
        self.assertEqual(self.calls, [["xdg-open", "/p"], ["claude-desktop", "--os-entry=folder_verb", "/p"]])


if __name__ == "__main__":
    unittest.main()
