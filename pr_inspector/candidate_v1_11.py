from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

PR_URL_RE = re.compile(r"https://github\.com/([^/\s]+/[^/\s]+)/pull/(\d+)")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MINIMAL = "minimal"
STRICT = "strict"
PROTOCOL_VERSION = "v1.11.0"
LOCKED_INSPECTOR_REPOSITORY = "rezahh107/PR-Inspector"
LOCKED_INSPECTOR_REPOSITORY_ID = 1288323264
OWNER_PROFILE_COMMANDS_ARTIFACT = "OWNER_PROFILE_COMMANDS.fa.txt"

TECHNICAL_REASON_CODES = {
    "required_technical_check_failed",
    "critical_supported_finding",
    "high_reproduced_finding",
    "blocking_medium_finding",
    "incomplete_technical_scope",
    "unresolved_valid_bot_finding",
    "stale_technical_review_identity",
    "bot_collection_incomplete",
}
TECHNICAL_STATUS_EFFECT = {
    "required_technical_check_failed": "RED",
    "critical_supported_finding": "RED",
    "high_reproduced_finding": "RED",
    "blocking_medium_finding": "YELLOW",
    "incomplete_technical_scope": "YELLOW",
    "unresolved_valid_bot_finding": "YELLOW",
    "stale_technical_review_identity": "YELLOW",
    "bot_collection_incomplete": "YELLOW",
}
GOVERNANCE_REASON_CODES = {
    "repository_settings_not_verified",
    "branch_protection_unavailable",
    "bypass_actors_unknown",
    "sequence_enforcement_missing",
    "required_review_enforcement_absent",
    "merge_authorization_unverified",
    "required_checks_not_verified",
    "rulesets_unavailable",
    "merge_queue_unavailable",
}
GOVERNANCE_STATUS_EFFECT = {
    "repository_settings_not_verified": "NOT_VERIFIABLE",
    "merge_authorization_unverified": "NOT_VERIFIABLE",
    "branch_protection_unavailable": "GAP_FOUND",
    "bypass_actors_unknown": "GAP_FOUND",
    "sequence_enforcement_missing": "GAP_FOUND",
    "required_review_enforcement_absent": "GAP_FOUND",
    "required_checks_not_verified": "GAP_FOUND",
    "rulesets_unavailable": "GAP_FOUND",
    "merge_queue_unavailable": "GAP_FOUND",
}
REQUIRED_GOVERNANCE_FACTS = {
    "branch_protection_verified",
    "rulesets_verified",
    "required_status_checks_verified",
    "required_check_app_identities_verified",
    "approvals_verified",
    "pr_author_reviewer_independent",
    "bypass_actors_verified",
    "merge_queue_verified",
    "rereview_sequence_verified",
}
GOVERNANCE_GAP_FIELDS = {
    "branch_protection_verified": "branch_protection_unavailable",
    "rulesets_verified": "rulesets_unavailable",
    "required_status_checks_verified": "required_checks_not_verified",
    "required_check_app_identities_verified": "required_checks_not_verified",
    "approvals_verified": "required_review_enforcement_absent",
    "pr_author_reviewer_independent": "required_review_enforcement_absent",
    "bypass_actors_verified": "bypass_actors_unknown",
    "merge_queue_verified": "merge_queue_unavailable",
    "rereview_sequence_verified": "sequence_enforcement_missing",
}
TRIAGE_TO_RECONCILIATION = {
    "accepted": "accepted",
    "resolved": "resolved",
    "stale": "stale",
    "false_positive": "false_positive",
    "duplicate": "duplicate",
    "insufficient_evidence": "insufficient_evidence",
    "deferred": "deferred",
    "out_of_scope": "out_of_scope",
    "rejected": "false_positive",
}
BLOCKING_FINDING_SEVERITIES = {"CRITICAL", "HIGH"}
MEDIUM_FINDING_SEVERITY = "MEDIUM"
LOW_FINDING_SEVERITY = "LOW"
ROOT = Path(__file__).resolve().parents[1]
_CAPABILITY_TOKEN = object()
_REVIEW_TOKEN = object()


@dataclass(frozen=True)
class VerifiedGovernanceCapability:
    _token: object
    target_repository: str
    pull_request: int
    reviewed_head_sha: str
    inspector_repository: str
    inspector_repository_id: int
    verified_at: str
    facts: Mapping[str, bool]
    required_check_app_ids: Mapping[str, int]


@dataclass(frozen=True)
class VerifiedMinimalReviewBundle:
    _token: object
    reference: Mapping[str, Any]
    package: Mapping[str, Any]
    projection: Mapping[str, Any]
    artifact_manifest: Mapping[str, Any]
    artifact_bytes: Mapping[str, bytes]
    package_file_sha256: str
    inspector_repository_id: int
    inspector_commit_verified: bool


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def is_verified_governance_capability(value: object) -> bool:
    return isinstance(value, VerifiedGovernanceCapability) and value._token is _CAPABILITY_TOKEN


def is_verified_minimal_review_bundle(value: object) -> bool:
    return isinstance(value, VerifiedMinimalReviewBundle) and value._token is _REVIEW_TOKEN


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path}: expected object")
    return value


def _require_key(value: Mapping[str, Any], key: str, path: str) -> Any:
    if key not in value:
        raise ValueError(f"{path}: missing required key {key}")
    return value[key]


def _validate_reason_codes(reason_codes: Sequence[str], domain: str) -> list[str]:
    if not isinstance(reason_codes, Sequence) or isinstance(reason_codes, (str, bytes)):
        raise ValueError(f"{domain} reason_codes must be an array")
    allowed = TECHNICAL_REASON_CODES if domain == "technical" else GOVERNANCE_REASON_CODES
    other = GOVERNANCE_REASON_CODES if domain == "technical" else TECHNICAL_REASON_CODES
    seen: set[str] = set()
    out: list[str] = []
    for code in reason_codes:
        if not isinstance(code, str) or not code:
            raise ValueError(f"{domain} reason code is malformed")
        if code in seen:
            raise ValueError(f"duplicate {domain} reason code: {code}")
        if code in other:
            raise ValueError(f"cross-domain {domain} reason code: {code}")
        if code not in allowed:
            raise ValueError(f"unknown {domain} reason code: {code}")
        seen.add(code)
        out.append(code)
    return out


def _technical_status_from_reasons(reason_codes: Sequence[str]) -> str:
    statuses = {TECHNICAL_STATUS_EFFECT[code] for code in reason_codes}
    if "RED" in statuses:
        return "RED"
    if "YELLOW" in statuses:
        return "YELLOW"
    return "GREEN"


def _governance_status_from_reasons(reason_codes: Sequence[str]) -> str:
    statuses = {GOVERNANCE_STATUS_EFFECT[code] for code in reason_codes}
    if "GAP_FOUND" in statuses:
        return "GAP_FOUND"
    if "NOT_VERIFIABLE" in statuses:
        return "NOT_VERIFIABLE"
    return "VERIFIED"


def mint_governance_capability(
    *,
    target_repository: str,
    pull_request: int,
    reviewed_head_sha: str,
    inspector_repository: str,
    inspector_repository_id: int,
    verified_at: str,
    facts: Mapping[str, bool],
    required_check_app_ids: Mapping[str, int],
    source: str,
) -> VerifiedGovernanceCapability:
    if source != "fresh_github_api_verifier":
        raise ValueError("governance capability source is not verifier-created")
    if inspector_repository != LOCKED_INSPECTOR_REPOSITORY or inspector_repository_id != LOCKED_INSPECTOR_REPOSITORY_ID:
        raise ValueError("governance capability inspector identity mismatch")
    if not SHA40_RE.match(reviewed_head_sha):
        raise ValueError("governance capability head sha is invalid")
    parsed_time = datetime.fromisoformat(verified_at.replace("Z", "+00:00"))
    if parsed_time > datetime.now(timezone.utc):
        raise ValueError("governance capability is future-dated")
    missing_or_malformed = [field for field in REQUIRED_GOVERNANCE_FACTS if not isinstance(facts.get(field), bool)]
    if missing_or_malformed:
        raise ValueError("governance capability facts are incomplete")
    if not required_check_app_ids or not all(isinstance(name, str) and isinstance(app_id, int) and app_id > 0 for name, app_id in required_check_app_ids.items()):
        raise ValueError("governance capability check App identities are incomplete")
    return VerifiedGovernanceCapability(
        _CAPABILITY_TOKEN,
        target_repository,
        pull_request,
        reviewed_head_sha,
        inspector_repository,
        inspector_repository_id,
        verified_at,
        dict(facts),
        dict(required_check_app_ids),
    )


def parse_intake(text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    profile = None
    if lines and lines[0] == "حداقلی":
        profile = MINIMAL
        lines = lines[1:]
    elif lines and lines[0] == "سخت گیرانه":
        profile = STRICT
        lines = lines[1:]
    url = next((line for line in lines if PR_URL_RE.match(line)), None)
    if profile is None:
        profile = MINIMAL
    if profile == STRICT and url is None and context and context.get("current_target") and context.get("verified_minimal_review"):
        target = context["current_target"]
        return {"inspection_profile": STRICT, "target": target, "reuse_current_minimal": True, "missing": []}
    if url is None:
        return {"inspection_profile": profile, "target": None, "reuse_current_minimal": False, "missing": ["pull_request_url"]}
    match = PR_URL_RE.match(url)
    return {
        "inspection_profile": profile,
        "target": {"repository": match.group(1), "pull_request": int(match.group(2)), "url": url},
        "reuse_current_minimal": False,
        "missing": [],
    }


def classify_governance(evidence: object) -> dict[str, Any]:
    if not is_verified_governance_capability(evidence):
        return {"status": "NOT_VERIFIABLE", "reason_codes": ["repository_settings_not_verified"]}
    gap_codes = sorted({GOVERNANCE_GAP_FIELDS[field] for field in REQUIRED_GOVERNANCE_FACTS if evidence.facts[field] is False})
    if gap_codes:
        return {"status": "GAP_FOUND", "reason_codes": gap_codes}
    return {"status": "VERIFIED", "reason_codes": []}


def project_decision(
    inspection_profile: str,
    technical_reason_codes: list[str] | None = None,
    governance_evidence: object | None = None,
) -> dict[str, Any]:
    technical_reason_codes = _validate_reason_codes(technical_reason_codes or [], "technical")
    tech_status = _technical_status_from_reasons(technical_reason_codes)
    if inspection_profile == MINIMAL:
        governance = {"status": "NOT_REQUESTED", "reason_codes": []}
    elif inspection_profile == STRICT:
        governance = classify_governance(governance_evidence)
    else:
        raise ValueError("unknown inspection_profile")
    governance["reason_codes"] = _validate_reason_codes(governance["reason_codes"], "governance")
    if governance["reason_codes"] and governance["status"] != _governance_status_from_reasons(governance["reason_codes"]):
        raise ValueError("governance status disagrees with registered reason effects")
    return {
        "schema_version": 1,
        "protocol_version": PROTOCOL_VERSION,
        "inspection_profile": inspection_profile,
        "technical_decision": {"status": tech_status, "reason_codes": technical_reason_codes},
        "governance_decision": governance,
        "overall_recommendation": {"technical_ready": tech_status == "GREEN", "merge_governance_verified": governance["status"] == "VERIFIED"},
        "governance_follow_up": {
            "kind": "none" if governance["status"] in {"NOT_REQUESTED", "VERIFIED"} else ("access_limitation" if governance["status"] == "NOT_VERIFIABLE" else "informational_gap"),
            "may_modify_code": False,
            "prompt_required": False,
        },
    }


def _reject_duplicate(value: str, seen: set[str], path: str) -> None:
    if value in seen:
        raise ValueError(f"{path}: duplicate id {value}")
    seen.add(value)


def reconcile_bot_reviews(sources: Sequence[Mapping[str, Any]], suggestions: Sequence[Mapping[str, Any]], findings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    source_ids: set[str] = set()
    inspected: set[str] = set()
    for index, raw_source in enumerate(sources):
        source = _require_mapping(raw_source, f"sources/{index}")
        source_id = _require_key(source, "source_id", f"sources/{index}")
        if not isinstance(source_id, str) or not source_id:
            raise ValueError(f"sources/{index}/source_id: expected non-empty string")
        _reject_duplicate(source_id, source_ids, f"sources/{index}/source_id")
        if source.get("inspected") is True:
            inspected.add(source_id)
    finding_ids: set[str] = set()
    finding_by_id: dict[str, Mapping[str, Any]] = {}
    for index, raw_finding in enumerate(findings):
        finding = _require_mapping(raw_finding, f"findings/{index}")
        finding_id = _require_key(finding, "finding_id", f"findings/{index}")
        if not isinstance(finding_id, str) or not finding_id:
            raise ValueError(f"findings/{index}/finding_id: expected non-empty string")
        _reject_duplicate(finding_id, finding_ids, f"findings/{index}/finding_id")
        finding_by_id[finding_id] = finding
    counts = {key: 0 for key in ["accepted", "resolved", "stale", "false_positive", "duplicate", "insufficient_evidence", "deferred", "out_of_scope"]}
    uninspected = sorted(source_ids - inspected)
    valid_blocking: list[str] = []
    seen_claims: set[tuple[Any, tuple[str, ...]]] = set()
    seen_suggestions: set[str] = set()
    suggestion_results: list[dict[str, Any]] = []
    for index, raw_item in enumerate(suggestions):
        item = _require_mapping(raw_item, f"suggestions/{index}")
        source_id = _require_key(item, "source_id", f"suggestions/{index}")
        if source_id not in source_ids:
            raise ValueError(f"suggestions/{index}/source_id: unknown source")
        suggestion_id = item.get("suggestion_id") or item.get("external_suggestion_id")
        if suggestion_id is not None:
            if not isinstance(suggestion_id, str) or not suggestion_id:
                raise ValueError(f"suggestions/{index}/suggestion_id: expected non-empty string")
            _reject_duplicate(suggestion_id, seen_suggestions, f"suggestions/{index}/suggestion_id")
        raw_classification = item.get("triage_decision", item.get("classification"))
        if not isinstance(raw_classification, str):
            raise ValueError(f"suggestions/{index}/triage_decision: expected string")
        classification = TRIAGE_TO_RECONCILIATION.get(raw_classification)
        if classification is None:
            raise ValueError(f"suggestions/{index}/triage_decision: invalid classification")
        counts[classification] += 1
        linked = item.get("linked_finding_ids", [])
        if not isinstance(linked, list) or not all(isinstance(fid, str) for fid in linked):
            raise ValueError(f"suggestions/{index}/linked_finding_ids: expected string array")
        for fid in linked:
            if fid not in finding_ids:
                raise ValueError(f"suggestions/{index}/linked_finding_ids: unknown finding {fid}")
        linked_tuple = tuple(linked)
        claim_key = (item.get("claim_summary"), linked_tuple)
        duplicate_confirmed = classification == "duplicate" and claim_key in seen_claims
        seen_claims.add(claim_key)
        repair_authorized = classification == "accepted" and bool(linked)
        if classification == "accepted" and linked:
            for fid in linked:
                finding = finding_by_id[fid]
                severity = finding.get("severity")
                if severity in BLOCKING_FINDING_SEVERITIES or (severity == MEDIUM_FINDING_SEVERITY and finding.get("blocking") is True):
                    valid_blocking.append(fid)
        suggestion_results.append(
            {
                "source_id": source_id,
                "classification": classification,
                "linked_finding_ids": linked,
                "repair_authorized": repair_authorized,
                "duplicate_confirmed": duplicate_confirmed,
            }
        )
    status = "COMPLETE" if not uninspected else "INCOMPLETE"
    return {
        "collection_status": status,
        "open_bot_sources_total": len(source_ids),
        "inspected_total": len(inspected),
        "counts": counts,
        "uninspected_source_ids": uninspected,
        "valid_blocking_finding_ids": sorted(set(valid_blocking)),
        "suggestion_results": suggestion_results,
    }


def technical_reasons_from_reconciliation(reconciliation: Mapping[str, Any]) -> list[str]:
    reasons = []
    if reconciliation["collection_status"] != "COMPLETE":
        reasons.append("bot_collection_incomplete")
    if reconciliation.get("valid_blocking_finding_ids"):
        reasons.append("unresolved_valid_bot_finding")
    return reasons


def _schema_validator(name: str) -> Draft202012Validator:
    schema = json.loads((ROOT / f"protocols/{PROTOCOL_VERSION}/schemas/{name}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def validate_candidate_package(package: Mapping[str, Any], governance_evidence: object | None = None) -> list[str]:
    errors = [error.message for error in _schema_validator("review-package").iter_errors(package)]
    if errors:
        return sorted(errors)
    profile = package.get("inspection_profile")
    technical_reasons = technical_reasons_from_reconciliation(package["external_review_reconciliation"])
    try:
        derived = project_decision(profile, technical_reasons, governance_evidence)
    except ValueError as exc:
        return [str(exc)]
    for key in ["technical_decision", "governance_decision", "overall_recommendation"]:
        if package.get(key) != derived[key]:
            errors.append(f"{key} disagrees with authoritative candidate projection")
    if profile == MINIMAL and package.get("governance_decision") != {"status": "NOT_REQUESTED", "reason_codes": []}:
        errors.append("minimal governance decision must be NOT_REQUESTED")
    legacy_status = package.get("decision", {}).get("technical_status") if isinstance(package.get("decision"), Mapping) else None
    if legacy_status == "RED_DO_NOT_MERGE" and package.get("technical_decision", {}).get("status") != "RED":
        errors.append("legacy technical_status RED conflicts with candidate technical_decision")
    if package["external_review_reconciliation"]["collection_status"] != "COMPLETE" and package.get("technical_decision", {}).get("status") == "GREEN":
        errors.append("incomplete bot collection cannot be technical GREEN")
    if package.get("overall_recommendation") != derived["overall_recommendation"]:
        errors.append("overall_recommendation disagrees with derived decisions")
    return sorted(set(errors))


REQUIRED_REF = {"target_repository", "pull_request", "reviewed_head_sha", "inspector_repository", "inspector_commit_sha", "review_package_sha256", "decision_projection_sha256", "artifact_manifest_sha256"}
REQUIRED_ARTIFACTS = {"review-package.json", "DECISION_PROJECTION.json", "OWNER_DECISION_CARD.fa.md", "TECHNICAL_HANDOFF.en.md", "OWNER_RESULT.fa.txt", "artifact-manifest.json"}


def mint_minimal_review_bundle(
    *,
    reference: Mapping[str, Any],
    package: Mapping[str, Any],
    projection: Mapping[str, Any],
    artifact_manifest: Mapping[str, Any],
    artifact_bytes: Mapping[str, bytes],
    package_file_sha256: str,
    inspector_repository_id: int,
    inspector_commit_verified: bool,
) -> VerifiedMinimalReviewBundle:
    return VerifiedMinimalReviewBundle(_REVIEW_TOKEN, dict(reference), dict(package), dict(projection), dict(artifact_manifest), dict(artifact_bytes), package_file_sha256, inspector_repository_id, inspector_commit_verified)


def verify_base_review_reference(evidence: object, live_head_sha: str) -> dict[str, Any]:
    if not is_verified_minimal_review_bundle(evidence):
        return {"status": "INVALID", "reason": "verified_minimal_review_required"}
    reference = evidence.reference
    package = evidence.package
    projection = evidence.projection
    manifest = evidence.artifact_manifest
    missing = REQUIRED_REF - set(reference)
    if missing:
        return {"status": "INVALID", "reason": "missing_fields"}
    if reference["inspector_repository"] != LOCKED_INSPECTOR_REPOSITORY or evidence.inspector_repository_id != LOCKED_INSPECTOR_REPOSITORY_ID:
        return {"status": "INVALID", "reason": "inspector_identity_mismatch"}
    if evidence.inspector_commit_verified is not True:
        return {"status": "INVALID", "reason": "inspector_commit_unverified"}
    if not SHA40_RE.match(reference["reviewed_head_sha"]) or not SHA40_RE.match(reference["inspector_commit_sha"]):
        return {"status": "INVALID", "reason": "invalid_sha"}
    if any(not SHA256_RE.match(reference[key]) for key in ["review_package_sha256", "decision_projection_sha256", "artifact_manifest_sha256"]):
        return {"status": "INVALID", "reason": "invalid_hash"}
    if package.get("protocol_version") != PROTOCOL_VERSION or projection.get("protocol_version") != PROTOCOL_VERSION:
        return {"status": "INVALID", "reason": "protocol_mismatch"}
    if package.get("inspection_profile") != MINIMAL or projection.get("inspection_profile") != MINIMAL:
        return {"status": "INVALID", "reason": "base_review_not_minimal"}
    if validate_candidate_package(package):
        return {"status": "INVALID", "reason": "package_semantic_invalid"}
    try:
        _schema_validator("decision-projection").validate(projection)
    except Exception:
        return {"status": "INVALID", "reason": "projection_schema_invalid"}
    derived = project_decision(MINIMAL, technical_reasons_from_reconciliation(package["external_review_reconciliation"]))
    if projection != derived:
        return {"status": "INVALID", "reason": "projection_semantic_mismatch"}
    artifact_names = set(evidence.artifact_bytes)
    if not REQUIRED_ARTIFACTS.issubset(artifact_names):
        return {"status": "INVALID", "reason": "artifact_set_incomplete"}
    manifest_items = manifest.get("artifacts")
    if not isinstance(manifest_items, list):
        return {"status": "INVALID", "reason": "manifest_malformed"}
    manifest_hashes = {item.get("path"): item.get("sha256") for item in manifest_items if isinstance(item, Mapping)}
    for name in REQUIRED_ARTIFACTS:
        if manifest_hashes.get(name) != bytes_sha256(evidence.artifact_bytes[name]):
            return {"status": "INVALID", "reason": "artifact_manifest_mismatch"}
    if reference["review_package_sha256"] != canonical_sha256(package):
        return {"status": "INVALID", "reason": "canonical_package_hash_mismatch"}
    if evidence.package_file_sha256 != bytes_sha256(evidence.artifact_bytes["review-package.json"]):
        return {"status": "INVALID", "reason": "package_file_hash_mismatch"}
    if reference["decision_projection_sha256"] != canonical_sha256(projection) or reference["artifact_manifest_sha256"] != canonical_sha256(manifest):
        return {"status": "INVALID", "reason": "hash_mismatch"}
    identity = package.get("review_identity", {})
    identity_pr = identity.get("pull_request", identity.get("pr_number"))
    if identity.get("target_repository") != reference["target_repository"] or identity_pr != reference["pull_request"]:
        return {"status": "INVALID", "reason": "target_mismatch"}
    if identity.get("reviewed_head_sha") != reference["reviewed_head_sha"]:
        return {"status": "INVALID", "reason": "package_head_mismatch"}
    if identity.get("inspector_repository") != reference["inspector_repository"] or identity.get("inspector_commit_sha") != reference["inspector_commit_sha"]:
        return {"status": "INVALID", "reason": "package_inspector_mismatch"}
    if reference["reviewed_head_sha"] != live_head_sha:
        return {"status": "STALE", "reason": "head_drift", "action": "rerun_minimal_then_strict"}
    return {"status": "VERIFIED", "reason": "same_head", "action": "reuse_technical_decision"}
