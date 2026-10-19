import unittest

from mishlat import view
from mishlat.model import DAY_MS

NOW = 1000 * DAY_MS
MIN = 60_000


def sess(state, **kw):
    s = {"id": kw.pop("id", "local_x"), "state": state, "title": "T", "project": "/p", "question": None,
         "detail": None, "step": None, "steps_done": 0, "steps_total": 0, "first_prompt": None,
         "last_activity": NOW - MIN, "attention": state in ("waiting", "review", "stopped"), "transcript": True}
    s.update(kw)
    return s


def proj(name, sessions=(), **kw):
    p = {"key": "/" + name, "name": name, "path": "/" + name, "moved_from": [], "ambiguous": False,
         "is_repo": False, "branch": None, "dirty": None, "scratch": False, "working": 0, "open": 0,
         "waiting": 0, "review": 0, "stopped": 0, "attention": 0, "last_activity": NOW - MIN,
         "sessions": list(sessions)}
    p.update(kw)
    return p


class EnglishTest(unittest.TestCase):
    def setUp(self):
        from mishlat.strings import set_lang
        set_lang("en")

    def tearDown(self):
        from mishlat.strings import set_lang
        set_lang("he")

    def test_strings_in_english(self):
        from mishlat.strings import EN, locale_lang, t
        self.assertEqual(view.format_age(NOW - 61 * MIN, NOW), "an hour ago")
        self.assertEqual(view.format_age(NOW - 3 * DAY_MS, NOW), "3 days ago")
        self.assertEqual(view.format_age(NOW - 10_000, NOW), "now")
        self.assertEqual(view.count_label(7), "7 sessions")
        self.assertEqual(view.subline(sess("working", step="Build", steps_done=1, steps_total=4)), "step 2/4: \u2068Build\u2069")
        self.assertEqual(view.subline(sess("waiting", question="permission prompt")), "asks you to approve an action")
        self.assertEqual(view.subline(sess("waiting", question="input needed")), "needs your input")
        self.assertEqual(view.cleanup_reason_text(sess("idle", cleanup="old", last_activity=NOW - 45 * DAY_MS), NOW),
                         "stale: untouched for 45 days")
        self.assertEqual(view.status_text(None, NOW, scanning=True), "scanning…")
        self.assertEqual(t("not a key"), "not a key")
        self.assertEqual(locale_lang({"LANG": "en_US.UTF-8"}), "en")
        self.assertEqual(locale_lang({"LC_ALL": "he_IL.UTF-8", "LANG": "en_US.UTF-8"}), "he")
        self.assertEqual(locale_lang({}), "en")
        for key, value in EN.items():  # every placeholder survives the translation
            import re
            self.assertEqual(sorted(re.findall(r"\{\w+\}", key)), sorted(re.findall(r"\{\w+\}", value)), key)


class AgeTest(unittest.TestCase):
    def test_ages(self):
        cases = [(10_000, "עכשיו"), (5 * MIN, "לפני 5 דק׳"), (61 * MIN, "לפני שעה"), (125 * MIN, "לפני שעתיים"),
                 (5 * 60 * MIN, "לפני 5 שע׳"), (DAY_MS + 1, "אתמול"), (2 * DAY_MS, "לפני יומיים"),
                 (4 * DAY_MS, "לפני 4 ימים"), (8 * DAY_MS, "לפני שבוע"), (15 * DAY_MS, "לפני שבועיים"),
                 (22 * DAY_MS, "לפני 3 שבועות"), (31 * DAY_MS, "לפני חודש"), (400 * DAY_MS, "לפני שנה")]
        for ago, text in cases:
            self.assertEqual(view.format_age(NOW - ago, NOW), text, ago)
        self.assertEqual(view.format_age(0, NOW), "—")
        self.assertEqual(view.short_age(NOW - 61 * MIN, NOW), "שעה")


class LabelTest(unittest.TestCase):
    def test_sublines(self):
        self.assertEqual(view.subline(sess("waiting", question="Commit?")), "Commit?")
        self.assertEqual(view.subline(sess("waiting")), "מחכה לתשובה שלך")
        self.assertEqual(view.subline(sess("waiting", question="permission prompt")), "מבקש אישור לפעולה")
        self.assertEqual(view.subline(sess("waiting", question="dialog open")), "חלון פתוח באפליקציה")
        self.assertEqual(view.subline(sess("waiting", question="worker request")), "מבקש אישור ל-worker")
        self.assertEqual(view.subline(sess("waiting", question="something new")), "something new")
        self.assertEqual(view.subline(sess("review", detail="PDF ready")), "PDF ready")
        self.assertEqual(view.subline(sess("stopped", step="Write", steps_done=1, steps_total=3)),
                         "נעצר באמצע · צעד 2/3: \u2068Write\u2069")
        self.assertEqual(view.subline(sess("working", step="Build", steps_done=1, steps_total=4)), "צעד 2/4: \u2068Build\u2069")
        self.assertEqual(view.subline(sess("working")), "עובד עכשיו")
        self.assertEqual(view.subline(sess("idle", steps_done=5, steps_total=5)), "5/5 צעדים הושלמו")
        self.assertEqual(view.subline(sess("idle", first_prompt="hello")), "hello")

    def test_counts_badges_notes(self):
        self.assertEqual([view.count_label(n) for n in (0, 1, 7)], ["אין שיחות", "שיחה אחת", "7 שיחות"])
        p = proj("shedu", [sess("working")] * 2, working=1, waiting=1, branch="main", dirty=True)
        self.assertEqual(view.project_badges(p), [("● 1", "working"), ("◐ 1", "waiting"), ("2 שיחות", ""), ("main ✎", "")])
        moved = proj("book", [sess("idle", transcript=False)], moved_from=["/h/Desktop/book"])
        self.assertEqual(view.project_note(moved, "/h"), "הוזזה מ־\u2066~/Desktop/book\u2069 · 1 בלי טרנסקריפט")
        general = proj("כללי", [sess("idle", cwd="/h/.config/Claude/scratch-workspaces/a/s1")], path=None,
                       general=True, moved_from=["/h/Desktop/gone"])
        self.assertEqual(view.project_note(general, "/h"),
                         "מתיקיות שכבר לא קיימות: \u2066gone\u2069\n1 שיחות זמניות של האפליקציה")
        self.assertIsNone(view.project_note(proj("ok"), "/h"))

    def test_assign_choices_and_started_line(self):
        index = {"projects": [proj("a", path="/h/a"), proj("כללי", path=None, key="general")]}
        self.assertEqual(view.assign_choices(index), [("a", "/h/a")])
        self.assertEqual(view.started_line(sess("idle", started_in="/h/Desktop/shedu"), {}, "/h"),
                         "התחילה ב־ \u2066~/Desktop/shedu\u2069")
        self.assertEqual(view.started_line(sess("idle", started_in="general"), {}, "/h"), "התחילה ב־כללי")
        self.assertIsNone(view.started_line(sess("idle"), {}, "/h"))

    def test_project_edge(self):
        self.assertEqual(view.project_edge(proj("a", waiting=1, working=1)), "waiting")
        self.assertEqual(view.project_edge(proj("a", working=1)), "working")
        self.assertIsNone(view.project_edge(proj("a")))

    def test_cleanup_view_model(self):
        a = sess("idle", id="a", cleanup="old", last_activity=NOW - 45 * DAY_MS)
        b = sess("idle", id="b", cleanup="gone")
        index = {"projects": [proj("p", [a, b])], "cleanup": ["b", "a"],
                 "totals": {"cleanup": 2, "cleanup_by": {"old": 1, "gone": 1}}}
        self.assertEqual([s["id"] for s in view.cleanup_list(index)], ["b", "a"])
        self.assertEqual([s["id"] for s in view.cleanup_list(index, {"b": {}})], ["a"])
        self.assertEqual(view.cleanup_reason_text(a, NOW), "ישנה: לא נגעו בה 45 יום")
        self.assertEqual(view.cleanup_reason_text(b, NOW), "הפרויקט כבר לא קיים")
        self.assertEqual(view.cleanup_counts(index), {"old": 1, "gone": 1})
        self.assertEqual([m for m, _ in view.FILTERS][-1], "cleanup")

    def test_filters_sections_status(self):
        w = sess("working", id="w")
        a = sess("waiting", id="a")
        old = proj("old", [sess("idle", last_activity=NOW - 40 * DAY_MS)], last_activity=NOW - 40 * DAY_MS)
        busy = proj("busy", [w, a], working=1, waiting=1, attention=1)
        index = {"projects": [busy, old], "attention": ["a"], "scanned_at": NOW - 5 * MIN, "errors": ["e"]}
        self.assertEqual([p["name"] for p in view.filter_projects(index, "active", NOW)], ["busy"])
        self.assertEqual([p["name"] for p in view.filter_projects(index, "week", NOW)], ["busy"])
        self.assertEqual(len(view.filter_projects(index, "all", NOW)), 2)
        self.assertEqual([(st, [s["id"] for s in rows]) for st, _, rows in view.sections(index)],
                         [("waiting", ["a"]), ("working", ["w"])])
        self.assertEqual(len(view.stale_list(index, NOW)), 1)
        self.assertEqual(view.status_text(index, NOW), "נסרק לפני 5 דק׳ · 1 שגיאות")
        self.assertEqual(view.status_text(None, NOW, scanning=True), "סורק…")
        label = view.session_menu_label(sess("waiting", title="x" * 50), {"/p": "apps/p"}, NOW)
        self.assertTrue(label.startswith("◐  p · " + "x" * 39 + "…"))


if __name__ == "__main__":
    unittest.main()
