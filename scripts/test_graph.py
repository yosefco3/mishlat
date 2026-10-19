#!/usr/bin/env python3
"""
Test Graph — maps test files to source files, runs the suite, writes TEST_GRAPH.md.

Stack-agnostic: configure the CONFIG block below for your project, then run:

    python scripts/test_graph.py            # run tests + write TEST_GRAPH.md
    python scripts/test_graph.py --no-run   # write TEST_GRAPH.md without running tests
    python scripts/test_graph.py --json      # emit JSON to stdout instead

Outputs: TEST_GRAPH.md  +  scripts/test_history.json (last 50 runs, coverage trend).
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ─────────────────────────── CONFIG (edit per project) ───────────────────────────
CONFIG = {
    # Command to run the whole suite, from REPO_ROOT.
    "test_cmd": ["python3", "-m", "pytest", "-v", "--tb=short", "--no-header"],
    # Directories scanned for SOURCE files (relative to REPO_ROOT).
    "source_dirs": ["mishlat", "extension"],
    # Source file extensions to count as "code that should be covered".
    "source_exts": [".py"],
    # Glob(s) that identify TEST files.
    "test_globs": ["test_*.py"],
    # Tests live in tests/, so the map is manual (MANUAL_MAP below).
    "mapping": "manual",
    # Paths (substring match) to treat as LOW priority when uncovered.
    "low_priority": ["__init__", "__main__", "paths"],
    # Paths (substring match) to treat as HIGH priority when uncovered.
    "high_priority": ["store", "transcripts", "model", "scan", "index"],
}

# Used only when CONFIG["mapping"] == "manual". Keys/values relative to REPO_ROOT.
MANUAL_MAP: dict[str, list[str]] = {
    "tests/test_store.py": ["mishlat/store.py", "mishlat/paths.py"],
    "tests/test_live.py": ["mishlat/live.py"],
    "tests/test_transcripts.py": ["mishlat/transcripts.py"],
    "tests/test_folders.py": ["mishlat/folders.py", "mishlat/gitinfo.py"],
    "tests/test_model_resolve.py": ["mishlat/model.py"],
    "tests/test_model_index.py": ["mishlat/model.py"],
    "tests/test_index_io.py": ["mishlat/index.py"],
    "tests/test_scan.py": ["mishlat/scan.py", "mishlat/cli.py"],
    "tests/test_actions.py": ["mishlat/actions.py"],
    "tests/test_view.py": ["mishlat/view.py", "mishlat/strings.py"],
    "tests/test_window_smoke.py": ["mishlat/window.py", "mishlat/app.py"],
    "tests/test_watcher.py": ["mishlat/watcher.py"],
    "tests/test_tray.py": ["mishlat/tray.py"],
    "tests/test_nemo.py": ["extension/mishlat_fm.py"],
    "tests/test_install.py": ["mishlat/__main__.py"],
    "tests/test_describe.py": ["mishlat/describe.py"],
    "tests/test_plugin.py": ["plugin/lib/mishlat_cli.py"],
    "tests/test_identity.py": ["mishlat/folders.py", "mishlat/gitinfo.py"],
}

HISTORY_PATH = Path(__file__).resolve().parent / "test_history.json"
MAX_HISTORY = 50
# ──────────────────────────────────────────────────────────────────────────────────


def is_test(path: Path) -> bool:
    return any(path.match(g) for g in CONFIG["test_globs"])


def find_test_files() -> list[Path]:
    out = []
    for d in CONFIG["source_dirs"]:
        base = REPO_ROOT / d
        if not base.exists():
            continue
        for ext in CONFIG["source_exts"]:
            for f in base.rglob(f"*{ext}"):
                if "node_modules" in f.parts:
                    continue
                if is_test(f):
                    out.append(f)
    return sorted(set(out))


def find_source_files() -> list[Path]:
    out = []
    for d in CONFIG["source_dirs"]:
        base = REPO_ROOT / d
        if not base.exists():
            continue
        for ext in CONFIG["source_exts"]:
            for f in base.rglob(f"*{ext}"):
                if "node_modules" in f.parts or is_test(f):
                    continue
                out.append(f)
    return sorted(set(out))


def rel(p: Path) -> str:
    return str(p.relative_to(REPO_ROOT))


def build_map() -> dict[str, list[str]]:
    """source_rel -> [test_rel]."""
    mapping: dict[str, list[str]] = defaultdict(list)
    if CONFIG["mapping"] == "manual":
        for test_path, sources in MANUAL_MAP.items():
            for s in sources:
                mapping[s].append(test_path)
        return dict(mapping)
    # colocated: foo.test.ts -> first existing sibling foo.<ext>
    for t in find_test_files():
        stem = re.sub(r"\.(test|spec)$", "", t.stem)
        for ext in CONFIG["source_exts"]:
            cand = t.with_name(stem + ext)
            if cand.exists():
                mapping[rel(cand)].append(rel(t))
                break
        else:
            mapping[f"(no source found for {t.name})"].append(rel(t))
    return dict(mapping)


def priority(src: str) -> tuple[str, str]:
    for pat in CONFIG["high_priority"]:
        if pat in src:
            return "HIGH", "🔴"
    for pat in CONFIG["low_priority"]:
        if pat in src:
            return "LOW", "⚪"
    return "MEDIUM", "🟡"


def run_tests() -> dict:
    """Best-effort: run the suite, return {passed, failed, ok, raw}."""
    try:
        proc = subprocess.run(
            CONFIG["test_cmd"], capture_output=True, text=True,
            cwd=str(REPO_ROOT), timeout=600,
        )
        out = proc.stdout + proc.stderr
    except Exception as e:  # noqa: BLE001
        print(f"Warning: could not run tests: {e}", file=sys.stderr)
        return {"passed": 0, "failed": 0, "ok": None, "raw": ""}

    passed = failed = 0
    # vitest / jest summary:  "Tests  12 passed (12)"  /  " 2 failed"
    for line in out.splitlines():
        m = re.search(r"Tests?\s+(\d+)\s+passed", line)
        if m:
            passed = max(passed, int(m.group(1)))
        m = re.search(r"(\d+)\s+failed", line)
        if m:
            failed = max(failed, int(m.group(1)))
    # pytest summary:  "12 passed, 1 failed in 0.3s"
    if passed == 0 and failed == 0:
        m = re.search(r"(\d+)\s+passed", out)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+)\s+failed", out)
        if m:
            failed = int(m.group(1))
    return {"passed": passed, "failed": failed, "ok": proc.returncode == 0, "raw": out}


def load_history() -> list[dict]:
    if HISTORY_PATH.exists():
        try:
            data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []
    return []


def save_history(history: list[dict]) -> None:
    HISTORY_PATH.write_text(
        json.dumps(history[-MAX_HISTORY:], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-run", action="store_true", help="skip running the suite")
    ap.add_argument("--json", action="store_true", help="emit JSON to stdout")
    args = ap.parse_args()
    do_run = not args.no_run

    source_files = [rel(p) for p in find_source_files()]
    mapping = build_map()
    covered = [s for s in source_files if s in mapping]
    uncovered = [s for s in source_files if s not in mapping]
    pct = len(covered) * 100 // max(len(source_files), 1)

    results = run_tests() if do_run else {"passed": 0, "failed": 0, "ok": None}

    # history + trend
    prev = load_history()[-1] if load_history() else None
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "coverage%": pct,
        "passed": results["passed"],
        "failed": results["failed"],
    }
    if do_run:
        hist = load_history()
        hist.append(record)
        save_history(hist)
    trend = ""
    if prev:
        d = pct - prev.get("coverage%", pct)
        trend = f" ↑{d}%" if d > 0 else (f" ↓{abs(d)}%" if d < 0 else " →0%")

    if args.json:
        print(json.dumps({
            "coverage%": pct, "covered": covered, "uncovered": uncovered,
            "map": mapping, "results": {k: results[k] for k in ("passed", "failed", "ok")},
        }, ensure_ascii=False, indent=2))
        return

    L = []
    L.append("# Test Coverage Graph")
    L.append("")
    L.append(f"_נוצר אוטומטית ב: {datetime.now().strftime('%Y-%m-%d %H:%M')}_")
    L.append("")
    L.append("## סיכום / Summary")
    L.append("")
    L.append("| מדד / Metric | ערך / Value |")
    L.append("|---|---|")
    L.append(f"| קבצי קוד / source files | {len(source_files)} |")
    L.append(f"| מכוסים / covered | {len(covered)} |")
    L.append(f"| ללא טסט / uncovered | {len(uncovered)} |")
    L.append(f"| כיסוי / coverage | {pct}%{trend} |")
    if do_run:
        L.append(f"| טסטים עוברים / passing | {results['passed']} ✅ |")
        L.append(f"| טסטים נכשלים / failing | {results['failed']} ❌ |")
    L.append("")

    L.append("## מיפוי קוד → טסטים / Source → Tests")
    L.append("")
    L.append("| קובץ קוד / source | קובץ טסט / test |")
    L.append("|---|---|")
    for src in sorted(mapping):
        for tf in sorted(mapping[src]):
            L.append(f"| `{src}` | `{tf}` |")
    L.append("")

    if uncovered:
        L.append("## קבצים ללא טסטים (לפי עדיפות) / Uncovered (by priority)")
        L.append("")
        L.append("| עדיפות / priority | קובץ / file |")
        L.append("|---|---|")
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        ranked = sorted(((order[priority(s)[0]], priority(s), s) for s in uncovered),
                        key=lambda x: (x[0], x[2]))
        for _, (label, icon), src in ranked:
            L.append(f"| {icon} {label} | `{src}` |")
        L.append("")

    (REPO_ROOT / "TEST_GRAPH.md").write_text("\n".join(L), encoding="utf-8")
    print(f"Wrote TEST_GRAPH.md — coverage {pct}%{trend}, "
          f"{results['passed']} passed / {results['failed']} failed")


if __name__ == "__main__":
    main()
