import os
import unittest

from mishlat.describe import ReadmeCache, parse_readme, write_readme
from tests.helpers import FakeHome


class ParseTest(unittest.TestCase):
    def test_heading_and_paragraph(self):
        text = "# ארכיון המאמרים — example.org\n\nייצוא מלא של 67 המאמרים שפורסמו באתר עד 2026-10-17,\nלפני הפיבוט.\n\n| א | ב |\n"
        self.assertEqual(parse_readme(text), "ארכיון המאמרים — example.org · ייצוא מלא של 67 המאמרים שפורסמו באתר עד 2026-10-17, לפני הפיבוט.")

    def test_markdown_noise_code_and_limits(self):
        text = "```\ncode first\n```\n<!-- c -->\n## Title with `code` and [a link](http://x)\n![img](x.png)\n**Bold** start.\n"
        self.assertEqual(parse_readme(text), "Title with code and a link · Bold start.")
        self.assertIsNone(parse_readme("\n\n```\nonly code\n```\n"))
        long = "# T\n\n" + "x" * 300
        out = parse_readme(long)
        self.assertEqual(len(out), 160)
        self.assertTrue(out.endswith("…"))
        self.assertEqual(parse_readme("just a paragraph\nsecond line"), "just a paragraph second line")


class CacheAndWriteTest(unittest.TestCase):
    def setUp(self):
        self.home = FakeHome()

    def tearDown(self):
        self.home.cleanup()

    def test_cache_and_write(self):
        folder = self.home.mkdir("Desktop/p")
        cache = ReadmeCache()
        self.assertIsNone(cache.purpose(folder))
        path = write_readme(folder, "What it is for.")
        self.assertEqual(os.path.basename(path), "README.md")
        self.assertEqual(cache.purpose(folder), "p · What it is for.")
        self.assertIsNone(write_readme(folder, "again"))                # never overwrites
        with open(path, "w", encoding="utf-8") as f:
            f.write("# New\n\nChanged.\n")
        os.utime(path, (1, 1))
        self.assertEqual(cache.purpose(folder), "New · Changed.")
        os.remove(path)
        self.assertIsNone(cache.purpose(folder))


if __name__ == "__main__":
    unittest.main()
