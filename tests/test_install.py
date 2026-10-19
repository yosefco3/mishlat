import os
import subprocess
import unittest

from tests.helpers import FakeHome

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


class InstallTest(unittest.TestCase):
    def test_install_run_uninstall_in_a_temp_home(self):
        home = FakeHome()
        try:
            env = dict(os.environ, HOME=home.root, MISHLAT_NO_RESTART="1", MISHLAT_NO_KEYBINDING="1", LC_ALL="C.UTF-8")
            env.pop("MISHLAT_HOME", None)
            env.pop("MISHLAT_LIB", None)
            out = subprocess.run([os.path.join(REPO, "install.sh")], env=env, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            p = home.path
            launcher = p(".local/bin/mishlat")
            self.assertTrue(os.access(launcher, os.X_OK))
            self.assertTrue(os.path.isfile(p(".local/share/mishlat/lib/mishlat/scan.py")))
            self.assertFalse(any("__pycache__" in d for d, _, _ in os.walk(p(".local/share/mishlat/lib"))))
            self.assertTrue(os.path.isfile(p(".local/share/mishlat/icons/mishlat-3.svg")))
            self.assertTrue(os.path.isfile(p(".local/share/nemo-python/extensions/mishlat_fm.py")))
            with open(p(".local/share/applications/mishlat.desktop")) as f:
                self.assertIn(f"Exec={launcher}\n", f.read())
            with open(p(".config/autostart/mishlat.desktop")) as f:
                text = f.read()
            self.assertIn(f"Exec={launcher} --tray", text)
            self.assertIn(f"Icon={p('.local/share/mishlat/icons')}/mishlat.svg", text)

            shedu = home.make_repo("Desktop/shedu")
            home.add_record("local_a", shedu, title="Installed", last=10**13)
            run = subprocess.run([launcher, "scan"], env=env, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("projects 1 · sessions 1", run.stdout)
            self.assertTrue(os.path.isfile(p(".cache/mishlat/index.json")))

            for _ in range(2):  # uninstall is safe to run twice
                out = subprocess.run([os.path.join(REPO, "uninstall.sh")], env=env, capture_output=True, text=True)
                self.assertEqual(out.returncode, 0, out.stderr)
            self.assertFalse(os.path.exists(launcher))
            self.assertFalse(os.path.exists(p(".local/share/mishlat")))
            self.assertFalse(os.path.exists(p(".local/share/nemo-python/extensions/mishlat_fm.py")))
            self.assertTrue(os.path.isfile(p(".cache/mishlat/index.json")))  # kept without --purge
        finally:
            home.cleanup()


if __name__ == "__main__":
    unittest.main()
