from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import MappingProxyType
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
PROFILE_COMMANDS_BYTES = (
    "برای بررسی حفاظت‌های Merge، تأییدهای مستقل و کنترل‌های حاکمیتی بنویس: سخت گیرانه\n"
    "برای بررسی حداقلی بنویس: حداقلی و سپس آدرس PR را ارسال کن.\n"
).encode("utf-8")
GOVERNANCE_FRESHNESS = timedelta(minutes=15)

TECHNICAL_REASON_CODES = {
    "required_technical_check_failed", "critical_supported_finding", "high_reproduced_finding",
    "blocking_medium_finding", "incomplete_technical_scope", "unresolved_valid_bot_finding",
    "stale_technical_review_identity", "bot_collection_incomplete",
}
TECHNICAL_STATUS_EFFECT = {
    "required_technical_check_failed": "RED", "critical_supported_finding": "RED", "high_reproduced_finding": "RED",
    "blocking_medium_finding": "YELLOW", "incomplete_technical_scope": "YELLOW", "unresolved_valid_bot_finding": "YELLOW",
    "stale_technical_review_identity": "YELLOW", "bot_collection_incomplete": "YELLOW",
}
GOVERNANCE_REASON_CODES = {
    "repository_settings_not_verified", "branch_protection_unavailable", "bypass_actors_unknown",
    "sequence_enforcement_missing", "required_review_enforcement_absent", "merge_authorization_unverified",
    "required_checks_not_verified", "rulesets_unavailable", "merge_queue_unavailable",
}
GOVERNANCE_STATUS_EFFECT = {
    "repository_settings_not_verified": "NOT_VERIFIABLE", "merge_authorization_unverified": "NOT_VERIFIABLE",
    "branch_protection_unavailable": "GAP_FOUND", "bypass_actors_unknown": "GAP_FOUND", "sequence_enforcement_missing": "GAP_FOUND",
    "required_review_enforcement_absent": "GAP_FOUND", "required_checks_not_verified": "GAP_FOUND", "rulesets_unavailable": "GAP_FOUND",
    "merge_queue_unavailable": "GAP_FOUND",
}
REQUIRED_GOVERNANCE_FACTS = {
    "branch_protection_verified", "rulesets_verified", "required_status_checks_verified", "required_check_app_identities_verified",
    "approvals_verified", "pr_author_reviewer_independent", "bypass_actors_verified", "merge_queue_verified", "rereview_sequence_verified",
}
GOVERNANCE_GAP_FIELDS = {
    "branch_protection_verified": "branch_protection_unavailable", "rulesets_verified": "rulesets_unavailable",
    "required_status_checks_verified": "required_checks_not_verified", "required_check_app_identities_verified": "required_checks_not_verified",
    "approvals_verified": "required_review_enforcement_absent", "pr_author_reviewer_independent": "required_review_enforcement_absent",
    "bypass_actors_verified": "bypass_actors_unknown", "merge_queue_verified": "merge_queue_unavailable", "rereview_sequence_verified": "sequence_enforcement_missing",
}
TRIAGE_TO_RECONCILIATION = {
    "accepted": "accepted", "resolved": "resolved", "stale": "stale", "false_positive": "false_positive", "duplicate": "duplicate",
    "insufficient_evidence": "insufficient_evidence", "deferred": "deferred", "out_of_scope": "out_of_scope", "rejected": "false_positive",
}
BLOCKING_FINDING_SEVERITIES = {"CRITICAL", "HIGH"}
MEDIUM_FINDING_SEVERITY = "MEDIUM"
ROOT = Path(__file__).resolve().parents[1]
_CAPABILITY_TOKEN = object()
_REVIEW_TOKEN = object()
_COMMIT_TOKEN = object()


@dataclass(frozen=True)
class CandidateVerifiedInspectorCommit:
    _token: object
    repository: str
    repository_id: int
    commit_sha: str


@dataclass(frozen=True)
class VerifiedGovernanceCapability:
    _token: object
    target_repository: str
    target_repository_id: int
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
    artifact_bytes: Mapping[str, bytes]
    package_file_sha256: str
    inspector_commit: CandidateVerifiedInspectorCommit


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _immutable_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


def _json_object(name: str, raw: bytes) -> dict[str, Any]:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"{name}: UTF-8 BOM is forbidden")
    if b"\r\n" in raw:
        raise ValueError(f"{name}: CRLF is forbidden")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{name}: expected JSON object")
    return value


def is_verified_governance_capability(value: object) -> bool:
    return isinstance(value, VerifiedGovernanceCapability) and value._token is _CAPABILITY_TOKEN


def is_verified_minimal_review_bundle(value: object) -> bool:
    return isinstance(value, VerifiedMinimalReviewBundle) and value._token is _REVIEW_TOKEN


def verify_candidate_inspector_commit_payload(repository_payload: Mapping[str, Any], commit_payload: Mapping[str, Any], expected_commit_sha: str) -> CandidateVerifiedInspectorCommit:
    if repository_payload.get("full_name") != LOCKED_INSPECTOR_REPOSITORY or repository_payload.get("id") != LOCKED_INSPECTOR_REPOSITORY_ID:
        raise ValueError("inspector repository payload does not match candidate trust policy")
    if commit_payload.get("sha") != expected_commit_sha:
        raise ValueError("inspector commit payload SHA mismatch")
    return CandidateVerifiedInspectorCommit(_COMMIT_TOKEN, LOCKED_INSPECTOR_REPOSITORY, LOCKED_INSPECTOR_REPOSITORY_ID, expected_commit_sha)


def _verified_commit(value: object) -> CandidateVerifiedInspectorCommit:
    if not isinstance(value, CandidateVerifiedInspectorCommit) or value._token is not _COMMIT_TOKEN:
        raise ValueError("verified inspector commit evidence is required")
    return value


def verify_governance_payload_bundle(payload: Mapping[str, Any], *, target_repository: str, target_repository_id: int, pull_request: int, reviewed_head_sha: str, now: datetime) -> VerifiedGovernanceCapability:
    if payload.get("source") != "github_rest_api_https":
        raise ValueError("governance payload source is not authoritative")
    if payload.get("target_repository") != target_repository or payload.get("target_repository_id") != target_repository_id:
        raise ValueError("governance payload repository mismatch")
    if payload.get("pull_request") != pull_request or payload.get("reviewed_head_sha") != reviewed_head_sha:
        raise ValueError("governance payload PR/head mismatch")
    observed = datetime.fromisoformat(str(payload.get("observed_at", "")).replace("Z", "+00:00"))
    if observed > now or now - observed > GOVERNANCE_FRESHNESS:
        raise ValueError("governance payload is not fresh")
    facts = payload.get("facts")
    if not isinstance(facts, Mapping) or any(not isinstance(facts.get(field), bool) for field in REQUIRED_GOVERNANCE_FACTS):
        raise ValueError("governance payload facts are incomplete")
    required = payload.get("required_checks")
    runs = payload.get("check_runs")
    if not isinstance(required, Mapping) or not isinstance(runs, Sequence):
        raise ValueError("governance check evidence is incomplete")
    app_ids: dict[str, int] = {}
    for name, app_id in required.items():
        if not isinstance(name, str) or not isinstance(app_id, int) or app_id <= 0:
            raise ValueError("required check identity is malformed")
        matching = [run for run in runs if isinstance(run, Mapping) and run.get("name") == name and run.get("app_id") == app_id and run.get("head_sha") == reviewed_head_sha and run.get("conclusion") in {"success", "neutral", "skipped"}]
        if not matching:
            raise ValueError("required check App identity was not observed on exact head")
        app_ids[name] = app_id
    return VerifiedGovernanceCapability(_CAPABILITY_TOKEN, target_repository, target_repository_id, pull_request, reviewed_head_sha, LOCKED_INSPECTOR_REPOSITORY, LOCKED_INSPECTOR_REPOSITORY_ID, observed.isoformat(), _immutable_mapping(facts), _immutable_mapping(app_ids))


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
    seen: set[str] = set(); out: list[str] = []
    for code in reason_codes:
        if not isinstance(code, str) or not code: raise ValueError(f"{domain} reason code is malformed")
        if code in seen: raise ValueError(f"duplicate {domain} reason code: {code}")
        if code in other: raise ValueError(f"cross-domain {domain} reason code: {code}")
        if code not in allowed: raise ValueError(f"unknown {domain} reason code: {code}")
        seen.add(code); out.append(code)
    return out


def _technical_status_from_reasons(reason_codes: Sequence[str]) -> str:
    statuses = {TECHNICAL_STATUS_EFFECT[code] for code in reason_codes}
    return "RED" if "RED" in statuses else "YELLOW" if "YELLOW" in statuses else "GREEN"


def _governance_status_from_reasons(reason_codes: Sequence[str]) -> str:
    statuses = {GOVERNANCE_STATUS_EFFECT[code] for code in reason_codes}
    return "GAP_FOUND" if "GAP_FOUND" in statuses else "NOT_VERIFIABLE" if "NOT_VERIFIABLE" in statuses else "VERIFIED"


def parse_intake(text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    profile = None
    if lines and lines[0] == "حداقلی": profile = MINIMAL; lines = lines[1:]
    elif lines and lines[0] == "سخت گیرانه": profile = STRICT; lines = lines[1:]
    url = next((line for line in lines if PR_URL_RE.match(line)), None)
    if profile is None: profile = MINIMAL
    if profile == STRICT and url is None and context:
        evidence = context.get("verified_minimal_review")
        target = context.get("current_target")
        live_head = context.get("live_head_sha")
        if target and live_head and verify_base_review_reference(evidence, live_head).get("status") == "VERIFIED" and evidence.reference["target_repository"] == target.get("repository") and evidence.reference["pull_request"] == target.get("pull_request"):
            return {"inspection_profile": STRICT, "target": target, "reuse_current_minimal": True, "missing": []}
    if url is None:
        return {"inspection_profile": profile, "target": None, "reuse_current_minimal": False, "missing": ["pull_request_url"]}
    match = PR_URL_RE.match(url)
    return {"inspection_profile": profile, "target": {"repository": match.group(1), "pull_request": int(match.group(2)), "url": url}, "reuse_current_minimal": False, "missing": []}


def classify_governance(evidence: object, *, target_repository: str | None = None, pull_request: int | None = None, reviewed_head_sha: str | None = None) -> dict[str, Any]:
    if not is_verified_governance_capability(evidence):
        return {"status": "NOT_VERIFIABLE", "reason_codes": ["repository_settings_not_verified"]}
    if (target_repository and evidence.target_repository != target_repository) or (pull_request and evidence.pull_request != pull_request) or (reviewed_head_sha and evidence.reviewed_head_sha != reviewed_head_sha):
        return {"status": "NOT_VERIFIABLE", "reason_codes": ["repository_settings_not_verified"]}
    gap_codes = sorted({GOVERNANCE_GAP_FIELDS[field] for field in REQUIRED_GOVERNANCE_FACTS if evidence.facts[field] is False})
    return {"status": "GAP_FOUND", "reason_codes": gap_codes} if gap_codes else {"status": "VERIFIED", "reason_codes": []}


def project_decision(inspection_profile: str, technical_reason_codes: list[str] | None = None, governance_evidence: object | None = None, *, target_repository: str | None = None, pull_request: int | None = None, reviewed_head_sha: str | None = None) -> dict[str, Any]:
    technical_reason_codes = _validate_reason_codes(technical_reason_codes or [], "technical")
    tech_status = _technical_status_from_reasons(technical_reason_codes)
    if inspection_profile == MINIMAL: governance = {"status": "NOT_REQUESTED", "reason_codes": []}
    elif inspection_profile == STRICT: governance = classify_governance(governance_evidence, target_repository=target_repository, pull_request=pull_request, reviewed_head_sha=reviewed_head_sha)
    else: raise ValueError("unknown inspection_profile")
    governance["reason_codes"] = _validate_reason_codes(governance["reason_codes"], "governance")
    if governance["reason_codes"] and governance["status"] != _governance_status_from_reasons(governance["reason_codes"]):
        raise ValueError("governance status disagrees with registered reason effects")
    return {"schema_version": 1, "protocol_version": PROTOCOL_VERSION, "inspection_profile": inspection_profile, "technical_decision": {"status": tech_status, "reason_codes": technical_reason_codes}, "governance_decision": governance, "overall_recommendation": {"technical_ready": tech_status == "GREEN", "merge_governance_verified": governance["status"] == "VERIFIED"}, "governance_follow_up": {"kind": "none" if governance["status"] in {"NOT_REQUESTED", "VERIFIED"} else ("access_limitation" if governance["status"] == "NOT_VERIFIABLE" else "informational_gap"), "may_modify_code": False, "prompt_required": False}}


def _reject_duplicate(value: str, seen: set[str], path: str) -> None:
    if value in seen: raise ValueError(f"{path}: duplicate id {value}")
    seen.add(value)


def reconcile_bot_reviews(sources: Sequence[Mapping[str, Any]], suggestions: Sequence[Mapping[str, Any]], findings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    source_ids: set[str] = set(); inspected: set[str] = set()
    for index, raw_source in enumerate(sources):
        source = _require_mapping(raw_source, f"sources/{index}"); source_id = _require_key(source, "source_id", f"sources/{index}")
        if not isinstance(source_id, str) or not source_id: raise ValueError(f"sources/{index}/source_id: expected non-empty string")
        _reject_duplicate(source_id, source_ids, f"sources/{index}/source_id")
        if source.get("inspected") is True: inspected.add(source_id)
    finding_ids: set[str] = set(); finding_by_id: dict[str, Mapping[str, Any]] = {}
    for index, raw_finding in enumerate(findings):
        finding = _require_mapping(raw_finding, f"findings/{index}"); finding_id = _require_key(finding, "finding_id", f"findings/{index}")
        if not isinstance(finding_id, str) or not finding_id: raise ValueError(f"findings/{index}/finding_id: expected non-empty string")
        _reject_duplicate(finding_id, finding_ids, f"findings/{index}/finding_id"); finding_by_id[finding_id] = finding
    counts = {key: 0 for key in ["accepted", "resolved", "stale", "false_positive", "duplicate", "insufficient_evidence", "deferred", "out_of_scope"]}
    uninspected = sorted(source_ids - inspected); valid_blocking: list[str] = []; seen_claims: set[tuple[Any, tuple[str, ...]]] = set(); seen_suggestions: set[str] = set(); suggestion_results: list[dict[str, Any]] = []
    for index, raw_item in enumerate(suggestions):
        item = _require_mapping(raw_item, f"suggestions/{index}"); source_id = _require_key(item, "source_id", f"suggestions/{index}")
        if source_id not in source_ids: raise ValueError(f"suggestions/{index}/source_id: unknown source")
        suggestion_id = item.get("suggestion_id") or item.get("external_suggestion_id")
        if suggestion_id is not None:
            if not isinstance(suggestion_id, str) or not suggestion_id: raise ValueError(f"suggestions/{index}/suggestion_id: expected non-empty string")
            _reject_duplicate(suggestion_id, seen_suggestions, f"suggestions/{index}/suggestion_id")
        raw_classification = item.get("triage_decision", item.get("classification"))
        if not isinstance(raw_classification, str): raise ValueError(f"suggestions/{index}/triage_decision: expected string")
        classification = TRIAGE_TO_RECONCILIATION.get(raw_classification)
        if classification is None: raise ValueError(f"suggestions/{index}/triage_decision: invalid classification")
        counts[classification] += 1
        linked = item.get("linked_finding_ids", [])
        if not isinstance(linked, list) or not all(isinstance(fid, str) for fid in linked): raise ValueError(f"suggestions/{index}/linked_finding_ids: expected string array")
        for fid in linked:
            if fid not in finding_ids: raise ValueError(f"suggestions/{index}/linked_finding_ids: unknown finding {fid}")
        linked_tuple = tuple(linked); claim_key = (item.get("claim_summary"), linked_tuple); duplicate_confirmed = classification == "duplicate" and claim_key in seen_claims; seen_claims.add(claim_key)
        repair_authorized = classification == "accepted" and bool(linked)
        if classification == "accepted" and linked:
            for fid in linked:
                finding = finding_by_id[fid]; severity = finding.get("severity")
                if severity in BLOCKING_FINDING_SEVERITIES or (severity == MEDIUM_FINDING_SEVERITY and finding.get("blocking") is True): valid_blocking.append(fid)
        suggestion_results.append({"source_id": source_id, "classification": classification, "linked_finding_ids": linked, "repair_authorized": repair_authorized, "duplicate_confirmed": duplicate_confirmed})
    return {"collection_status": "COMPLETE" if not uninspected else "INCOMPLETE", "open_bot_sources_total": len(source_ids), "inspected_total": len(inspected), "counts": counts, "uninspected_source_ids": uninspected, "valid_blocking_finding_ids": sorted(set(valid_blocking)), "suggestion_results": suggestion_results}


def recompute_external_review_reconciliation(package: Mapping[str, Any]) -> dict[str, Any]:
    intake = package.get("external_review_intake") or {}
    sources = intake.get("sources_inspected", [])
    suggestions = intake.get("suggestions", [])
    findings = package.get("findings", [])
    return reconcile_bot_reviews(sources, suggestions, findings)


def technical_reasons_from_reconciliation(reconciliation: Mapping[str, Any]) -> list[str]:
    reasons = []
    if reconciliation["collection_status"] != "COMPLETE": reasons.append("bot_collection_incomplete")
    if reconciliation.get("valid_blocking_finding_ids"): reasons.append("unresolved_valid_bot_finding")
    return reasons


def collect_candidate_technical_reasons(package: Mapping[str, Any]) -> list[str]:
    reasons: set[str] = set(technical_reasons_from_reconciliation(package["external_review_reconciliation"]))
    identity = package.get("review_identity", {})
    if identity.get("review_validity") != "CURRENT": reasons.add("stale_technical_review_identity")
    if identity.get("review_mode") == "PARTIAL": reasons.add("incomplete_technical_scope")
    scope = package.get("scope", {})
    if scope.get("coverage_complete") is False or scope.get("high_risk_areas_not_reviewed"): reasons.add("incomplete_technical_scope")
    if package.get("unverified_areas") or package.get("required_actions"): reasons.add("incomplete_technical_scope")
    intent = package.get("intent_fit") or {}
    if intent.get("intent_fit_result") not in {None, "satisfied"} or intent.get("unsupported_claims"): reasons.add("incomplete_technical_scope")
    for check in package.get("checks", []):
        if isinstance(check, Mapping) and check.get("required") is True and check.get("result") == "FAIL": reasons.add("required_technical_check_failed")
        elif isinstance(check, Mapping) and check.get("required") is True and check.get("result") in {"UNKNOWN", "NOT_RUN", None}: reasons.add("incomplete_technical_scope")
    for finding in package.get("findings", []):
        if not isinstance(finding, Mapping): continue
        severity = finding.get("severity"); evidence = finding.get("evidence_label")
        if severity == "CRITICAL" and evidence in {"REPRODUCED", "CODE_SUPPORTED"}: reasons.add("critical_supported_finding")
        elif severity == "HIGH" and evidence == "REPRODUCED": reasons.add("high_reproduced_finding")
        elif severity == "HIGH" and evidence == "CODE_SUPPORTED": reasons.add("blocking_medium_finding")
        elif severity == "MEDIUM" and finding.get("blocking") is True: reasons.add("blocking_medium_finding")
    if package.get("repair_handoff", {}).get("affected_findings"):
        reasons.add("incomplete_technical_scope")
    return sorted(reasons)


def _schema_validator(name: str) -> Draft202012Validator:
    schema = json.loads((ROOT / f"protocols/{PROTOCOL_VERSION}/schemas/{name}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def validate_candidate_package(package: Mapping[str, Any], governance_evidence: object | None = None) -> list[str]:
    errors = [error.message for error in _schema_validator("review-package").iter_errors(package)]
    if errors: return sorted(errors)
    if package.get("external_review_intake") is not None:
        try:
            recomputed = recompute_external_review_reconciliation(package)
            if package["external_review_reconciliation"] != recomputed: errors.append("external_review_reconciliation disagrees with recomputed bot review evidence")
        except ValueError as exc:
            errors.append(str(exc))
    technical_reasons = collect_candidate_technical_reasons(package)
    try: derived = project_decision(package.get("inspection_profile"), technical_reasons, governance_evidence)
    except ValueError as exc: return [str(exc)]
    for key in ["technical_decision", "governance_decision", "overall_recommendation"]:
        if package.get(key) != derived[key]: errors.append(f"{key} disagrees with authoritative candidate projection")
    legacy_status = package.get("decision", {}).get("technical_status") if isinstance(package.get("decision"), Mapping) else None
    if legacy_status == "GREEN_TECHNICALLY_READY" and derived["technical_decision"]["status"] != "GREEN": errors.append("legacy technical_status GREEN conflicts with derived candidate status")
    if legacy_status == "RED_DO_NOT_MERGE" and derived["technical_decision"]["status"] != "RED": errors.append("legacy technical_status RED conflicts with derived candidate status")
    return sorted(set(errors))


REQUIRED_REF = {"target_repository", "pull_request", "reviewed_head_sha", "inspector_repository", "inspector_commit_sha", "review_package_sha256", "decision_projection_sha256", "artifact_manifest_sha256"}
REQUIRED_ARTIFACTS = {"review-package.json", "DECISION_PROJECTION.json", "OWNER_DECISION_CARD.fa.md", "TECHNICAL_HANDOFF.en.md", "OWNER_RESULT.fa.txt", "artifact-manifest.json", OWNER_PROFILE_COMMANDS_ARTIFACT}


def verify_minimal_review_artifact_bytes(artifact_bytes: Mapping[str, bytes], inspector_commit: CandidateVerifiedInspectorCommit) -> VerifiedMinimalReviewBundle:
    commit = _verified_commit(inspector_commit)
    snapshot = MappingProxyType({name: bytes(raw) for name, raw in artifact_bytes.items()})
    package = _json_object("review-package.json", snapshot["review-package.json"])
    projection = _json_object("DECISION_PROJECTION.json", snapshot["DECISION_PROJECTION.json"])
    manifest = _json_object("artifact-manifest.json", snapshot["artifact-manifest.json"])
    if package.get("inspection_profile") != MINIMAL or projection.get("inspection_profile") != MINIMAL: raise ValueError("base review is not minimal")
    if validate_candidate_package(package): raise ValueError("candidate package is semantically invalid")
    _schema_validator("decision-projection").validate(projection)
    derived = project_decision(MINIMAL, collect_candidate_technical_reasons(package))
    if projection != derived: raise ValueError("projection does not match authoritative candidate projection")
    if snapshot.get(OWNER_PROFILE_COMMANDS_ARTIFACT) != PROFILE_COMMANDS_BYTES: raise ValueError("owner profile commands artifact bytes are invalid")
    if any(b"\r\n" in raw or raw.startswith(b"\xef\xbb\xbf") for raw in snapshot.values()): raise ValueError("artifact bytes contain forbidden BOM or CRLF")
    manifest_items = manifest.get("artifacts")
    if not isinstance(manifest_items, list): raise ValueError("artifact manifest is malformed")
    paths: set[str] = set(); manifest_hashes: dict[str, str] = {}
    for item in manifest_items:
        if not isinstance(item, Mapping) or not isinstance(item.get("path"), str): raise ValueError("artifact manifest entry is malformed")
        path = item["path"]
        if path in paths: raise ValueError("artifact manifest contains duplicate path")
        if "/" in path or path.startswith("."): raise ValueError("artifact manifest path is not canonical")
        paths.add(path); manifest_hashes[path] = item.get("sha256")
    if not REQUIRED_ARTIFACTS.issubset(set(snapshot)): raise ValueError("artifact set is incomplete")
    for name in REQUIRED_ARTIFACTS - {"artifact-manifest.json"}:
        if manifest_hashes.get(name) != bytes_sha256(snapshot[name]): raise ValueError("artifact manifest mismatch")
    reference = {"target_repository": package["review_identity"]["target_repository"], "pull_request": package["review_identity"].get("pr_number"), "reviewed_head_sha": package["review_identity"]["reviewed_head_sha"], "inspector_repository": commit.repository, "inspector_commit_sha": commit.commit_sha, "review_package_sha256": canonical_sha256(package), "decision_projection_sha256": canonical_sha256(projection), "artifact_manifest_sha256": canonical_sha256(manifest)}
    return VerifiedMinimalReviewBundle(_REVIEW_TOKEN, MappingProxyType(reference), snapshot, bytes_sha256(snapshot["review-package.json"]), commit)


def verify_base_review_reference(evidence: object, live_head_sha: str) -> dict[str, Any]:
    if not is_verified_minimal_review_bundle(evidence): return {"status": "INVALID", "reason": "verified_minimal_review_required"}
    reference = evidence.reference
    if REQUIRED_REF - set(reference): return {"status": "INVALID", "reason": "missing_fields"}
    if evidence.inspector_commit.repository != LOCKED_INSPECTOR_REPOSITORY or evidence.inspector_commit.repository_id != LOCKED_INSPECTOR_REPOSITORY_ID: return {"status": "INVALID", "reason": "inspector_identity_mismatch"}
    if reference["reviewed_head_sha"] != live_head_sha: return {"status": "STALE", "reason": "head_drift", "action": "rerun_minimal_then_strict"}
    return {"status": "VERIFIED", "reason": "same_head", "action": "reuse_technical_decision"}


def render_owner_profile_commands(profile: str) -> bytes:
    if profile not in {MINIMAL, STRICT}: raise ValueError("unknown inspection_profile")
    return PROFILE_COMMANDS_BYTES


def validate_owner_profile_commands(raw: bytes) -> list[str]:
    errors = []
    if raw != PROFILE_COMMANDS_BYTES: errors.append("owner profile commands bytes differ from canonical text")
    if raw.startswith(b"\xef\xbb\xbf"): errors.append("owner profile commands must not contain BOM")
    if b"\r\n" in raw: errors.append("owner profile commands must use LF newlines")
    if not raw.endswith(b"\n"): errors.append("owner profile commands must end with LF")
    if len(raw.decode("utf-8").splitlines()) != 2: errors.append("owner profile commands must contain exactly two visible lines")
    return errors
