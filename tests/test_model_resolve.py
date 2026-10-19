import unittest

from mishlat.folders import Folder, FolderIndex
from mishlat.model import SCRATCH, WORKING_WINDOW_MS, resolve_project, state_of
from mishlat.transcripts import encode_path

D = "/h/Desktop"


def index(*paths):
    return FolderIndex([Folder(p, False) for p in paths], [D])


def isdir_of(*existing):
    return lambda p: p in existing


class ResolveTest(unittest.TestCase):
    def test_existing_folder_and_worktree(self):
        exists = isdir_of(f"{D}/shedu")
        self.assertEqual(resolve_project(f"{D}/shedu/", index(), isdir=exists).key, f"{D}/shedu")
        ref = resolve_project(f"{D}/shedu/.claude/worktrees/brave-x", index(), isdir=exists)
        self.assertEqual((ref.key, ref.moved_from), (f"{D}/shedu", None))

    def test_scratch(self):
        ref = resolve_project("/h/.config/Claude/scratch-workspaces/a/b/scratch-1", index(), isdir=isdir_of())
        self.assertEqual((ref.key, ref.path), (SCRATCH, None))

    def test_moved_by_transcript_folder(self):
        new = f"{D}/web_site/web-site"
        ref = resolve_project(f"{D}/web-site", index(new), tx_folder=encode_path(new), isdir=isdir_of(new))
        self.assertEqual((ref.key, ref.path, ref.moved_from), (new, new, f"{D}/web-site"))

    def test_reused_folder_name_follows_the_transcripts(self):
        parent, child = f"{D}/trading", f"{D}/trading/prop-challenge"
        ref = resolve_project(parent, index(parent, child), tx_folder=encode_path(child), isdir=isdir_of(parent, child))
        self.assertEqual((ref.key, ref.moved_from), (child, parent))
        # A worktree session keeps its repo even though its transcript folder differs.
        ref = resolve_project(f"{child}/.claude/worktrees/x", index(parent, child),
                              tx_folder=encode_path(f"{child}/.claude/worktrees/x"), isdir=isdir_of(parent, child))
        self.assertEqual(ref.key, child)

    def test_alias_wins_over_heuristics(self):
        a, b = f"{D}/apps/one", f"{D}/apps/two"
        ref = resolve_project(f"{D}/old", index(a, b), tx_folder=encode_path(b),
                              aliases={f"{D}/old": a}, isdir=isdir_of(a, b))
        self.assertEqual(ref.path, a)

    def test_unique_basename_when_no_transcript(self):
        new = f"{D}/apps/sched/sched-app"
        ref = resolve_project(f"{D}/sched_app", index(new, f"{D}/x"), isdir=isdir_of(new))
        self.assertEqual(ref.path, new)

    def test_lost_and_ambiguous(self):
        ref = resolve_project(f"{D}/gone", index(), isdir=isdir_of())
        self.assertEqual((ref.key, ref.path, ref.moved_from, ref.ambiguous), (f"{D}/gone", None, f"{D}/gone", False))
        a, b = f"{D}/x/gone", f"{D}/y/gone"
        ref = resolve_project(f"{D}/gone", index(a, b), isdir=isdir_of(a, b))
        self.assertTrue(ref.ambiguous)
        self.assertIsNone(ref.path)


class StateTest(unittest.TestCase):
    NOW = 10_000_000

    def tx(self, ago=10**9, interrupted=False, open_step=False):
        plan = [{"content": "s", "status": "in_progress" if open_step else "completed"}]
        return {"last_write": self.NOW - ago, "interrupted": interrupted, "plan": plan}

    def test_each_state(self):
        s = lambda *a: state_of(*a, now=self.NOW)
        self.assertEqual(s(None, True, True, self.tx(ago=5_000)), "working")
        self.assertEqual(s(None, True, True, self.tx(ago=WORKING_WINDOW_MS + 1)), "open")
        self.assertEqual(s("blocked", True, False, self.tx()), "waiting")
        self.assertEqual(s("blocked", False, False, self.tx()), "idle")      # an older turn's question
        self.assertEqual(s("review_ready", True, True, self.tx()), "review")
        self.assertEqual(s(None, True, False, self.tx(interrupted=True, open_step=True)), "stopped")
        self.assertEqual(s(None, True, False, self.tx(interrupted=True)), "idle")  # nothing left open
        self.assertEqual(s("completed", True, False, None), "idle")

    def test_order(self):
        s = lambda *a: state_of(*a, now=self.NOW)
        # Working beats everything; stopped beats a stale-looking waiting summary.
        self.assertEqual(s("blocked", True, True, self.tx(ago=1, interrupted=True, open_step=True)), "working")
        self.assertEqual(s("blocked", True, False, self.tx(interrupted=True, open_step=True)), "stopped")
        self.assertEqual(s("blocked", True, True, self.tx()), "waiting")


if __name__ == "__main__":
    unittest.main()
