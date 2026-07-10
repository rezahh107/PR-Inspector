#!/usr/bin/env python3
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pr_inspector.official_review import (
    IncompleteReview,
    complete_review,
    is_verified_review_completion,
)


_FAILURE_MESSAGE = (
    "The official PR Inspector review did not complete.\n"
    "No valid decision or action prompt was produced.\n"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-target-repository", required=True)
    parser.add_argument("--expected-pr-number", type=int, required=True)
    parser.add_argument("--expected-reviewed-head-sha", required=True)
    args = parser.parse_args()

    try:
        outcome = complete_review(
            args.package,
            args.output_dir,
            expected_target_repository=args.expected_target_repository,
            expected_pr_number=args.expected_pr_number,
            expected_reviewed_head_sha=args.expected_reviewed_head_sha,
        )
    except Exception as exc:
        print(_FAILURE_MESSAGE, end="", file=sys.stderr)
        print(
            "ERROR: PRI-COMPLETE-999 /official-review-boundary: "
            f"unexpected handled CLI failure: {exc}",
            file=sys.stderr,
        )
        return 1

    if isinstance(outcome, IncompleteReview):
        print(outcome.technical_message, end="", file=sys.stderr)
        for item in outcome.diagnostics:
            print("ERROR:", item.line(), file=sys.stderr)
        return 1
    if not is_verified_review_completion(outcome):
        print(_FAILURE_MESSAGE, end="", file=sys.stderr)
        return 1

    print(
        "OK: canonical package, projection, rendered artifacts, manifest, "
        "and final bytes completed verified validation."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
