# Progress — open-source

Mishlat goes public: an English UI with a Hebrew switch, support beyond Linux Mint (GNOME /
Nautilus, a generic tray, a desktop-aware hotkey), a demo home for screenshots, scrubbed specs,
an MIT license, a GitHub repository, and a Claude Code plugin that carries the parts that fit
inside Claude Code (the scanner and slash commands) to every OS.

## החלטות (מול המשתמש, 2026-10-19) / Decisions (with the user, 2026-10-19)
- Audience: Linux broadly (not Mint only). UI language: English by default, Hebrew when the
  locale is Hebrew or `settings.json` says `"lang": "he"`; Ctrl+L switches and saves. Direction
  follows the language.
- The public repo keeps `features-prompts/` as a dev-kit example, scrubbed of personal folder
  names and quotes; the plan HTML pages (they quote real session titles) stay out.
- GitHub `yosefco3/mishlat`, MIT. The first public push happens only after the user's go.
- A plugin too (the user, 2026-10-19: "אולי אפשר לבנות את זה כפלאגין?"): `plugin/` in the same repo
  with the scanner (pure Python, no GTK) and slash commands `/projects`, `/needs-me`, `/cleanup`;
  it runs inside Claude Code on Linux and macOS (store path per OS). The tray, notifications,
  folder marks and the window stay in the desktop app. The in-app pane (mod API) is for later.
- Not supported and said so: Windows (no GTK/Nemo; the plugin's scanner may work), KDE's Dolphin
  (no Python extension API like Nemo/Nautilus), Wayland-only trays without an indicator host.
- Nautilus support is written against nautilus-python 4.x (GNOME 43+) and cannot be run on this
  machine (Nautilus is not installed); marked "untested" in the README.

## מבחן הצלחה / Acceptance test (במחשב הפיתוח, אחרי הדחיפה)
1. `MISHLAT_HOME=$(python3 scripts/demo_home.py) mishlat scan` ⇒ a summary of the demo data, no
   personal names; `python3 scripts/screenshot.py` ⇒ `docs/screenshots/*.png` in English and Hebrew.
2. Super+Shift+C ⇒ Hebrew UI as before (settings `lang: he`); Ctrl+L ⇒ English, left-to-right;
   Ctrl+L again ⇒ Hebrew.
3. `grep -rn "yosef" --include=*.py --include=*.md --include=*.sh .` ⇒ only the GitHub owner
   name (README, LICENSE, this spec) and the `io.github.yosefco3` app id.
4. https://github.com/yosefco3/mishlat shows the README with screenshots, the license, and
   `plugin/` with a valid `.claude-plugin/plugin.json`; `claude plugin validate plugin/` passes.
5. In a Claude Code session with the plugin loaded (`CLAUDE_CODE_PLUGIN_DIRS=~/Desktop/apps/mishlat/plugin`):
   `/projects` prints the summary; `/needs-me` the attention list; `/cleanup` the proposals.

## ✅ Pending (6/6 completed):
1. ✅ `01_i18n.md` — `strings.py` (`t()`, EN table, language from settings/locale), every UI string, direction, Ctrl+L.
2. ✅ `02_desktops.md` — Nautilus branch in the extension, AyatanaAppIndicator fallback, GNOME hotkey, installer detection.
3. ✅ `03_demo.md` — `scripts/demo_home.py` (fake home), `scripts/screenshot.py` (offscreen, both languages), README screenshots.
4. ✅ `04_scrub.md` — scrub specs/tests/docs of personal names, drop plan pages, generic app id, LICENSE, CONTRIBUTING, README rewrite.
5. ✅ `05_plugin.md` — `plugin/` with the scanner and the three commands; `claude plugin validate`.
6. ✅ `06_publish.md` — `gh repo create yosefco3/mishlat --public`, push, announcement draft; after the user's go.
