# Progress — folder-identity

A renamed project folder must keep its sessions. Today a move that keeps the name is followed (by
name), but a rename drops the sessions into "General" and even marks the idle ones for deletion
("the project folder no longer exists"). Mishlat now remembers every folder's identity while it
exists, and finds it again by that identity after a rename or a move.

## מטרת-על / High-level goal
- Identity = the folder's (device, inode), stable across `mv` within a filesystem, plus the git
  `origin` remote URL when the folder is a repository (stable across copies and clones).
- Remembered at every scan for every folder Mishlat knows (the folder index, and every session's
  folder that still exists), in `~/.cache/mishlat/folders.json`. Entries of folders that vanish
  stay: that is the point.
- A lost folder is resolved, in order: its remembered identity (same device+inode, with the remote
  agreeing when both sides have one), its remembered remote (unique), the transcript folder's
  encoding, a unique folder with the same name, `aliases.json`; else "General".
- When a remembered identity is not among the indexed folders (e.g. the folder moved into a
  repository, where the index does not descend), a deeper bounded search (depth 6, skipping `.git`
  and `node_modules`) runs once per scan while there are such folders.

## החלטות (מול המשתמש, 2026-10-19) / Decisions (with the user, 2026-10-19)
- The user, after the experiment: build it, with tests for rename and move, install, publish v0.1.1.
- Guard against inode reuse (the user, after "ומחיקת ספריה?"): an inode match is accepted only
  when the git remotes agree (both absent, or equal) and at least one of up to 8 remembered
  top-level entry names of the old folder is still inside the candidate. A renamed folder keeps its
  contents; a new folder that got a recycled inode does not. A copied folder (new inode) is found
  by its remote.
- Mishlat must have run once before the change: it runs at login, and the memory also records
  folders at every scan, so the window of risk is the first run only.

## מבחן הצלחה / Acceptance test (במחשב הפיתוח)
1. `H=$(python3 scripts/demo_home.py); export MISHLAT_HOME=$H MISHLAT_PROC_ROOT=$H/_proc;
   python3 -m mishlat scan >/dev/null; mv $H/Desktop/shop-site $H/Desktop/store-site;
   mkdir -p $H/Desktop/elsewhere; mv $H/Desktop/writing/cookbook $H/Desktop/elsewhere/book;
   python3 -m mishlat scan` ⇒ `store-site` has 4 sessions and `elsewhere/book` 4; no new session in
   General; the Cleanup line has no new "folder gone".
2. `python3 -m pytest -q` ⇒ green, including rename, move, nested move and reuse-guard tests.
3. After `./install.sh` on the dev laptop: rename a real project folder, press Super+Shift+C ⇒ the
   card follows with all its sessions and the note "moved from …"; rename it back ⇒ same.
4. https://github.com/yosefco3/mishlat/releases/tag/v0.1.1 exists.

## ✅ Pending (3/3 completed):
1. ✅ `01_identity.md` — identity capture (`folders.py`, `gitinfo.remote_url`), the memory file, scan wiring.
2. ✅ `02_resolve.md` — resolution by identity and remote, the deeper search, tests.
3. ✅ `03_release.md` — docs, version 0.1.1, plugin sync, install, push, tag, release.
