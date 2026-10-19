import unittest

from mishlat.tray import (MENU_ROWS, badge_count, icon_file, menu_model, notification_text, to_notify,
                          tooltip)
from tests.test_model_index import D, NOW, build, rec


class TrayModelTest(unittest.TestCase):
    def index(self, n_waiting=1, extra=()):
        w = f"{D}/book"
        recs = [rec(f"local_{i}", w, title=f"שאלה {i}", status="blocked", question=f"Q{i}?", last=NOW - 1000 - i)
                for i in range(n_waiting)]
        return build(recs + list(extra), existing={w})

    def test_icon_per_count(self):
        self.assertTrue(icon_file("/i", 0).endswith("mishlat-0.svg"))
        self.assertTrue(icon_file("/i", 7).endswith("mishlat-3.svg"))
        self.assertEqual(badge_count(self.index(2)), 2)
        self.assertEqual(badge_count(None), 0)

    def test_menu_model(self):
        model = menu_model(self.index(MENU_ROWS + 2), NOW)
        self.assertEqual(model[0], ("header", f"מחכים לך · {MENU_ROWS + 2}"))
        self.assertEqual(sum(1 for e in model if e[0] == "session"), MENU_ROWS)
        self.assertIn(("more", "ועוד 2…"), model)
        self.assertEqual([e[1] for e in model if e[0] == "action"], ["open", "scan", "quit"])
        self.assertEqual(menu_model(self.index(0), NOW)[0], ("header", "אין שיחות שמחכות לך"))
        self.assertEqual(menu_model(None, NOW)[0], ("header", "סורק…"))

    def test_tooltip(self):
        self.assertEqual(tooltip(self.index(3)), "משלט · 3 מחכים לך")
        self.assertEqual(tooltip(self.index(0)), "משלט · אין שיחות שמחכות לך")

    def test_notification_rules(self):
        first = self.index(1)
        self.assertEqual(to_notify(None, first), [])                 # the baseline
        second = self.index(2)
        self.assertEqual([s["id"] for s in to_notify(first, second)], ["local_1"])
        self.assertEqual(to_notify(second, second), [])
        stopped = build([rec("local_s", f"{D}/book")], existing={f"{D}/book"})
        self.assertEqual(to_notify(first, stopped), [])               # nothing new waits
        s = second["projects"][0]["sessions"][0]
        self.assertEqual(notification_text(s, {f"{D}/book": "book"}), ("book · שאלה 0", "מחכה לתשובה: Q0?"))


if __name__ == "__main__":
    unittest.main()
