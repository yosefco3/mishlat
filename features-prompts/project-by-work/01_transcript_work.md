# 01 — Record written and read paths per transcript

## מטרה / Goal
While reading a transcript (incrementally), count the absolute paths that its tool calls wrote and
read, and the writes with no absolute path. No change to which project a session belongs to yet.

## קבצים לשינוי / Files to change
- `mishlat/transcripts.py` — `work_of(tool_name, input)`, new fields `writes`, `reads`, `local_writes`.
- `mishlat/index.py` — `CACHE_VERSION = 2` (old caches lack the fields: one full re-read).
- `tests/test_transcripts.py`

## מצב נוכחי / Current state
`_apply_assistant` (transcripts.py) looks at tool_use blocks only for the task list. `_wanted` reads
assistant lines only when they hold `update_plan`, `wrap_up` or `TodoWrite`.

## שינוי נדרש / Required change
- Paths: `~/…` and `/home/<user>/…` inside the tool input, cut to 6 components (the cache stays small).
- Write: `Write`/`Edit`/`NotebookEdit` `file_path`; a `Bash` command that matches a write pattern
  (`cat >`, `>>`, `> file`, `tee`, `cp`, `mv`, `install`, `mkdir`, `sed -i`, `git add/commit`,
  `step_done`) — its absolute paths, or one local write when it has none. Read: any other tool call's
  absolute paths.
- `_wanted` also reads assistant lines with `"tool_use"`.

## טסטים נדרשים / Tests required
- Write and Edit paths; a Bash heredoc write with `cd ~/x &&`; a relative `git commit` is a local
  write; a Read is a read; paths are cut to 6 components; incremental reads add up.

## קומיט / Commit
`feat(transcripts): record where each session wrote and read`
