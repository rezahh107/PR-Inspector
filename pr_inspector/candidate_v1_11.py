"""Compatibility-only v1.11 intake and evidence helpers.

After a canonical review package exists, callers must use the official projection,
artifact, verification, completion, and owner-delivery APIs.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable

from ._governance_transport import (
    GitHubApiResponse,
    VerifiedGitHubGovernanceSource,
    github_response_payload,
    is_verified_github_api_response,
)
from ._official_bundle import VerifiedReviewCompletion, is_verified_review_completion
from .derived_outputs import (
    PROFILE_COMMANDS_NAME,
    PROFILE_COMMANDS_TEXT,
    render_owner_profile_commands as _official_profile_commands,
)
from .governance import (
    VerifiedGovernanceEvidence,
    is_verified_governance_evidence,
    is_verified_github_governance_source,
)
from .validation_v2 import validate_package as _official_validate_package

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
PR_URL_RE = re.compile(r"https://github\.com/([^/\s]+/[^/\s]+)/pull/(\d+)")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
MINIMAL, STRICT = "minimal", "strict"
LOCKED_INSPECTOR_REPOSITORY = "rezahh107/PR-Inspector"
LOCKED_INSPECTOR_REPOSITORY_ID = 1288323264
OWNER_PROFILE_COMMANDS_ARTIFACT = PROFILE_COMMANDS_NAME
PROFILE_COMMANDS_BYTES = PROFILE_COMMANDS_TEXT.encode("utf-8")
GOVERNANCE_FRESHNESS = timedelta(minutes=15)
TECHNICAL_REASON_CODES = {
    "required_technical_check_failed", "critical_supported_finding",
    "high_reproduced_finding", "blocking_medium_finding",
    "incomplete_technical_scope", "unresolved_valid_bot_finding",
    "stale_technical_review_identity", "bot_collection_incomplete",
}
GOVERNANCE_REASON_CODES = {
    "repository_settings_not_verified", "branch_protection_unavailable",
    "bypass_actors_unknown", "sequence_enforcement_missing",
    "required_review_enforcement_absent", "merge_authorization_unverified",
    "required_checks_not_verified", "rulesets_unavailable",
    "merge_queue_unavailable",
}
GOVERNANCE_STATUS_EFFECT = {
    code: ("NOT_VERIFIABLE" if code == "repository_settings_not_verified" else "GAP_FOUND")
    for code in GOVERNANCE_REASON_CODES
}
TRIAGE_TO_RECONCILIATION = {
    "accepted": "accepted", "resolved": "resolved", "stale": "stale",
    "false_positive": "false_positive", "duplicate": "duplicate",
    "insufficient_evidence": "insufficient_evidence", "deferred": "deferred",
    "out_of_scope": "out_of_scope", "rejected": "false_positive",
}
_CAPABILITY_TOKEN, _COMMIT_TOKEN, _TARGET_TOKEN = object(), object(), object()
_SURFACE_TOKEN, _REFRESH_TOKEN, _REFERENCE_TOKEN = object(), object(), object()


class CandidateOutputMigrationError(RuntimeError):
    """A removed Candidate output authority was invoked."""


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
class VerifiedLivePrHead:
    _token: object
    repository: str
    repository_id: int
    pull_request: int
    head_sha: str
    receipt_id: str


@dataclass(frozen=True)
class CheckAnnotationCollection:
    items: tuple[Mapping[str, Any], ...]
    pagination_complete: bool
    pages_fetched: int
    check_runs_fetched: int
    annotation_pages_fetched: int


@dataclass(frozen=True)
class CandidateGovernanceEvidence:
    _token: object
    evidence: VerifiedGovernanceEvidence
    governance_source: VerifiedGitHubGovernanceSource
    target_identity: VerifiedTargetIdentity


@dataclass(frozen=True)
class VerifiedMinimalReviewReference:
    _token: object
    completion: VerifiedReviewCompletion
    target_repository_id: int
    inspector_commit: CandidateVerifiedInspectorCommit


@dataclass(frozen=True)
class MinimalRefreshResult:
    _token: object
    state: str
    target: Mapping[str, Any]
    live_head_sha: str
    bundle: VerifiedMinimalReviewReference | None
    reason: str | None = None


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fresh(response: GitHubApiResponse) -> None:
    observed = datetime.fromisoformat(response.fetched_at.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    if observed > now + timedelta(seconds=30) or now - observed > GOVERNANCE_FRESHNESS:
        raise ValueError("GitHub response receipt is not fresh")


def _operational(response: GitHubApiResponse, label: str) -> None:
    if not is_verified_github_api_response(response):
        raise ValueError(f"{label} is not a sealed GitHub API response receipt")
    if getattr(response, "transport_origin", None) != "github_https":
        raise ValueError(f"{label} was not produced by the operational GitHub HTTPS adapter")
    _fresh(response)


def verify_candidate_inspector_commit_payload(*args: Any, **kwargs: Any) -> None:
    raise ValueError("sealed GitHub API response receipts are required; caller mappings cannot mint inspector provenance")


def verify_candidate_inspector_commit_responses(
    repository_response: GitHubApiResponse,
    commit_response: GitHubApiResponse,
    *, expected_commit_sha: str,
) -> CandidateVerifiedInspectorCommit:
    _operational(repository_response, "inspector repository response")
    _operational(commit_response, "inspector commit response")
    repo_url = f"https://api.github.com/repos/{LOCKED_INSPECTOR_REPOSITORY}"
    commit_url = f"{repo_url}/commits/{expected_commit_sha}"
    if (repository_response.request_url, repository_response.response_url, repository_response.status_code) != (repo_url, repo_url, 200):
        raise ValueError("inspector repository response is not authoritative")
    if (commit_response.request_url, commit_response.response_url, commit_response.status_code) != (commit_url, commit_url, 200):
        raise ValueError("inspector commit response is not authoritative")
    repo, commit = github_response_payload(repository_response), github_response_payload(commit_response)
    if not isinstance(repo, Mapping) or repo.get("full_name") != LOCKED_INSPECTOR_REPOSITORY or repo.get("id") != LOCKED_INSPECTOR_REPOSITORY_ID:
        raise ValueError("inspector repository identity mismatch")
    if not isinstance(commit, Mapping) or commit.get("sha") != expected_commit_sha or not SHA40_RE.fullmatch(expected_commit_sha):
        raise ValueError("inspector commit SHA mismatch")
    return CandidateVerifiedInspectorCommit(
        _COMMIT_TOKEN, LOCKED_INSPECTOR_REPOSITORY, LOCKED_INSPECTOR_REPOSITORY_ID,
        expected_commit_sha, repository_response.receipt_id, commit_response.receipt_id,
    )


def _verified_commit(value: object) -> CandidateVerifiedInspectorCommit:
    if not isinstance(value, CandidateVerifiedInspectorCommit) or value._token is not _COMMIT_TOKEN:
        raise ValueError("candidate inspector commit receipt capability is required")
    return value


def verify_target_identity_response(response: GitHubApiResponse, *, expected_repository: str) -> VerifiedTargetIdentity:
    _operational(response, "target repository response")
    expected_url = f"https://api.github.com/repos/{expected_repository}"
    if (response.request_url, response.response_url, response.status_code) != (expected_url, expected_url, 200):
        raise ValueError("target repository response is not authoritative")
    payload = github_response_payload(response)
    if not isinstance(payload, Mapping) or payload.get("full_name") != expected_repository:
        raise ValueError("target repository identity mismatch")
    repository_id = payload.get("id")
    if not isinstance(repository_id, int) or isinstance(repository_id, bool) or repository_id <= 0:
        raise ValueError("target repository id is missing or invalid")
    return VerifiedTargetIdentity(_TARGET_TOKEN, expected_repository, repository_id)


def verify_live_pr_head_response(response: GitHubApiResponse, *, target_repository: str, target_repository_id: int, pull_request: int) -> VerifiedLivePrHead:
    if not target_repository or not isinstance(target_repository_id, int) or isinstance(target_repository_id, bool) or target_repository_id <= 0 or not isinstance(pull_request, int) or pull_request <= 0:
        raise ValueError("verified target is required for live PR head")
    _operational(response, "live PR head response")
    expected = f"https://api.github.com/repos/{target_repository}/pulls/{pull_request}"
    if (response.request_url, response.response_url, response.status_code) != (expected, expected, 200):
        raise ValueError("live PR head response is not authoritative")
    payload = github_response_payload(response)
    if not isinstance(payload, Mapping) or payload.get("number") != pull_request:
        raise ValueError("live PR identity mismatch")
    head = payload.get("head")
    if not isinstance(head, Mapping) or not isinstance(head.get("sha"), str) or not SHA40_RE.fullmatch(head["sha"]):
        raise ValueError("live PR head is malformed")
    base = payload.get("base")
    repo = base.get("repo") if isinstance(base, Mapping) else None
    if isinstance(repo, Mapping):
        if repo.get("full_name") not in {None, target_repository} or repo.get("id") not in {None, target_repository_id}:
            raise ValueError("live PR repository identity mismatch")
    return VerifiedLivePrHead(_TARGET_TOKEN, target_repository, target_repository_id, pull_request, head["sha"], response.receipt_id)


def _next_page(url: str) -> str | None:
    match = re.search(r"(?:[?&])page=(\d+)", url)
    if match:
        return re.sub(r"([&?]page=)\d+", lambda m: f"{m.group(1)}{int(match.group(1)) + 1}", url, count=1)
    return f"{url}{'&' if '?' in url else '?'}page=2"


def _annotation_items(responses: Mapping[str, GitHubApiResponse], *, base: str, reviewed_head_sha: str) -> CheckAnnotationCollection:
    items: list[Mapping[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    run_page, pages, runs and f"{base}/commits/{reviewed_head_sha}/check-runs?per_page=100", 0, 0
    visited: set[str] = set()
    while run_page:
        if run_page in visited or len(visited) >= 100: raise ValueError("review surface pagination is incomplete")
        visited.add(run_page)
        response = responses.get("check_runs") if run_page.endswith("?per_page=100") els`responses.get(run_page)
        if response is None: raise ValueError("review surface pagination is incomplete")
        _operational(response, "check run listing response")
        if (response.request_url, response.response_url, response.status_code) != (run_page, run_page, 200): raise ValueError("check run listing response is not authoritative")
        payload = github_response_payload(response)
        run_list = payload.get("check_runs") if isinstance(payload, Mapping) else None
        if not isinstance(run_list, list): raise ValueError("check run listing payload is malformed")
        pages += 1; runs += len(run_list)
        for run in run_list:
            if not isinstance(run, Mapping): raise ValueError("check run item is malformed")
            run_id = run.get("id")
            if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0: raise ValueError("check run identity is missing")
            if run.get("head_sha") != reviewed_head_sha: raise ValueError("check run head does not match reviewed head")
            ann_page = f"{base}/check-runs/{run_id}/annotations?per_page=100"; ann_visited: set[str] = set()
            while ann_page:
                if ann_page in ann_visited or len(ann_visited) >= 100: raise ValueError("review surface pagination is incomplete")
                ann_visited.add(ann_page)
                ann_response = responses.get(ann_page)
                if ann_response is None: raise ValueError("review surface pagination is incomplete")
                _operational(ann_response, "check annotation response")
                if (ann_response.request_url, ann_response.response_url, ann_response.status_code) != (ann_page, ann_page, 200): raise ValueError("check annotation response is not authoritative")
                annotations = github_response_payload(ann_response)
                if not isinstance(annotations, list): raise ValueError("check annotation payload is malformed")
                for ann in annotations:
                    if not isinstance(ann, Mapping): raise ValueError("check annotation item is malformed")
                    start, end = ann.get("start_line"), ann.get("end_line")
                    for name, value in (("start_line", start), ("end_line", end)):
                        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value <= 0): raise ValueError(f"check annotation {name} is malformed")
                    if start is not None and end is not None and end < start: raise ValueError("check annotation line range is malformed")
                    level = ann.get("annotation_level")
                    if not isinstance(level, str) or not level: raise ValueError("check annotation level is malformed")
                    key = (run_id, ann.get("path"), start, end, level, ann.get("message"), ann.get("raw_details"))
                    if key in seen: continue
                    seen.add(key)
                    payload_item = {
                        "check_run_id": run_id, "path": ann.get("path"), "start_line": start, "end_line": end,
                        "annotation_level": level, "message": ann.get("message"), "raw_details": ann.get("raw_details"),
                        "id": ann.get("id") or f"{run_id}:{ann.get('path')}:{start}:{end}:{level}:{ann.get('message')}",
                        "app": run.get("app") or {"slug": run.get("name"), "type": "App"},
                        "html_url": run.get("html_url") or run.get("details_url"), "target_url": ann_page,
                        "receipt_id": ann_response.receipt_id,
                    }
                    items.append(MappingProxyType(payload_item))
                ann_page = _next_page(ann_page) if len(annotations) >= 100 else None
        run_page = _next_page(run_page) if len(run_list) >= 100 else None
    return CheckAnnotationCollection(tuple(items), True, pages, runs, sum(len(1) for _ in items))


def verify_review_surface_inventory_responses(responses: Mapping[str, GitHubApiResponse], *, target_repository: str, target_identity: VerifiedTargetIdentity, pull_request: int, reviewed_head_sha: str) -> VerifiedReviewSurfaceInventory:
    if not isinstance(target_identity, VerifiedTargetIdentity) or target_identity._token is not _TARGET_TOKEN or target_identity.repository != target_repository:
        raise ValueError("sealed target identity is required")
    base = f"https://api.github.com/repos/{target_repository}"
    expected = {
        "review_comments": f"{base}/pulls/{pull_request}/comments?per_page=100",
        "review_threads": f"{base}/pulls/{pull_request}/threads?per_page=100",
        "reviews": f"{base}/pulls/{pull_request}/reviews?per_page=100",
        "issue_comments": f"{base}/issues/{pull_request}/comments?per_page=100",
        "check_summaries": f"{base}/commits/{reviewed_head_sha}/status",
    }
    missing = (set(expected) |  {"check_runs"}) - set(responses)
    if missing: raise ValueError("review surface inventory endpoints are incomplete")
    annotations = _annotation_items(responses, base=base, reviewed_head_sha=reviewed_head_sha)
    sources: list[Mapping[str, Any]] = []
    for key, url in expected.items():
        response = responses[key]; _operational(response, "review surface response")
        if (response.request_url, response.response_url, response.status_code) != (url, url, 200): raise ValueError("review surface response URL0/status is not authoritative")
        payload = github_response_payload(response)
        items = payload.get("statuses", []) if key == "check_summaries" and isinstance(payload, Mapping) else payload
        if not isinstance(items, list) or len(items) >= 100: raise ValueError("review surface payload/pagination is incomplete")
        for item in items:
            if not isinstance(item, Mapping): raise ValueError("review surface item is malformed")
            author = item.get("user") or item.get("app") or {}
            is_bot = isinstance(author, Mapping) and (author.get("type") in {"Bot", "App"} or bool(item.get("app")))
            if not is_bot: continue
            stable = item.get("node_id") or item.get("id")
            if stable is None: raise ValueError("review surface source identity is missing")
            sources.append(MappingProxyType({
                "source_id": f"EXTSRC-{len(sources)+1:03d}", "github_source_key": f"{key}:{stable}",
                "github_object_type": key, "github_object_id": str(stable), "target_repository_id": target_identity.repository_id,
                "pr_number": pull_request, "reviewed_head_sha": reviewed_head_sha, "receipt_id": response.receipt_id,
                "triage_disposition": "inspected_no_action", "inspected": False, "source_type": key,
                "author": author.get("login") or author.get("slug"), "is_bot": True, "url": item.get("html_url") or item.get("target_url"),
                "content_sha256": bytes_sha256(json.dumps(dict(item), sort_keys=True, separators=(",", ":")).encode()),
            }))
    for ann in annotations.items:
        sources.append(MappingProxyType({
            "source_id": f"EXTSRC-{len(sources)+1:03d}", "github_source_key": f"check_runs:{ann['check_run_id']}:{ann['path']}:{ann['start_line']}:{ann['end_line']}:{ann['annotation_level']}:{ann['message']}",
            "github_object_type": "check_annotation", "github_object_id": str(ann["id"]), "target_repository_id": target_identity.repository_id,
            "pr_number": pull_request, "reviewed_head_sha": reviewed_head_sha, "receipt_id": ann["receipt_id"],
            "triage_disposition": "inspected_no_action", "inspected": False, "source_type": "github_check_annotation",
            "author": (ann["app"] or {}).get("slug"), "is_bot": True, "url": ann.get("html_url"), "content_sha256": bytes_sha256(json.dumps(dict(ann), sort_keys=True, separators=(",", ":")).encode()),
        }))
    return VerifiedReviewSurfaceInventory(_SURFACE_TOKEN, target_repository, target_identity.repository_id, pull_request, reviewed_head_sha, tuple(sources), True)


def bind_candidate_governance_evidence(evidence: VerifiedGovernanceEvidence, governance_source: VerifiedGitHubGovernanceSource, target_identity: VerifiedTargetIdentity) -> CandidateGovernanceEvidence:
    if not is_verified_governance_evidence(evidence) or not is_verified_github_governance_source(governance_source):
        raise ValueError("sealed governance evidence and source are required")
    if not isinstance(target_identity, VerifiedTargetIdentity) or target_identity._token is not _TARGET_TOKEN:
        raise ValueError("sealed target identity is required")
    if evidence.repository != target_identity.repository or governance_source.repository_id != target_identity.repository_id:
        raise ValueError("governance evidence target identity mismatch")
    return CandidateGovernanceEvidence(_CAPABILITY_TOKEN, evidence, governance_source, target_identity)


def official_governance_evidence(value: object) -> VerifiedGovernanceEvidence | None:
    return value.evidence if isinstance(value, CandidateGovernanceEvidence) and value._token is _CAPABILITY_TOKEN else None


def verify_governance_payload_bundle(*args: Any, **kwargs: Any) -> None:
    raise ValueError("sealed active GitHub governance evidence is required; caller payloads cannot mint governance capability")


def classify_governance(evidence: object, *, target_repository: str | None = None, target_repository_id: int | None = None, pull_request: int | None = None, reviewed_head_sha: str | None = None) -> dict[str, Any]:
    sealed = official_governance_evidence(evidence)
    if not (target_repository and isinstance(target_repository_id, int) and pull_request and reviewed_head_sha) or sealed is None:
        return {"status": "NOT_VERIFIABLE", "reason_codes": ["repository_settings_not_verified"]}
    if sealed.repository != target_repository or sealed.pull_request_number != pull_request or sealed.exact_head_sha != reviewed_head_sha:
        return {"status": "NOT_VERIFIABLE", "reason_codes": ["repository_settings_not_verified"]}
    if sealed.merge_authorized: return {"status": "VERIFIED", "reason_codes": []}
    return {"status": "GAP_FOUND", "reason_codes": ["merge_authorization_unverified"]}


def reconcile_bot_reviews(sources: Sequence[Mapping[str, Any]], suggestions: Sequence[Mapping[str, Any]], findings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    source_ids: set[str] = set(); inspected: set[str] = set()
    for source in sources:
        sid = source.get("source_id")
        if not isinstance(sid, str) or not sid or sid in source_ids: raise ValueError("source identity is missing or duplicate")
        source_ids.add(sid)
        if source.get("inspected") is True: inspected.add(sid)
    finding_by_id: {str, Mapping[str, Any]} = {}
    for finding in findings:
        fid = finding.get("finding_id")
        if not isinstance(fid, str) or not fid or fid in finding_by_id: raise ValueError("finding identity is missing or duplicate")
        finding_by_id[fid] = finding
    counts = {key: 0 for key in {"accepted", "resolved", "stale", "false_positive", "duplicate", "insufficient_evidence", "deferred", "out_of_scope"}}
    valid_blocking: list[str] = []; results: list[dict[str, Any]] = []; seen = set()
    for suggestion in suggestions:
        sid = suggestion.get("source_id")
        if sid not in source_ids: raise ValueError("suggestion references unknown source")
        suggestion_id = suggestion.get("suggestion_id") or suggestion.get("external_suggestion_id")
        if suggestion_id is in seen: raise ValueError("duplicate suggestion identity")
        seen.add(suggestion_id)
      raw = suggestion.get("triage_decision", suggestion.get("classification"))
        classification = TRIAGE_TO_RECONCILIATION.get(raw)
        if classification is None: raise ValueError("invalid suggestion classification")
        linked = suggestion.get("linked_finding_ids", [])
        if not isinstance(linked, list) or any(not isinstance(fid, str) for fid in linked): raise ValueError("linked_finding_ids must be a string array")
        if any(fid not in finding_by_id for fid in linked): raise ValueError("suggestion references unknown finding")
        counts[classification] += 1
        repair = classification == "accepted" and bool(linked)
        for fid in linked:
            finding = finding_by_id[fid]
            if repair and finding.get("severity") in {"CRITICAL", "HIGH", 'MEDIUM%ô…¹™¥¹‘¥¹œ¹•Ð ‰‰±½­¥¹œˆ¤èÙ…±¥‘}‰±½­¥¹œ¹…ÁÁ•¹¡™¥¤(€€€€€€€É•ÍÕ±ÑÌ¹…ÁÁ•¹¡ì‰Í½ÕÉ•}¥ˆèÍ¥°€‰±…ÍÍ¥™¥…Ñ¥½¸ˆè±…ÍÍ¥™¥…Ñ¥½¸°€‰±¥¹­•‘}™¥¹‘¥¹}¥‘Ìˆè±¥¹­•°€‰É•Á…¥É}…ÕÑ¡½É¥é•ˆèÉ•Á…¥È°€‰‘ÕÁ±¥…Ñ•}½¹™¥Éµ•ˆè±…ÍÍ¥™¥…Ñ¥½¸€ôô€‰‘ÕÁ±¥…Ñ”‰ô¤(€€€Õ¹¥¹ÍÁ•Ñ•€ôÍ½ÉÑ•¡Í½ÕÉ•}¥‘Ì€´¥¹ÍÁ•Ñ•¤(€€€É•ÑÕÉ¸ì‰½±±•Ñ¥½¹}ÍÑ…ÑÕÌˆè€‰=5A1Qˆ¥˜¹½ÐÕ¹¥¹ÍÁ•Ñ••±Í”€‰%9=5A1Qˆ°€‰½Á•¹}‰½Ñ}Í½ÕÉ•Í}Ñ½Ñ…°ˆè±•¸¡Í½ÕÉ•}¥‘Ì¤°€‰¥¹ÍÁ•Ñ•‘}Ñ½Ñ…°ˆè±•¸¡¥¹ÍÁ•Ñ•¤°€‰½Õ¹ÑÌˆè½Õ¹ÑÌ°€‰Õ¹¥¹ÍÁ•Ñ•‘}Í½ÕÉ•}¥‘ÌˆèÕ¹¥¹ÍÁ•Ñ•°€‰Ù…±¥‘}‰±½­¥¹}™¥¹‘¥¹}¥‘ÌˆèÍ½ÉÑ•¡Í•Ð¡Ù…±¥‘}‰±½­¥¹œ¤¤°€‰ÍÕ•ÍÑ¥½¹}É•ÍÕ±ÑÌˆèÉ•ÍÕ±ÑÍô(()‘•˜É•½µÁÕÑ•}•áÑ•É¹…±}É•Ù¥•Ý}É•½¹¥±¥…Ñ¥½¸¡Á…­…”è5…ÁÁ¥¹mÍÑÈ°¹åt°¥¹Ù•¹Ñ½ÉäèY•É¥™¥•‘I•Ù¥•ÝMÕÉ™…•%¹Ù•¹Ñ½Éä¤€´ø‘¥ÑmÍÑÈ°¹åtè(€€€¥˜¹½Ð¥Í¥¹ÍÑ…¹”¡¥¹Ù•¹Ñ½Éä°Y•É¥™¥•‘I•Ù¥•ÝMÕÉ™…•%¹Ù•¹Ñ½Éä¤½È¥¹Ù•¹Ñ½Éä¹}Ñ½­•¸¥Ì¹½Ð}MUI}Q=-8è(€€€€€€€É…¥Í”Y…±Õ•ÉÉ½È ‰Í•…±•É•Ù¥•ÜÍÕÉ™…”¥¹Ù•¹Ñ½Éä¥ÌÉ•ÅÕ¥É•ˆ¤(€€€¥¹Ñ…­”€ôÁ…­…”¹•Ð ‰•áÑ•É¹…±}É•Ù¥•Ý}¥¹Ñ…­”ˆ¤½Èíô(€€€Í½ÕÉ•Ì€ô±¥ÍÐ¡¥¹Ñ…­”¹•Ð ‰Í½ÕÉ•Í}¥¹ÍÁ•Ñ•ˆ°mt¤¤(€€€ÍÕ•ÍÑ¥½¹Ì€ô±¥ÍÐ¡¥¹Ñ…­”¹•Ð ‰ÍÕ•ÍÑ¥½¹Ìˆ°mt¤¤(€€€¥˜í¥Ñ•µl‰Í½ÕÉ•}¥‰t™½È¥Ñ•´¥¸Í½ÕÉ•Íô€„ôí¥Ñ•µl‰Í½ÕÉ•}¥‰t™½È¥Ñ•´¥¸¥¹Ù•¹Ñ½Éä¹Í½ÕÉ•Íôè(€€€€€€€É…¥Í”Y…±Õ•ÉÉ½È ‰•áÑ•É¹…°É•Ù¥•Ü¥¹Ñ…­”‘½•Ì¹½Ðµ…Ñ Ù•É¥™¥•É•Ù¥•ÜÍÕÉ™…”¥¹Ù•¹Ñ½Éäˆ¤(€€€É•ÑÕÉ¸É•½¹¥±•}‰½Ñ}É•Ù¥•ÝÌ¡Í½ÕÉ•Ì°ÍÕ•ÍÑ¥½¹Ì°Á…­…”¹•Ð ‰™¥¹‘¥¹Ìˆ°mt¤¤(()‘•˜Ù…±¥‘…Ñ•}…¹‘¥‘…Ñ•}Á…­…”¡Á…­…”è5…ÁÁ¥¹mÍÑÈ°¹åt°½Ù•É¹…¹•}•Ù¥‘•¹”è½‰©•Ðð9½¹”€ô9½¹”°€¨°É•Ù¥•Ý}ÍÕÉ™…•}¥¹Ù•¹Ñ½Éäè½‰©•Ðð9½¹”€ô9½¹”°Ñ…É•Ñ}É•Á½Í¥Ñ½Éå}¥è¥¹Ðð9½¹”€ô9½¹”¤€´ø±¥ÍÑmÍÑÉtè(€€€…¹‘¥‘…Ñ”€ô‘¥Ð¡Á…­…”¤(€€€¥˜…¹‘¥‘…Ñ”¹•Ð ‰ÁÉ½Ñ½½±}Ù•ÉÍ¥½¸ˆ¤€„ôAI=Q==1}YIM%=8è(€€€€€€€É•ÑÕÉ¸l‰Á…­…”ÁÉ½Ñ½½±}Ù•ÉÍ¥½¸‘½•Ì¹½Ðµ…Ñ Ñ¡”…Ñ¥Ù”ÁÉ½Ñ½½°‰t(€€€¥˜É•Ù¥•Ý}ÍÕÉ™…•}¥¹Ù•¹Ñ½Éä¥Ì¹½Ð9½¹”è(€€€€€€€ÑÉäè…¹‘¥‘…Ñ•l‰•áÑ•É¹…±}É•Ù¥•Ý}É•½¹¥±¥…Ñ¥½¸‰t€ôÉ•½µÁÕÑ•}•áÑ•É¹…±}É•Ù¥•Ý}É•½¹¥±¥…Ñ¥½¸¡…¹‘¥‘…Ñ”°É•Ù¥•Ý}ÍÕÉ™…•}¥¹Ù•¹Ñ½Éä¤(€€€€€€€•á•ÁÐY…±Õ•ÉÉ½È…Ì•áŒèÉ•ÑÕÉ¸mÍÑÈ¡•áŒ ¥t(€€€•Ù¥‘•¹”€ô½™™¥¥…±}½Ù•É¹…¹•}•Ù¥‘•¹”¡½Ù•É¹…¹•}•Ù¥‘•¹”¤(€€€É•ÑÕÉ¸m¥Ñ•´¹±¥¹” ¤™½È¥Ñ•´¥¸}½™™¥¥…±}Ù…±¥‘…Ñ•}Á…­…”¡…¹‘¥‘…Ñ”°½Ù•É¹…¹•}•Ù¥‘•¹”õ•Ù¥‘•¹”¥t(()‘•˜‰¥¹‘}µ¥¹¥µ…±}É•Ù¥•Ý}½µÁ±•Ñ¥½¸¡½µÁ±•Ñ¥½¸èY•É¥™¥•‘I•Ù¥•Ý½µÁ±•Ñ¥½¸°€¨°Ñ…É•Ñ}É•Á½Í¥Ñ½Éå}¥è¥¹Ð°¥¹ÍÁ•Ñ½É}½µµ¥Ðè…¹‘¥‘…Ñ•Y•É¥™¥•‘%¹ÍÁ•Ñ½É½µµ¥Ð¤€´øY•É¥™¥•‘5¥¹¥µ…±I•Ù¥•ÝI•™•É•¹”è(€€€¥˜¹½Ð¥Í}Ù•É¥™¥•‘}É•Ù¥•Ý}½µÁ±•Ñ¥½¸¡½µÁ±•Ñ¥½¸¤½È½µÁ±•Ñ¥½¸¹‘•¥Í¥½¹}ÁÉ½©•Ñ¥½¸ ¤¹•Ð ‰¥¹ÍÁ•Ñ¥½¹}ÁÉ½™¥±”ˆ¤€„ô5%9%50è(€€€€€€€É…¥Í”Y…±Õ•ÉÉ½È ‰Ù•É¥™¥•½™™¥¥…°µ¥¹¥µ…°½µÁ±•Ñ¥½¸¥ÌÉ•ÅÕ¥É•ˆ¤(€€€½µµ¥Ð€ô}Ù•É¥™¥•‘}½µµ¥Ð¡¥¹ÍÁ•Ñ½É}½µµ¥Ð¤(€€€¥˜¹½Ð¥Í¥¹ÍÑ…¹”¡Ñ…É•Ñ}É•Á½Í¥Ñ½Éå}¥°¥¹Ð¤½ÈÑ…É•Ñ}É•Á½Í¥Ñ½Éå}¥€ðô€ÀèÉ…¥Í”Y…±Õ•ÉÉ½È ‰Ñ…É•ÐÉ•Á½Í¥Ñ½Éå}¥¥Ì¥¹Ù…±¥ˆ¤(€€€É•ÑÕÉ¸Y•É¥™¥•‘5¥¹¥µ…±I•Ù¥•ÝI•™•É•¹”¡}II9}Q=-8°½µÁ±•Ñ¥½¸°Ñ…É•Ñ}É•Á½Í¥Ñ½Éå}¥°½µµ¥Ð¤(()‘•˜¥Í}Ù•É¥™¥•‘}µ¥¹¥µ…±}É•Ù¥•Ý}É•™•É•¹”¡Ù…±Õ”è½‰©•Ð¤€´ø‰½½°è(€€€É•ÑÕÉ¸¥Í¥¹ÍÑ…¹”¡Ù…±Õ”°Y•É¥™¥•‘5¥¹¥µ…±I•Ù¥•ÝI•™•É•¹”¤…¹Ù…±Õ”¹}Ñ½­•¸¥Ì}II9}Q=-8(()‘•˜Ù•É¥™å}‰…Í•}É•Ù¥•Ý}É•™•É•¹”¡•Ù¥‘•¹”è½‰©•Ð°±¥Ù•}¡•…‘}Í¡„èÍÑÈ°€¨°Ñ…É•Ñ}É•Á½Í¥Ñ½ÉäèÍÑÈð9½¹”€ô9½¹”°Ñ…É•Ñ}É•Á½Í¥Ñ½Éå}¥è¥¹Ðð9½¹”€ô9½¹”°ÁÕ±±}É•ÅÕ•ÍÐè¥¹Ðð9½¹”€ô9½¹”¤€´ø‘¥ÑmÍÑÈ°¹åtè(€€€¥˜¹½Ð¥Í}Ù•É¥™¥•‘}µ¥¹¥µ…±}É•Ù¥•Ý}É•™•É•¹”¡•Ù¥‘•¹”¤èÉ•ÑÕÉ¸ì‰ÍÑ…ÑÕÌˆè€‰%9Y1%ˆ°€‰É•…Í½¸ˆè€‰Ù•É¥™¥•‘}µ¥¹¥µ…±}É•Ù¥•Ý}É•ÅÕ¥É•‰ô(€€€½µÁ±•Ñ¥½¸€ô•Ù¥‘•¹”¹½µÁ±•Ñ¥½¸(€€€¥˜Ñ…É•Ñ}É•Á½Í¥Ñ½Éä¥Ì¹½Ð9½¹”…¹½µÁ±•Ñ¥½¸¹Ñ…É•Ñ}É•Á½Í¥Ñ½Éä€„ôÑ…É•Ñ}É•Á½Í¥Ñ½ÉäèÉ•ÑÕÉ¸ì‰ÍÑ…ÑÕÌˆè€‰%9Y1%ˆ°€‰É•…Í½¸ˆè€‰Ñ…É•Ñ}É•Á½Í¥Ñ½Éå}µ¥Íµ…Ñ ‰ô(€€€¥˜¹½Ð¥Í¥¹ÍÑ…¹”¡Ñ…É•Ñ}É•Á½Í¥Ñ½Éå}¥°¥¹Ð¤½ÈÑ…É•Ñ}É•Á½Í¥Ñ½Éå}¥€ðô€ÀèÉ•ÑÕÉ¸ì‰ÍÑ…ÑÕÌˆè€‰%9Y1%ˆ°€‰É•…Í½¸ˆè€‰Ñ…É•Ñ}É•Á½Í¥Ñ½Éå}¥‘}É•ÅÕ¥É•‰ô(€€€¥˜•Ù¥‘•¹”¹Ñ…É•Ñ}É•Á½Í¥Ñ½Éå}¥€„ôÑ…É•Ñ}É•Á½Í¥Ñ½Éå}¥èÉ•ÑÕÉ¸ì‰ÍÑ…ÑÕÌˆè€‰%9Y1%ˆ°€‰É•…Í½¸ˆè€‰Ñ…É•Ñ}É•Á½Í¥Ñ½Éå}¥‘}µ¥Íµ…Ñ ‰ô(€€€¥˜ÁÕ±±}É•ÅÕ•ÍÐ¥Ì¹½Ð9½¹”…¹½µÁ±•Ñ¥½¸¹ÁÉ}¹Õµ‰•È€„ôÁÕ±±}É•ÅÕ•ÍÐèÉ•ÑÕÉ¸ì‰ÍÑ…ÑÕÌˆè€‰%9Y1%ˆ°€‰É•…Í½¸ˆè€‰ÁÕ±±}É•ÅÕ•ÍÑ}µ¥Íµ…Ñ ‰ô(€€€¥˜½µÁ±•Ñ¥½¸¹É•Ù¥•Ý•‘}¡•…‘}Í¡„€„ô±¥Ù•}¡•…‘}Í¡„èÉ•ÑÕÉ¸ì‰ÍÑ…ÑÕÌˆè€‰MQ1ˆ°€‰É•…Í½¸ˆè€‰¡•…‘}‘É¥™Ðˆ°€‰…Ñ¥½¸ˆè€‰É•ÉÕ¹}µ¥¹¥µ…±}Ñ¡•¹}ÍÑÉ¥Ð‰ô(€€€É•ÑÕÉ¸ì‰ÍÑ…ÑÕÌˆè€‰YI%%ˆ°€‰É•…Í½¸ˆè€‰Í…µ•}¡•…ˆ°€‰…Ñ¥½¸ˆè€‰É•ÕÍ•}Ñ•¡¹¥…±}‘•¥Í¥½¸‰ô(()‘•˜}Ñ…É•Ð¡É•™•É•¹”èY•É¥™¥•‘5¥¹¥µ…±I•Ù¥•ÝI•™•É•¹”¤€´ø5…ÁÁ¥¹mÍÑÈ°¹åtè(€€€Œ€ôÉ•™•É•¹”¹½µÁ±•Ñ¥½¸(€€€É•ÑÕÉ¸5…ÁÁ¥¹AÉ½áåQåÁ”¡ì‰É•Á½Í¥Ñ½ÉäˆèŒ¹Ñ…É•Ñ}É•Á½Í¥Ñ½Éä°€‰É•Á½Í¥Ñ½Éå}¥ˆèÉ•™•É•¹”¹Ñ…É•Ñ}É•Á½Í¥Ñ½Éå}¥°€‰ÁÕ±±}É•ÅÕ•ÍÐˆèŒ¹ÁÉ}¹Õµ‰•È°€‰ÕÉ°ˆè˜‰¡ÑÑÁÌè¼½¥Ñ¡Õˆ¹½´½íŒ¹Ñ…É•Ñ}É•Á½Í¥Ñ½Éåô½ÁÕ±°½íŒ¹ÁÉ}¹Õµ‰•Éô‰ô¤(()‘•˜½É¡•ÍÑÉ…Ñ•}ÍÑÉ¥Ñ}…™Ñ•É}µ¥¹¥µ…°¡½¹Ñ•áÐè5…ÁÁ¥¹mÍÑÈ°¹åt°É•™É•Í¡}µ¥¹¥µ…±}É•Ù¥•Üè…±±…‰±•mm5…ÁÁ¥¹mÍÑÈ°¹åt°ÍÑÉt°Y•É¥™¥•‘5¥¹¥µ…±I•Ù¥•ÝI•™•É•¹•tð9½¹”€ô9½¹”¤€´ø5¥¹¥µ…±I•™É•Í¡I•ÍÕ±Ðè(€€€É•™•É•¹”€ô½¹Ñ•áÐ¹•Ð ‰Ù•É¥™¥•‘}µ¥¹¥µ…±}É•Ù¥•Üˆ¤¥˜¥Í¥¹ÍÑ…¹”¡½¹Ñ•áÐ°5…ÁÁ¥¹œ¤•±Í”9½¹”(€€€¥˜¹½Ð¥Í}Ù•É¥™¥•‘}µ¥¹¥µ…±}É•Ù¥•Ý}É•™•É•¹”¡É•™•É•¹”¤è(€€€€€€€É•ÑÕÉ¸5¥¹¥µ…±I•™É•Í¡I•ÍÕ±Ð¡}IIM!}Q=-8°€‰É•™É•Í¡}™…¥±•ˆ°5…ÁÁ¥¹AÉ½áåQåÁ”¡íô¤°€ˆˆ°9½¹”°€‰Ù•É¥™¥•‘}µ¥¹¥µ…±}É•Ù¥•Ý}É•ÅÕ¥É•ˆ¤(€€€Ñ…É•Ð€ô}Ñ…É•Ð¡É•™•É•¹”¤(€€€±¥Ù”€ô½¹Ñ•áÐ¹•Ð ‰Ù•É¥™¥•‘}±¥Ù•}ÁÉ}¡•…ˆ¤(€€€¥˜¹½Ð¥Í¥¹ÍÑ…¹”¡±¥Ù”°Y•É¥™¥•‘1¥Ù•AÉ!•…¤½È±¥Ù”¹}Ñ½­•¸¥Ì¹½Ð}QIQ}Q=-8è(€€€€€€€É•ÍÁ½¹Í”€ô½¹Ñ•áÐ¹•Ð ‰±¥Ù•}ÁÉ}É•ÍÁ½¹Í”ˆ¤(€€€€€€€¥˜É•ÍÁ½¹Í”¥Ì9½¹”è(€€€€€€€€€€€É•ÑÕÉ¸5¥¹¥µ…±I•™É•Í¡I•ÍÕ±Ð¡}IIM!}Q=-8°€‰É•™É•Í¡}™…¥±•ˆ°Ñ…É•Ð°€ˆˆ°9½¹”°€‰Í•…±•‘}±¥Ù•}ÁÉ}¡•…‘}É•ÅÕ¥É•ˆ¤(€€€€€€€±¥Ù”€ôÙ•É¥™å}±¥Ù•}ÁÉ}¡•…‘}É•ÍÁ½¹Í”¡É•ÍÁ½¹Í”°Ñ…É•Ñ}É•Á½Í¥Ñ½ÉäõÑ…É•Ñl‰É•Á½Í¥Ñ½Éä‰t°Ñ…É•Ñ}É•Á½Í¥Ñ½Éå}¥õÑ…É•Ñl‰É•Á½Í¥Ñ½Éå}¥‰t°ÁÕ±±}É•ÅÕ•ÍÐõÑ…É•Ñl‰ÁÕ±±}É•ÅÕ•ÍÐ‰t¤(€€€ÍÑ…ÑÕÌ€ôÙ•É¥™å}‰…Í•}É•Ù¥•Ý}É•™•É•¹”¡É•™•É•¹”°±¥Ù”¹¡•…‘}Í¡„°Ñ…É•Ñ}É•Á½Í¥Ñ½ÉäõÑ…É•Ñl‰É•Á½Í¥Ñ½Éä‰t°Ñ…É•Ñ}É•Á½Í¥Ñ½Éå}¥õÑ…É•Ñl‰É•Á½Í¥Ñ½Éå}¥‰t°ÁÕ±±}É•ÅÕ•ÍÐõÑ…É•Ñl‰ÁÕ±±}É•ÅÕ•ÍÐ‰t¤(€€€¥˜ÍÑ…ÑÕÍl‰ÍÑ…ÑÕÌ‰t€ôô€‰YI%%ˆè(€€€€€€€É•ÑÕÉ¸5¥¹¥µ…±I•™É•Í¡I•ÍÕ±Ð¡}IIM!}Q=-8°€‰Í…µ•}¡•…‘}É•ÕÍ”ˆ°Ñ…É•Ð°±¥Ù”¹¡•…‘}Í¡„°É•™•É•¹”¤(€€€¥˜ÍÑ…ÑÕÍl‰ÍÑ…ÑÕÌ‰t€„ô€‰MQ1ˆè(€€€€€€€É•ÑÕÉ¸5¥¹¥µ…±I•™É•Í¡I•ÍÕ±Ð¡}IIM!}Q=-8°€‰É•™É•Í¡}™…¥±•ˆ°Ñ…É•Ð°±¥Ù”¹¡•…‘}Í¡„°9½¹”°ÍÑ…ÑÕÌ¹•Ð ‰É•…Í½¸ˆ¤¤(€€€…±±‰…¬€ôÉ•™É•Í¡}µ¥¹¥µ…±}É•Ù¥•Ü½È½¹Ñ•áÐ¹•Ð ‰É•™É•Í¡}µ¥¹¥µ…±}É•Ù¥•Üˆ¤(€€€¥˜…±±‰…¬¥Ì9½¹”è(€€€€€€€É•ÑÕÉ¸5¥¹¥µ…±I•™É•Í¡I•ÍÕ±Ð¡}IIM!}Q=-8°€‰¡•…‘}‘É¥™Ñ}É•™É•Í¡}É•ÅÕ¥É•ˆ°Ñ…É•Ð°±¥Ù”¹¡•…‘}Í¡„°9½¹”°€‰µ¥¹¥µ…±}É•™É•Í¡}É•ÅÕ¥É•ˆ¤(€€€É•™É•Í¡•€ô…±±‰…¬¡Ñ…É•Ð°±¥Ù”¹¡•…‘}Í¡„¤(€€€Ù•É¥™ä€ôÙ•É¥™å}‰…Í•}É•Ù¥•Ý}É•™•É•¹”¡É•™É•Í¡•°±¥Ù”¹¡•…‘}Í¡„°Ñ…É•Ñ}É•Á½Í¥Ñ½ÉäõÑ…É•Ñl‰É•Á½Í¥Ñ½Éä‰t°Ñ…É•Ñ}É•Á½Í¥Ñ½Éå}¥õÑ…É•Ñl‰É•Á½Í¥Ñ½Éå}¥‰t°ÁÕ±±}É•ÅÕ•ÍÐõÑ…É•Ñl‰ÁÕ±±}É•ÅÕ•ÍÐ‰t¤(€€€¥˜Ù•É¥™ål‰ÍÑ…ÑÕÌ‰t€„ô€‰YI%%ˆè(€€€€€€€É•ÑÕÉ¸5¥¹¥µ…±I•™É•Í¡I•ÍÕ±Ð¡}IIM!}Q=-8°€‰É•™É•Í¡}™…¥±•ˆ°Ñ…É•Ð°±¥Ù”¹¡•…‘}Í¡„°9½¹”°Ù•É¥™ä¹•Ð ‰É•…Í½¸ˆ¤¤(€€€É•ÑÕÉ¸5¥¹¥µ…±I•™É•Í¡I•ÍÕ±Ð¡}IIM!}Q=-8°€‰É•™É•Í¡}Ù•É¥™¥•ˆ°Ñ…É•Ð°±¥Ù”¹¡•…‘}Í¡„°É•™É•Í¡•¤(()‘•˜Á…ÉÍ•}¥¹Ñ…­”¡Ñ•áÐèÍÑÈ°½¹Ñ•áÐè5…ÁÁ¥¹mÍÑÈ°¹åtð9½¹”€ô9½¹”¤€´ø‘¥ÑmÍÑÈ°¹åtè(€€€¥˜½¹Ñ•áÐ¥Ì¹½Ð9½¹”…¹¹½Ð¥Í¥¹ÍÑ…¹”¡½¹Ñ•áÐ°5…ÁÁ¥¹œ¤è(€€€€€€€É•ÑÕÉ¸ì‰¥¹ÍÁ•Ñ¥½¹}ÁÉ½™¥±”ˆè5%9%50°€‰Ñ…É•Ðˆè9½¹”°€‰É•ÕÍ•}ÕÉÉ•¹Ñ}µ¥¹¥µ…°ˆè…±Í”°€‰µ¥ÍÍ¥¹œˆèl‰Ù…±¥‘}½¹Ñ•áÐ‰t°€‰•ÉÉ½Èˆè€‰½¹Ñ•áÑ}µ…±™½Éµ•‰ô(€€€±¥¹•Ì€ôm±¥¹”¹ÍÑÉ¥À ¤™½È±¥¹”¥¸Ñ•áÐ¹ÍÁ±¥Ñ±¥¹•Ì ¤¥˜±¥¹”¹ÍÑÉ¥À ¥t(€€€ÁÉ½™¥±”€ô5%9%50(€€€¥˜±¥¹•Ì…¹±¥¹•ÍlÁt¥¸ì‹b·b¿bŸffn0ˆ°€‹bÏb»b¨ƒj¿n3bÇbŸff‰ôè(€€€€€€€ÁÉ½™¥±”€ô5%9%50¥˜±¥¹•Ì¹Á½À À¤€ôô€‹b·b¿bŸffn0ˆ•±Í”MQI%P(€€€ÕÉ°€ô¹•áÐ ¡±¥¹”™½È±¥¹”¥¸±¥¹•Ì¥˜AI}UI1}I¹™Õ±±µ…Ñ ¡±¥¹”¤¤°9½¹”¤(€€€¥˜ÁÉ½™¥±”€ôôMQI%P…¹ÕÉ°¥Ì9½¹”…¹½¹Ñ•áÐè(€€€€€€€É•™É•Í €ô½É¡•ÍÑÉ…Ñ•}ÍÑÉ¥Ñ}…™Ñ•É}µ¥¹¥µ…°¡½¹Ñ•áÐ¤(€€€€€€€¥˜É•™É•Í ¹ÍÑ…Ñ”¥¸ì‰Í…µ•}¡•…‘}É•ÕÍ”ˆ°€‰¡•…‘}‘É¥™Ñ}É•™É•Í¡}É•ÅÕ¥É•ˆ°€‰É•™É•Í¡}Ù•É¥™¥•‰ôè(€€€€€€€€€€€É•ÑÕÉ¸ì‰¥¹ÍÁ•Ñ¥½¹}ÁÉ½™¥±”ˆèMQI%P°€‰Ñ…É•Ðˆè‘¥Ð¡É•™É•Í ¹Ñ…É•Ð¤°€‰É•ÕÍ•}ÕÉÉ•¹Ñ}µ¥¹¥µ…°ˆèÉ•™É•Í ¹ÍÑ…Ñ”€ôô€‰Í…µ•}¡•…‘}É•ÕÍ”ˆ°€‰É•™É•Í¡•‘}µ¥¹¥µ…±}É•Ù¥•ÜˆèÉ•™É•Í ¹‰Õ¹‘±”°€‰µ¥¹¥µ…±}É•™É•Í¡}ÍÑ…Ñ”ˆèÉ•™É•Í ¹ÍÑ…Ñ”°€‰½¹Ñ¥¹Õ•}ÍÑÉ¥ÐˆèÉ•™É•Í ¹ÍÑ…Ñ”¥¸ì‰Í…µ•}¡•…‘}É•ÕÍ”ˆ°€‰É•™É•Í¡}Ù•É¥™¥•‰ô°€‰µ¥ÍÍ¥¹œˆèmuô(€€€€€€€¥˜É•™É•Í ¹Ñ…É•Ðè(€€€€€€€€€€€É•ÑÕÉ¸ì‰¥¹ÍÁ•Ñ¥½¹}ÁÉ½™¥±”ˆèMQI%P°€‰Ñ…É•Ðˆè‘¥Ð¡É•™É•Í ¹Ñ…É•Ð¤°€‰É•ÕÍ•}ÕÉÉ•¹Ñ}µ¥¹¥µ…°ˆè…±Í”°€‰µ¥¹¥µ…±}É•™É•Í¡}ÍÑ…Ñ”ˆèÉ•™É•Í ¹ÍÑ…Ñ”°€‰½¹Ñ¥¹Õ•}ÍÑÉ¥Ðˆè…±Í”°€‰µ¥ÍÍ¥¹œˆèmt°€‰•ÉÉ½ÈˆèÉ•™É•Í ¹É•…Í½¹ô(€€€¥˜ÕÉ°¥Ì9½¹”è(€€€€€€€É•ÑÕÉ¸ì‰¥¹ÍÁ•Ñ¥½¹}ÁÉ½™¥±”ˆèÁÉ½™¥±”°€‰Ñ…É•Ðˆè9½¹”°€‰É•ÕÍ•}ÕÉÉ•¹Ñ}µ¥¹¥µ…°ˆè…±Í”°€‰µ¥ÍÍ¥¹œˆèl‰ÁÕ±±}É•ÅÕ•ÍÑ}ÕÉ°‰uô(€€€µ…Ñ €ôAI}UI1}I¹™Õ±±µ…Ñ ¡ÕÉ°¤(€€€É•ÑÕÉ¸ì‰¥¹ÍÁ•Ñ¥½¹}ÁÉ½™¥±”ˆèÁÉ½™¥±”°€‰Ñ…É•Ðˆèì‰É•Á½Í¥Ñ½Éäˆèµ…Ñ ¹É½ÕÀ Ä¤°€‰ÁÕ±±}É•ÅÕ•ÍÐˆè¥¹Ð¡µ…Ñ ¹É½ÕÀ È¤¤°€‰ÕÉ°ˆèÕÉ±ô°€‰É•ÕÍ•}ÕÉÉ•¹Ñ}µ¥¹¥µ…°ˆè…±Í”°€‰µ¥ÍÍ¥¹œˆèmuô(()‘•˜É•¹‘•É}½Ý¹•É}ÁÉ½™¥±•}½µµ…¹‘Ì¡ÁÉ½™¥±”èÍÑÈ¤€´ø‰åÑ•Ìè(€€€¥˜ÁÉ½™¥±”¹½Ð¥¸í5%9%50°MQI%Qôè(€€€€€€€É…¥Í”Y…±Õ•ÉÉ½È ‰Õ¹­¹½Ý¸¥¹ÍÁ•Ñ¥½¹}ÁÉ½™¥±”ˆ¤(€€€É•ÑÕÉ¸}½™™¥¥…±}ÁÉ½™¥±•}½µµ…¹‘Ì ¤¹•¹½‘” ‰ÕÑ˜´àˆ¤(()‘•˜Ù…±¥‘…Ñ•}½Ý¹•É}ÁÉ½™¥±•}½µµ…¹‘Ì¡É…Üè‰åÑ•Ì¤€´ø±¥ÍÑmÍÑÉtè(€€€•ÉÉ½ÉÌ€ômt(€€€¥˜É…Ü€„ôAI=%1}=559M}	eQLè•ÉÉ½ÉÌ¹…ÁÁ•¹ ‰½Ý¹•ÈÁÉ½™¥±”½µµ…¹‘Ì‘¥™™•È™É½´…¹½¹¥…°½™™¥¥…°‰åÑ•Ìˆ¤(€€€¥˜É…Ü¹ÍÑ…ÉÑÍÝ¥Ñ ¡ˆ‰qá•™qá‰‰qá‰˜ˆ¤è•ÉÉ½ÉÌ¹…ÁÁ•¹ ‰½Ý¹•ÈÁÉ½™¥±”½µµ…¹‘ÌµÕÍÐ¹½Ð½¹Ñ…¥¸	=4ˆ¤(€€€¥˜ˆ‰qÉq¸ˆ¥¸É…Üè•ÉÉ½ÉÌ¹…ÁÁ•¹ ‰½Ý¹•ÈÁÉ½™¥±”½µµ…¹‘ÌµÕÍÐÕÍ”1¹•Ý±¥¹•Ìˆ¤(€€€¥˜¹½ÐÉ…Ü¹•¹‘ÍÝ¥Ñ ¡ˆ‰q¸ˆ¤è•ÉÉ½ÉÌ¹…ÁÁ•¹ ‰½Ý¹•ÈÁÉ½™¥±”½µµ…¹‘ÌµÕÍÐ•¹Ý¥Ñ 1ˆ¤(€€€É•ÑÕÉ¸•ÉÉ½ÉÌ(()‘•˜}Õ¹ÍÕÁÁ½ÉÑ•‘}½ÕÑÁÕÐ¡Íåµ‰½°èÍÑÈ¤€´ø9½¹”è(€€€É…¥Í”…¹‘¥‘…Ñ•=ÕÑÁÕÑ5¥É…Ñ¥½¹ÉÉ½È¡˜‰íÍåµ‰½±ô¥Ì¹¼±½¹•È…¸½ÕÑÁÕÐ…ÕÑ¡½É¥ÑäìÕÍ”…¹½¹¥…°É•Ù¥•ÜµÁ…­…”ÁÉ½•ÍÍ¥¹œ°Y•É¥™¥•‘I•Ù¥•Ý½µÁ±•Ñ¥½¸°…¹½™™¥¥…±}½Ý¹•É}‘•±¥Ù•Éäˆ¤(()‘•˜ÁÉ½©•Ñ}‘•¥Í¥½¸ ©…ÉÌè¹ä°€¨©­Ý…ÉÌè¹ä¤€´ø9½¹”è}Õ¹ÍÕÁÁ½ÉÑ•‘}½ÕÑÁÕÐ ‰…¹‘¥‘…Ñ•}ØÅ|ÄÄ¹ÁÉ½©•Ñ}‘•¥Í¥½¸ˆ¤)‘•˜É•¹‘•É}…¹‘¥‘…Ñ•}¹•áÑ}…Ñ¥½¹}ÁÉ½µÁÐ ©…ÉÌè¹ä°€¨©­Ý…ÉÌè¹ä¤€´ø9½¹”è}Õ¹ÍÕÁÁ½ÉÑ•‘}½ÕÑÁÕÐ ‰É•¹‘•É}…¹‘¥‘…Ñ•}¹•áÑ}…Ñ¥½¹}ÁÉ½µÁÐˆ¤)‘•˜É•¹‘•É}…¹‘¥‘…Ñ•}½Ý¹•É}É•ÍÕ±Ð ©…ÉÌè¹ä°€¨©­Ý…ÉÌè¹ä¤€´ø9½¹”è}Õ¹ÍÕÁÁ½ÉÑ•‘}½ÕÑÁÕÐ ‰É•¹‘•É}…¹‘¥‘…Ñ•}½Ý¹•É}É•ÍÕ±Ðˆ¤)‘•˜É•¹‘•É}…¹‘¥‘…Ñ•}½Ý¹•É}…É ©…ÉÌè¹ä°€¨©­Ý…ÉÌè¹ä¤€´ø9½¹”è}Õ¹ÍÕÁÁ½ÉÑ•‘}½ÕÑÁÕÐ ‰É•¹‘•É}…¹‘¥‘…Ñ•}½Ý¹•É}…Éˆ¤)‘•˜É•¹‘•É}…¹‘¥‘…Ñ•}Ñ•¡¹¥…±}¡…¹‘½™˜ ©…ÉÌè¹ä°€¨©­Ý…ÉÌè¹ä¤€´ø9½¹”è}Õ¹ÍÕÁÁ½ÉÑ•‘}½ÕÑÁÕÐ ‰É•¹‘•É}…¹‘¥‘…Ñ•}Ñ•¡¹¥…±}¡…¹‘½™˜ˆ¤)‘•˜‰Õ¥±‘}…¹‘¥‘…Ñ•}É•Ù¥•Ý}…ÉÑ¥™…ÑÌ ©…ÉÌè¹ä°€¨©­Ý…ÉÌè¹ä¤€´ø9½¹”è}Õ¹ÍÕÁÁ½ÉÑ•‘}½ÕÑÁÕÐ ‰‰Õ¥±‘}…¹‘¥‘…Ñ•}É•Ù¥•Ý}…ÉÑ¥™…ÑÌˆ¤)‘•˜Ù•É¥™å}…¹‘¥‘…Ñ•}É•Ù¥•Ý}…ÉÑ¥™…Ñ}‰åÑ•Ì ©…ÉÌè¹ä°€¨©­Ý…ÉÌè¹ä¤€´ø9½¹”è}Õ¹ÍÕÁÁ½ÉÑ•‘}½ÕÑÁÕÐ ‰Ù•É¥™å}…¹‘¥‘…Ñ•}É•Ù¥•Ý}…ÉÑ¥™…Ñ}‰åÑ•Ìˆ¤)‘•˜Ù•É¥™å}µ¥¹¥µ…±}É•Ù¥•Ý}…ÉÑ¥™…Ñ}‰åÑ•Ì ©…ÉÌè¹ä°€¨©­Ý…ÉÌè¹ä¤€´ø9½¹”è}Õ¹ÍÕÁÁ½ÉÑ•‘}½ÕÑÁÕÐ ‰Ù•É¥™å}µ¥¹¥µ…±}É•Ù¥•Ý}…ÉÑ¥™…Ñ}‰åÑ•Ìˆ¤)‘•˜‰Õ¥±‘}…¹‘¥‘…Ñ•}½Ý¹•É}‘•±¥Ù•Éå}…ÉÑ¥™…ÑÌ ©…ÉÌè¹ä°€¨©­Ý…ÉÌè¹ä¤€´ø9½¹”è}Õ¹ÍÕÁÁ½ÉÑ•‘}½ÕÑÁÕÐ ‰‰Õ¥±‘}…¹‘¥‘…Ñ•}½Ý¹•É}‘•±¥Ù•Éå}…ÉÑ¥™…ÑÌˆ¤)‘•˜…¹‘¥‘…Ñ•}½Ý¹•É}‘•±¥Ù•Éå}ÍÑ‘½ÕÐ ©…ÉÌè¹ä°€¨©­Ý…ÉÌè¹ä¤€´ø9½¹”è}Õ¹ÍÕÁÁ½ÉÑ•‘}½ÕÑÁÕÐ ‰…¹‘¥‘…Ñ•}½Ý¹•É}‘•±¥Ù•Éå}ÍÑ‘½ÕÐˆ¤(()}}…±±}|€ôl(€€€€‰…¹‘¥‘…Ñ•½Ù•É¹…¹•Ù¥‘•¹”ˆ°€‰…¹‘¥‘…Ñ•=ÕÑÁÕÑ5¥É…Ñ¥½¹ÉÉ½Èˆ°(€€€€‰…¹‘¥‘…Ñ•Y•É¥™¥•‘%¹ÍÁ•Ñ½É½µµ¥Ðˆ°€‰¡•­¹¹½Ñ…Ñ¥½¹½±±•Ñ¥½¸ˆ°(€€€€‰=YI99}IM=9}=Lˆ°€‰=YI99}MQQUM}Pˆ°(€€€€‰1=-}%9MAQ=I}IA=M%Q=Ie}%ˆ°€‰5%9%50ˆ°€‰5¥¹¥µ…±I•™É•Í¡I•ÍÕ±Ðˆ°(€€€€‰=]9I}AI=%1}=559M}IQ%Pˆ°€‰AI=%1}=559M}	eQLˆ°€‰AI=Q==1}YIM%=8ˆ°(€€€€‰MQI%Pˆ°€‰Q!9%1}IM=9}=Lˆ°€‰Y•É¥™¥•‘1¥Ù•AÉ!•…ˆ°(€€€€‰Y•É¥™¥•‘5¥¹¥µ…±I•Ù¥•ÝI•™•É•¹”ˆ°€‰Y•É¥™¥•‘I•Ù¥•ÝMÕÉ™…•%¹Ù•¹Ñ½Éäˆ°(€€€€‰Y•É¥™¥•‘Q…É•Ñ%‘•¹Ñ¥Ñäˆ°€‰‰¥¹‘}…¹‘¥‘…Ñ•}½Ù•É¹…¹•}•Ù¥‘•¹”ˆ°(€€€€‰‰¥¹‘}µ¥¹¥µ…±}É•Ù¥•Ý}½µÁ±•Ñ¥½¸ˆ°€‰‰åÑ•Í}Í¡„ÈÔØˆ°€‰…¹½¹¥…±}Í¡„ÈÔØˆ°(€€€€‰±…ÍÍ¥™å}½Ù•É¹…¹”ˆ°€‰¥Í}Ù•É¥™¥•‘}µ¥¹¥µ…±}É•Ù¥•Ý}É•™•É•¹”ˆ°(€€€€‰½™™¥¥…±}½Ù•É¹…¹•}•Ù¥‘•¹”ˆ°€‰½É¡•ÍÑÉ…Ñ•}ÍÑÉ¥Ñ}…™Ñ•É}µ¥¹¥µ…°ˆ°(€€€€‰Á…ÉÍ•}¥¹Ñ…­”ˆ°€‰É•½µÁÕÑ•}•áÑ•É¹…±}É•Ù¥•Ý}É•½¹¥±¥…Ñ¥½¸ˆ°(€€€€‰É•½¹¥±•}‰½Ñ}É•Ù¥•ÝÌˆ°€‰É•¹‘•É}½Ý¹•É}ÁÉ½™¥±•}½µµ…¹‘Ìˆ°(€€€€‰Ù…±¥‘…Ñ•}…¹‘¥‘…Ñ•}Á…­…”ˆ°€‰Ù…±¥‘…Ñ•}½Ý¹•É}ÁÉ½™¥±•}½µµ…¹‘Ìˆ°(€€€€‰Ù•É¥™å}‰…Í•}É•Ù¥•Ý}É•™•É•¹”ˆ°€‰Ù•É¥™å}…¹‘¥‘…Ñ•}¥¹ÍÁ•Ñ½É}½µµ¥Ñ}Á…å±½…ˆ°(€€€€‰Ù•É¥™å}…¹‘¥‘…Ñ•}¥¹ÍÁ•Ñ½É}½µµ¥Ñ}É•ÍÁ½¹Í•Ìˆ°€‰Ù•É¥™å}½Ù•É¹…¹•}Á…å±½…‘}‰Õ¹‘±”ˆ°(€€€€‰Ù•É¥™å}±¥Ù•}ÁÉ}¡•…‘}É•ÍÁ½¹Í”ˆ°€‰Ù•É¥™å}É•Ù¥•Ý}ÍÕÉ™…•}¥¹Ù•¹Ñ½Éå}É•ÍÁ½¹Í•Ìˆ°(€€€€‰Ù•É¥™å}Ñ…É•Ñ}¥‘•¹Ñ¥Ñå}É•ÍÁ½¹Í”ˆ°)t(