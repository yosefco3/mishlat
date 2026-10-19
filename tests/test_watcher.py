import os
import unittest

from mishlat.watcher import Coalescer, ScanRunner, watched_dirs
from tests.helpers import FakeHome


class FakeTimers:
    def __init__(self):
        self.pending = []

    def add(self, delay, fn):
        self.pending.append((delay, fn))
        return len(self.pending)

    def fire_all(self):
        pending, self.pending = self.pending, []
        for _, fn in pending:
            fn()


class CoalescerTest(unittest.TestCase):
    def test_a_burst_gives_one_call_and_a_later_poke_another(self):
        timers, calls = FakeTimers(), []
        c = Coalescer(lambda: calls.append(1), 2000, timeout_add=timers.add)
        for _ in range(5):
            c.poke()
        self.assertEqual([d for d, _ in timers.pending], [2000])
        timers.fire_all()
        self.assertEqual(calls, [1])
        c.poke()
        timers.fire_all()
        self.assertEqual(calls, [1, 1])


class ScanRunnerTest(unittest.TestCase):
    def make(self, scan):
        self.done, self.busy = [], []
        return ScanRunner(scan, self.done.append, self.busy.append,
                          start_thread=lambda target: target(), idle_add=lambda fn, *a: fn(*a))

    def test_requests_during_a_scan_give_one_more_scan(self):
        scans = []

        def scan():
            scans.append(1)
            if len(scans) == 1:
                runner.request()
                runner.request()  # two requests while busy: still one more scan
            return {"n": len(scans)}
        runner = self.make(scan)
        runner.request()
        self.assertEqual(self.done, [{"n": 1}, {"n": 2}])
        self.assertEqual(runner.count, 2)
        self.assertFalse(runner.busy)
        self.assertEqual(self.busy, [True, False, True, False])

    def test_an_exception_is_reported_not_raised(self):
        def scan():
            raise OSError("gone")
        runner = self.make(scan)
        runner.request()
        self.assertIsInstance(self.done[0], OSError)
        self.assertFalse(runner.busy)


class WatchedDirsTest(unittest.TestCase):
    def test_dirs(self):
        home = FakeHome()
        try:
            home.add_record("local_a", "/w")
            home.add_transcript("/w/a", "c1", [])
            dirs = watched_dirs(home.root)
            self.assertIn(home.path(".config/Claude/claude-code-sessions/org1/ws1"), dirs)
            self.assertIn(home.path(".claude/projects"), dirs)
            self.assertIn(home.path(".claude/projects/-w-a"), dirs)
            self.assertIn(home.path(".claude/sessions"), dirs)
        finally:
            home.cleanup()


if __name__ == "__main__":
    unittest.main()
