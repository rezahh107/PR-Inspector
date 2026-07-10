from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .diagnostics import Diagnostic

ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
SCHEMA_PATH = (
    ROOT / f"protocols/{CURRENT_VERSION}/schemas/ci-identity.schema.json"
)


def build_ci_identity(
    *,
    tested_ref_type: str,
    tested_sha: str,
    tested_tree_sha: str | None,
    reviewed_head_sha: str,
    synthetic_merge: bool,
    claim_exact_head: bool,
    workflow_run_id: int | None,
    job_ids: list[str],
) -> dict[str, Any]:
    exact = (
        tested_ref_type == "pull_request_head"
        and not synthetic_merge
        and tested_sha == reviewed_head_sha
    )
    return {
        "schema_version": 1,
        "tested_ref_type": tested_ref_type,
        "tested_sha": tested_sha,
        "tested_tree_sha": tested_tree_sha,
        "reviewed_head_sha": reviewed_head_sha,
        "exact_head_match": exact,
        "synthetic_merge": synthetic_merge,
        "claim_exact_head": claim_exact_head,
        "workflow_run_id": workflow_run_id,
        "job_ids": list(dict.fromkeys(job_ids)),
    }


def validate_ci_identity(record: dict[str, Any]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for error in validator.iter_errors(record):
        path = "/" + "/".join(str(item) for item in error.absolute_path)
        diagnostics.append(
            Diagnostic("PRI-CI-IDENTITY-001", path, error.message)
        )
    if diagnostics:
        return sorted(set(diagnostics))

    expected_exact = (
        record["tested_ref_type"] == "pull_request_head"
        and not record["synthetic_merge"]
        and record["tested_sha"] == record["reviewed_head_sha"]
    )
    if record["exact_head_match"] != expected_exact:
        diagnostics.append(
            Diagnostic(
                "PRI-CI-IDENTITY-002",
                "/exact_head_match",
                "exact_head_match does not match tested object identity",
            )
        )
    if record["claim_exact_head"] and not expected_exact:
        diagnostics.append(
            Diagnostic(
                "PRI-CI-IDENTITY-003",
                "/claim_exact_head",
                (
                    "an exact-head claim requires a non-synthetic "
                    "pull-request head SHA equal to reviewed_head_sha"
                ),
            )
        )
    if (
        record["tested_ref_type"] == "pull_request_merge"
        and not record["synthetic_merge"]
    ):
        diagnostics.append(
            Diagnostic(
                "PRI-CI-IDENTITY-004",
                "/synthetic_merge",
                "pull_request_merge ref must be marked synthetic_merge",
            )
        )
    return sorted(set(diagnostics))


def ci_identity_json(record: dict[str, Any]) -> str:
    diagnostics = validate_ci_identity(record)
    if diagnostics:
        raise ValueError("; ".join(item.line() for item in diagnostics))
    return (
        json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    )
