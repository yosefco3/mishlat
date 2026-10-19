import filecmp
import json
import os
import subprocess
import sys
import unittest

from tests.helpers import FakeHome

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
PLUGIN = os.path.join(REPO, "plugin")
BUNDLED = {"actions", "agents", "cli", "describe", "folders", "gitinfo", "index", "__init__", "live", "__main__", "model",
           "paths", "scan", "store", "strings", "transcripts", "view"}


class PluginTest(unittest.TestCase):
    def test_manifest(self):
        with open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            manifest = json.load(f)
        self.assertEqual(manifest["name"], "mishlat")
        self.assertEqual(manifest["license"], "MIT")
        for skill in ("projects", "needs-me", "cleanup"):
            path = os.path.join(PLUGIN, "skills", skill, "SKILL.md")
            with open(path, encoding="utf-8") as f:
                head = f.read(400)
            self.assertTrue(head.startswith("---\nname: " + skill), path)

    def test_bundled_package_is_in_sync(self):
        """`make plugin-sync` copies the scanner modules; a stale copy would ship old rules."""
        lib = os.path.join(PLUGIN, "lib", "mishlat")
        names = {f[:-3] for f in os.listdir(lib) if f.endswith(".py")}
        self.assertEqual(names, BUNDLED)
        for name in BUNDLED:
            self.assertTrue(filecmp.cmp(os.path.join(REPO, "mishlat", name + ".py"), os.path.join(lib, name + ".py"),
                                        shallow=False), f"{name}.py differs: run make plugin-sync")

    def test_entry_point_scans_a_fake_home(self):
        home = FakeHome()
        try:
            w = home.make_repo("Desktop/w")
            home.add_record("local_a", w, cli_id="c1", title="Plugin run", status="blocked", question="Go?", last=10**13)
            env = dict(os.environ, MISHLAT_HOME=home.root, LC_ALL="C.UTF-8")
            out = subprocess.run([sys.executable, os.path.join(PLUGIN, "lib", "mishlat_cli.py"), "scan", "--json"],
                                 env=env, capture_output=True, text=True, cwd="/")
            self.assertEqual(out.returncode, 0, out.stderr)
            index = json.loads(out.stdout)
            self.assertEqual(index["attention"], ["local_a"])
        finally:
            home.cleanup()


if __name__ == "__main__":
    unittest.main()
