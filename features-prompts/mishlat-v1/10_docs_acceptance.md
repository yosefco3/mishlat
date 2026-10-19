# 10 — Docs, graphs, install on the dev laptop, acceptance

## מטרה / Goal
Close the feature: README, APP_OVERVIEW, test graph and code graph current; Mishlat installed on
the dev laptop; the acceptance checks run where Claude can run them.

## קבצים לשינוי / Files to change
- `README.md`, `APP_OVERVIEW.md`, `TEST_GRAPH.md`, `features-prompts/mishlat-v1/_PROGRESS.md`

## שינוי נדרש / Required change
- README: what it is, install, use, uninstall, privacy (what it reads, what it writes).
- APP_OVERVIEW: architecture, data model, workflow, change history.
- Run `make check`, `./install.sh`, then acceptance checks 1 and 7, and the parts of 2–6 that a
  script can confirm (the tray process runs, the index is fresh, the Nemo extension loads).

## קריטריון הצלחה / Success criteria
- All tests pass; the closing message gives the user the acceptance test with exact steps.

## קומיט / Commit
`docs: README, overview and graphs for mishlat v1`
