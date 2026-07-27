#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pr_inspector.planning_governance import (  # noqa: E402
    validate_git_diff,
    validate_planning_repository,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check-static", action="store_true")
    parser.add_argument("--check-diff", action="store_true")
    parser.add_argument("--authoritative-base-sha")
    parser.add_argument("--head-sha")
    parser.add_argument("--report")
    args = parser.parse_args()

    diagnostics = []
    report = None
    if args.check_static or not args.check_diff:
        diagnostics.extend(validate_planning_repository(args.root))
    if args.check_diff:
        if not args.authoritative_base_sha or not args.head_sha:
            parser.error(
                "--check-diff requires --authoritative-base-sha and --head-sha"
            )
        more, report = validate_git_diff(
            args.root,
            args.authoritative_base_sha,
            args.head_sha,
        )
        diagnostics.extend(more)
    if args.report and report is not None:
        Path(args.report).write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if diagnostics:
        for item in sorted(set(diagnostics)):
            print("ERROR:", item.line())
        return 1
    print("OK: governed planning validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
