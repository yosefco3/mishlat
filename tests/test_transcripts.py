import json
import os
import time
import unittest

from mishlat.transcripts import (apply_line, apply_op, clean_prompt, empty, encode_path,
                                 index_transcripts, plan_summary, step_open, work_of)
from tests.helpers import FakeHome, tool_result, tool_use, user, user_blocks


def items(*specs):
    return [{"content": c, "status": s} for c, s in specs]


def feed(*lines):
    data = empty()
    for line in lines:
        apply_line(data, (json.dumps(line) + "\n").encode())
    return data


class ApplyOpTest(unittest.TestCase):
    def test_items_advance_done_start(self):
        plan = apply_op([], {"items": items(("a", "in_progress"), ("b", "pending"), ("c", "pending"))})
        plan = apply_op(plan, {"advance": True})
        self.assertEqual([i["status"] for i in plan], ["completed", "in_progress", "pending"])
        plan = apply_op(plan, {"done": [2], "start": 3})
        self.assertEqual([i["status"] for i in plan], ["completed", "completed", "in_progress"])
        self.assertEqual(plan_summary(plan), ("c", 2, 3))

    def test_all_done_and_bad_input(self):
        plan = apply_op(items(("a", "in_progress"), ("b", "pending")), {"all_done": True})
        self.assertFalse(step_open(plan))
        self.assertEqual(apply_op(plan, "nonsense"), plan)
        plan = apply_op([], {"items": [{"content": ""}, {"status": "pending"}, {"content": "x", "status": "odd"}]})
        self.assertEqual(plan, items(("x", "pending")))
        self.assertEqual(apply_op(plan, {"start": True}), plan)  # a bool is not a step number


class ApplyLineTest(unittest.TestCase):
    def test_titles_and_first_prompt(self):
        data = feed({"type": "custom-title", "customTitle": "My title"},
                    {"type": "agent-name", "agentName": "agent"},
                    user('<local-command-caveat>x</local-command-caveat>'),
                    user("Fix the bug\n<pasted_content id=\"1\">huge\npaste</pasted_content>  please", cwd="/p"),
                    user("second prompt", cwd="/p"))
        self.assertEqual((data["title"], data["name"]), ("My title", "agent"))
        self.assertEqual(data["first_prompt"], "Fix the bug … please")
        self.assertEqual(data["cwd"], "/p")

    def test_meta_sidechain_and_tool_results_are_not_prompts(self):
        data = feed(user_blocks("Base directory for this skill", isMeta=True),
                    user("from a subagent", isSidechain=True),
                    tool_result("lots of output"))
        self.assertIsNone(data["first_prompt"])

    def test_interruption_then_new_prompt(self):
        data = feed(tool_use("mcp__ccd_turn__update_plan", {"items": items(("a", "in_progress"))}),
                    user_blocks("[Request interrupted by user]"))
        self.assertTrue(data["interrupted"] and step_open(data["plan"]))
        data2 = feed(user_blocks("[Request interrupted by user]"), user("<task-notification>x"))
        self.assertTrue(data2["interrupted"])  # an automated event does not resume the work
        data3 = feed(user_blocks("[Request interrupted by user]"), user("go on"))
        self.assertFalse(data3["interrupted"])

    def test_wrap_up_checks_off_and_todowrite(self):
        data = feed(tool_use("mcp__ccd_turn__update_plan", {"items": items(("a", "in_progress"))}),
                    tool_use("mcp__ccd_turn__wrap_up", {"recap": "done"}))
        self.assertFalse(step_open(data["plan"]))
        data = feed(tool_use("TodoWrite", {"todos": [{"content": "t", "status": "in_progress", "activeForm": "T"}]}))
        self.assertEqual(plan_summary(data["plan"]), ("t", 0, 1))

    def test_broken_line_is_ignored(self):
        data = empty()
        apply_line(data, b"{not json\n")
        self.assertEqual(data, empty())

    def test_spaced_json_is_read_too(self):
        home = FakeHome()
        try:
            p = home.transcript_path("/w", "c9")
            with open(p, "w") as f:
                f.write(json.dumps(user("spaced")) + "\n")
            self.assertEqual(index_transcripts(home.root, {})["c9"]["first_prompt"], "spaced")
        finally:
            home.cleanup()

    def test_encode_and_clean(self):
        self.assertEqual(encode_path("/home/y/Desktop/web_site/web-site"),
                         "-home-y-Desktop-web-site-web-site")
        self.assertEqual(len(clean_prompt("x" * 500)), 200)


class WorkTest(unittest.TestCase):
    H = "/home/u"

    def test_writes_reads_and_local_writes(self):
        w = lambda name, inp: work_of(name, inp, self.H)
        self.assertEqual(w("Write", {"file_path": "/home/u/Desktop/apps/mishlat/mishlat/deep/x.py"}),
                         ("write", {"/home/u/Desktop/apps/mishlat/mishlat"}))
        self.assertEqual(w("Bash", {"command": "cd ~/Desktop/apps/mishlat && cat > mishlat/x.py <<'EOF'"}),
                         ("write", {"/home/u/Desktop/apps/mishlat"}))
        self.assertEqual(w("Bash", {"command": "git commit -m 'x'"}), ("write", set()))
        self.assertEqual(w("Bash", {"command": "grep -c x ~/Desktop/shedu/a.go 2>/dev/null > /dev/null"}),
                         ("read", {"/home/u/Desktop/shedu/a.go"}))
        self.assertEqual(w("Read", {"file_path": "/home/u/Desktop/book/ch1.md"}), ("read", {"/home/u/Desktop/book/ch1.md"}))
        self.assertEqual(w("Bash", {"command": 'ls "~/Desktop/a b/c.mp3"'}), ("read", {"/home/u/Desktop/a"}))  # no backslash
        self.assertEqual(w("Bash", {"command": "cat ~/.claude/settings.json"}), ("read", set()))  # hidden: not a project
        self.assertEqual(w("Bash", {"command": "ls ~/x"}), ("read", {"/home/u/x"}))
        self.assertEqual(w("Write", {"file_path": "/tmp/scratch/plan.html"}), ("skip", set()))
        self.assertEqual(w("Bash", {"command": "cat > /tmp/x.txt <<'EOF'"}), ("skip", set()))

    def test_last_ts_comes_from_the_lines_not_the_file(self):
        home = FakeHome()
        try:
            p = home.add_transcript("/w", "c7", [dict(user("a"), timestamp="2026-07-01T10:00:00.000Z"),
                                                 dict(tool_result("x"), timestamp="2026-07-02T10:00:00.000Z")])
            os.utime(p, (time.time(), time.time()))  # a fresh mtime, as after a copy
            out = index_transcripts(home.root, {})
            self.assertEqual(out["c7"]["last_write"], 1782986400000)  # 2026-07-02T10:00Z
            p2 = home.add_transcript("/w", "c8", [user("no time")])
            self.assertAlmostEqual(out and index_transcripts(home.root, {})["c8"]["last_write"] / 1000,
                                   os.stat(p2).st_mtime, delta=2)
        finally:
            home.cleanup()

    def test_counts_add_up_in_a_transcript(self):
        data = empty()
        for line in (tool_use("Write", {"file_path": "/home/u/Desktop/a/f.py"}),
                     tool_use("Edit", {"file_path": "/home/u/Desktop/a/g.py"}),
                     tool_use("Bash", {"command": "git add -A"}),
                     tool_use("Read", {"file_path": "/home/u/Desktop/b/r.md"})):
            apply_line(data, (json.dumps(line) + "\n").encode(), "/home/u")
        self.assertEqual(data["writes"], {"/home/u/Desktop/a/f.py": 1, "/home/u/Desktop/a/g.py": 1})
        self.assertEqual((data["local_writes"], data["reads"]), (1, {"/home/u/Desktop/b/r.md": 1}))


class IndexTest(unittest.TestCase):
    def setUp(self):
        self.home = FakeHome()

    def tearDown(self):
        self.home.cleanup()

    def test_incremental_growth_and_half_line(self):
        p = self.home.add_transcript("/w/a", "c1", [user("first")])
        cache = {}
        out = index_transcripts(self.home.root, cache)
        self.assertEqual(out["c1"]["first_prompt"], "first")
        self.assertEqual(out["c1"]["folder"], "-w-a")
        offset = cache[p]["offset"]
        # A half-written line does not move the offset.
        with open(p, "ab") as f:
            f.write(b'{"type":"custom-title","customTi')
        out = index_transcripts(self.home.root, cache)
        self.assertEqual(cache[p]["offset"], offset)
        self.assertIsNone(out["c1"]["title"])
        with open(p, "ab") as f:
            f.write(b'tle":"Done"}\n')
        os.utime(p, (time.time() + 3, time.time() + 3))
        out = index_transcripts(self.home.root, cache)
        self.assertEqual(out["c1"]["title"], "Done")
        self.assertEqual(out["c1"]["first_prompt"], "first")  # kept from the earlier read

    def test_truncated_file_is_read_again_and_deleted_leaves_cache(self):
        p = self.home.add_transcript("/w/a", "c1", [user("one"), user("two")])
        cache = {}
        index_transcripts(self.home.root, cache)
        with open(p, "wb") as f:
            f.write((json.dumps(user("new start")) + "\n").encode())
        os.utime(p, (time.time() + 5, time.time() + 5))
        self.assertEqual(index_transcripts(self.home.root, cache)["c1"]["first_prompt"], "new start")
        os.remove(p)
        self.assertEqual(index_transcripts(self.home.root, cache), {})
        self.assertEqual(cache, {})

    def test_subagent_files_are_not_sessions(self):
        self.home.add_transcript("/w/a", "c1", [user("main")])
        sub = self.home.path(".claude/projects/-w-a/c1/subagents")
        os.makedirs(sub)
        with open(os.path.join(sub, "agent-1.jsonl"), "w") as f:
            f.write(json.dumps(user("sub")) + "\n")
        self.assertEqual(set(index_transcripts(self.home.root, {})), {"c1"})

    def test_unchanged_file_is_not_read(self):
        p = self.home.add_transcript("/w/a", "c1", [user("first")])
        cache = {}
        index_transcripts(self.home.root, cache)
        cache[p]["data"]["first_prompt"] = "from cache"
        self.assertEqual(index_transcripts(self.home.root, cache)["c1"]["first_prompt"], "from cache")


if __name__ == "__main__":
    unittest.main()
