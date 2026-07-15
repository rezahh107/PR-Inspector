from __future__ import annotations

import hashlib
import json
import re
from typing import Any

PR_URL_RE = re.compile(r"https://github\.com/([^/\s]+/[^/\s]+)/pull/(\d+)")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MINIMAL = "minimal"
STRICT = "strict"

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
GOVERNANCE_REASON_CODES = {
    "repository_settings_not_verified",
    "branch_protection_unavailable",
    "bypass_actors_unknown",
    "sequence_enforcement_missing",
    "required_review_enforcement_absent",
    "merge_authorization_unverified",
    "required_checks_not_verified",
}


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


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
    m = PR_URL_RE.match(url)
    return {"inspection_profile": profile, "target": {"repository": m.group(1), "pull_request": int(m.group(2)), "url": url}, "reuse_current_minimal": False, "missing": []}


def classify_governance(evidence: dict[str, Any] | None) -> dict[str, Any]:
    if evidence is None or evidence.get("available") is False:
        return {"status": "NOT_VERIFIABLE", "reason_codes": ["repository_settings_not_verified"]}
    if evidence.get("missing_protection") or evidence.get("required_review_enforcement") is False:
        return {"status": "GAP_FOUND", "reason_codes": ["required_review_enforcement_absent"]}
    return {"status": "VERIFIED", "reason_codes": []}


def project_decision(inspection_profile: str, technical_reason_codes: list[str] | None = None, governance_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    technical_reason_codes = technical_reason_codes or []
    leaked = [code for code in technical_reason_codes if code in GOVERNANCE_REASON_CODES]
    if leaked:
        raise ValueError(f"governance reason in technical domain: {', '.join(leaked)}")
    tech_status = "GREEN" if not technical_reason_codes else ("RED" if any(code in {"critical_supported_finding", "high_reproduced_finding"} for code in technical_reason_codes) else "YELLOW")
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
        "inspection_profile": inspection_profile,
        "technical_decision": {"status": tech_status, "reason_codes": technical_reason_codes},
        "governance_decision": governance,
        "overall_recommendation": {"technical_ready": tech_status == "GREEN", "merge_governance_verified": governance["status"] == "VERIFIED"},
        "governance_follow_up": {"kind": "none" if governance["status"] in {"NOT_REQUESTED", "VERIFIED"} else ("access_limitation" if governance["status"] == "NOT_VERIFIABLE" else "informational_gap"), "may_modify_code": False, "prompt_required": False},
    }


def reconcile_bot_reviews(sources: list[dict[str, Any]], suggestions: list[dict[str, Any]], findings: list[dict[str, Any]]) -> dict[str, Any]:
    source_ids = {s["source_id"] for s in sources}
    inspected = {s["source_id"] for s in sources if s.get("inspected")}
    finding_ids = {f["finding_id"] for f in findings}
    counts = {k: 0 for k in ["accepted", "resolved", "stale", "false_positive", "duplicate", "insufficient_evidence", "deferred", "out_of_scope"]}
    uninspected = sorted(source_ids - inspected)
    valid_blocking = []
    seen_claims = set()
    for item in suggestions:
        cls = item["classification"]
        if cls not in counts:
            raise ValueError("invalid bot classification")
        counts[cls] += 1
        if item["source_id"] not in source_ids:
            raise ValueError("unknown bot source")
        linked = item.get("linked_finding_ids", [])
        for fid in linked:
            if fid not in finding_ids:
                raise ValueError("linked finding is missing")
        claim_key = (item.get("claim_summary"), tuple(linked))
        if cls == "accepted" and not linked:
            item["repair_authorized"] = False
        if cls == "duplicate" and claim_key in seen_claims:
            item["duplicate_confirmed"] = True
        seen_claims.add(claim_key)
        if cls == "accepted" and linked:
            for finding in findings:
                if finding["finding_id"] in linked and (finding.get("severity") in {"Critical", "High"} or (finding.get("severity") == "Medium" and finding.get("blocking"))):
                    valid_blocking.append(finding["finding_id"])
    status = "COMPLETE" if not uninspected else "INCOMPLETE"
    return {"collection_status": status, "open_bot_sources_total": len(sources), "inspected_total": len(inspected), "counts": counts, "uninspected_source_ids": uninspected, "valid_blocking_finding_ids": sorted(set(valid_blocking))}


def technical_reasons_from_reconciliation(reconciliation: dict[str, Any]) -> list[str]:
    reasons = []
    if reconciliation["collection_status"] != "COMPLETE":
        reasons.append("bot_collection_incomplete")
    if reconciliation.get("valid_blocking_finding_ids"):
        reasons.append("unresolved_valid_bot_finding")
    return reasons


REQUIRED_REF = {"target_repository", "pull_request", "reviewed_head_sha", "inspector_repository", "inspector_commit_sha", "review_package_sha256", "decision_projection_sha256", "artifact_manifest_sha256"}


def verify_base_review_reference(reference: dict[str, Any], package: dict[str, Any], projection: dict[str, Any], manifest: dict[str, Any], live_head_sha: str) -> dict[str, Any]:
    missing = REQUIRED_REF - set(reference)
    if missing:
        return {"status": "INVALID", "reason": "missing_fields"}
    if not SHA40_RE.match(reference["reviewed_head_sha"]) or not SHA40_RE.match(reference["inspector_commit_sha"]):
        return {"status": "INVALID", "reason": "invalid_sha"}
    if any(not SHA256_RE.match(reference[k]) for k in ["review_package_sha256", "decision_projection_sha256", "artifact_manifest_sha256"]):
        return {"status": "INVALID", "reason": "invalid_hash"}
    if reference["review_package_sha256"] != canonical_sha256(package) or reference["decision_projection_sha256"] != canonical_sha256(projection) or reference["artifact_manifest_sha256"] != canonical_sha256(manifest):
        return {"status": "INVALID", "reason": "hash_mismatch"}
    identity = package.get("review_identity", {})
    if identity.get("target_repository") != reference["target_repository"] or identity.get("pull_request") != reference["pull_request"]:
        return {"status": "INVALID", "reason": "target_mismatch"}
    if reference["reviewed_head_sha"] != live_head_sha:
        return {"status": "STALE", "reason": "head_drift", "action": "rerun_minimal_then_strict"}
    return {"status": "VERIFIED", "reason": "same_head", "action": "reuse_technical_decision"}
