#!/usr/bin/env bash
# Close a dev-kit step: run the tests, tick the step in _PROGRESS.md, commit everything.
# Usage: scripts/step_done.sh <step number> "<commit message>" [feature folder, default mishlat-v1]
set -euo pipefail
n="$1"; msg="$2"; feature="${3:-mishlat-v1}"
cd "$(dirname "$0")/.."
python3 -m pytest -q
python3 - "features-prompts/$feature/_PROGRESS.md" "$n" <<'PY'
import re, sys
path, n = sys.argv[1], sys.argv[2]
lines = open(path, encoding="utf-8").read().split("\n")
start = next(i for i, l in enumerate(lines) if re.match(r"^## (⏳|✅) Pending", l))  # only the checklist
for i in range(start, len(lines)):
    if re.match(rf"^{n}\. `", lines[i]):
        lines[i] = lines[i].replace(f"{n}. `", f"{n}. ✅ `", 1)
checklist = lines[start:]
done = sum(1 for l in checklist if re.match(r"^\d+\. ✅ ", l))
total = sum(1 for l in checklist if re.match(r"^\d+\. (✅ )?`", l))
text = "\n".join(lines)
text = re.sub(r"## (⏳|✅) Pending \(\d+/\d+ completed\):",
              f"## {'✅' if done == total else '⏳'} Pending ({done}/{total} completed):", text)
open(path, "w", encoding="utf-8").write(text)
print(f"progress: {done}/{total}")
PY
git add -A
git commit -q -m "$msg" -m "Co-Authored-By: ${MISHLAT_COAUTHOR:-Claude Fable 5.1} <noreply@anthropic.com>"
git log --oneline -1
