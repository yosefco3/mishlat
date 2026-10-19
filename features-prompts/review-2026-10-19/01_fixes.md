# 01 — Review fixes

Files: `mishlat/transcripts.py` (content timestamps, no trailing escape in paths),
`mishlat/model.py` (old paths as candidates), `mishlat/index.py` (cache v3), tests.
Success: suite green; on the dev laptop `mishlat scan` reports the real stale count and the same 7 moved
sessions as before (no new false moves).
Commit: `fix(model): session time from transcript lines, old folder paths count for their project`
Co-authored commits in this repo end with the model that wrote them.
