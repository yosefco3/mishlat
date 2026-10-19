import unittest

from mishlat.folders import Folder, FolderIndex
from mishlat.live import Live
from mishlat.model import (DAY_MS, attention_sessions, build_index, entered, owner_of, search, stale_sessions,
                           work_project)
from mishlat.store import Record
from mishlat.transcripts import encode_path

D = "/h/Desktop"
NOW = 100 * DAY_MS


def rec(sid, cwd, cli=None, title="T", last=NOW - 1000, status=None, question=None, detail=None,
        fresh=True, archived=False):
    return Record(id=sid, cli_id=cli, title=title, cwd=cwd, last_activity=last, archived=archived,
                  starred=False, status=status, question=question, detail=detail, fresh=fresh)


def tx(folder, last_write=NOW - DAY_MS, cwd=None, title=None, first_prompt=None, plan=None, interrupted=False,
       writes=None, reads=None, local_writes=0):
    return {"title": title, "name": None, "first_prompt": first_prompt, "interrupted": interrupted,
            "plan": plan or [], "cwd": cwd, "folder": folder, "last_write": last_write, "path": "/x",
            "writes": writes or {}, "reads": reads or {}, "local_writes": local_writes}


def folders(*paths, repos=()):
    return FolderIndex([Folder(p, p in repos) for p in paths], [D])


def build(records, transcripts=None, live=None, fi=None, existing=(), **kw):
    return build_index(records, transcripts or {}, live or {}, fi or folders(), NOW,
                       isdir=lambda p: p in existing, **kw)


class BuildIndexTest(unittest.TestCase):
    def test_app_session_waiting_counts_and_attention(self):
        shedu = f"{D}/shedu"
        idx = build([rec("local_a", shedu, "c1", status="blocked", question="Commit?"),
                     rec("local_b", shedu, "c2", title="older", last=NOW - 5 * DAY_MS)],
                    {"c1": tx(encode_path(shedu))}, fi=folders(shedu, repos={shedu}), existing={shedu},
                    git=lambda p: {"is_repo": True, "branch": "main", "dirty": True})
        p = idx["projects"][0]
        self.assertEqual((p["name"], p["path"], p["waiting"], p["attention"], p["branch"], p["dirty"]),
                         ("shedu", shedu, 1, 1, "main", True))
        self.assertEqual([s["id"] for s in p["sessions"]], ["local_a", "local_b"])
        self.assertEqual(p["sessions"][0]["question"], "Commit?")
        self.assertEqual(idx["attention"], ["local_a"])
        self.assertEqual(idx["totals"]["attention"], 1)

    def test_terminal_only_sessions_and_archived_claims(self):
        w = f"{D}/w"
        idx = build([rec("local_arch", w, "c-arch", archived=True)],
                    {"c-arch": tx(encode_path(w), cwd=w), "c-cli": tx(encode_path(w), cwd=w, first_prompt="hello there")},
                    existing={w})
        sessions = idx["projects"][0]["sessions"]
        self.assertEqual([(s["id"], s["source"], s["title"]) for s in sessions], [("c-cli", "cli", "hello there")])

    def test_moved_folder_learns_for_siblings_without_transcript(self):
        old, new = f"{D}/web-site", f"{D}/web_site/web-site"
        decoy = f"{D}/web_site"
        idx = build([rec("local_a", old, "c1"), rec("local_b", old, "c-gone")],
                    {"c1": tx(encode_path(new))}, fi=folders(new, decoy), existing={new, decoy})
        keys = {s["id"]: s["project"] for p in idx["projects"] for s in p["sessions"]}
        self.assertEqual(keys, {"local_a": new, "local_b": new})
        p = next(p for p in idx["projects"] if p["key"] == new)
        self.assertEqual((p["name"], p["moved_from"]), ("web_site/web-site", [old]))
        self.assertFalse(p["sessions"][1]["transcript"])

    def test_gone_folders_and_scratch_go_to_general_last(self):
        repo, w = f"{D}/apps/appx", f"{D}/w"
        idx = build([rec("local_a", f"{D}/scheduler", last=NOW - 10),          # newest, but its folder is gone
                     rec("local_b", f"{D}/misc", last=NOW - 20),
                     rec("local_c", "/h/.config/Claude/scratch-workspaces/x/y/scratch-1", last=NOW - 30),
                     rec("local_d", w, last=NOW - 5 * DAY_MS)],
                    fi=folders(repo, w, repos={repo}), existing={repo, w})
        by_key = {p["key"]: p for p in idx["projects"]}
        general = by_key["general"]
        self.assertEqual((general["name"], general["path"], general["general"]), ("כללי", None, True))
        self.assertEqual([s["id"] for s in general["sessions"]], ["local_a", "local_b", "local_c"])
        self.assertEqual(general["moved_from"], [f"{D}/misc", f"{D}/scheduler"])
        self.assertEqual(idx["projects"][-1]["key"], "general")              # last, though newest
        self.assertNotIn(f"{D}/scheduler", by_key)
        self.assertEqual((by_key[repo]["sessions"], by_key[repo]["is_repo"]), ([], True))
        self.assertEqual((idx["totals"]["lost"], idx["totals"]["projects"], idx["totals"]["repos"]), (2, 2, 1))
        projects, sessions = search(idx, "scheduler")
        self.assertEqual(([p["key"] for p in projects], [s["id"] for s in sessions]), (["general"], ["local_a"]))

    def test_dismissed_until_newer_activity_and_attention_window(self):
        w = f"{D}/w"
        recs = [rec("local_a", w, status="blocked", last=NOW - 1000),
                rec("local_old", w, status="blocked", last=NOW - 20 * DAY_MS)]
        idx = build(recs, existing={w}, dismissed={"local_a": NOW - 1000})
        self.assertEqual(idx["attention"], [])
        idx = build(recs, existing={w}, dismissed={"local_a": NOW - 5000})  # newer activity since
        self.assertEqual(idx["attention"], ["local_a"])
        old = next(s for s in idx["projects"][0]["sessions"] if s["id"] == "local_old")
        self.assertEqual((old["state"], old["attention"]), ("waiting", False))

    def test_title_fallbacks_and_state_from_live(self):
        w = f"{D}/w"
        idx = build([rec("local_a", w, "c1", title="")],
                    {"c1": tx(encode_path(w), last_write=NOW - 1000, title="Custom")},
                    live={"c1": Live(7, "c1", w, None, None, 0)}, existing={w})
        s = idx["projects"][0]["sessions"][0]
        self.assertEqual((s["title"], s["state"], s["pid"]), ("Custom", "working", 7))
        idx = build([rec("local_b", w, None, title="")], existing={w})
        self.assertEqual(idx["projects"][0]["sessions"][0]["title"], "(ללא כותרת)")

    def test_cli_status_and_waiting_for(self):
        w = f"{D}/w"
        live = {"c1": Live(7, "c1", w, None, None, 0, status="waiting", waiting_for="permission prompt"),
                "c2": Live(8, "c2", w, None, None, 0, status="idle"),
                "c3": Live(9, "c3", w, None, None, 0, status="busy"),
                "c4": Live(10, "c4", w, None, None, 0, status="waiting", waiting_for="input needed")}
        idx = build([rec("local_a", w, "c1", status="completed", detail="all done"),
                     rec("local_b", w, "c2", status="blocked", question="Merge?"),
                     rec("local_c", w, "c3", status="blocked", question="Merge?"),
                     rec("local_d", w, "c4", status="blocked", question="Old?", fresh=False)],
                    {"c2": tx(encode_path(w), last_write=NOW - 1000)}, live=live, existing={w})
        rows = {s["id"]: s for s in idx["projects"][0]["sessions"]}
        a, b, c, d = rows["local_a"], rows["local_b"], rows["local_c"], rows["local_d"]
        self.assertEqual((a["state"], a["question"], a["waiting_for"], a["detail"]),
                         ("waiting", "permission prompt", "permission prompt", "all done"))
        self.assertEqual((b["state"], b["question"], b["waiting_for"]), ("waiting", "Merge?", None))  # idle, store wins
        self.assertEqual((c["state"], c["question"], c["waiting_for"]), ("working", None, None))
        self.assertEqual((d["state"], d["question"], d["waiting_for"]), ("waiting", "input needed", "input needed"))
        self.assertEqual(set(idx["attention"]), {"local_a", "local_b", "local_d"})
        self.assertEqual(idx["projects"][0]["waiting"], 3)
        self.assertEqual(idx["totals"]["working"], 1)


class DescriptionTest(unittest.TestCase):
    def test_user_text_wins_over_readme(self):
        a, b, c = f"{D}/a", f"{D}/b", f"{D}/c"
        fi = folders(a, b, c, repos={a, b, c})
        idx = build([], fi=fi, existing={a, b, c}, describe=lambda p: "from readme" if p in (a, b) else None,
                    descriptions={b: "the user's words"})
        by = {p["key"]: (p["description"], p["description_source"]) for p in idx["projects"]}
        self.assertEqual(by[a], ("from readme", "readme"))
        self.assertEqual(by[b], ("the user's words", "user"))
        self.assertEqual(by[c], (None, None))


class WorkTest(unittest.TestCase):
    SHEDU, MISHLAT, LEVELBOT = f"{D}/shedu", f"{D}/apps/mishlat", f"{D}/apps/tradebot"
    CANDS = sorted([f"{D}/shedu", f"{D}/apps/mishlat", f"{D}/apps/tradebot"], key=len, reverse=True)
    NAMES = {"shedu": [f"{D}/shedu"], "mishlat": [f"{D}/apps/mishlat"], "tradebot": [f"{D}/apps/tradebot"]}

    def test_owner_of_prefix_and_moved_name(self):
        self.assertEqual(owner_of(f"{D}/apps/mishlat/mishlat", self.CANDS, self.NAMES), self.MISHLAT)
        self.assertEqual(owner_of(f"{D}/tradebot/app", self.CANDS, self.NAMES), self.LEVELBOT)   # its old place
        self.assertEqual(owner_of("/h/tradebot/user_data", self.CANDS, self.NAMES), self.LEVELBOT)
        self.assertIsNone(owner_of(f"{D}/apps/mishlat-old/x", self.CANDS, {}))

    def test_old_path_of_a_moved_folder_counts_for_its_project(self):
        book = f"{D}/cookbook"
        cands = sorted([book, f"{D}/notes", f"{D}/book"], key=len, reverse=True)
        old = {f"{D}/book": book}
        self.assertEqual(owner_of(f"{D}/book/manuscript/x.md", cands, {}, old), book)
        # 40 writes to the old path of its own folder, 6 to notes: it stays.
        self.assertIsNone(work_project(tx("f", writes={f"{D}/book/manuscript": 40, f"{D}/notes": 6}),
                                       book, cands, {}, old))

    def test_work_project_rule(self):
        w = lambda **kw: work_project(tx("f", **kw), self.SHEDU, self.CANDS, self.NAMES)
        self.assertEqual(w(writes={f"{D}/apps/mishlat": 40}, local_writes=10), self.MISHLAT)
        self.assertIsNone(w(writes={f"{D}/apps/mishlat": 6}, local_writes=4))           # own folder wrote enough
        self.assertEqual(w(reads={f"{D}/tradebot": 17}), self.LEVELBOT)                 # read-only, enough
        self.assertIsNone(w(reads={f"{D}/tradebot": 10}))                               # below the bar
        self.assertIsNone(w(writes={f"{D}/shedu/x": 20}))                               # its own folder
        self.assertIsNone(work_project(None, self.SHEDU, self.CANDS, self.NAMES))

    def test_build_index_moves_and_the_manual_assignment_wins(self):
        repos = {self.SHEDU, self.MISHLAT, self.LEVELBOT}
        fi = folders(*repos, repos=repos)
        recs = [rec("local_m", self.SHEDU, "c1", title="dashboard"), rec("local_s", self.SHEDU, "c2", title="shedu work")]
        txs = {"c1": tx(encode_path(self.SHEDU), writes={f"{self.MISHLAT}/mishlat": 40}),
               "c2": tx(encode_path(self.SHEDU), writes={f"{self.MISHLAT}/mishlat": 40})}
        idx = build(recs, txs, fi=fi, existing=repos)
        where = {s["id"]: (s["project"], s["started_in"], s["assigned"]) for p in idx["projects"] for s in p["sessions"]}
        self.assertEqual(where["local_m"], (self.MISHLAT, self.SHEDU, False))
        idx = build(recs, txs, fi=fi, existing=repos,
                    assignments={"local_s": self.SHEDU, "local_m": f"{D}/gone"})   # a gone folder is ignored
        where = {s["id"]: (s["project"], s["started_in"], s["assigned"]) for p in idx["projects"] for s in p["sessions"]}
        self.assertEqual(where["local_s"], (self.SHEDU, None, True))
        self.assertEqual(where["local_m"], (self.MISHLAT, self.SHEDU, False))
        idx = build([rec("local_x", self.SHEDU, "c3")], {"c3": tx(encode_path(self.SHEDU))}, fi=fi, existing=repos,
                    assignments={"local_x": self.LEVELBOT})
        p = next(p for p in idx["projects"] if p["sessions"])
        self.assertEqual((p["key"], p["sessions"][0]["started_in"]), (self.LEVELBOT, self.SHEDU))


class QueryTest(unittest.TestCase):
    def setUp(self):
        a, b = f"{D}/book", f"{D}/trading/prop"
        self.idx = build([rec("local_1", a, "c1", title="תיקון פרק 4", status="blocked", question="איזה פתיח?"),
                          rec("local_2", b, "c2", title="בוט", last=NOW - 40 * DAY_MS),
                          rec("local_3", b, "c3", title="x", status="review_ready", detail="PDF ready")],
                         {"c2": tx(encode_path(b), last_write=NOW - 40 * DAY_MS, first_prompt="בדוק את פרק 4 בבקשה")},
                         existing={a, b})

    def test_search_fields(self):
        projects, sessions = search(self.idx, "פרק 4")
        self.assertEqual([s["id"] for s in sessions], ["local_1", "local_2"])
        self.assertEqual(projects, [])
        projects, sessions = search(self.idx, "TRADING")
        self.assertEqual([p["name"] for p in projects], ["trading/prop"])
        self.assertEqual({s["id"] for s in sessions}, {"local_2", "local_3"})  # by project name
        self.assertEqual(search(self.idx, "  "), ([], []))
        self.assertEqual([s["id"] for s in search(self.idx, "pdf")[1]], ["local_3"])

    def test_attention_order_stale_and_entered(self):
        self.assertEqual([s["id"] for s in attention_sessions(self.idx)], ["local_1", "local_3"])
        self.assertEqual([s["id"] for s in stale_sessions(self.idx, NOW)], ["local_2"])
        self.assertEqual([s["id"] for s in entered(None, self.idx)], ["local_1", "local_3"])
        self.assertEqual(entered(self.idx, self.idx), [])
        later = build([rec("local_1", f"{D}/book", "c1", status="review_ready")], existing={f"{D}/book"})
        self.assertEqual([(s["id"], s["state"]) for s in entered(self.idx, later)], [("local_1", "review")])


if __name__ == "__main__":
    unittest.main()


class CleanupTest(unittest.TestCase):
    W = f"{D}/w"

    def index(self, recs, txs=None, kept=None, **kw):
        from mishlat.model import mark_cleanup
        idx = build(recs, txs or {}, existing={self.W, f"{D}/v"}, fi=folders(self.W, f"{D}/v"), **kw)
        mark_cleanup(idx, NOW, 30, kept)
        return idx

    def reasons(self, idx):
        return {s["id"]: s["cleanup"] for p in idx["projects"] for s in p["sessions"]}

    def test_each_rule_and_the_exemptions(self):
        from mishlat.store import Record
        def r(sid, title="t", last=NOW - 1000, turns=5, cwd=None, **kw):
            base = rec(sid, cwd or self.W, cli=f"c-{sid}", title=title, last=last, **kw)
            return Record(**{**base.__dict__, "turns": turns})
        recs = [
            r("local_new", title="newest"),                                               # newest in w: exempt
            r("local_old", title="old one", last=NOW - 40 * DAY_MS),                      # old
            r("local_empty", title="empty", last=NOW - 10 * DAY_MS, turns=1),             # empty (no writes)
            r("local_dup_old", title="same", last=NOW - 3 * DAY_MS),                      # duplicate of a newer one
            r("local_dup_new", title="same", last=NOW - 2 * DAY_MS),
            r("local_notx", title="lost history", last=NOW - 2 * DAY_MS),                 # no transcript
            r("local_gone", title="gone", cwd=f"{D}/gone", last=NOW - DAY_MS),            # folder gone -> gone
            r("local_star", title="star", last=NOW - 90 * DAY_MS, archived=False),
            r("local_wait", title="waits", last=NOW - 90 * DAY_MS, status="blocked", question="?"),
            r("local_v_only", title="only one in v", cwd=f"{D}/v", last=NOW - 90 * DAY_MS),  # newest in v: exempt
        ]
        recs[7] = Record(**{**recs[7].__dict__, "starred": True})
        txs = {f"c-{sid}": tx(encode_path(self.W), last_write=NOW - 50 * DAY_MS)
               for sid in ("local_new", "local_old", "local_empty", "local_dup_old", "local_dup_new", "local_star",
                           "local_wait")}
        txs["c-local_old"] = tx(encode_path(self.W), last_write=NOW - 40 * DAY_MS, writes={f"{self.W}/a": 3})
        txs["c-local_v_only"] = tx(encode_path(f"{D}/v"), last_write=NOW - 90 * DAY_MS)
        idx = self.index(recs, txs)
        got = self.reasons(idx)
        self.assertEqual(got["local_new"], None)
        self.assertEqual(got["local_old"], "old")
        self.assertEqual(got["local_empty"], "empty")
        self.assertEqual(got["local_dup_old"], "duplicate")
        self.assertIsNone(got["local_dup_new"])
        self.assertEqual(got["local_notx"], "no_transcript")
        self.assertEqual(got["local_gone"], "gone")
        self.assertIsNone(got["local_star"])
        self.assertIsNone(got["local_wait"])
        self.assertIsNone(got["local_v_only"])
        self.assertEqual(idx["totals"]["cleanup"], 5)
        self.assertEqual(idx["totals"]["cleanup_by"]["old"], 1)
        self.assertEqual(idx["cleanup"][0], "local_gone")  # newest first
        # Kept by the user, and assigned by hand: never listed.
        idx = self.index(recs, txs, kept={"local_old": NOW})
        self.assertIsNone(self.reasons(idx)["local_old"])
        idx = self.index(recs, txs, assignments={"local_empty": self.W})
        self.assertIsNone(self.reasons(idx)["local_empty"])
