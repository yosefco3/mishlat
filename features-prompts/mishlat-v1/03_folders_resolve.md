# 03 — Folder index, git info, project resolution, session state

## מטרה / Goal
Turn a session folder into a project, also when the folder moved, and turn the raw signals into
one of six states.

## קבצים לשינוי / Files to change
- `mishlat/folders.py` (new) — `folder_index(roots, depth=3)`, `FolderIndex` lookups.
- `mishlat/gitinfo.py` (new) — `read_branch(repo)`, `is_dirty(repo, run)`.
- `mishlat/model.py` (new) — `resolve_project(...)`, `state_of(...)`.
- `tests/test_folders.py`, `tests/test_model_resolve.py`

## מצב נוכחי / Current state
Desktop layout 2026-10-19: `apps/`, `trading/`, `essays/`, `web_site/` hold projects one
level down; transcript folder `-home-user-Desktop-web-site-web-site` encodes
`~/Desktop/web_site/web-site`. 8 sessions of `~/Desktop/sched_app` lost their
transcripts.

## שינוי נדרש / Required change
- `folder_index`: breadth-first under each root to depth 3; skip hidden folders, `node_modules`,
  `__pycache__`, `venv`, `build`, `dist`; a git repository is recorded and not descended into.
  Lookups: `at(path)`, `by_encoding(name)`, `by_basename_encoding(name)`.
- `resolve_project(cwd, folders, tx_folder, aliases, isdir)` in this order: worktree and scratch
  folding; the folder exists; a user alias; one folder whose encoding equals the transcript
  folder; one folder whose encoded basename equals the old one; else missing (ambiguous when
  several candidates exist).
- `state_of(status, fresh, alive, tx, now)`: working (alive and a write in the last 90 s) >
  stopped (interrupted with a step in progress) > waiting (fresh `blocked`) > review (fresh
  `review_ready`) > open (alive) > idle.
- `read_branch` reads `.git/HEAD` (also a `gitdir:` file); `is_dirty` runs
  `git status --porcelain --untracked-files=no` with a 3 s timeout and returns None on error.

## טסטים נדרשים / Tests required
- Each resolution branch, including the ambiguous case and worktree folding.
- Each state, and the order between them.
- folder_index skips and repo cut-off on a temp tree; branch on a fake `.git/HEAD`.

## קריטריון הצלחה / Success criteria
- Tests pass. On the real home every moved folder of the 2026-10-17 move resolves.

## קומיט / Commit
`feat(model): resolve moved project folders and classify six session states`
