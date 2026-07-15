from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

PR_URL_RE = re.compile(r"https://github\.com/([^/\s]+/[^/\s]+)/pull/(\d+)")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MINIMAL = "minimal"
STRICT = "strict"
PROTOCOL_VERSION = "v1.11.0"
LOCKED_INSPECTOR_REPOSITORY = "rezahh107/PR-Inspector"

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
RED_TECHNICAL_REASON_CODES = {
    "required_technical_check_failed",
    "critical_supported_finding",
    "high_reproduced_finding",
}
GOVERNANCE_REASON_CODES = {
    "repository_settings_not_verified",
    "branch_protection_unavailable",
    "bypass_actors_unknown",
    "sequence_enforcement_missing",
    "required_review_enforcement_absent",
    "merge_authorization_unverified",
    "required_checks_not_verified",
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
    "required_status_checks_verified": "required_checks_not_verified",
    "required_check_app_identities_verified": "required_checks_not_verified",
    "approvals_verified": "required_review_enforcement_absent",
    "pr_author_reviewer_independent": "required_review_enforcement_absent",
    "bypass_actors_verified": "bypass_actors_unknown",
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


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path}: expected object")
    return value


def _require_key(value: Mapping[str, Any], key: str, path: str) -> Any:
    if key not in value:
        raise ValueError(f"{path}: missing required key {key}")
    return value[key]


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


def classify_governance(evidence: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(evidence, Mapping) or not evidence:
        return {"status": "NOT_VERIFIABLE", "reason_codes": ["repository_settings_not_verified"]}
    if evidence.get("available") is not True:
        return {"status": "NOT_VERIFIABLE", "reason_codes": ["repository_settings_not_verified"]}
    missing_or_malformed = [field for field in REQUIRED_GOVERNANCE_FACTS if not isinstance(evidence.get(field), bool)]
    if missing_or_malformed:
        return {"status": "NOT_VERIFIABLE", "reason_codes": ["repository_settings_not_verified"]}
    gap_codes = sorted({GOVERNANCE_GAP_FIELDS.get(field, "repository_settings_not_verified") for field in REQUIRED_GOVERNANCE_FACTS if evidence[field] is False})
    if gap_codes:
        return {"status": "GAP_FOUND", "reason_codes": gap_codes}
    return {"status": "VERIFIED", "reason_codes": []}


def project_decision(
    inspection_profile: str,
    technical_reason_codes: list[str] | None = None,
    governance_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    technical_reason_codes = technical_reason_codes or []
    leaked = [code for code in technical_reason_codes if code in GOVERNANCE_REASON_CODES]
    if leaked:
        raise ValueError(f"governance reason in technical domain: {', '.join(leaked)}")
    tech_status = "GREEN"
    if any(code in RED_TECHNICAL_REASON_CODES for code in technical_reason_codes):
        tech_status = "RED"
    elif technical_reason_codes:
        tech_status = "YELLOW"
    if inspection_profile == MINIMAL:
        governance = {"status": "NOT_REQUESTED", "reason_codes": []}
    elif inspection_profile == STRICT:
        governance = classify_governance(governance_evidence)
    else:
        raise ValueError("unknown inspection_profile")
    for code in governance["reason_codes"]:
        if code in TECHNICAL_REASON_CODES:
            raise ValueError(f"technical reason in governance domain: {code}")
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


def reconcile_bot_reviews(sources: Sequence[Mapping[str, Any]], suggestions: Sequence[Mapping[str, Any]], findings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    source_ids: set[str] = set()
    inspected: set[str] = set()
    for index, raw_source in enumerate(sources):
        source = _require_mapping(raw_source, f"sources/{index}")
        source_id = _require_key(source, "source_id", f"sources/{index}")
        if not isinstance(source_id, str) or not source_id:
            raise ValueError(f"sources/{index}/source_id: expected non-empty string")
        source_ids.add(source_id)
        if source.get("inspected") is True:
            inspected.add(source_id)
    finding_ids: set[str] = set()
    finding_by_id: dict[str, Mapping[str, Any]] = {}
    for index, raw_finding in enumerate(findings):
        finding = _require_mapping(raw_finding, f"findings/{index}")
        finding_id = _require_key(finding, "finding_id", f"findings/{index}")
        if not isinstance(finding_id, str) or not finding_id:
            raise ValueError(f"findings/{index}/finding_id: expected non-empty string")
        finding_ids.add(finding_id)
        finding_by_id[finding_id] = finding
    counts = {key: 0 for key in ["accepted", "resolved", "stale", "false_positive", "duplicate", "insufficient_evidence", "deferred", "out_of_scope"]}
    uninspected = sorted(source_ids - inspected)
    valid_blocking: list[str] = []
    seen_claims: set[tuple[Any, tuple[str, ...]]] = set()
    suggestion_results: list[dict[str, Any]] = []
    for index, raw_item in enumerate(suggestions):
        item = _require_mapping(raw_item, f"suggestions/{index}")
        source_id = _require_key(item, "source_id", f"suggestions/{index}")
        if source_id not in source_ids:
            raise ValueError(f"suggestions/{index}/source_id: unknown source")
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
                if finding.get("severity") in {"Critical", "High"} or (finding.get("severity") == "Medium" and finding.get("blocking") is True):
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


def technical_reasons_from_reconciliation(reconciliation: dict[str, Any]) -> list[str]:
    reasons = []
    if reconciliation["collection_status"] != "COMPLETE":
        reasons.append("bot_collection_incomplete")
    if reconciliation.get("valid_blocking_finding_ids"):
        reasons.append("unresolved_valid_bot_finding")
    return reasons


REQUIRED_REF = {"target_repository", "pull_request", "reviewed_head_sha", "inspector_repository", "inspector_commit_sha", "review_package_sha256", "decision_projection_sha256", "artifact_manifest_sha256"}


def verify_base_review_reference(
    reference: dict[str, Any],
    package: dict[str, Any],
    projection: dict[str, Any],
    manifest: dict[str, Any],
    live_head_sha: str,
    *,
    inspector_repository: str = LOCKED_INSPECTOR_REPOSITORY,
    commit_verifier: Callable[[str, str], bool] | None = None,
) -> dict[str, Any]:
    if not isinstance(reference, Mapping):
        return {"status": "INVALID", "reason": "reference_malformed"}
    missing = REQUIRED_REF - set(reference)
    if missing:
        return {"status": "INVALID", "reason": "missing_fields"}
    if reference["inspector_repository"] != inspector_repository:
        return {"status": "INVALID", "reason": "inspector_repository_mismatch"}
    if not SHA40_RE.match(reference["reviewed_head_sha"]) or not SHA40_RE.match(reference["inspector_commit_sha"]):
        return {"status": "INVALID", "reason": "invalid_sha"}
    if any(not SHA256_RE.match(reference[key]) for key in ["review_package_sha256", "decision_projection_sha256", "artifact_manifest_sha256"]):
        return {"status": "INVALID", "reason": "invalid_hash"}
    if commit_verifier is not None and not commit_verifier(reference["inspector_repository"], reference["inspector_commit_sha"]):
        return {"status": "INVALID", "reason": "inspector_commit_unverified"}
    if package.get("protocol_version") != PROTOCOL_VERSION:
        return {"status": "INVALID", "reason": "protocol_mismatch"}
    if reference["review_package_sha256"] != canonical_sha256(package) or reference["decision_projection_sha256"] != canonical_sha256(projection) or reference["artifact_manifest_sha256"] != canonical_sha256(manifest):
        return {"status": "INVALID", "reason": "hash_mismatch"}
    identity = package.get("review_identity", {})
    if identity.get("target_repository") != reference["target_repository"] or identity.get("pull_request") != reference["pull_request"]:
        return {"status": "INVALID", "reason": "target_mismatch"}
    if identity.get("reviewed_head_sha") != reference["reviewed_head_sha"]:
        return {"status": "INVALID", "reason": "package_head_mismatch"}
    if identity.get("inspector_repository") != reference["inspector_repository"] or identity.get("inspector_commit_sha") != reference["inspector_commit_sha"]:
        return {"status": "INVALID", "reason": "package_inspector_mismatch"}
    if reference["reviewed_head_sha"] != live_head_sha:
        return {"status": "STALE", "reason": "head_drift", "action": "rerun_minimal_then_strict"}
    return {"status": "VERIFIED", "reason": "same_head", "action": "reuse_technical_decision"}
