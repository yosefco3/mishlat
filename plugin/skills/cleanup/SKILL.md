---
name: cleanup
description: Sessions worth deleting, with a reason each (project folder gone, transcript deleted, duplicate title, empty, untouched for 30 days), and deletion of the ones the user approves, through the Claude desktop app. Use when the user types /cleanup, asks to clean up, prune or delete old Claude sessions, or asks which sessions are safe to delete.
---

# /cleanup

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/mishlat_cli.py" scan --json
```

From the JSON, take `cleanup` (session ids, newest first) and look each one up in
`projects[].sessions[]`; the reason is in the session's `cleanup` field: `gone` (the project
folder no longer exists), `no_transcript` (the transcript was deleted; nothing to resume),
`duplicate` (a newer session has the same title), `empty` (two turns or fewer, nothing written,
older than a week), `old` (untouched for 30 days). The scanner never lists starred sessions,
sessions that wait for the user or work, sessions assigned by hand, sessions the user kept, or
the newest session of a folder.

1. Show the list grouped by reason: project `name`, `title` (as `[title](#id)` for `local_` ids),
   how old (`last_activity` is milliseconds since the epoch). Give the count per reason.
2. Ask which ones to delete: all, a reason group, or specific ones. Do not delete anything before
   the user answers. $ARGUMENTS may already say (for example `/cleanup old` or `/cleanup all`).
3. Delete only inside the Claude desktop app, with the session tool `delete_session`, one call per
   session id; the app asks the user to confirm each one. If that tool is not available (a plain
   terminal session), say so and print the ids instead; the user can delete them in the app's
   sidebar.
4. Afterwards run the scan again and report how many sessions are left in the cleanup list.

Sessions the user wants to keep out of the list for good go into
`~/.config/mishlat/keep.json` as `{"<session id>": <now in ms>}`; write that file when asked.
