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

## awesome-claude-code (submit it yourself, from 2026-11-02)

The list (https://github.com/hesreallyhim/awesome-claude-code) takes recommendations only through
its web issue form, filled in by a human; PRs and `gh`-made issues are closed. A resource must be
14 days past its first commit on the default branch, with more commits after the first day, or
have 100 stars. Mishlat's first public commit is 2026-10-19, so it is eligible from **2026-11-02**;
keep committing in between.

Form: https://github.com/hesreallyhim/awesome-claude-code/issues/new?template=recommend-resource.yml

| Field | Value |
|---|---|
| Display Name | Mishlat |
| Category | Observability & Monitoring > Session Monitors |
| Link | https://github.com/yosefco3/mishlat |
| Author Name | yosefco3 |
| Author Link | https://github.com/yosefco3 |
| Description | see below (431 characters) |

> A GTK window for Linux that lists every project with its Claude Code sessions and their state (working, waiting for an answer, ready for review, stopped midway), with a panel badge, folder marks in Nemo and Nautilus, and a standing list of sessions worth deleting. Sessions are grouped by the project they worked in and follow a folder that is renamed or moved. Includes a Claude Code plugin with /projects, /needs-me and /cleanup.

Checklist: tick all (you have seen the repo; links public; specific to Claude Code).

## anthropics/claude-code (feature request issue; Discussions are disabled there)

The repository has no Discussions tab, so there is no "Show and tell". What it does accept is a
feature request in its issue tracker, and this one is already filed twice: #94620 (a built-in way
to list running sessions and their state, open since 2026-09-16) and #85192 (expose the
"waiting for user input" state in `claude agents --json`, open since 2026-08-09). Comment there
with Mishlat as an example rather than opening a third issue.

Note that `claude agents --json` (verified on CLI 2.1.299) already lists the *live* sessions:
`pid`, `cwd`, `kind`, `startedAt`, `sessionId`, `name`, `status` (`busy`/`idle`). What it lacks is
the waiting-for-you state and the sessions that are not running. Posted on 2026-10-19 as yosefco3:
https://github.com/anthropics/claude-code/issues/94620#issuecomment-6275154547

Another data point, from the Linux desktop side. I built Mishlat (https://github.com/yosefco3/mishlat), a GTK window that lists every project with its Claude Code sessions and their state, with a tray badge, file-manager marks and a cleanup list. Like the tools above it runs on undocumented files: the desktop app's session store (`~/.config/Claude/claude-code-sessions/*/*/local_*.json`), the transcripts under `~/.claude/projects/`, and the pid registry in `~/.claude/sessions/`.

Two things I can add to the thread:

1. The "turn ended with a question in prose" gap is already solved inside the desktop app. Every record in its session store carries a `postTurnSummary` with `status_category` (`blocked`, `review_ready` or `completed`), `needs_action` (what the user must do, e.g. the open question) and `status_detail`. That is exactly the signal missing from `claude agents --json`, where such a session reads `idle`. Exposing the same classification in the listing would close the gap for interactive sessions without new inference on the consumer side.

2. On CLI 2.1.299 the desktop app's own sessions do appear in `claude agents --json` as `kind: "interactive"` with `busy`/`idle`, so live state is covered. What a cross-project view still has to read from undocumented files:
   - sessions that are not running: saved interactive sessions with `sessionId`, `cwd`, `name` and a last-activity time (the listing drops an interactive session once its process exits; `--all` only adds completed background ones);
   - the post-turn classification above, plus its one-line detail;
   - the transcript path per session, so tools stop reconstructing `~/.claude/projects/<encoded cwd>/<id>.jsonl`, which breaks as soon as a project folder is renamed or moved.

Happy to adjust Mishlat to whatever shape ships.
