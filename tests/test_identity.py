import os
import shutil
import unittest

from mishlat import index as io
from mishlat.folders import folder_index, identity, same_folder
from mishlat.gitinfo import remote_url
from tests.helpers import FakeHome


def write_config(repo: str, text: str) -> None:
    with open(os.path.join(repo, ".git", "config"), "w", encoding="utf-8") as f:
        f.write(text)


class RemoteTest(unittest.TestCase):
    def setUp(self):
        self.home = FakeHome()

    def tearDown(self):
        self.home.cleanup()

    def test_origin_first_remote_none_and_worktree(self):
        repo = self.home.make_repo("r")
        self.assertIsNone(remote_url(repo))
        write_config(repo, '[core]\n\tbare = false\n[remote "upstream"]\n\turl = git@x:up.git\n[remote "origin"]\n\turl = https://x/o.git\n\tfetch = +refs/heads/*:refs/remotes/origin/*\n')
        self.assertEqual(remote_url(repo), "https://x/o.git")
        write_config(repo, '[remote "only"]\n\turl = git@x:only.git\n')
        self.assertEqual(remote_url(repo), "git@x:only.git")
        wt = self.home.mkdir("wt")
        gd = self.home.mkdir("r/.git/worktrees/wt")
        with open(os.path.join(wt, ".git"), "w") as f:
            f.write(f"gitdir: {gd}\n")
        with open(os.path.join(gd, "commondir"), "w") as f:
            f.write("../..\n")
        self.assertEqual(remote_url(wt), "git@x:only.git")
        self.assertIsNone(remote_url(self.home.mkdir("plain")))


class IdentityTest(unittest.TestCase):
    def setUp(self):
        self.home = FakeHome()

    def tearDown(self):
        self.home.cleanup()

    def test_rename_keeps_identity(self):
        a = self.home.mkdir("Desktop/alpha")
        for name in ("src", "README.md", "tests"):
            open(os.path.join(a, name), "w").close()
        before = identity(a)
        self.assertEqual(before["entries"], ["README.md", "src", "tests"])
        b = os.path.join(self.home.root, "Desktop", "beta")
        os.rename(a, b)
        self.assertTrue(same_folder(before, b))
        self.assertFalse(same_folder(before, self.home.mkdir("Desktop/other")))

    def test_recycled_inode_with_other_files_is_rejected(self):
        a = self.home.mkdir("Desktop/alpha")
        open(os.path.join(a, "notes.txt"), "w").close()
        before = identity(a)
        shutil.rmtree(a)
        # The same path, a new folder, other files: whatever inode it got, the entries do not match.
        c = self.home.mkdir("Desktop/alpha")
        open(os.path.join(c, "unrelated.py"), "w").close()
        fake = dict(before, dev=os.stat(c).st_dev, ino=os.stat(c).st_ino)  # force the inode match
        self.assertFalse(same_folder(fake, c))
        same = dict(fake, entries=["unrelated.py"])
        self.assertTrue(same_folder(same, c))

    def test_remote_decides_for_copies_and_rejects_strangers(self):
        a = self.home.make_repo("Desktop/alpha")
        write_config(a, '[remote "origin"]\n\turl = https://x/alpha.git\n')
        before = identity(a)
        copy = os.path.join(self.home.root, "Desktop", "alpha-copy")
        shutil.copytree(a, copy)                       # a new inode, the same remote
        self.assertTrue(same_folder(before, copy))
        stranger = self.home.make_repo("Desktop/stranger")
        write_config(stranger, '[remote "origin"]\n\turl = https://x/stranger.git\n')
        fake = dict(before, dev=os.stat(stranger).st_dev, ino=os.stat(stranger).st_ino, entries=[".git"])
        self.assertFalse(same_folder(fake, stranger))  # the inode "matches" but the remotes differ

    def test_index_lookup_and_memory_file(self):
        root = self.home.mkdir("Desktop")
        a = self.home.make_repo("Desktop/alpha")
        open(os.path.join(a, "a.txt"), "w").close()
        before = identity(a)
        b = os.path.join(root, "renamed")
        os.rename(a, b)
        idx = folder_index([root])
        self.assertEqual(idx.by_identity(before), b)
        self.assertIsNone(idx.by_identity({"dev": 1, "ino": 2, "remote": None, "entries": []}))
        io.save_folder_memory(self.home.root, {a: before})
        self.assertEqual(io.load_folder_memory(self.home.root), {a: before})
        self.assertEqual(io.load_folder_memory(self.home.path("nowhere")), {})


class ScanRemembersTest(unittest.TestCase):
    def test_scan_records_known_folders(self):
        from mishlat.scan import Scanner
        home = FakeHome()
        try:
            w = home.make_repo("Desktop/w")
            home.add_record("local_a", w, cli_id="c1", title="t", last=10**13)
            s = Scanner(home.root, proc_root=home.proc, clock=lambda: 5)
            s.scan()
            self.assertIn(w, s.folder_memory)
            self.assertEqual(s.folder_memory[w]["seen"], 5)
            self.assertEqual(set(io.load_folder_memory(home.root)), {w})
        finally:
            home.cleanup()


if __name__ == "__main__":
    unittest.main()


class RenameAndMoveTest(unittest.TestCase):
    """The experiment the user asked for: two scans, a change in between, the sessions follow."""

    def setUp(self):
        from mishlat.scan import Scanner
        self.home = FakeHome()
        self.desk = self.home.mkdir("Desktop")
        self.shop = self.home.make_repo("Desktop/shop-site")
        open(os.path.join(self.shop, "package.json"), "w").close()
        self.book = self.home.mkdir("Desktop/writing/cookbook")
        open(os.path.join(self.book, "chapter1.md"), "w").close()
        self.tools = self.home.make_repo("Desktop/tools/backup-scripts")
        open(os.path.join(self.tools, "backup.sh"), "w").close()
        self.api = self.home.make_repo("Desktop/apps/shop-api")
        for i, cwd in enumerate((self.shop, self.shop, self.book, self.tools)):
            self.home.add_record(f"local_{i}", cwd, cli_id=f"c{i}", title=f"session {i}", last=10**13 - i)
        self.scanner = Scanner(self.home.root, proc_root=self.home.proc, clock=lambda: 10**13)
        self.scanner.scan()

    def tearDown(self):
        self.home.cleanup()

    def where(self):
        idx = self.scanner.scan()
        return {s["id"]: (p["name"], sorted(p["moved_from"])) for p in idx["projects"] for s in p["sessions"]}

    def test_rename_move_and_move_into_a_repository(self):
        os.rename(self.shop, os.path.join(self.desk, "store-site"))
        os.makedirs(os.path.join(self.desk, "elsewhere"))
        os.rename(self.book, os.path.join(self.desk, "elsewhere", "book"))
        os.rename(self.tools, os.path.join(self.api, "vendor-scripts"))
        where = self.where()
        self.assertEqual(where["local_0"], ("store-site", [self.shop]))
        self.assertEqual(where["local_1"], ("store-site", [self.shop]))
        self.assertEqual(where["local_2"], ("elsewhere/book", [self.book]))
        self.assertEqual(where["local_3"], ("apps/shop-api/vendor-scripts", [self.tools]))
        idx = self.scanner.scan()
        self.assertEqual(idx["totals"]["lost"], 0)
        self.assertEqual(idx["totals"]["cleanup_by"]["gone"], 0)
        # Renamed back: followed again, by the same memory.
        os.rename(os.path.join(self.desk, "store-site"), self.shop)
        self.assertEqual(self.where()["local_0"], ("shop-site", []))

    def test_deleted_folder_is_gone_and_a_recycled_inode_does_not_fool_it(self):
        import shutil
        shutil.rmtree(self.book)
        where = self.where()
        self.assertEqual(where["local_2"][0], "כללי")
        # A new, unrelated folder appears (whatever inode it gets): the entries differ, so no match.
        other = self.home.mkdir("Desktop/writing/novel")
        open(os.path.join(other, "outline.txt"), "w").close()
        remembered = dict(self.scanner.folder_memory[self.book])
        remembered["dev"], remembered["ino"] = os.stat(other).st_dev, os.stat(other).st_ino
        self.scanner.folder_memory[self.book] = remembered
        self.assertEqual(self.where()["local_2"][0], "כללי")
