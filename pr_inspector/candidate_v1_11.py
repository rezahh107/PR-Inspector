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

from ._governance_transport import GitHubApiResponse, github_response_payload, is_verified_github_api_response
from .governance import VerifiedGovernanceEvidence, is_verified_governance_evidence
from .review_provenance import VerifiedInspectorCommit, _VERIFIED_MARKER

PR_URL_RE = re.compile(r"https://github\.com/([^/\s]+/[^/\s]+)/pull/(\d+)")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MINIMAL = "minimal"
STRICT = "strict"
PROTOCOL_VERSION = "v1.11.0"
LOCKED_INSPECTOR_REPOSITORY = "rezahh107/PR-Inspector"
LOCKED_INSPECTOR_REPOSITORY_ID = 1288323264
OWNER_PROFILE_COMMANDS_ARTIFACT = "OWNER_PROFILE_COMMANDS.fa.txt"
OWNER_RESULT_ARTIFACT = "OWNER_RESULT.fa.txt"
OWNER_CARD_ARTIFACT = "OWNER_DECISION_CARD.fa.md"
TECHNICAL_HANDOFF_ARTIFACT = "TECHNICAL_HANDOFF.en.md"
PROFILE_COMMANDS_BYTES = (
    "برای بررسی حفاظت‌های Merge، تأییدهای مستقل و کنترل‌های حاکمیتی بنویس: سخت گیرانه\n"
    "برای بررسی حداقلی بنویس: حداقلی و سپس آدرس PR را ارسال کن.\n"
).encode("utf-8")
GOVERNANCE_FRESHNESS = timedelta(minutes=15)
OWNER_MESSAGE_REGISTRY = {
    "technical_green": ("🟢 وضعیت: از نظر فنی آماده", "آمادگی فنی تأیید شده؛ حفاظت ادغام در GitHub جداگانه بررسی شود."),
    "technical_yellow_repair": ("🟡 وضعیت: نیازمند اقدام", "پرامپت اقدام فنی آماده است؛ پس از اصلاح، بازبینی تازه لازم است."),
    "technical_red_repair": ("🔴 وضعیت: آماده ادغام نیست", "پرامپت اصلاح فنی آماده است؛ تا رفع موارد بحرانی ادغام نکنید."),
}

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
    "repository_settings_not_verified": "NOT_VERIFIABLE", "merge_authorization_unverified": "GAP_FOUND",
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
_TARGET_TOKEN = object()
_SURFACE_TOKEN = object()


@dataclass(frozen=True)
class CandidateVerifiedInspectorCommit:
    _token: object
    repository: str
    repository_id: int
    commit_sha: str
    repository_receipt_id: str
    commit_receipt_id: str


@dataclass(frozen=True)
class VerifiedTargetIdentity:
    _token: object
    repository: str
    repository_id: int


@dataclass(frozen=True)
class VerifiedReviewSurfaceInventory:
    _token: object
    target_repository: str
    target_repository_id: int
    pull_request: int
    reviewed_head_sha: str
    sources: tuple[Mapping[str, Any], ...]
    complete: bool


@dataclass(frozen=True)
class CandidateGovernanceEvidence:
    _token: object
    evidence: VerifiedGovernanceEvidence
    target_identity: VerifiedTargetIdentity


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
    raise ValueError("sealed GitHub API response receipts are required; caller-authored mappings cannot mint candidate inspector provenance")


def verify_candidate_inspector_commit_responses(repository_response: GitHubApiResponse, commit_response: GitHubApiResponse, *, expected_commit_sha: str) -> CandidateVerifiedInspectorCommit:
    if not is_verified_github_api_response(repository_response) or not is_verified_github_api_response(commit_response):
        raise ValueError("sealed GitHub API response receipts are required for inspector provenance")
    repo_url = f"https://api.github.com/repos/{LOCKED_INSPECTOR_REPOSITORY}"
    commit_url = f"{repo_url}/commits/{expected_commit_sha}"
    if repository_response.request_url != repo_url or repository_response.response_url != repo_url or repository_response.status_code != 200:
        raise ValueError("inspector repository response is not authoritative")
    if commit_response.request_url != commit_url or commit_response.response_url != commit_url or commit_response.status_code != 200:
        raise ValueError("inspector commit response is not authoritative")
    repo_payload = github_response_payload(repository_response)
    commit_payload = github_response_payload(commit_response)
    if not isinstance(repo_payload, Mapping) or repo_payload.get("full_name") != LOCKED_INSPECTOR_REPOSITORY or repo_payload.get("id") != LOCKED_INSPECTOR_REPOSITORY_ID:
        raise ValueError("inspector repository identity mismatch")
    if repo_payload.get("url") != repo_url or repo_payload.get("html_url") != f"https://github.com/{LOCKED_INSPECTOR_REPOSITORY}":
        raise ValueError("inspector repository canonical URL mismatch")
    if not isinstance(commit_payload, Mapping) or commit_payload.get("sha") != expected_commit_sha:
        raise ValueError("inspector commit SHA mismatch")
    if commit_payload.get("url") != commit_url or commit_payload.get("html_url") != f"https://github.com/{LOCKED_INSPECTOR_REPOSITORY}/commit/{expected_commit_sha}":
        raise ValueError("inspector commit canonical URL mismatch")
    return CandidateVerifiedInspectorCommit(_COMMIT_TOKEN, LOCKED_INSPECTOR_REPOSITORY, LOCKED_INSPECTOR_REPOSITORY_ID, expected_commit_sha, repository_response.receipt_id, commit_response.receipt_id)


def _verified_commit(value: object) -> CandidateVerifiedInspectorCommit:
    if not isinstance(value, CandidateVerifiedInspectorCommit) or value._token is not _COMMIT_TOKEN:
        raise ValueError("candidate inspector commit receipt capability is required")
    if value.repository != LOCKED_INSPECTOR_REPOSITORY or value.repository_id != LOCKED_INSPECTOR_REPOSITORY_ID:
        raise ValueError("verified inspector commit repository identity mismatch")
    if not value.repository_receipt_id or not value.commit_receipt_id:
        raise ValueError("inspector commit receipt identity is missing")
    return value


def verify_governance_payload_bundle(payload: Mapping[str, Any], *, target_repository: str, target_repository_id: int, pull_request: int, reviewed_head_sha: str, now: datetime) -> VerifiedGovernanceCapability:
    raise ValueError("sealed active GitHub governance evidence is required; caller-authored payloads cannot mint candidate governance capability")


def bind_candidate_governance_evidence(evidence: VerifiedGovernanceEvidence, target_identity: VerifiedTargetIdentity) -> CandidateGovernanceEvidence:
    if not is_verified_governance_evidence(evidence):
        raise ValueError("sealed active governance evidence is required")
    if not isinstance(target_identity, VerifiedTargetIdentity) or target_identity._token is not _TARGET_TOKEN:
        raise ValueError("sealed target identity is required")
    if evidence.repository != target_identity.repository:
        raise ValueError("governance evidence repository mismatch")
    return CandidateGovernanceEvidence(_CAPABILITY_TOKEN, evidence, target_identity)


def _fresh_response(response: GitHubApiResponse) -> None:
    observed = datetime.fromisoformat(response.fetched_at.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    if observed > now + timedelta(seconds=30) or now - observed > GOVERNANCE_FRESHNESS:
        raise ValueError("GitHub response receipt is not fresh")


def verify_target_identity_response(response: GitHubApiResponse, *, expected_repository: str) -> VerifiedTargetIdentity:
    if not is_verified_github_api_response(response):
        raise ValueError("sealed GitHub repository response is required for target identity")
    _fresh_response(response)
    expected_url = f"https://api.github.com/repos/{expected_repository}"
    if response.request_url != expected_url or response.response_url != expected_url or response.status_code != 200:
        raise ValueError("target repository response URL/status is not authoritative")
    payload = github_response_payload(response)
    if not isinstance(payload, Mapping) or payload.get("full_name") != expected_repository:
        raise ValueError("target repository response identity mismatch")
    if payload.get("url") != expected_url or payload.get("html_url") != f"https://github.com/{expected_repository}":
        raise ValueError("target repository canonical URL mismatch")
    repository_id = payload.get("id")
    if not isinstance(repository_id, int) or repository_id <= 0:
        raise ValueError("target repository id is missing or invalid")
    return VerifiedTargetIdentity(_TARGET_TOKEN, expected_repository, repository_id)


def verify_review_surface_inventory_responses(responses: Mapping[str, GitHubApiResponse], *, target_repository: str, target_identity: VerifiedTargetIdentity, pull_request: int, reviewed_head_sha: str) -> VerifiedReviewSurfaceInventory:
    if not isinstance(target_identity, VerifiedTargetIdentity) or target_identity._token is not _TARGET_TOKEN or target_identity.repository != target_repository:
        raise ValueError("sealed target identity is required for review surface inventory")
    required = {"review_comments", "review_threads", "reviews", "issue_comments", "check_runs", "check_annotations", "check_summaries"}
    missing = required - set(responses)
    if missing:
        raise ValueError("review surface inventory endpoints are incomplete")
    base = f"https://api.github.com/repos/{target_repository}"
    expected_urls = {
        "review_comments": f"{base}/pulls/{pull_request}/comments?per_page=100",
        "review_threads": f"{base}/pulls/{pull_request}/threads?per_page=100",
        "reviews": f"{base}/pulls/{pull_request}/reviews?per_page=100",
        "issue_comments": f"{base}/issues/{pull_request}/comments?per_page=100",
        "check_runs": f"{base}/commits/{reviewed_head_sha}/check-runs?per_page=100",
        "check_annotations": f"{base}/commits/{reviewed_head_sha}/check-runs/annotations?per_page=100",
        "check_summaries": f"{base}/commits/{reviewed_head_sha}/status",
    }
    sources: list[Mapping[str, Any]] = []
    github_source_keys: set[str] = set()
    for key, expected_url in expected_urls.items():
        response = responses[key]
        if not is_verified_github_api_response(response):
            raise ValueError("review surface response is not sealed GitHub evidence")
        _fresh_response(response)
        if response.request_url != expected_url or response.response_url != expected_url:
            raise ValueError("review surface response URL does not match target")
        if response.status_code != 200:
            raise ValueError("review surface endpoint is inaccessible")
        payload = github_response_payload(response)
        if key == "check_runs":
            payload_items = payload.get("check_runs") if isinstance(payload, Mapping) else None
        elif key == "check_summaries":
            payload_items = payload.get("statuses", []) if isinstance(payload, Mapping) else None
        else:
            payload_items = payload
        if isinstance(payload, Mapping) and payload.get("incomplete_pagination") is True:
            raise ValueError("review surface pagination is incomplete")
        if not isinstance(payload_items, list):
            raise ValueError("review surface payload is malformed")
        if len(payload_items) >= 100:
            raise ValueError("review surface pagination is incomplete")
        for index, item in enumerate(payload_items):
            if not isinstance(item, Mapping):
                raise ValueError("review surface item is malformed")
            author = item.get("user") or item.get("app") or {}
            login = author.get("login") or author.get("slug") if isinstance(author, Mapping) else None
            actor_type = author.get("type") if isinstance(author, Mapping) else None
            is_bot = actor_type in {"Bot", "App"} or bool(item.get("app"))
            if is_bot:
                stable_id = item.get("node_id") or item.get("id")
                if stable_id is None:
                    raise ValueError("review surface source identity is missing")
                source_type = {"review_comments": "github_pr_review_comment", "review_threads": "github_inline_review_thread", "issue_comments": "github_issue_comment", "check_annotations": "github_check_annotation", "check_summaries": "github_check_summary"}.get(key, "github_bot_comment")
                github_key = f"{key}:{stable_id}"
                if github_key in github_source_keys:
                    raise ValueError("duplicate review surface source identity")
                github_source_keys.add(github_key)
                sources.append(MappingProxyType({"source_id": f"EXTSRC-{len(sources)+1:03d}", "github_source_key": github_key, "inspected": False, "source_type": source_type, "author": login, "is_bot": True, "url": item.get("html_url") or item.get("target_url"), "head_sha": reviewed_head_sha, "content_sha256": bytes_sha256(json.dumps(item, sort_keys=True, separators=(",", ":")).encode())}))
    return VerifiedReviewSurfaceInventory(_SURFACE_TOKEN, target_repository, target_identity.repository_id, pull_request, reviewed_head_sha, tuple(sources), True)


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
        if target and live_head and isinstance(target.get("repository_id"), int) and target.get("repository_id") > 0 and verify_base_review_reference(evidence, live_head, target_repository=target.get("repository"), target_repository_id=target.get("repository_id"), pull_request=target.get("pull_request")).get("status") == "VERIFIED":
            return {"inspection_profile": STRICT, "target": target, "reuse_current_minimal": True, "missing": []}
    if url is None:
        return {"inspection_profile": profile, "target": None, "reuse_current_minimal": False, "missing": ["pull_request_url"]}
    match = PR_URL_RE.match(url)
    return {"inspection_profile": profile, "target": {"repository": match.group(1), "pull_request": int(match.group(2)), "url": url}, "reuse_current_minimal": False, "missing": []}


def classify_governance(evidence: object, *, target_repository: str | None = None, target_repository_id: int | None = None, pull_request: int | None = None, reviewed_head_sha: str | None = None) -> dict[str, Any]:
    if not (target_repository and isinstance(target_repository_id, int) and pull_request and reviewed_head_sha):
        return {"status": "NOT_VERIFIABLE", "reason_codes": ["repository_settings_not_verified"]}
    if isinstance(evidence, CandidateGovernanceEvidence) and evidence._token is _CAPABILITY_TOKEN:
        sealed = evidence.evidence
        if evidence.target_identity.repository != target_repository or evidence.target_identity.repository_id != target_repository_id or sealed.repository != target_repository or sealed.pull_request_number != pull_request or sealed.exact_head_sha != reviewed_head_sha:
            return {"status": "NOT_VERIFIABLE", "reason_codes": ["repository_settings_not_verified"]}
        if sealed.merge_authorized:
            return {"status": "VERIFIED", "reason_codes": []}
        return {"status": "GAP_FOUND", "reason_codes": ["merge_authorization_unverified"]}
    if not is_verified_governance_capability(evidence):
        return {"status": "NOT_VERIFIABLE", "reason_codes": ["repository_settings_not_verified"]}
    if evidence.target_repository != target_repository or evidence.target_repository_id != target_repository_id or evidence.pull_request != pull_request or evidence.reviewed_head_sha != reviewed_head_sha:
        return {"status": "NOT_VERIFIABLE", "reason_codes": ["repository_settings_not_verified"]}
    gap_codes = sorted({GOVERNANCE_GAP_FIELDS[field] for field in REQUIRED_GOVERNANCE_FACTS if evidence.facts[field] is False})
    return {"status": "GAP_FOUND", "reason_codes": gap_codes} if gap_codes else {"status": "VERIFIED", "reason_codes": []}


def project_decision(inspection_profile: str, technical_reason_codes: list[str] | None = None, governance_evidence: object | None = None, *, target_repository: str | None = None, target_repository_id: int | None = None, pull_request: int | None = None, reviewed_head_sha: str | None = None) -> dict[str, Any]:
    technical_reason_codes = _validate_reason_codes(technical_reason_codes or [], "technical")
    tech_status = _technical_status_from_reasons(technical_reason_codes)
    if inspection_profile == MINIMAL: governance = {"status": "NOT_REQUESTED", "reason_codes": []}
    elif inspection_profile == STRICT: governance = classify_governance(governance_evidence, target_repository=target_repository, target_repository_id=target_repository_id, pull_request=pull_request, reviewed_head_sha=reviewed_head_sha)
    else: raise ValueError("unknown inspection_profile")
    governance["reason_codes"] = _validate_reason_codes(governance["reason_codes"], "governance")
    if governance["reason_codes"] and governance["status"] != _governance_status_from_reasons(governance["reason_codes"]):
        raise ValueError("governance status disagrees with registered reason effects")
    owner_key = "technical_green" if tech_status == "GREEN" else ("technical_red_repair" if tech_status == "RED" else "technical_yellow_repair")
    prompt_required = tech_status != "GREEN"
    next_action_kind = "owner_confirmation" if tech_status == "GREEN" else "repair"
    owner_color = "GREEN" if tech_status == "GREEN" else ("RED" if tech_status == "RED" else "YELLOW")
    return {"schema_version": 1, "protocol_version": PROTOCOL_VERSION, "inspection_profile": inspection_profile, "technical_decision": {"status": tech_status, "reason_codes": technical_reason_codes}, "governance_decision": governance, "overall_recommendation": {"technical_ready": tech_status == "GREEN", "merge_governance_verified": governance["status"] == "VERIFIED"}, "owner_readiness": {"color": owner_color, "action_kind": next_action_kind, "message_key": owner_key, "reason_codes": []}, "next_action": {"kind": next_action_kind, "recipient": "project_owner" if tech_status == "GREEN" else "implementer_model", "may_modify_code": prompt_required, "prompt_required": prompt_required, "prompt_kind": None if not prompt_required else "implementer_repair_prompt", "reason_codes": []}, "approval_requirement": "NO_ADDITIONAL_TECHNICAL_APPROVAL" if tech_status == "GREEN" else "HUMAN_TECHNICAL_REVIEW_REQUIRED", "security_profile": {"name": "personal_ai_operated_strong_governance_minimum_security", "security_level": "minimum_security", "sequence_ci_enforced": False, "repository_hosted_requirement": "required", "repository_hosted_enforcement": "not_verified", "github_app_exact_source_enforcement": "required", "repository_settings_enforced": "not_claimed", "merge_authorized": "not_claimed", "governance_evidence_status": "not_provided", "governance_evidence_id": None, "blocks_green_merge_recommendation": False, "reason_codes": [], "controls": []}, "governance_follow_up": {"kind": "none" if governance["status"] in {"NOT_REQUESTED", "VERIFIED"} else ("access_limitation" if governance["status"] == "NOT_VERIFIABLE" else "informational_gap"), "may_modify_code": False, "prompt_required": False}}


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


def recompute_external_review_reconciliation(package: Mapping[str, Any], review_surface_inventory: object | None = None) -> dict[str, Any]:
    intake = package.get("external_review_intake") or {}
    sources = intake.get("sources_inspected", [])
    if isinstance(review_surface_inventory, VerifiedReviewSurfaceInventory) and review_surface_inventory._token is _SURFACE_TOKEN:
        identity = package.get("review_identity", {})
        if review_surface_inventory.target_repository != identity.get("target_repository") or review_surface_inventory.pull_request != identity.get("pr_number") or review_surface_inventory.reviewed_head_sha != identity.get("reviewed_head_sha"):
            raise ValueError("review surface inventory target mismatch")
        if not review_surface_inventory.complete:
            raise ValueError("review surface inventory is incomplete")
        inventory_by_id = {source["source_id"]: source for source in review_surface_inventory.sources}
        package_by_id = {source.get("source_id"): source for source in sources if isinstance(source, Mapping)}
        if set(inventory_by_id) != set(package_by_id):
            raise ValueError("external_review_intake disagrees with sealed review surface inventory")
        for source_id, inventory_source in inventory_by_id.items():
            package_source = package_by_id[source_id]
            for field in ("source_type", "author", "is_bot", "url"):
                if package_source.get(field) != inventory_source.get(field):
                    raise ValueError("external_review_intake source identity mismatch")
            if package_source.get("inspected") is not True:
                raise ValueError("external_review_intake source requires explicit inspected disposition")
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
    reviewed_head = identity.get("reviewed_head_sha")
    evidence_records = [e for e in (package.get("evidence") or package.get("evidence_records") or []) if isinstance(e, Mapping)]
    evidence_ids = [e.get("evidence_id") for e in evidence_records]
    if len(evidence_ids) != len(set(evidence_ids)): reasons.add("incomplete_technical_scope")
    evidence_by_id = {e.get("evidence_id"): e for e in evidence_records}
    if package.get("red_gate_flags"):
        reasons.add("required_technical_check_failed")
    for check in package.get("checks", []):
        if not isinstance(check, Mapping):
            continue
        if check.get("required") is True and check.get("result") == "FAIL": reasons.add("required_technical_check_failed")
        elif check.get("required") is True and check.get("result") in {"UNKNOWN", "NOT_RUN", None}: reasons.add("incomplete_technical_scope")
        if check.get("required") is True and check.get("result") == "PASS":
            evidence_id = check.get("evidence_ref") or check.get("evidence_id")
            evidence = evidence_by_id.get(evidence_id)
            if check.get("state") not in {"EXECUTED", "CI_INSPECTED"} or evidence is None:
                reasons.add("incomplete_technical_scope")
            elif evidence.get("reviewed_head_sha") not in {None, reviewed_head}:
                reasons.add("stale_technical_review_identity")
            elif evidence.get("result") != "PASS" or evidence.get("evidence_type") not in {"CI", "EXECUTION"}:
                reasons.add("incomplete_technical_scope")
    actual_blocking = 0
    for finding in package.get("findings", []):
        if not isinstance(finding, Mapping): continue
        severity = finding.get("severity"); evidence = finding.get("evidence_label")
        refs = finding.get("evidence_refs", [])
        if refs and any(ref not in evidence_by_id for ref in refs): reasons.add("incomplete_technical_scope")
        if any(isinstance(evidence_by_id.get(ref), Mapping) and evidence_by_id[ref].get("reviewed_head_sha") not in {None, reviewed_head} for ref in refs): reasons.add("stale_technical_review_identity")
        if evidence == "REPRODUCED" and not any(isinstance(evidence_by_id.get(ref), Mapping) and evidence_by_id[ref].get("evidence_type") in {"EXECUTION", "CI"} and evidence_by_id[ref].get("result") == "FAIL" for ref in refs): reasons.add("incomplete_technical_scope")
        if evidence == "CODE_SUPPORTED" and not any(isinstance(evidence_by_id.get(ref), Mapping) and evidence_by_id[ref].get("evidence_type") == "CODE" for ref in refs): reasons.add("incomplete_technical_scope")
        if severity == "CRITICAL" and evidence in {"REPRODUCED", "CODE_SUPPORTED"}: reasons.add("critical_supported_finding")
        elif severity == "HIGH" and evidence == "REPRODUCED": reasons.add("high_reproduced_finding")
        elif severity == "HIGH" and evidence == "CODE_SUPPORTED": reasons.add("blocking_medium_finding")
        elif severity in {"CRITICAL", "HIGH"} and evidence in {"HYPOTHESIS", "NOT_ASSESSABLE"}: reasons.add("incomplete_technical_scope")
        elif severity == "MEDIUM" and finding.get("blocking") is True: reasons.add("blocking_medium_finding")
        if finding.get("blocking") is True: actual_blocking += 1
    declared_blocking = package.get("decision", {}).get("blocking_findings_count") if isinstance(package.get("decision"), Mapping) else None
    if isinstance(declared_blocking, int) and declared_blocking != actual_blocking: reasons.add("incomplete_technical_scope")
    if package.get("repair_handoff", {}).get("affected_findings"):
        reasons.add("incomplete_technical_scope")
    return sorted(reasons)


def _schema_validator(name: str) -> Draft202012Validator:
    schema = json.loads((ROOT / f"protocols/{PROTOCOL_VERSION}/schemas/{name}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def validate_candidate_package(package: Mapping[str, Any], governance_evidence: object | None = None, *, review_surface_inventory: object | None = None, target_repository_id: int | None = None) -> list[str]:
    errors = [error.message for error in _schema_validator("review-package").iter_errors(package)]
    if errors: return sorted(errors)
    if not isinstance(review_surface_inventory, VerifiedReviewSurfaceInventory) or review_surface_inventory._token is not _SURFACE_TOKEN:
        errors.append("sealed review surface inventory is required for candidate technical Green eligibility")
    if package.get("external_review_intake") is None:
        errors.append("external_review_intake is required for candidate technical Green eligibility")
    else:
        try:
            recomputed = recompute_external_review_reconciliation(package, review_surface_inventory)
            if package["external_review_reconciliation"] != recomputed: errors.append("external_review_reconciliation disagrees with recomputed bot review evidence")
        except ValueError as exc:
            errors.append(str(exc))
    technical_reasons = collect_candidate_technical_reasons(package)
    identity = package.get("review_identity", {}) if isinstance(package.get("review_identity"), Mapping) else {}
    effective_repository_id = target_repository_id if target_repository_id is not None else identity.get("target_repository_id")
    try: derived = project_decision(package.get("inspection_profile"), technical_reasons, governance_evidence, target_repository=identity.get("target_repository"), target_repository_id=effective_repository_id, pull_request=identity.get("pr_number"), reviewed_head_sha=identity.get("reviewed_head_sha"))
    except ValueError as exc: return [str(exc)]
    for key in ["technical_decision", "governance_decision", "overall_recommendation"]:
        if package.get(key) != derived[key]: errors.append(f"{key} disagrees with authoritative candidate projection")
    legacy_status = package.get("decision", {}).get("technical_status") if isinstance(package.get("decision"), Mapping) else None
    if legacy_status == "GREEN_TECHNICALLY_READY" and derived["technical_decision"]["status"] != "GREEN": errors.append("legacy technical_status GREEN conflicts with derived candidate status")
    if legacy_status == "RED_DO_NOT_MERGE" and derived["technical_decision"]["status"] != "RED": errors.append("legacy technical_status RED conflicts with derived candidate status")
    if legacy_status == "YELLOW_CHANGES_OR_VERIFICATION_REQUIRED" and derived["technical_decision"]["status"] != "YELLOW": errors.append("legacy technical_status YELLOW conflicts with derived candidate status")
    return sorted(set(errors))


def render_candidate_owner_result(projection: Mapping[str, Any]) -> bytes:
    message_key = projection["owner_readiness"]["message_key"]
    first, second = OWNER_MESSAGE_REGISTRY[message_key]
    return f"{first}\n{second}\n".encode("utf-8")


def render_candidate_owner_card(package: Mapping[str, Any], projection: Mapping[str, Any]) -> bytes:
    return ("# Candidate owner decision card\n" f"technical_status: {projection['technical_decision']['status']}\n" f"governance_status: {projection['governance_decision']['status']}\n").encode("utf-8")


def render_candidate_technical_handoff(package: Mapping[str, Any], projection: Mapping[str, Any]) -> bytes:
    return ("# Candidate technical handoff\n" f"technical_reason_codes: {','.join(projection['technical_decision']['reason_codes'])}\n").encode("utf-8")


def render_candidate_next_action_prompt(projection: Mapping[str, Any]) -> bytes | None:
    if not projection["next_action"]["prompt_required"]:
        return None
    return b"Repair independently validated technical findings before rereview.\n"


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"


def build_candidate_review_artifacts(package: Mapping[str, Any], *, governance_evidence: object | None = None, review_surface_inventory: object | None = None, target_repository_id: int | None = None) -> Mapping[str, bytes]:
    errors = validate_candidate_package(package, governance_evidence, review_surface_inventory=review_surface_inventory, target_repository_id=target_repository_id)
    if errors:
        raise ValueError("candidate package is semantically invalid: " + "; ".join(errors))
    reasons = collect_candidate_technical_reasons(package)
    identity = package["review_identity"]
    projection = project_decision(package["inspection_profile"], reasons, governance_evidence, target_repository=identity["target_repository"], target_repository_id=identity["target_repository_id"], pull_request=identity["pr_number"], reviewed_head_sha=identity["reviewed_head_sha"])
    artifacts: dict[str, bytes] = {
        "review-package.json": canonical_json_bytes(package),
        "DECISION_PROJECTION.json": canonical_json_bytes(projection),
        OWNER_CARD_ARTIFACT: render_candidate_owner_card(package, projection),
        TECHNICAL_HANDOFF_ARTIFACT: render_candidate_technical_handoff(package, projection),
        OWNER_RESULT_ARTIFACT: render_candidate_owner_result(projection),
        OWNER_PROFILE_COMMANDS_ARTIFACT: PROFILE_COMMANDS_BYTES,
    }
    prompt = render_candidate_next_action_prompt(projection)
    if prompt is not None:
        artifacts["NEXT_ACTION_PROMPT.en.md"] = prompt
    manifest = {"schema_version": 2, "artifacts": [{"path": name, "sha256": bytes_sha256(raw)} for name, raw in sorted(artifacts.items())], "review_package_canonical_sha256": canonical_sha256(package), "review_package_file_sha256": bytes_sha256(artifacts["review-package.json"])}
    artifacts["artifact-manifest.json"] = canonical_json_bytes(manifest)
    return MappingProxyType(artifacts)

REQUIRED_REF = {"target_repository", "target_repository_id", "pull_request", "reviewed_head_sha", "inspector_repository", "inspector_commit_sha", "review_package_sha256", "decision_projection_sha256", "artifact_manifest_sha256"}
BASE_REQUIRED_ARTIFACTS = {"review-package.json", "DECISION_PROJECTION.json", "OWNER_DECISION_CARD.fa.md", "TECHNICAL_HANDOFF.en.md", "OWNER_RESULT.fa.txt", "artifact-manifest.json", OWNER_PROFILE_COMMANDS_ARTIFACT}


def verify_minimal_review_artifact_bytes(artifact_bytes: Mapping[str, bytes], inspector_commit: VerifiedInspectorCommit, *, review_surface_inventory: object | None = None) -> VerifiedMinimalReviewBundle:
    commit = _verified_commit(inspector_commit)
    snapshot = MappingProxyType({name: bytes(raw) for name, raw in artifact_bytes.items()})
    package = _json_object("review-package.json", snapshot["review-package.json"])
    projection = _json_object("DECISION_PROJECTION.json", snapshot["DECISION_PROJECTION.json"])
    manifest = _json_object("artifact-manifest.json", snapshot["artifact-manifest.json"])
    if manifest.get("schema_version") != 2: raise ValueError("artifact manifest schema_version must be 2")
    if package.get("inspection_profile") != MINIMAL or projection.get("inspection_profile") != MINIMAL: raise ValueError("base review is not minimal")
    identity = package.get("review_identity", {})
    if identity.get("review_validity") != "CURRENT": raise ValueError("base review validity is not CURRENT")
    if identity.get("inspector_repository") != commit.repository or identity.get("inspector_commit_sha") != commit.commit_sha: raise ValueError("base review inspector identity mismatch")
    errors = validate_candidate_package(package, review_surface_inventory=review_surface_inventory)
    if errors: raise ValueError("candidate package is semantically invalid: " + "; ".join(errors))
    _schema_validator("decision-projection").validate(projection)
    derived = project_decision(MINIMAL, collect_candidate_technical_reasons(package))
    if projection != derived: raise ValueError("projection does not match authoritative candidate projection")
    expected = build_candidate_review_artifacts(package, review_surface_inventory=review_surface_inventory)
    if set(snapshot) != set(expected): raise ValueError("artifact set contains missing or unexpected artifacts")
    for name, raw in expected.items():
        if snapshot.get(name) != raw: raise ValueError(f"{name} bytes are not canonical")
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
    if not set(expected).issubset(set(snapshot)): raise ValueError("artifact set is incomplete")
    for name in set(expected) - {"artifact-manifest.json"}:
        if manifest_hashes.get(name) != bytes_sha256(snapshot[name]): raise ValueError("artifact manifest mismatch")
    reference = {"target_repository": package["review_identity"]["target_repository"], "target_repository_id": package["review_identity"].get("target_repository_id"), "pull_request": package["review_identity"].get("pr_number"), "reviewed_head_sha": package["review_identity"]["reviewed_head_sha"], "inspector_repository": commit.repository, "inspector_commit_sha": commit.commit_sha, "review_package_sha256": canonical_sha256(package), "decision_projection_sha256": bytes_sha256(snapshot["DECISION_PROJECTION.json"]), "artifact_manifest_sha256": bytes_sha256(snapshot["artifact-manifest.json"])}
    return VerifiedMinimalReviewBundle(_REVIEW_TOKEN, MappingProxyType(reference), snapshot, bytes_sha256(snapshot["review-package.json"]), commit)


def verify_base_review_reference(evidence: object, live_head_sha: str, *, target_repository: str | None = None, target_repository_id: int | None = None, pull_request: int | None = None) -> dict[str, Any]:
    if not is_verified_minimal_review_bundle(evidence): return {"status": "INVALID", "reason": "verified_minimal_review_required"}
    reference = evidence.reference
    if REQUIRED_REF - set(reference): return {"status": "INVALID", "reason": "missing_fields"}
    if evidence.inspector_commit.repository != LOCKED_INSPECTOR_REPOSITORY or evidence.inspector_commit.repository_id != LOCKED_INSPECTOR_REPOSITORY_ID: return {"status": "INVALID", "reason": "inspector_identity_mismatch"}
    if target_repository is not None and reference["target_repository"] != target_repository: return {"status": "INVALID", "reason": "target_repository_mismatch"}
    if not isinstance(target_repository_id, int) or target_repository_id <= 0: return {"status": "INVALID", "reason": "target_repository_id_required"}
    if reference.get("target_repository_id") != target_repository_id: return {"status": "INVALID", "reason": "target_repository_id_mismatch"}
    if pull_request is not None and reference["pull_request"] != pull_request: return {"status": "INVALID", "reason": "pull_request_mismatch"}
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


def build_candidate_owner_delivery_artifacts(bundle: VerifiedMinimalReviewBundle) -> Mapping[str, bytes]:
    if not is_verified_minimal_review_bundle(bundle):
        raise ValueError("verified candidate bundle is required for owner delivery")
    return bundle.artifact_bytes


def candidate_owner_delivery_stdout(bundle: object) -> bytes:
    try:
        if not is_verified_minimal_review_bundle(bundle):
            return b""
        artifacts = bundle.artifact_bytes
        projection = _json_object("DECISION_PROJECTION.json", artifacts["DECISION_PROJECTION.json"])
        raw_owner = artifacts[OWNER_RESULT_ARTIFACT]
        if raw_owner != render_candidate_owner_result(projection):
            return b""
        if validate_owner_profile_commands(artifacts.get(OWNER_PROFILE_COMMANDS_ARTIFACT, b"")):
            return b""
        prompt = render_candidate_next_action_prompt(projection)
        if prompt is None:
            if "NEXT_ACTION_PROMPT.en.md" in artifacts:
                return b""
            return raw_owner + artifacts[OWNER_PROFILE_COMMANDS_ARTIFACT]
        if artifacts.get("NEXT_ACTION_PROMPT.en.md") != prompt:
            return b""
        return raw_owner + "\n## پرامپت اقدام\n\n".encode("utf-8") + prompt + artifacts[OWNER_PROFILE_COMMANDS_ARTIFACT]
    except Exception:
        return b""
