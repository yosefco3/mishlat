"""The demo home (scripts/demo_home.py) must show both live sources: the CLI's listing and the registry."""

import importlib.util
import os
import subprocess
import tempfile
import unittest

from mishlat.agents import parse_agents_json
from mishlat.scan import Scanner

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


def load_demo():
    spec = importlib.util.spec_from_file_location("demo_home", os.path.join(REPO, "scripts", "demo_home.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DemoHomeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        load_demo().build(self.root)
        self.git = lambda *a, **k: subprocess.CompletedProcess(a, 0, "", "")

    def tearDown(self):
        self.tmp.cleanup()

    def by_title(self, index) -> dict:
        return {s["title"]: s for p in index["projects"] for s in p["sessions"]}

    def test_listing_is_the_primary_source(self):
        with open(os.path.join(self.root, "_agents.json"), encoding="utf-8") as f:
            listing = parse_agents_json(f.read())
        self.assertEqual(sorted(e.status for e in listing.values()), ["busy", "idle", "waiting"])
        env = {"MISHLAT_AGENTS_CMD": f"cat {self.root}/_agents.json", "MISHLAT_PROC_ROOT": f"{self.root}/_proc"}
        index = Scanner(self.root, env=env, git_run=self.git).scan()
        self.assertEqual((index["errors"], index["live_source"]), ([], "agents"))
        rows = self.by_title(index)
        self.assertEqual(rows["Fix the checkout redirect after 3-D Secure"]["state"], "working")
        self.assertEqual(rows["Rate limiting for the search endpoint"]["state"], "open")
        audit = rows["Add the audit log table"]
        self.assertEqual((audit["state"], audit["question"]), ("waiting", "permission prompt"))
        self.assertEqual(index["totals"]["working"], 1)
        self.assertEqual(index["totals"]["open"], 1)

    def test_registry_fallback(self):
        env = {"MISHLAT_AGENTS_DISABLE": "1", "MISHLAT_PROC_ROOT": f"{self.root}/_proc"}
        index = Scanner(self.root, env=env, git_run=self.git).scan()
        self.assertEqual((index["errors"], index["live_source"]), ([], "registry"))
        rows = self.by_title(index)
        self.assertEqual(rows["Fix the checkout redirect after 3-D Secure"]["state"], "working")  # written now
        self.assertEqual(rows["Rate limiting for the search endpoint"]["state"], "open")           # alive, quiet
        self.assertEqual(rows["Add the audit log table"]["state"], "open")                         # no listing


if __name__ == "__main__":
    unittest.main()
