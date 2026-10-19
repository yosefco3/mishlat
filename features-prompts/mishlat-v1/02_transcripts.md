# 02 — Incremental transcript index

## מטרה / Goal
Index every top-level transcript `~/.claude/projects/*/*.jsonl` by its file name (the cli session
id) and extract, incrementally: the custom title, the agent name, the first real prompt, the
interruption flag, the replayed task list, the last `cwd`, the transcript folder name and the last
write time.

## קבצים לשינוי / Files to change
- `mishlat/transcripts.py` (new)
- `tests/test_transcripts.py`

## מצב נוכחי / Current state
175 top-level transcripts (753 MB); 189 more under `<session>/subagents/` (excluded). Line facts
(2026-10-19): user prompts are string content or text blocks; `isMeta` lines carry skill text;
4,870 user lines are only `tool_result`; interruptions are text blocks
`[Request interrupted by user…]`; automated events start with `<` (`<task-notification>`,
`<command-name>`); titles come as `{"type":"custom-title","customTitle":…}`. The task list is
`update_plan` tool_use inputs (`items`, `advance`, `done`, `start`); `wrap_up` checks it off; CLI
sessions use `TodoWrite` (`todos`).

## שינוי נדרש / Required change
- `encode_path(path)`: every character outside `[A-Za-z0-9]` becomes `-` (Claude Code's rule).
- `apply_line(data, raw)` and `apply_op(items, op)` — pure. A line is parsed only when it holds
  one of the interesting keys; a `tool_result` user line is skipped unless it is an interruption.
- `index_transcripts(home, cache)`: unchanged (size, mtime, inode) ⇒ cached data; grown ⇒ read
  from the stored offset; shrunk or replaced ⇒ read again from 0. Only complete lines advance
  the offset, so a half-written last line is read on the next scan. Cache entries of deleted files
  are dropped.

## טסטים נדרשים / Tests required
- apply_op: items, advance, done, start, all_done, TodoWrite.
- apply_line: custom title, first prompt with a pasted block stripped, meta and `<…>` lines
  ignored, interrupt then a new prompt clears it, sidechain ignored, broken JSON ignored.
- index: growth reads only the new bytes; a half line waits; a truncated file is re-read;
  subagent files are not indexed; a deleted file leaves the cache.

## קריטריון הצלחה / Success criteria
- Tests pass. A first full index of the real home takes well under a minute; a second one with no
  change takes under a second.

## קומיט / Commit
`feat(transcripts): index transcripts by session id, incrementally`
