from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from . import candidate_v1_11_base as _base
from ._governance_transport import (
    GitHubApiResponse,
    fetch_github_api_response,
    github_response_payload,
)

_HEAD_TOKEN = object()
ORCHESTRATION_STATES = {
    "same_head_reuse",
    "head_drift_refresh_required",
    "refresh_in_progress",
    "refresh_verified",
    "refresh_failed",
}


@dataclass(frozen=True)
class VerifiedPullRequestHead:
    _token: object
    target_repository: str
    target_repository_id: int
    pull_request: int
    head_sha: str
    receipt_id: str


@dataclass(frozen=True)
class StrictOrchestrationResult:
    state: str
    state_history: tuple[str, ...]
    target: Mapping[str, Any]
    live_head_sha: str
    minimal_bundle: object | None
    strict_result: object | None
    error: str | None


def _require_sha40(value: object, label: str) -> str:
    if not isinstance(value, str) or not _base.SHA40_RE.fullmatch(value):
        raise ValueError(f"{label} must be a 40-character lowercase SHA")
    return value


def _bundle_reference_integrity(bundle: object) -> tuple[bool, str | None]:
    if not _base.is_verified_minimal_review_bundle(bundle):
        return False, "verified_minimal_review_required"
    try:
        artifacts = bundle.artifact_bytes
        required = set(_base.BASE_REQUIRED_ARTIFACTS)
        if not isinstance(artifacts, Mapping) or required - set(artifacts):
            return False, "incomplete_artifact_bundle"
        package_raw = artifacts["review-package.json"]
        projection_raw = artifacts["DECISION_PROJECTION.json"]
        manifest_raw = artifacts["artifact-manifest.json"]
        if not all(isinstance(raw, bytes) for raw in (package_raw, projection_raw, manifest_raw)):
            return False, "artifact_bytes_required"
        package = _base._json_object("review-package.json", package_raw)
        _base._json_object("DECISION_PROJECTION.json", projection_raw)
        manifest = _base._json_object("artifact-manifest.json", manifest_raw)
        reference = bundle.reference
        if reference.get("review_package_sha256") != _base.canonical_sha256(package):
            return False, "review_package_hash_mismatch"
        if reference.get("decision_projection_sha256") != _base.bytes_sha256(projection_raw):
            return False, "decision_projection_hash_mismatch"
        if reference.get("artifact_manifest_sha256") != _base.bytes_sha256(manifest_raw):
            return False, "artifact_manifest_hash_mismatch"
        identity = package.get("review_identity") or {}
        expected_identity = {
            "target_repository": reference.get("target_repository"),
            "target_repository_id": reference.get("target_repository_id"),
            "pr_number": reference.get("pull_request"),
            "reviewed_head_sha": reference.get("reviewed_head_sha"),
            "inspector_repository": reference.get("inspector_repository"),
            "inspector_commit_sha": reference.get("inspector_commit_sha"),
        }
        for key, expected in expected_identity.items():
            if identity.get(key) != expected:
                return False, f"review_identity_{key}_mismatch"
        manifest_items = manifest.get("artifacts")
        if not isinstance(manifest_items, list):
            return False, "artifact_manifest_malformed"
        listed: dict[str, str] = {}
        for item in manifest_items:
            if not isinstance(item, Mapping) or not isinstance(item.get("path"), str):
                return False, "artifact_manifest_malformed"
            path = item["path"]
            if path in listed:
                return False, "artifact_manifest_duplicate_path"
            listed[path] = item.get("sha256")
        for path in required - {"artifact-manifest.json"}:
            raw = artifacts.get(path)
            if not isinstance(raw, bytes) or listed.get(path) != _base.bytes_sha256(raw):
                return False, f"artifact_manifest_mismatch:{path}"
        if bundle.inspector_commit.repository != _base.LOCKED_INSPECTOR_REPOSITORY:
            return False, "inspector_identity_mismatch"
        if bundle.inspector_commit.repository_id != _base.LOCKED_INSPECTOR_REPOSITORY_ID:
            return False, "inspector_identity_mismatch"
        if bundle.inspector_commit.commit_sha != reference.get("inspector_commit_sha"):
            return False, "inspector_commit_mismatch"
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False, "artifact_integrity_invalid"
    return True, None


def verify_base_review_reference(
    evidence: object,
    live_head_sha: str,
    *,
    target_repository: str | None = None,
    target_repository_id: int | None = None,
    pull_request: int | None = None,
) -> dict[str, Any]:
    ok, reason = _bundle_reference_integrity(evidence)
    if not ok:
        return {"status": "INVALID", "reason": reason}
    return _base.verify_base_review_reference(
        evidence,
        live_head_sha,
        target_repository=target_repository,
        target_repository_id=target_repository_id,
        pull_request=pull_request,
    )


def _target_from_verified_bundle(bundle: object) -> dict[str, Any] | None:
    ok, _ = _bundle_reference_integrity(bundle)
    if not ok:
        return None
    reference = bundle.reference
    repository = reference.get("target_repository")
    repository_id = reference.get("target_repository_id")
    pull_request = reference.get("pull_request")
    if not isinstance(repository, str) or not repository:
        return None
    if not isinstance(repository_id, int) or repository_id <= 0:
        return None
    if not isinstance(pull_request, int) or pull_request <= 0:
        return None
    return {
        "repository": repository,
        "repository_id": repository_id,
        "pull_request": pull_request,
        "url": f"https://github.com/{repository}/pull/{pull_request}",
    }


def parse_intake(text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    profile = None
    if lines and lines[0] == "حداقلی":
        profile = _base.MINIMAL
        lines = lines[1:]
    elif lines and lines[0] == "سخت گیرانه":
        profile = _base.STRICT
        lines = lines[1:]
    url = next((line for line in lines if _base.PR_URL_RE.match(line)), None)
    if profile is None:
        profile = _base.MINIMAL
    if profile == _base.STRICT and url is None and context:
        evidence = context.get("verified_minimal_review")
        target = _target_from_verified_bundle(evidence)
        live_head = context.get("live_head_sha")
        if target and isinstance(live_head, str) and _base.SHA40_RE.fullmatch(live_head):
            reference_status = verify_base_review_reference(
                evidence,
                live_head,
                target_repository=target["repository"],
                target_repository_id=target["repository_id"],
                pull_request=target["pull_request"],
            )
            if reference_status.get("status") == "VERIFIED":
                return {
                    "inspection_profile": _base.STRICT,
                    "target": target,
                    "reuse_current_minimal": True,
                    "refresh_minimal": False,
                    "orchestration_state": "same_head_reuse",
                    "missing": [],
                }
            if reference_status.get("status") == "STALE":
                return {
                    "inspection_profile": _base.STRICT,
                    "target": target,
                    "reuse_current_minimal": False,
                    "refresh_minimal": True,
                    "orchestration_state": "head_drift_refresh_required",
                    "missing": [],
                }
    if url is None:
        return {
            "inspection_profile": profile,
            "target": None,
            "reuse_current_minimal": False,
            "refresh_minimal": False,
            "orchestration_state": None,
            "missing": ["pull_request_url"],
        }
    match = _base.PR_URL_RE.match(url)
    return {
        "inspection_profile": profile,
        "target": {
            "repository": match.group(1),
            "pull_request": int(match.group(2)),
            "url": url,
        },
        "reuse_current_minimal": False,
        "refresh_minimal": False,
        "orchestration_state": None,
        "missing": [],
    }


def verify_pull_request_head_response(
    response: GitHubApiResponse,
    *,
    target_identity: object,
    pull_request: int,
) -> VerifiedPullRequestHead:
    if not isinstance(target_identity, _base.VerifiedTargetIdentity):
        raise ValueError("sealed target identity is required")
    if target_identity._token is not _base._TARGET_TOKEN:
        raise ValueError("sealed target identity is required")
    if not isinstance(pull_request, int) or pull_request <= 0:
        raise ValueError("pull_request must be a positive integer")
    _base._require_operational_response(response, "pull request response")
    expected_url = f"https://api.github.com/repos/{target_identity.repository}/pulls/{pull_request}"
    if response.request_url != expected_url or response.response_url != expected_url:
        raise ValueError("pull request response URL does not match verified target")
    if response.status_code != 200:
        raise ValueError("pull request response is inaccessible")
    payload = github_response_payload(response)
    if not isinstance(payload, Mapping) or payload.get("number") != pull_request:
        raise ValueError("pull request response identity mismatch")
    head = payload.get("head") or {}
    head_sha = _require_sha40(head.get("sha"), "pull request head")
    return VerifiedPullRequestHead(
        _HEAD_TOKEN,
        target_identity.repository,
        target_identity.repository_id,
        pull_request,
        head_sha,
        response.receipt_id,
    )


def orchestrate_strict_review(
    *,
    previous_minimal: object,
    target_identity: object,
    pull_request_response: GitHubApiResponse,
    refresh_minimal: Callable[[object, int, str], object],
    continue_strict: Callable[[object, object, int, str], object],
) -> StrictOrchestrationResult:
    target = _target_from_verified_bundle(previous_minimal)
    if target is None:
        raise ValueError("verified previous Minimal review is required")
    if not isinstance(target_identity, _base.VerifiedTargetIdentity):
        raise ValueError("sealed target identity is required")
    if target_identity._token is not _base._TARGET_TOKEN:
        raise ValueError("sealed target identity is required")
    if target_identity.repository != target["repository"] or target_identity.repository_id != target["repository_id"]:
        raise ValueError("verified target identity does not match Minimal review")
    head = verify_pull_request_head_response(
        pull_request_response,
        target_identity=target_identity,
        pull_request=target["pull_request"],
    )
    status = verify_base_review_reference(
        previous_minimal,
        head.head_sha,
        target_repository=target["repository"],
        target_repository_id=target["repository_id"],
        pull_request=target["pull_request"],
    )
    if status.get("status") == "VERIFIED":
        strict_result = continue_strict(
            previous_minimal,
            target_identity,
            target["pull_request"],
            head.head_sha,
        )
        return StrictOrchestrationResult(
            "same_head_reuse",
            ("same_head_reuse",),
            MappingProxyType(target),
            head.head_sha,
            previous_minimal,
            strict_result,
            None,
        )
    if status.get("status") != "STALE":
        raise ValueError(f"previous Minimal review is invalid: {status.get('reason')}")

    history = ["head_drift_refresh_required", "refresh_in_progress"]
    try:
        refreshed = refresh_minimal(target_identity, target["pull_request"], head.head_sha)
        refreshed_status = verify_base_review_reference(
            refreshed,
            head.head_sha,
            target_repository=target["repository"],
            target_repository_id=target["repository_id"],
            pull_request=target["pull_request"],
        )
        if refreshed_status.get("status") != "VERIFIED":
            raise ValueError("fresh Minimal review did not verify on the live exact Head")
        history.append("refresh_verified")
        strict_result = continue_strict(
            refreshed,
            target_identity,
            target["pull_request"],
            head.head_sha,
        )
        return StrictOrchestrationResult(
            "refresh_verified",
            tuple(history),
            MappingProxyType(target),
            head.head_sha,
            refreshed,
            strict_result,
            None,
        )
    except Exception as exc:
        history.append("refresh_failed")
        return StrictOrchestrationResult(
            "refresh_failed",
            tuple(history),
            MappingProxyType(target),
            head.head_sha,
            None,
            None,
            str(exc),
        )


def _response_pages(value: object, label: str) -> tuple[GitHubApiResponse, ...]:
    if isinstance(value, GitHubApiResponse):
        return (value,)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        pages = tuple(value)
        if pages and all(isinstance(item, GitHubApiResponse) for item in pages):
            return pages
    raise ValueError(f"{label} response pages are missing or malformed")


def _check_runs_page_url(base: str, reviewed_head_sha: str, page: int) -> str:
    return f"{base}/commits/{reviewed_head_sha}/check-runs?per_page=100&page={page}"


def _annotations_page_url(base: str, check_run_id: int, page: int) -> str:
    return f"{base}/check-runs/{check_run_id}/annotations?per_page=100&page={page}"


def _validate_page_response(
    response: GitHubApiResponse,
    *,
    expected_url: str,
    label: str,
    allow_legacy_first_page_url: str | None = None,
) -> Any:
    _base._require_operational_response(response, label)
    accepted = {expected_url}
    if allow_legacy_first_page_url:
        accepted.add(allow_legacy_first_page_url)
    if response.request_url not in accepted or response.response_url != response.request_url:
        raise ValueError(f"{label} response URL does not match expected endpoint")
    if response.status_code != 200:
        raise ValueError(f"{label} endpoint is inaccessible")
    return github_response_payload(response)


def collect_check_run_annotation_responses(
    *,
    target_repository: str,
    reviewed_head_sha: str,
    token: str | None,
    api_version: str,
    fetcher: Callable[..., GitHubApiResponse] = fetch_github_api_response,
    max_pages: int = 100,
) -> Mapping[str, Any]:
    if not isinstance(target_repository, str) or "/" not in target_repository:
        raise ValueError("target_repository must be owner/name")
    _require_sha40(reviewed_head_sha, "reviewed_head_sha")
    if not isinstance(max_pages, int) or max_pages <= 0:
        raise ValueError("max_pages must be positive")
    base = f"https://api.github.com/repos/{target_repository}"
    check_pages: list[GitHubApiResponse] = []
    check_runs: list[Mapping[str, Any]] = []
    total_count: int | None = None
    for page in range(1, max_pages + 1):
        url = _check_runs_page_url(base, reviewed_head_sha, page)
        response = fetcher(url, token=token, api_version=api_version)
        payload = _validate_page_response(response, expected_url=url, label="check-runs")
        if not isinstance(payload, Mapping) or not isinstance(payload.get("check_runs"), list):
            raise ValueError("check-runs payload is malformed")
        page_items = payload["check_runs"]
        if total_count is None:
            observed_total = payload.get("total_count")
            if not isinstance(observed_total, int) or observed_total < 0:
                raise ValueError("check-runs total_count is missing or invalid")
            total_count = observed_total
        check_pages.append(response)
        check_runs.extend(page_items)
        if len(check_runs) >= total_count:
            break
        if len(page_items) < 100:
            raise ValueError("check-run listing is incomplete")
    else:
        raise ValueError("check-run listing exceeded pagination limit")
    if len(check_runs) != total_count:
        raise ValueError("check-run listing total_count mismatch")

    annotation_pages: dict[int, tuple[GitHubApiResponse, ...]] = {}
    seen_run_ids: set[int] = set()
    for run in check_runs:
        if not isinstance(run, Mapping):
            raise ValueError("check-run record is malformed")
        run_id = run.get("id")
        if not isinstance(run_id, int) or run_id <= 0 or run_id in seen_run_ids:
            raise ValueError("check-run id is missing, invalid, or duplicated")
        seen_run_ids.add(run_id)
        if run.get("head_sha") != reviewed_head_sha:
            raise ValueError("check-run is not bound to the exact reviewed Head")
        pages: list[GitHubApiResponse] = []
        for page in range(1, max_pages + 1):
            url = _annotations_page_url(base, run_id, page)
            response = fetcher(url, token=token, api_version=api_version)
            payload = _validate_page_response(response, expected_url=url, label=f"check-annotations:{run_id}")
            if not isinstance(payload, list):
                raise ValueError("check-annotation payload is malformed")
            pages.append(response)
            if len(payload) < 100:
                break
        else:
            raise ValueError("check-annotation pagination exceeded limit")
        annotation_pages[run_id] = tuple(pages)
    return MappingProxyType(
        {
            "check_runs": tuple(check_pages),
            "check_annotations_by_run": MappingProxyType(annotation_pages),
        }
    )


def _noncheck_sources(
    responses: Mapping[str, Any],
    *,
    target_repository: str,
    target_identity: object,
    pull_request: int,
    reviewed_head_sha: str,
) -> list[Mapping[str, Any]]:
    base = f"https://api.github.com/repos/{target_repository}"
    expected = {
        "review_comments": f"{base}/pulls/{pull_request}/comments?per_page=100",
        "review_threads": f"{base}/pulls/{pull_request}/threads?per_page=100",
        "reviews": f"{base}/pulls/{pull_request}/reviews?per_page=100",
        "issue_comments": f"{base}/issues/{pull_request}/comments?per_page=100",
        "check_summaries": f"{base}/commits/{reviewed_head_sha}/status",
    }
    type_map = {
        "review_comments": ("github_pr_review_comment", "review_comment"),
        "review_threads": ("github_inline_review_thread", "review_thread"),
        "reviews": ("github_bot_comment", "review_submission"),
        "issue_comments": ("github_issue_comment", "issue_comment"),
        "check_summaries": ("github_check_summary", "check_summary"),
    }
    sources: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for key, url in expected.items():
        response = responses.get(key)
        if not isinstance(response, GitHubApiResponse):
            raise ValueError(f"required review surface {key} was not fetched")
        payload = _validate_page_response(response, expected_url=url, label=key)
        if key == "check_summaries":
            items = payload.get("statuses", []) if isinstance(payload, Mapping) else None
        else:
            items = payload
        if not isinstance(items, list) or len(items) >= 100:
            raise ValueError(f"{key} payload is malformed or pagination is incomplete")
        for item in items:
            if not isinstance(item, Mapping):
                raise ValueError(f"{key} review surface item is malformed")
            author = item.get("user") or item.get("app") or {}
            login = None
            actor_type = None
            if isinstance(author, Mapping):
                login = author.get("login") or author.get("slug")
                actor_type = author.get("type")
            is_bot = actor_type in {"Bot", "App"} or bool(item.get("app"))
            if not is_bot:
                continue
            stable_id = item.get("node_id") or item.get("id")
            if stable_id is None:
                raise ValueError("review surface source identity is missing")
            source_type, object_type = type_map[key]
            source_key = f"{key}:{stable_id}"
            if source_key in seen:
                raise ValueError("duplicate review surface source identity")
            seen.add(source_key)
            sources.append(
                {
                    "github_source_key": source_key,
                    "github_object_type": object_type,
                    "github_object_id": str(stable_id),
                    "target_repository_id": target_identity.repository_id,
                    "pr_number": pull_request,
                    "reviewed_head_sha": reviewed_head_sha,
                    "receipt_id": response.receipt_id,
                    "triage_disposition": "inspected_no_action",
                    "inspected": False,
                    "source_type": source_type,
                    "author": login or "unknown-bot",
                    "is_bot": True,
                    "url": item.get("html_url") or item.get("target_url"),
                    "content_sha256": _base.bytes_sha256(
                        json.dumps(item, sort_keys=True, separators=(",", ":")).encode()
                    ),
                }
            )
    return sources


def _check_annotation_sources(
    responses: Mapping[str, Any],
    *,
    target_repository: str,
    target_identity: object,
    pull_request: int,
    reviewed_head_sha: str,
) -> list[Mapping[str, Any]]:
    base = f"https://api.github.com/repos/{target_repository}"
    check_pages = _response_pages(responses.get("check_runs"), "check-runs")
    runs: dict[int, Mapping[str, Any]] = {}
    total_count: int | None = None
    collected = 0
    for page_number, response in enumerate(check_pages, start=1):
        expected = _check_runs_page_url(base, reviewed_head_sha, page_number)
        legacy = f"{base}/commits/{reviewed_head_sha}/check-runs?per_page=100" if page_number == 1 else None
        payload = _validate_page_response(
            response,
            expected_url=expected,
            allow_legacy_first_page_url=legacy,
            label="check-runs",
        )
        if not isinstance(payload, Mapping) or not isinstance(payload.get("check_runs"), list):
            raise ValueError("check-runs payload is malformed")
        if total_count is None:
            observed_total = payload.get("total_count")
            if isinstance(observed_total, int) and observed_total >= 0:
                total_count = observed_total
        items = payload["check_runs"]
        collected += len(items)
        for run in items:
            if not isinstance(run, Mapping):
                raise ValueError("check-run record is malformed")
            run_id = run.get("id")
            if not isinstance(run_id, int) or run_id <= 0 or run_id in runs:
                raise ValueError("check-run id is missing, invalid, or duplicated")
            if run.get("head_sha") != reviewed_head_sha:
                raise ValueError("check-run is not bound to the exact reviewed Head")
            runs[run_id] = run
    if total_count is not None and collected != total_count:
        raise ValueError("check-run listing is incomplete")
    if total_count is None and len(github_response_payload(check_pages[-1]).get("check_runs", [])) >= 100:
        raise ValueError("check-run listing pagination is incomplete")

    by_run = responses.get("check_annotations_by_run")
    if not isinstance(by_run, Mapping):
        if runs:
            raise ValueError("per-check-run annotation responses are required")
        return []
    if set(by_run) != set(runs):
        raise ValueError("annotation response set does not match check-run identities")

    sources: list[Mapping[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for run_id in sorted(runs):
        run = runs[run_id]
        pages = _response_pages(by_run[run_id], f"check-annotations:{run_id}")
        app = run.get("app") or {}
        check_name = run.get("name") if isinstance(run.get("name"), str) else "unnamed-check"
        check_app_id = app.get("id") if isinstance(app, Mapping) and isinstance(app.get("id"), int) else None
        author = None
        if isinstance(app, Mapping):
            author = app.get("slug") or app.get("name")
        for page_number, response in enumerate(pages, start=1):
            expected = _annotations_page_url(base, run_id, page_number)
            legacy = f"{base}/check-runs/{run_id}/annotations?per_page=100" if page_number == 1 else None
            payload = _validate_page_response(
                response,
                expected_url=expected,
                allow_legacy_first_page_url=legacy,
                label=f"check-annotations:{run_id}",
            )
            if not isinstance(payload, list):
                raise ValueError("check-annotation payload is malformed")
            if page_number == len(pages) and len(payload) >= 100:
                raise ValueError("check-annotation pagination is incomplete")
            for annotation in payload:
                if not isinstance(annotation, Mapping):
                    raise ValueError("check-annotation record is malformed")
                identity = {
                    "check_run_id": run_id,
                    "check_name": check_name,
                    "check_app_id": check_app_id,
                    "annotation_path": annotation.get("path"),
                    "annotation_start_line": annotation.get("start_line"),
                    "annotation_end_line": annotation.get("end_line"),
                    "annotation_level": annotation.get("annotation_level"),
                    "reviewed_head_sha": reviewed_head_sha,
                    "source_url": annotation.get("blob_href") or run.get("html_url") or run.get("details_url"),
                }
                if not isinstance(identity["annotation_level"], str) or not identity["annotation_level"]:
                    raise ValueError("check-annotation level is missing")
                dedupe_key = (
                    run_id,
                    annotation.get("path"),
                    annotation.get("start_line"),
                    annotation.get("end_line"),
                    annotation.get("annotation_level"),
                    annotation.get("message"),
                    annotation.get("title"),
                    annotation.get("raw_details"),
                )
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                identity_json = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                digest = hashlib.sha256(
                    json.dumps(
                        {"identity": identity, "annotation": annotation},
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest()
                sources.append(
                    {
                        "github_source_key": f"check_annotations:{run_id}:{digest}",
                        "github_object_type": "check_annotation",
                        "github_object_id": identity_json,
                        "target_repository_id": target_identity.repository_id,
                        "pr_number": pull_request,
                        "reviewed_head_sha": reviewed_head_sha,
                        "receipt_id": response.receipt_id,
                        "triage_disposition": "inspected_no_action",
                        "inspected": False,
                        "source_type": "github_check_annotation",
                        "author": author or check_name,
                        "is_bot": True,
                        "url": identity["source_url"],
                        "content_sha256": digest,
                    }
                )
    return sources


def verify_review_surface_inventory_responses(
    responses: Mapping[str, Any],
    *,
    target_repository: str,
    target_identity: object,
    pull_request: int,
    reviewed_head_sha: str,
) -> object:
    if not isinstance(target_identity, _base.VerifiedTargetIdentity):
        raise ValueError("sealed target identity is required for review surface inventory")
    if target_identity._token is not _base._TARGET_TOKEN:
        raise ValueError("sealed target identity is required for review surface inventory")
    if target_identity.repository != target_repository:
        raise ValueError("sealed target identity does not match repository")
    _require_sha40(reviewed_head_sha, "reviewed_head_sha")
    required = {
        "review_comments",
        "review_threads",
        "reviews",
        "issue_comments",
        "check_runs",
        "check_summaries",
    }
    missing = required - set(responses)
    if missing:
        raise ValueError("review surface inventory endpoints are incomplete")
    sources = _noncheck_sources(
        responses,
        target_repository=target_repository,
        target_identity=target_identity,
        pull_request=pull_request,
        reviewed_head_sha=reviewed_head_sha,
    )
    sources.extend(
        _check_annotation_sources(
            responses,
            target_repository=target_repository,
            target_identity=target_identity,
            pull_request=pull_request,
            reviewed_head_sha=reviewed_head_sha,
        )
    )
    sources.sort(key=lambda item: item["github_source_key"])
    normalized: list[Mapping[str, Any]] = []
    for index, source in enumerate(sources, start=1):
        item = dict(source)
        item["source_id"] = f"EXTSRC-{index:03d}"
        normalized.append(MappingProxyType(item))
    return _base.VerifiedReviewSurfaceInventory(
        _base._SURFACE_TOKEN,
        target_repository,
        target_identity.repository_id,
        pull_request,
        reviewed_head_sha,
        tuple(normalized),
        True,
    )
