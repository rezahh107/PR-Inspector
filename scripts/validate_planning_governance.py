#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pr_inspector.planning_governance import validate_git_diff, validate_planning_repository


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Validate governed planning artifacts")
    result.add_argument("--check-static", action="store_true")
    result.add_argument("--check-diff", action="store_true")
    result.add_argument("--base-sha")
    result.add_argument("--head-sha")
    result.add_argument("--report")
    return result


def main() -> int:
    args = parser().parse_args()
    check_static = args.check_static or not args.check_diff
    diagnostics = []
    report = None
    if check_static:
        diagnostics.extend(validate_planning_repository(ROOT))
    if args.check_diff:
        if not args.base_sha or not args.head_sha:
            print("ERROR: --check-diff requires --base-sha and --head-sha")
            return 2
        diff_diagnostics, report = validate_git_diff(ROOT, args.base_sha, args.head_sha)
        diagnostics.extend(diff_diagnostics)
    diagnostics = sorted(set(diagnostics))
    if args.report and report is not None:
        Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if diagnostics:
        for item in diagnostics:
            print("ERROR:", item.line())
        return 1
    print("OK: governed planning validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
