#!/usr/bin/env python3
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pr_inspector.validation_v2 import validate_directory
from pr_inspector.evidence_adapter import mint_evidence_from_governance_fixture


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("review_directory", type=Path)
    parser.add_argument("--package-only", action="store_true")
    parser.add_argument("--target-repository")
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--reviewed-head-sha")
    parser.add_argument("--governance-fixture", type=Path)
    parser.add_argument("--sequence-app-id", type=int, default=15368)
    parser.add_argument("--sequence-workflow-path", default=".github/workflows/validate-rereview-sequence.yml")
    parser.add_argument("--sequence-workflow-sha")
    parser.add_argument("--sequence-validator-command", default="python scripts/validate_rereview_sequence.py SEQUENCE.json --review EVENT=REVIEW_DIRECTORY")
    args = parser.parse_args()
    governance_evidence = None
    sequence_enforcement = None
    if args.governance_fixture is not None:
        if not (args.target_repository and args.pr_number and args.reviewed_head_sha and args.sequence_workflow_sha):
            print("ERROR: --governance-fixture requires --target-repository, --pr-number, --reviewed-head-sha, and --sequence-workflow-sha")
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
    diagnostics = validate_directory(
        args.review_directory,
        compare_rendered=not args.package_only,
        governance_evidence=governance_evidence,
        sequence_enforcement=sequence_enforcement,
    )
    if diagnostics:
        for item in diagnostics:
            print("ERROR:", item.line())
        return 1
    print("OK: review package is schema-valid, semantically valid, and artifact-consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
