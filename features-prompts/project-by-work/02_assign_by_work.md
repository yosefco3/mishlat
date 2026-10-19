# 02 — Assign a session to the project it worked in

## מטרה / Goal
In `build_index`, after a session's folder is resolved, move it to the project where its work went,
unless the user assigned it by hand.

## קבצים לשינוי / Files to change
- `mishlat/model.py` — `work_project(...)`, the move in `build_index`, `started_in` on the session.
- `mishlat/index.py` — `load_assignments`, `assign(home, session_id, project_path | None)`.
- `mishlat/scan.py` — pass the assignments.
- `tests/test_model_index.py`, `tests/test_index_io.py`

## שינוי נדרש / Required change
- Candidates: the folders of the folder index and the resolved project paths. A path belongs to the
  deepest candidate it starts with; a path that no longer exists, to the unique candidate whose name
  equals one of its first three components below the root (a moved folder).
- Writes: the top project has ≥ 5 and more than twice the start project's (local writes count for
  the start project). No writes: reads, ≥ 15 and more than twice. Else the start project.
- `assignments.json` `{session id: project path}` wins when that folder exists.
- The session gets `started_in` (the start project key) when it moved.

## טסטים נדרשים / Tests required
- Moves by writes; stays when the start folder wrote enough; read-only fallback; a moved old path
  by name; the manual assignment wins; a missing assigned folder is ignored.

## קומיט / Commit
`feat(model): a session belongs to the project it worked in`
