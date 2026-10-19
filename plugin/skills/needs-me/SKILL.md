---
name: needs-me
description: The Claude Code sessions that need the user right now, across every project: waiting for an answer (with the open question), ready for review, stopped midway. Use when the user types /needs-me, asks "what is waiting for me", "which sessions need me", "did anything finish", or at the start of a work session.
---

# /needs-me

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/mishlat_cli.py" scan --json
```

From the JSON, take `attention` (session ids, in order) and look each one up in
`projects[].sessions[]`. Print one line per session, grouped by state in this order: waiting,
stopped, review. Each line: the state glyph (◐ waiting · ◼ stopped · ◑ review), the project
`name`, the session `title` as a link `[title](#id)` when the id starts with `local_`, and the
`question` (or `detail`) after a dash (for a session the CLI lists as waiting, `question` is what
it waits for: "permission prompt", "input needed", …). Then the sessions that `working` right now, with their
`step`. Nothing else: no advice, no summary of everything.

If `attention` is empty, say so in one line and list the working sessions if any.
