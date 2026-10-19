# Progress — review-2026-10-19

A review of the v1 build (Claude Opus 5.5, dev-kit, 2026-10-19) by Claude Fable 5.1, on the user's
request ("תבדוק את עבודתו של אופוס"). Method: read every module, run the suite, profile a scan,
and probe each rule against the real data on the dev laptop.

## ממצאים / Findings
1. **Session age came from the transcript file's mtime** (`last_write = st.st_mtime`). On this
   machine 122 of 175 transcripts carry an mtime days after their last line (a copy on 10–12
   October), so old sessions looked recent: 14 "stale" instead of the real count, and a touched
   file could even count as "working". **Fixed**: the last `"timestamp"` in the lines is the
   session's time; mtime is the fallback for a transcript with no timestamps.
2. **Work under a folder's old path was not counted** for its project: `~/Desktop/book` (now
   `cookbook`) had 850+ writes that mapped to nothing, so the 52 book sessions' own work
   scored 0 and a few writes elsewhere could move them. **Fixed**: the `moved_from` paths of every
   project are candidates that resolve to the project's current folder.
3. **Paths picked out of tool calls ended with a JSON escape** (`…mp3\`) and a path with spaces
   was cut at the first space. **Fixed** the escape; spaces stay cut (they still match their
   project by prefix).
4. The scan is light: 92 ms warm (profile: 50 ms index build, 30 ms JSON write). The 500 ms seen
   in `mishlat scan` is the cold folder index and `git status`, cached for 30 s / 60 s. OK.
5. Checked and fine: incremental transcript reads (half lines, truncation, deleted files), the
   process-liveness check, the six-state order, atomic 0600 writes, single-instance app, baseline
   before notifications, Nemo extension loaded by Nemo and nemo-desktop, installer idempotent and
   hotkey-safe for tests, argv-only process launches (no shell injection), the app's own deep-link
   routes.
6. Minor, left as is: the Nemo extension keeps a reference to every folder row it marked (tiny);
   the write-command regex can take `print(1 > 0)` for a write (harmless); `~/trading` (a folder
   outside the roots) stays unmapped.

## ✅ Pending (1/1 completed):
1. ✅ `01_fixes.md` — findings 1–3 fixed with tests; re-install; re-check stale and moved counts.
