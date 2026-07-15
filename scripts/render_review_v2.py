#!/usr/bin/env python3
from pathlib import Path
import argparse
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pr_inspector.official_review import (
    CompletionError,
    IncompleteReview,
    complete_review,
    github_pull_request_head_source,
    is_verified_review_completion,
    official_owner_delivery,
)
from pr_inspector.review_provenance import trust_policy
from pr_inspector.evidence_adapter import mint_evidence_from_governance_fixture


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Produce an official PR Inspector artifact bundle only after canonical "
            "validation and live GitHub PR-head rechecks. On success, stdout contains "
            "the complete owner delivery, including the canonical prompt when required."
        )
    )
    parser.add_argument("package", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target-repository", required=True)
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--governance-fixture", type=Path)
    parser.add_argument("--reviewed-head-sha")
    parser.add_argument("--sequence-app-id", type=int, default=15368)
    parser.add_argument("--sequence-workflow-path", default=".github/workflows/validate-rereview-sequence.yml")
    parser.add_argument("--sequence-workflow-sha")
    parser.add_argument("--sequence-validator-command", default="python scripts/validate_rereview_sequence.py SEQUENCE.json --review EVENT=REVIEW_DIRECTORY")
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

    governance_evidence = None
    sequence_enforcement = None
    if args.governance_fixture is not None:
        if not args.reviewed_head_sha or not args.sequence_workflow_sha:
            print("ERROR: --governance-fixture requires --reviewed-head-sha and --sequence-workflow-sha", file=sys.stderr)
            return 1
        governance_evidence, sequence_enforcement = mint_evidence_from_governance_fixture(
            args.governance_fixture,
            repository=args.target_repository,
            pr_number=args.pr_number,
            head_sha=args.reviewed_head_sha,
            sequence_app_id=args.sequence_app_id,
            sequence_workflow_path=args.sequence_workflow_path,
            sequence_workflow_sha=args.sequence_workflow_sha,
            sequence_validator_command=args.sequence_validator_command,
        )

    outcome = complete_review(
        args.package,
        args.output_dir,
        head_source=head_source,
        governance_evidence=governance_evidence,
        sequence_enforcement=sequence_enforcement,
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

    try:
        delivery = official_owner_delivery(outcome)
    except CompletionError as exc:
        print(
            "The official PR Inspector owner delivery did not complete.\n"
            "No partial owner result or prompt was emitted.",
            file=sys.stderr,
        )
        print(f"ERROR: PRI-DELIVERY-001 /owner-delivery: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(delivery)
    print(
        "OK: canonical package, projection, rendered artifacts, manifest, final bytes, "
        f"live GitHub head {outcome.reviewed_head_sha}, and atomic owner delivery completed "
        "verified validation.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
