# Announcement drafts (post them yourself; edit freely)

## r/ClaudeAI or r/ClaudeCode

**Title:** Mishlat: a Linux desktop "control post" for your Claude Code sessions (open source, MIT)

I had 170 Claude Code sessions in the desktop app's sidebar and could not tell which belonged to
which project or which one was waiting for me. So I built Mishlat (Hebrew for "control post"):

- one window, every project as a card with its sessions and their state (working / open /
  waiting for you / ready for review / stopped midway), and an attention column across projects;
- a session belongs to the project it *worked in* (files written and read), not the folder it was
  opened in, so a session that started in one folder and built another lands where it belongs;
- a panel badge + notifications when a session starts waiting for you;
- emblems, a "Claude" column and a right-click menu on project folders in Nemo/Nautilus;
- a standing cleanup list: sessions worth deleting with a reason each (folder gone, transcript
  deleted, duplicate, empty, 30 days idle), never the newest session of a folder; the deletions
  run through the app itself;
- plus a Claude Code plugin with `/projects`, `/needs-me`, `/cleanup` for Linux and macOS.

It reads the app's own files and writes nothing into them. Python 3 + GTK 3, no dependencies.
English and Hebrew UI. Built on Linux Mint; GNOME/Nautilus support is there but untested, so
reports are welcome.

Repo: https://github.com/yosefco3/mishlat

Caveat up front: it relies on undocumented files the desktop app keeps, so an app update can break
a reader; the scanner then says what it could not read instead of showing nothing.

## GitHub discussion / feature request for anthropics/claude-code (optional)

**Title:** Group sessions by the project they worked in, and show what waits for me across projects

A small open-source tool shows what this could look like inside the app: sessions assigned to the
project they wrote files in (not the folder they started in), one attention list across projects
with the open question on the row, and a cleanup list with reasons. https://github.com/yosefco3/mishlat.
The rules are documented in its README ("How it decides"); happy to share the data behind them.
