# Mishlat as a Claude Code plugin

The scanner of [Mishlat](https://github.com/yosefco3/mishlat) and three slash commands, for
Claude Code itself: no window, no tray, no file-manager marks. Linux and macOS.

| Command | What it does |
|---|---|
| `/projects [word]` | every project with its sessions and their state, newest first |
| `/needs-me` | the sessions that wait for your answer, are ready for review, or stopped midway |
| `/cleanup [all \| old \| …]` | sessions worth deleting, with a reason each; deletes the ones you approve through the desktop app |

## Install

From this repository, for one session:

```bash
CLAUDE_CODE_PLUGIN_DIRS=/path/to/mishlat/plugin claude
```

or add it to your user settings so every session has it:

```json
{"env": {"CLAUDE_CODE_PLUGIN_DIRS": "/path/to/mishlat/plugin"}}
```

(`~/.claude/settings.json`; the desktop app reads the same file.)

## What it reads, what it writes

Reads the Claude desktop app's session records (`~/.config/Claude/claude-code-sessions/` on Linux,
`~/Library/Application Support/Claude/claude-code-sessions/` on macOS), Claude Code's transcripts
(`~/.claude/projects/`) and its live process registry (`~/.claude/sessions/`). Writes only
`~/.cache/mishlat/` (the index and the incremental-read cache) and, when you ask, `~/.config/mishlat/keep.json`.
Deletions are done by the desktop app's own session tool, which confirms each one.

`lib/mishlat/` is a copy of the package in the repository root, refreshed by `make plugin-sync`.
