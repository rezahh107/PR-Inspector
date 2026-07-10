#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pr_inspector.ci_identity import build_ci_identity, ci_identity_json


def _bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes"}:
        return True
    if lowered in {"0", "false", "no"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean: {value}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tested-ref-type", required=True)
    parser.add_argument("--tested-sha", required=True)
    parser.add_argument("--tested-tree-sha")
    parser.add_argument("--reviewed-head-sha", required=True)
    parser.add_argument("--synthetic-merge", type=_bool, required=True)
    parser.add_argument("--claim-exact-head", type=_bool, required=True)
    parser.add_argument("--workflow-run-id", type=int)
    parser.add_argument("--job-id", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    record = build_ci_identity(
        tested_ref_type=args.tested_ref_type,
        tested_sha=args.tested_sha,
        tested_tree_sha=args.tested_tree_sha,
        reviewed_head_sha=args.reviewed_head_sha,
        synthetic_merge=args.synthetic_merge,
        claim_exact_head=args.claim_exact_head,
        workflow_run_id=args.workflow_run_id,
        job_ids=args.job_id,
    )
    text = ci_identity_json(record)
    args.output.write_bytes(text.encode("utf-8"))
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
