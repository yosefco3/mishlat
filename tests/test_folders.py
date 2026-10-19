import os
import subprocess
import unittest

from mishlat.folders import folder_index
from mishlat.gitinfo import is_dirty, read_branch
from tests.helpers import FakeHome


class FolderIndexTest(unittest.TestCase):
    def setUp(self):
        self.home = FakeHome()
        self.root = self.home.mkdir("Desktop")
        self.home.make_repo("Desktop/shedu")
        self.home.mkdir("Desktop/shedu/internal")           # inside a repo: not indexed
        self.home.mkdir("Desktop/web_site/web-site")
        self.home.make_repo("Desktop/apps/vault")
        self.home.mkdir("Desktop/apps/node_modules/x")
        self.home.mkdir("Desktop/.hidden/x")
        self.home.mkdir("Desktop/a/b/c/d")                    # depth 4: d is not indexed

    def tearDown(self):
        self.home.cleanup()

    def test_walk_skips_and_cuts_at_repos(self):
        idx = folder_index([self.root])
        rel = {os.path.relpath(f.path, self.root) for f in idx.folders}
        self.assertIn("shedu", rel)
        self.assertNotIn("shedu/internal", rel)
        self.assertIn("apps/vault", rel)
        self.assertNotIn("apps/node_modules", rel)
        self.assertFalse(any(r.startswith(".hidden") for r in rel))
        self.assertIn("a/b/c", rel)
        self.assertNotIn("a/b/c/d", rel)
        self.assertEqual({os.path.basename(f.path) for f in idx.repos()}, {"shedu", "vault"})

    def test_lookups(self):
        idx = folder_index([self.root])
        target = os.path.join(self.root, "web_site", "web-site")
        enc = target.replace("/", "-").replace("_", "-")
        self.assertEqual(idx.by_encoding(enc), [target])
        # "_" and "-" encode alike, so both folders answer to the old name.
        self.assertEqual(sorted(idx.by_basename("/old/place/web_site")),
                         [os.path.join(self.root, "web_site"), target])
        self.assertIsNotNone(idx.at(target))
        self.assertEqual(folder_index([self.home.path("missing")]).folders, [])


class GitInfoTest(unittest.TestCase):
    def setUp(self):
        self.home = FakeHome()

    def tearDown(self):
        self.home.cleanup()

    def test_branch_detached_and_gitdir_file(self):
        repo = self.home.make_repo("r", branch="feature/x")
        self.assertEqual(read_branch(repo), "feature/x")
        with open(os.path.join(repo, ".git", "HEAD"), "w") as f:
            f.write("0123456789abcdef0123456789abcdef01234567\n")
        self.assertEqual(read_branch(repo), "0123456")
        wt = self.home.mkdir("wt")
        real = self.home.mkdir("store/wt-git")
        with open(os.path.join(real, "HEAD"), "w") as f:
            f.write("ref: refs/heads/side\n")
        with open(os.path.join(wt, ".git"), "w") as f:
            f.write("gitdir: ../store/wt-git\n")
        self.assertEqual(read_branch(wt), "side")
        self.assertIsNone(read_branch(self.home.mkdir("plain")))

    def test_dirty(self):
        ok = lambda out, code=0: (lambda *a, **k: subprocess.CompletedProcess(a, code, out, ""))
        self.assertTrue(is_dirty("/r", run=ok(" M file.py\n")))
        self.assertFalse(is_dirty("/r", run=ok("")))
        self.assertIsNone(is_dirty("/r", run=ok("", 128)))

        def boom(*a, **k):
            raise subprocess.TimeoutExpired("git", 3)
        self.assertIsNone(is_dirty("/r", run=boom))


if __name__ == "__main__":
    unittest.main()
