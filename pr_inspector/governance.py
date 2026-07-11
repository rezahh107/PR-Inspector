from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping

from ._governance_settings import _derive_settings, derive_enforcement_status
from ._governance_transport import (
    GovernanceEvidenceError,
    GitHubApiResponse,
    SpecialistRequirement,
    VerifiedGitHubGovernanceSource,
    VerifiedGovernanceEvidence,
    _EVIDENCE_CAPABILITIES,
    _HUMAN_GOVERNANCE_MESSAGE,
    _SOURCE_CAPABILITIES,
    _UNVERIFIED_MESSAGE,
    _canonical_json,
    _fresh_response,
    _iso,
    _utcnow,
    _validate_schema,
    fetch_github_api_response,
    github_response_payload,
    is_verified_github_api_response,
)

_SUCCESS_CONCLUSIONS = {"success", "neutral", "skipped"}


def is_verified_github_governance_source(value: object) -> bool:
    return (
        isinstance(value, VerifiedGitHubGovernanceSource)
        and value in _SOURCE_CAPABILITIES
    )


def is_verified_governance_evidence(value: object) -> bool:
    return (
        isinstance(value, VerifiedGovernanceEvidence)
        and value in _EVIDENCE_CAPABILITIES
    )


def _mapping_payload(response: GitHubApiResponse, name: str) -> Mapping[str, Any]:
    if response.status_code != 200:
        raise GovernanceEvidenceError(
            f"insufficient_evidence: {name} endpoint returned HTTP {response.status_code}"
        )
    payload = github_response_payload(response)
    if not isinstance(payload, Mapping):
        raise GovernanceEvidenceError(
            f"insufficient_evidence: {name} endpoint is not a JSON object"
        )
    return payload


def _normalize_reviews(
    response: GitHubApiResponse,
    *,
    expected_head_sha: str,
    author_login: str,
    limitations: list[str],
) -> list[dict[str, Any]]:
    if response.status_code != 200:
        limitations.append("pull-request reviews endpoint is inaccessible")
        return []
    payload = github_response_payload(response)
    if not isinstance(payload, list):
        limitations.append("pull-request reviews payload is not an array")
        return []

    reviews: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, Mapping):
            limitations.append("pull-request reviews payload contains a non-object entry")
            continue
        user = item.get("user")
        login = user.get("login") if isinstance(user, Mapping) else None
        user_type = user.get("type") if isinstance(user, Mapping) else None
        state = item.get("state")
        commit_id = item.get("commit_id")
        submitted_at = item.get("submitted_at")
        if (
            not isinstance(login, str)
            or not login
            or state not in {
                "APPROVED",
                "COMMENTED",
                "CHANGES_REQUESTED",
                "DISMISSED",
                "PENDING",
            }
            or (commit_id is not None and not isinstance(commit_id, str))
            or not isinstance(submitted_at, str)
        ):
            limitations.append("pull-request review entry is incomplete")
            continue
        reviews.append(
            {
                "reviewer": login,
                "state": state,
                "commit_id": commit_id,
                "is_bot": user_type == "Bot" or login.endswith("[bot]"),
                "is_author": login == author_login,
                "submitted_at": submitted_at,
            }
        )
    return reviews


def _normalize_checks(
    response: GitHubApiResponse,
    *,
    limitations: list[str],
) -> list[dict[str, Any]]:
    if response.status_code != 200:
        limitations.append("check-runs endpoint is inaccessible")
        return []
    payload = github_response_payload(response)
    runs = payload.get("check_runs") if isinstance(payload, Mapping) else None
    if not isinstance(runs, list):
        limitations.append("check-runs payload is not complete")
        return []

    checks: list[dict[str, Any]] = []
    for item in runs:
        app = item.get("app") if isinstance(item, Mapping) else None
        app_id = app.get("id") if isinstance(app, Mapping) else None
        name = item.get("name") if isinstance(item, Mapping) else None
        head_sha = item.get("head_sha") if isinstance(item, Mapping) else None
        status = item.get("status") if isinstance(item, Mapping) else None
        conclusion = item.get("conclusion") if isinstance(item, Mapping) else None
        completed_at = item.get("completed_at") if isinstance(item, Mapping) else None
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(app_id, int)
            or app_id <= 0
            or not isinstance(head_sha, str)
            or status not in {"queued", "in_progress", "completed"}
            or (conclusion is not None and not isinstance(conclusion, str))
            or (completed_at is not None and not isinstance(completed_at, str))
        ):
            limitations.append("check-run entry lacks producer or completion identity")
            continue
        checks.append(
            {
                "name": name,
                "app_id": app_id,
                "head_sha": head_sha,
                "status": status,
                "conclusion": conclusion,
                "completed_at": completed_at,
            }
        )
    return checks


def _specialist_record(
    responses: Mapping[str, GitHubApiResponse],
    *,
    valid_reviewers: list[str],
    requirement: SpecialistRequirement | None,
    now: datetime,
    limitations: list[str],
) -> dict[str, Any]:
    if requirement is None:
        return {
            "required": False,
            "reviewer": None,
            "qualification_status": "not_required",
            "qualification_evidence": [],
            "enforcement_status": "not_required",
        }

    evidence: list[str] = []
    qualified: list[str] = []
    for reviewer in sorted(valid_reviewers):
        key = f"specialist:{reviewer}"
        expected_url = (
            "https://api.github.com/orgs/"
            f"{requirement.organization}/teams/{requirement.team_slug}/memberships/{reviewer}"
        )
        response = _fresh_response(
            responses,
            key,
            expected_url=expected_url,
            now=now,
            required=False,
        )
        if response is None:
            continue
        evidence.append(response.response_url)
        payload = github_response_payload(response)
        if (
            response.status_code == 200
            and isinstance(payload, Mapping)
            and payload.get("state") == "active"
        ):
            qualified.append(reviewer)

    if qualified:
        return {
            "required": True,
            "reviewer": qualified[0],
            "qualification_status": "verified",
            "qualification_evidence": sorted(set(evidence)),
            "enforcement_status": "repository_team_enforced",
        }

    limitations.append(_HUMAN_GOVERNANCE_MESSAGE)
    return {
        "required": True,
        "reviewer": sorted(valid_reviewers)[0] if valid_reviewers else None,
        "qualification_status": "unverified",
        "qualification_evidence": sorted(set(evidence)),
        "enforcement_status": "human_governance_required",
    }


def verify_github_governance_source(
    responses: Mapping[str, GitHubApiResponse],
    *,
    expected_repository: str,
    expected_pr_number: int,
    expected_head_sha: str,
    specialist_requirement: SpecialistRequirement | None = None,
    now: datetime | None = None,
) -> VerifiedGitHubGovernanceSource:
    """Derive a sealed governance source from fresh official GitHub API receipts."""

    if not isinstance(responses, Mapping):
        raise GovernanceEvidenceError(
            "governance input is not a mapping of verified official GitHub API responses"
        )
    observed_now = (now or _utcnow()).astimezone(timezone.utc)
    base = f"https://api.github.com/repos/{expected_repository}"

    repository_response = _fresh_response(
        responses,
        "repository",
        expected_url=base,
        now=observed_now,
        required=True,
    )
    pull_request_response = _fresh_response(
        responses,
        "pull_request",
        expected_url=f"{base}/pulls/{expected_pr_number}",
        now=observed_now,
        required=True,
    )
    assert repository_response is not None and pull_request_response is not None
    repository = _mapping_payload(repository_response, "repository")
    pull_request = _mapping_payload(pull_request_response, "pull_request")

    repository_id = repository.get("id")
    default_branch = repository.get("default_branch")
    if repository.get("full_name") != expected_repository:
        raise GovernanceEvidenceError("GitHub repository identity does not match target")
    if not isinstance(repository_id, int) or repository_id <= 0:
        raise GovernanceEvidenceError("GitHub repository id is missing or invalid")
    if repository.get("url") != base:
        raise GovernanceEvidenceError("GitHub repository API URL is not canonical")
    if repository.get("html_url") != f"https://github.com/{expected_repository}":
        raise GovernanceEvidenceError("GitHub repository HTML URL is not canonical")
    if not isinstance(default_branch, str) or not default_branch:
        raise GovernanceEvidenceError("GitHub repository default branch is missing")

    head = pull_request.get("head")
    base_ref = pull_request.get("base")
    author = pull_request.get("user")
    if pull_request.get("number") != expected_pr_number:
        raise GovernanceEvidenceError("GitHub pull request number does not match target")
    if not isinstance(head, Mapping) or head.get("sha") != expected_head_sha:
        raise GovernanceEvidenceError("GitHub pull request head does not match target")
    if not isinstance(base_ref, Mapping) or base_ref.get("ref") != default_branch:
        raise GovernanceEvidenceError("GitHub pull request base does not match repository default")
    author_login = author.get("login") if isinstance(author, Mapping) else None
    if not isinstance(author_login, str) or not author_login:
        raise GovernanceEvidenceError("GitHub pull request author identity is missing")

    protection_url = f"{base}/branches/{default_branch}/protection"
    rulesets_url = f"{base}/rulesets?includes_parents=true&per_page=100"
    reviews_url = f"{base}/pulls/{expected_pr_number}/reviews?per_page=100"
    checks_url = f"{base}/commits/{expected_head_sha}/check-runs?per_page=100"
    protection = _fresh_response(
        responses,
        "branch_protection",
        expected_url=protection_url,
        now=observed_now,
        required=True,
    )
    rulesets = _fresh_response(
        responses,
        "rulesets",
        expected_url=rulesets_url,
        now=observed_now,
        required=True,
    )
    reviews_response = _fresh_response(
        responses,
        "reviews",
        expected_url=reviews_url,
        now=observed_now,
        required=True,
    )
    checks_response = _fresh_response(
        responses,
        "checks",
        expected_url=checks_url,
        now=observed_now,
        required=True,
    )
    assert protection is not None and rulesets is not None
    assert reviews_response is not None and checks_response is not None

    ruleset_details: dict[int, GitHubApiResponse] = {}
    rulesets_payload = github_response_payload(rulesets)
    if rulesets.status_code == 200 and isinstance(rulesets_payload, list):
        for item in rulesets_payload:
            if (
                isinstance(item, Mapping)
                and item.get("enforcement") == "active"
                and isinstance(item.get("id"), int)
            ):
                rule_id = item["id"]
                detail = _fresh_response(
                    responses,
                    f"ruleset:{rule_id}",
                    expected_url=f"{base}/rulesets/{rule_id}",
                    now=observed_now,
                    required=True,
                )
                assert detail is not None
                ruleset_details[rule_id] = detail

    limitations: list[str] = []
    settings = _derive_settings(
        branch=default_branch,
        protection_response=protection,
        rulesets_response=rulesets,
        ruleset_details=ruleset_details,
        limitations=limitations,
    )
    reviews = _normalize_reviews(
        reviews_response,
        expected_head_sha=expected_head_sha,
        author_login=author_login,
        limitations=limitations,
    )
    checks = _normalize_checks(checks_response, limitations=limitations)
    valid_reviewers = [
        item["reviewer"]
        for item in reviews
        if item["state"] == "APPROVED"
        and item["commit_id"] == expected_head_sha
        and not item["is_bot"]
        and not item["is_author"]
    ]
    specialist = _specialist_record(
        responses,
        valid_reviewers=valid_reviewers,
        requirement=specialist_requirement,
        now=observed_now,
        limitations=limitations,
    )

    response_values = [repository_response, pull_request_response, protection, rulesets, reviews_response, checks_response, *ruleset_details.values()]
    for key, response in responses.items():
        if key.startswith("specialist:") and is_verified_github_api_response(response):
            response_values.append(response)

    record: dict[str, Any] = {
        "schema_version": 2,
        "repository": expected_repository,
        "repository_id": repository_id,
        "default_branch": default_branch,
        "pull_request_number": expected_pr_number,
        "exact_head_sha": expected_head_sha,
        "observed_at": _iso(observed_now),
        "source": "github_rest_api_https",
        **settings,
        "reviews": reviews,
        "checks": checks,
        "specialist_review": specialist,
        "status": "insufficient_evidence",
        "limitations": sorted(set(limitations)),
    }
    record["status"] = derive_enforcement_status(record)
    _validate_schema(record)

    source = object.__new__(VerifiedGitHubGovernanceSource)
    object.__setattr__(source, "canonical_record_json", _canonical_json(record))
    object.__setattr__(source, "repository", expected_repository)
    object.__setattr__(source, "repository_id", repository_id)
    object.__setattr__(source, "response_urls", tuple(sorted({item.response_url for item in response_values})))
    object.__setattr__(source, "response_receipt_ids", tuple(sorted({item.receipt_id for item in response_values})))
    object.__setattr__(source, "response_content_ids", tuple(sorted({item.content_id for item in response_values})))
    _SOURCE_CAPABILITIES.add(source)
    return source


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
    record = json.loads(source.canonical_record_json)
    _validate_schema(record)
    if source.repository != expected_repository or record["repository"] != expected_repository:
        raise GovernanceEvidenceError("governance repository does not match target")
    if record["repository_id"] != source.repository_id:
        raise GovernanceEvidenceError("governance repository id does not match source")
    if record["pull_request_number"] != expected_pr_number:
        raise GovernanceEvidenceError("governance pull request does not match target")
    if record["exact_head_sha"] != expected_head_sha:
        raise GovernanceEvidenceError("governance evidence is not tied to the exact target head")

    derived_status = derive_enforcement_status(record)
    if record["status"] != derived_status:
        raise GovernanceEvidenceError(
            f"governance status {record['status']} does not match derived {derived_status}"
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
        and required_approvals >= 1
        and len(valid_reviewers) >= required_approvals
    )

    required_checks = tuple(
        sorted(
            (item["context"], item["app_id"])
            for item in (record["required_status_checks"]["value"] or [])
        )
    )
    successful_checks = {
        (item["name"], item["app_id"])
        for item in record["checks"]
        if item["head_sha"] == expected_head_sha
        and item["status"] == "completed"
        and item["conclusion"] in _SUCCESS_CONCLUSIONS
        and item["completed_at"] is not None
    }
    exact_head_checks_satisfied = bool(required_checks) and set(required_checks).issubset(successful_checks)

    specialist = record["specialist_review"]
    specialist_satisfied = not specialist["required"] or (
        specialist["qualification_status"] == "verified"
        and specialist["enforcement_status"] == "repository_team_enforced"
        and specialist["reviewer"] in valid_reviewers
        and bool(specialist["qualification_evidence"])
    )
    specialist_status = specialist["enforcement_status"]
    bypass_actors = tuple(record["bypass_actors"]["value"] or [])
    merge_readiness_satisfied = approval_complete and exact_head_checks_satisfied and specialist_satisfied
    merge_authorized = merge_readiness_satisfied and derived_status == "verified_enforced" and not bypass_actors
    conclusion = (
        "repository-level merge governance is verified and current-head readiness is satisfied"
        if merge_authorized
        else _UNVERIFIED_MESSAGE
    )

    evidence_payload = {
        "record": record,
        "repository_id": source.repository_id,
        "response_urls": source.response_urls,
        "response_receipt_ids": source.response_receipt_ids,
        "response_content_ids": source.response_content_ids,
    }
    evidence_id = hashlib.sha256(_canonical_json(evidence_payload).encode("utf-8")).hexdigest()
    evidence = object.__new__(VerifiedGovernanceEvidence)
    values = {
        "evidence_id": evidence_id,
        "repository": record["repository"],
        "default_branch": record["default_branch"],
        "pull_request_number": record["pull_request_number"],
        "exact_head_sha": record["exact_head_sha"],
        "enforcement_status": derived_status,
        "valid_approval_reviewers": valid_reviewers,
        "required_status_checks": required_checks,
        "exact_head_checks_satisfied": exact_head_checks_satisfied,
        "approval_complete": approval_complete,
        "specialist_satisfied": specialist_satisfied,
        "specialist_status": specialist_status,
        "bypass_actors": bypass_actors,
        "merge_readiness_satisfied": merge_readiness_satisfied,
        "merge_authorized": merge_authorized,
        "conclusion": conclusion,
        "source_response_urls": source.response_urls,
    }
    for name, value in values.items():
        object.__setattr__(evidence, name, value)
    _EVIDENCE_CAPABILITIES.add(evidence)
    return evidence


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


__all__ = [
    "GovernanceEvidenceError",
    "GitHubApiResponse",
    "SpecialistRequirement",
    "VerifiedGitHubGovernanceSource",
    "VerifiedGovernanceEvidence",
    "derive_enforcement_status",
    "fetch_github_api_response",
    "github_response_payload",
    "is_verified_github_api_response",
    "is_verified_github_governance_source",
    "is_verified_governance_evidence",
    "verify_github_governance_source",
    "verify_governance_record",
    "governance_matches_event",
]
