---
name: projects
description: Every project with its Claude Code sessions and their state (working, open, waiting for you, ready for review, stopped midway, idle), newest first, with the sessions that need you on top. Use when the user types /projects, asks "what am I working on", "which sessions are open", "what did I do in project X", or wants an overview of their Claude sessions across folders.
---

# /projects

Run the scanner and show the result. The scanner reads the Claude desktop app's session records,
Claude Code's transcripts and the live process registry; it writes only its own cache under
`~/.cache/mishlat/`. It never changes anything of the user's.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/mishlat_cli.py" scan
```

Print the summary the command returns as it is (it is already formatted), inside one fenced block.
Then, in one or two sentences, say what stands out: sessions that wait for the user, sessions that
work right now, a project that is busier than usual. $ARGUMENTS, when given, is a project name or a
word to filter by: run the command with `--json`, keep only the matching projects or sessions, and
print those.

A session row's id starts with `local_` for desktop-app sessions; `[title](#local_…)` in your reply
is a link the desktop app opens. A plain uuid is a terminal session; it opens with
`claude --resume <uuid>` from its folder.

If the command reports errors, show them: they say which source the scanner could not read (an
app update may have changed a file format).
