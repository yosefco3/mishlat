import os
import time
import unittest

from mishlat.store import StoreReader, parse_record
from tests.helpers import FakeHome


class ParseRecordTest(unittest.TestCase):
    def base(self, **kw):
        rec = {"sessionId": "local_a", "cwd": "/w", "title": "T", "lastActivityAt": 5,
               "cliSessionId": "c1", "lastAssistantUuid": "u1"}
        rec.update(kw)
        return rec

    def test_waiting_record(self):
        r = parse_record(self.base(postTurnSummary={"status_category": "blocked", "needs_action": "Q?",
                                                     "status_detail": "Q?", "summarizes_uuid": "u1"}))
        self.assertEqual((r.status, r.question, r.fresh, r.cli_id), ("blocked", "Q?", True, "c1"))

    def test_summary_of_an_older_turn_is_not_fresh(self):
        r = parse_record(self.base(postTurnSummary={"status_category": "blocked", "summarizes_uuid": "u0"}))
        self.assertFalse(r.fresh)

    def test_missing_uuid_counts_as_fresh(self):
        r = parse_record(self.base(lastAssistantUuid=None, postTurnSummary={"status_category": "blocked",
                                                                             "summarizes_uuid": "u0"}))
        self.assertTrue(r.fresh)

    def test_rejects_unknown_shapes(self):
        self.assertIsNone(parse_record({"sessionId": "cse_1", "cwd": "/w"}))
        self.assertIsNone(parse_record({"sessionId": "local_a"}))
        self.assertIsNone(parse_record(["not", "a", "dict"]))

    def test_last_focused(self):
        self.assertEqual(parse_record(self.base(lastFocusedAt=777)).last_focused, 777)
        self.assertEqual(parse_record(self.base()).last_focused, 0)
        self.assertEqual(parse_record(self.base(lastFocusedAt="soon")).last_focused, 0)

    def test_turns(self):
        self.assertEqual(parse_record(self.base(completedTurns=7)).turns, 7)
        self.assertIsNone(parse_record(self.base(completedTurns=True)).turns)
        self.assertIsNone(parse_record(self.base()).turns)

    def test_archived_and_starred_and_created_fallback(self):
        r = parse_record(self.base(isArchived=True, isStarred=True, lastActivityAt=None, createdAt=7))
        self.assertTrue(r.archived and r.starred)
        self.assertEqual(r.last_activity, 7)


class StoreReaderTest(unittest.TestCase):
    def setUp(self):
        self.home = FakeHome()

    def tearDown(self):
        self.home.cleanup()

    def test_reads_and_caches(self):
        self.home.add_record("local_a", "/w/a")
        p = self.home.add_record("local_b", "/w/b")
        reader = StoreReader()
        records, errors = reader.read(self.home.root)
        self.assertEqual(({r.id for r in records}, errors, reader.parsed), ({"local_a", "local_b"}, [], 2))
        records, _ = reader.read(self.home.root)
        self.assertEqual((len(records), reader.parsed), (2, 0))
        # A changed file is parsed again.
        self.home.add_record("local_b", "/w/b", title="new title, longer")
        os.utime(p, (time.time() + 5, time.time() + 5))
        records, _ = reader.read(self.home.root)
        self.assertEqual(reader.parsed, 1)
        self.assertIn("new title, longer", {r.title for r in records})

    def test_broken_file_becomes_one_error_line(self):
        self.home.add_record("local_a", "/w/a")
        with open(os.path.join(os.path.dirname(self.home.add_record("local_b", "/w")), "local_c.json"), "w") as f:
            f.write("{broken")
        records, errors = StoreReader().read(self.home.root)
        self.assertEqual(len(records), 2)
        self.assertEqual(len(errors), 1)
        self.assertIn("1 of 3", errors[0])

    def test_no_store_says_so(self):
        records, errors = StoreReader().read(self.home.root)
        self.assertEqual(records, [])
        self.assertIn("no session records", errors[0])


if __name__ == "__main__":
    unittest.main()
