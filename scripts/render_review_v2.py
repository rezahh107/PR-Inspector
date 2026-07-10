#!/usr/bin/env python3
from pathlib import Path
import argparse
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pr_inspector.official_review import (
    IncompleteReview,
    complete_review,
    github_pull_request_head_source,
    is_verified_review_completion,
)
from pr_inspector.review_provenance import trust_policy


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Produce an official PR Inspector artifact bundle only after canonical "
            "validation and live GitHub PR-head rechecks."
        )
    )
    parser.add_argument("package", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target-repository", required=True)
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument(
        "--github-token-env",
        default="GITHUB_TOKEN",
        help="Environment variable containing an optional GitHub token.",
    )
    args = parser.parse_args()

    try:
        api_version = trust_policy()["github_api_version"]
        head_source = github_pull_request_head_source(
            args.target_repository,
            args.pr_number,
            token=os.environ.get(args.github_token_env),
            api_version=api_version,
        )
    except Exception as exc:
        print(
            "The official PR Inspector review did not complete.\n"
            "No valid decision or action prompt was produced.",
            file=sys.stderr,
        )
        print(f"ERROR: PRI-COMPLETE-008 /live-target-head: {exc}", file=sys.stderr)
        return 1

    outcome = complete_review(
        args.package,
        args.output_dir,
        head_source=head_source,
    )
    if isinstance(outcome, IncompleteReview):
        print(outcome.technical_message, end="", file=sys.stderr)
        for item in outcome.diagnostics:
            print("ERROR:", item.line(), file=sys.stderr)
        return 1
    if not is_verified_review_completion(outcome):
        print(
            "The official PR Inspector review did not complete.\n"
            "No valid decision or action prompt was produced.",
            file=sys.stderr,
        )
        return 1

    print(
        "OK: canonical package, projection, rendered artifacts, manifest, final bytes, "
        f"and live GitHub head {outcome.reviewed_head_sha} completed verified validation."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
