# Announcement drafts (post them yourself; edit freely)

## r/ClaudeAI or r/ClaudeCode

**Title:** Mishlat: a Linux desktop "control post" for your Claude Code sessions (open source, MIT)

It started with a tidy-up. I moved my project folders around to organize my Desktop, and the
desktop app's sidebar lost the thread: sessions stayed filed under the old paths, one project
became three, and I had 170 Claude Code sessions I could not navigate or tell apart, let alone
see which one was waiting for me. So I built Mishlat (Hebrew for "control post"):

- one window, every project as a card with its sessions and their state (working / open /
  waiting for you / ready for review / stopped midway), and an attention column across projects;
- a session belongs to the project it *worked in* (files written and read), not the folder it was
  opened in, so a session that started in one folder and built another lands where it belongs;
- rename or move a project folder (even into another repository) and its sessions follow: Mishlat
  remembers each folder's inode, git remote and file names, so it finds the folder again; a
  deleted folder stays deleted and its sessions are offered for cleanup;
- a panel badge + notifications when a session starts waiting for you;
- emblems, a "Claude" column and a right-click menu on project folders in Nemo/Nautilus;
- a standing cleanup list: sessions worth deleting with a reason each (folder gone, transcript
  deleted, duplicate, empty, 30 days idle), never the newest session of a folder; the deletions
  run through the app itself;
- plus a Claude Code plugin with `/projects`, `/needs-me`, `/cleanup` for Linux and macOS.

It reads the app's own files and writes nothing into them. Python 3 + GTK 3, no dependencies.
English and Hebrew UI. Built on Linux Mint; GNOME/Nautilus support is there but untested, so
reports are welcome.

Repo: https://github.com/yosefco3/mishlat (v0.1.1)

Caveat up front: it relies on undocumented files the desktop app keeps, so an app update can break
a reader; the scanner then says what it could not read instead of showing nothing.

## GitHub discussion for anthropics/claude-code (optional; ask for the stable interface, not the feature)

**Title:** A documented way to list sessions and their state (e.g. `claude sessions --json`)

Tools that show sessions across projects have to read the desktop app's own files
(`claude-code-sessions/*.json`, the transcripts, the pid registry), none of which is documented, so
every app update can break them. A small open-source example: https://github.com/yosefco3/mishlat
(one window with every project, the sessions that wait for you, folder marks, a cleanup list).
A documented listing with the session id, folder, title, last activity and the post-turn state
(working / blocked on the user / review ready) would make such tools safe to maintain.
