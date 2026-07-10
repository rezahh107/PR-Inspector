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
_SOURCE_MARKER = object()
_VERIFIED_MARKER = object()
_UNVERIFIED_MESSAGE = (
    "merge readiness appears satisfied, but repository-level enforcement is unverified"
)
_EVIDENCE_CARRIERS = (
    "pull_request_required",
    "required_status_checks",
    "required_approvals",
    "dismiss_stale_approvals",
    "code_owner_review_required",
    "bypass_actors",
    "merge_queue_required",
)


class GovernanceEvidenceError(ValueError):
    pass


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _validate_schema(record: Mapping[str, Any]) -> None:
    errors = sorted(
        _validator().iter_errors(record),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        rendered = "; ".join(
            f"/{'/'.join(map(str, error.absolute_path))}: {error.message}"
            for error in errors
        )
        raise GovernanceEvidenceError(
            f"governance evidence schema validation failed: {rendered}"
        )


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
        isinstance(values["required_approvals"], int)
        and values["required_approvals"] >= 1,
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
class VerifiedGitHubGovernanceSource:
    """Opaque receipt for a normalized record bound to official GitHub API responses."""

    canonical_record_json: str
    repository: str
    repository_id: int
    response_urls: tuple[str, ...]
    _marker: object = field(repr=False, compare=False)


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
    source_response_urls: tuple[str, ...]
    _marker: object = field(repr=False, compare=False)


def is_verified_github_governance_source(value: object) -> bool:
    return (
        isinstance(value, VerifiedGitHubGovernanceSource)
        and value._marker is _SOURCE_MARKER
    )


def is_verified_governance_evidence(value: object) -> bool:
    return (
        isinstance(value, VerifiedGovernanceEvidence)
        and value._marker is _VERIFIED_MARKER
    )


def verify_github_governance_source(
    record: Mapping[str, Any],
    *,
    repository_payload: Mapping[str, Any],
    response_urls: list[str] | tuple[str, ...],
    expected_repository: str,
) -> VerifiedGitHubGovernanceSource:
    """Bind a normalized governance record to official GitHub REST response receipts.

    The operational adapter must obtain ``repository_payload`` and every URL in
    ``response_urls`` over HTTPS from ``api.github.com``. This pure verifier makes
    the boundary deterministic and testable; it does not accept repository JSON as
    authoritative merely because the JSON is schema-valid.
    """

    _validate_schema(record)
    if record["source"] != "github_rest_api_https":
        raise GovernanceEvidenceError(
            "only official GitHub REST API evidence can create a verified governance source"
        )
    if record["repository"] != expected_repository:
        raise GovernanceEvidenceError("governance repository does not match target")

    repository_api_url = f"https://api.github.com/repos/{expected_repository}"
    repository_html_url = f"https://github.com/{expected_repository}"
    repository_id = repository_payload.get("id")
    if repository_payload.get("full_name") != expected_repository:
        raise GovernanceEvidenceError(
            "GitHub repository full_name does not match governance target"
        )
    if not isinstance(repository_id, int) or repository_id <= 0:
        raise GovernanceEvidenceError("GitHub repository id is missing or invalid")
    if repository_payload.get("url") != repository_api_url:
        raise GovernanceEvidenceError("GitHub repository API URL is not canonical")
    if repository_payload.get("html_url") != repository_html_url:
        raise GovernanceEvidenceError("GitHub repository HTML URL is not canonical")

    urls = tuple(sorted(set(response_urls)))
    if not urls:
        raise GovernanceEvidenceError("GitHub governance response receipts are missing")
    for url in urls:
        if not isinstance(url, str) or not (
            url == repository_api_url or url.startswith(repository_api_url + "/")
        ):
            raise GovernanceEvidenceError(
                f"governance response URL is not canonical for {expected_repository}: {url}"
            )
    if repository_api_url not in urls:
        raise GovernanceEvidenceError(
            "verified governance source is missing the GitHub repository response"
        )

    evidence_urls: set[str] = set()
    for carrier_name in _EVIDENCE_CARRIERS:
        carrier = record[carrier_name]
        carrier_evidence = carrier["evidence"]
        if not carrier_evidence:
            raise GovernanceEvidenceError(
                f"{carrier_name} has no authoritative GitHub evidence receipt"
            )
        for url in carrier_evidence:
            if not (
                url == repository_api_url or url.startswith(repository_api_url + "/")
            ):
                raise GovernanceEvidenceError(
                    f"{carrier_name} evidence is not an official GitHub API URL"
                )
            evidence_urls.add(url)

    reviews_url = (
        f"{repository_api_url}/pulls/{record['pull_request_number']}/reviews"
    )
    checks_url = f"{repository_api_url}/commits/{record['exact_head_sha']}/check-runs"
    required_receipts = evidence_urls | {reviews_url, checks_url}
    missing_receipts = sorted(required_receipts - set(urls))
    if missing_receipts:
        raise GovernanceEvidenceError(
            "verified governance source is missing fetched response receipts: "
            + ", ".join(missing_receipts)
        )

    canonical_record_json = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return VerifiedGitHubGovernanceSource(
        canonical_record_json=canonical_record_json,
        repository=expected_repository,
        repository_id=repository_id,
        response_urls=urls,
        _marker=_SOURCE_MARKER,
    )


def verify_governance_record(
    source: VerifiedGitHubGovernanceSource,
    *,
    expected_repository: str,
    expected_pr_number: int,
    expected_head_sha: str,
) -> VerifiedGovernanceEvidence:
    if not is_verified_github_governance_source(source):
        raise GovernanceEvidenceError(
            "governance source is not verified official GitHub API evidence"
        )
    assert isinstance(source, VerifiedGitHubGovernanceSource)
    record = json.loads(source.canonical_record_json)
    _validate_schema(record)

    if source.repository != expected_repository or record["repository"] != expected_repository:
        raise GovernanceEvidenceError("governance repository does not match target")
    if record["pull_request_number"] != expected_pr_number:
        raise GovernanceEvidenceError("governance pull request does not match target")
    if record["exact_head_sha"] != expected_head_sha:
        raise GovernanceEvidenceError(
            "governance evidence is not tied to the exact target head"
        )

    derived_status = derive_enforcement_status(record)
    if record["status"] != derived_status:
        raise GovernanceEvidenceError(
            f"caller-supplied governance status {record['status']} does not match derived {derived_status}"
        )

    valid_reviewers = tuple(
        sorted(
            {
                review["reviewer"]
                for review in record["reviews"]
                if review["state"] == "APPROVED"
                and review["commit_id"] == expected_head_sha
                and not review["is_bot"]
                and not review["is_author"]
            }
        )
    )
    required_approvals = record["required_approvals"]["value"]
    approval_complete = (
        isinstance(required_approvals, int)
        and len(valid_reviewers) >= required_approvals
    )

    required_checks = tuple(
        sorted(record["required_status_checks"]["value"] or [])
    )
    successful = {
        check["name"]
        for check in record["checks"]
        if check["head_sha"] == expected_head_sha
        and check["status"] == "completed"
        and check["conclusion"] in {"success", "neutral", "skipped"}
    }
    exact_head_checks_satisfied = bool(required_checks) and set(
        required_checks
    ).issubset(successful)

    specialist = record["specialist_review"]
    specialist_satisfied = not specialist["required"] or (
        specialist["reviewer_identity_observed"]
        and specialist["qualification_verified"]
        and specialist["reviewer"] in valid_reviewers
    )
    bypass_actors = tuple(record["bypass_actors"]["value"] or [])
    merge_readiness_satisfied = (
        approval_complete and exact_head_checks_satisfied and specialist_satisfied
    )
    merge_authorized = (
        merge_readiness_satisfied
        and derived_status == "verified_enforced"
        and not bypass_actors
    )
    conclusion = (
        "repository-level merge governance is verified and current-head readiness is satisfied"
        if merge_authorized
        else _UNVERIFIED_MESSAGE
    )

    evidence_payload = {
        "record": record,
        "repository_id": source.repository_id,
        "response_urls": source.response_urls,
    }
    evidence_id = hashlib.sha256(
        json.dumps(
            evidence_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
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
        source_response_urls=source.response_urls,
        _marker=_VERIFIED_MARKER,
    )


def governance_matches_event(
    evidence: VerifiedGovernanceEvidence,
    event: Mapping[str, Any],
) -> bool:
    return (
        is_verified_governance_evidence(evidence)
        and event.get("governance_evidence_id") == evidence.evidence_id
        and event.get("target_repository") == evidence.repository
        and event.get("pr_number") == evidence.pull_request_number
        and event.get("resulting_head_sha") == evidence.exact_head_sha
    )
