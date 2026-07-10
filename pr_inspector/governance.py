from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
SCHEMA_PATH = ROOT / f"protocols/{CURRENT_VERSION}/schemas/governance-evidence.schema.json"
_VERIFIED_MARKER = object()
_UNVERIFIED_MESSAGE = "merge readiness appears satisfied, but repository-level enforcement is unverified"


class GovernanceEvidenceError(ValueError):
    pass


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def derive_enforcement_status(record: Mapping[str, Any]) -> str:
    if record.get("source") == "unavailable":
        return "unavailable"
    values = {
        "pull_request_required": record.get("pull_request_required", {}).get("value"),
        "required_status_checks": record.get("required_status_checks", {}).get("value"),
        "required_approvals": record.get("required_approvals", {}).get("value"),
        "dismiss_stale_approvals": record.get("dismiss_stale_approvals", {}).get("value"),
        "code_owner_review_required": record.get("code_owner_review_required", {}).get("value"),
        "bypass_actors": record.get("bypass_actors", {}).get("value"),
    }
    if any(value is None for value in values.values()):
        return "insufficient_evidence"
    protections = [
        values["pull_request_required"] is True,
        bool(values["required_status_checks"]),
        isinstance(values["required_approvals"], int) and values["required_approvals"] >= 1,
        values["dismiss_stale_approvals"] is True,
        values["code_owner_review_required"] is True,
    ]
    no_bypass = values["bypass_actors"] == []
    if all(protections) and no_bypass:
        return "verified_enforced"
    if not any(protections) and values["bypass_actors"] == []:
        return "verified_not_enforced"
    return "partially_enforced"


@dataclass(frozen=True)
class VerifiedGovernanceEvidence:
    evidence_id: str
    repository: str
    default_branch: str
    pull_request_number: int
    exact_head_sha: str
    enforcement_status: str
    valid_approval_reviewers: tuple[str, ...]
    required_status_checks: tuple[str, ...]
    exact_head_checks_satisfied: bool
    approval_complete: bool
    specialist_satisfied: bool
    bypass_actors: tuple[str, ...]
    merge_readiness_satisfied: bool
    merge_authorized: bool
    conclusion: str
    _marker: object = field(repr=False, compare=False)


def is_verified_governance_evidence(value: object) -> bool:
    return isinstance(value, VerifiedGovernanceEvidence) and value._marker is _VERIFIED_MARKER


def verify_governance_record(
    record: Mapping[str, Any],
    *,
    expected_repository: str,
    expected_pr_number: int,
    expected_head_sha: str,
) -> VerifiedGovernanceEvidence:
    errors = sorted(_validator().iter_errors(record), key=lambda item: list(item.absolute_path))
    if errors:
        rendered = "; ".join(f"/{'/'.join(map(str, error.absolute_path))}: {error.message}" for error in errors)
        raise GovernanceEvidenceError(f"governance evidence schema validation failed: {rendered}")
    if record["repository"] != expected_repository:
        raise GovernanceEvidenceError("governance repository does not match target")
    if record["pull_request_number"] != expected_pr_number:
        raise GovernanceEvidenceError("governance pull request does not match target")
    if record["exact_head_sha"] != expected_head_sha:
        raise GovernanceEvidenceError("governance evidence is not tied to the exact target head")

    derived_status = derive_enforcement_status(record)
    if record["status"] != derived_status:
        raise GovernanceEvidenceError(
            f"caller-supplied governance status {record['status']} does not match derived {derived_status}"
        )

    valid_reviewers = tuple(sorted({
        review["reviewer"]
        for review in record["reviews"]
        if review["state"] == "APPROVED"
        and review["commit_id"] == expected_head_sha
        and not review["is_bot"]
        and not review["is_author"]
    }))
    required_approvals = record["required_approvals"]["value"]
    approval_complete = isinstance(required_approvals, int) and len(valid_reviewers) >= required_approvals

    required_checks = tuple(sorted(record["required_status_checks"]["value"] or []))
    successful = {
        check["name"]
        for check in record["checks"]
        if check["head_sha"] == expected_head_sha
        and check["status"] == "completed"
        and check["conclusion"] in {"success", "neutral", "skipped"}
    }
    exact_head_checks_satisfied = bool(required_checks) and set(required_checks).issubset(successful)

    specialist = record["specialist_review"]
    specialist_satisfied = (
        not specialist["required"]
        or (
            specialist["reviewer_identity_observed"]
            and specialist["qualification_verified"]
            and specialist["reviewer"] in valid_reviewers
        )
    )
    bypass_actors = tuple(record["bypass_actors"]["value"] or [])
    merge_readiness_satisfied = approval_complete and exact_head_checks_satisfied and specialist_satisfied
    merge_authorized = merge_readiness_satisfied and derived_status == "verified_enforced" and not bypass_actors
    conclusion = "repository-level merge governance is verified and current-head readiness is satisfied" if merge_authorized else _UNVERIFIED_MESSAGE

    canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    evidence_id = hashlib.sha256(canonical).hexdigest()
    return VerifiedGovernanceEvidence(
        evidence_id=evidence_id,
        repository=record["repository"],
        default_branch=record["default_branch"],
        pull_request_number=record["pull_request_number"],
        exact_head_sha=record["exact_head_sha"],
        enforcement_status=derived_status,
        valid_approval_reviewers=valid_reviewers,
        required_status_checks=required_checks,
        exact_head_checks_satisfied=exact_head_checks_satisfied,
        approval_complete=approval_complete,
        specialist_satisfied=specialist_satisfied,
        bypass_actors=bypass_actors,
        merge_readiness_satisfied=merge_readiness_satisfied,
        merge_authorized=merge_authorized,
        conclusion=conclusion,
        _marker=_VERIFIED_MARKER,
    )


def governance_matches_event(evidence: VerifiedGovernanceEvidence, event: Mapping[str, Any]) -> bool:
    return (
        is_verified_governance_evidence(evidence)
        and event.get("governance_evidence_id") == evidence.evidence_id
        and event.get("target_repository") == evidence.repository
        and event.get("pr_number") == evidence.pull_request_number
        and event.get("resulting_head_sha") == evidence.exact_head_sha
    )
