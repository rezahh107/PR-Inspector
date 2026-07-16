from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from types import MappingProxyType
from typing import Any

from . import candidate_v1_11_base as _base
from . import candidate_v1_11_repair as _repair
from ._governance_transport import GitHubApiResponse, github_response_payload


def _bundle_reference_integrity(bundle: object) -> tuple[bool, str | None]:
    if not _base.is_verified_minimal_review_bundle(bundle):
        return False, "verified_minimal_review_required"
    try:
        artifacts = bundle.artifact_bytes
        if not isinstance(artifacts, Mapping):
            return False, "artifact_bytes_required"
        package_raw = artifacts.get("review-package.json")
        if not isinstance(package_raw, bytes):
            return False, "incomplete_artifact_bundle"
        package = _base._json_object("review-package.json", package_raw)
        identity = package.get("review_identity")
        if not isinstance(identity, Mapping):
            return False, "review_identity_malformed"
        return _repair._bundle_reference_integrity(bundle)
    except (AttributeError, KeyError, TypeError, ValueError):
        return False, "artifact_integrity_invalid"


def verify_base_review_reference(
    evidence: object,
    live_head_sha: str,
    *,
    target_repository: str | None = None,
    target_repository_id: int | None = None,
    pull_request: int | None = None,
) -> dict[str, Any]:
    valid, reason = _bundle_reference_integrity(evidence)
    if not valid:
        return {"status": "INVALID", "reason": reason}
    return _base.verify_base_review_reference(
        evidence,
        live_head_sha,
        target_repository=target_repository,
        target_repository_id=target_repository_id,
        pull_request=pull_request,
    )


def _target_from_verified_bundle(bundle: object) -> dict[str, Any] | None:
    valid, _ = _bundle_reference_integrity(bundle)
    if not valid:
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

    if profile == _base.STRICT and url is None and isinstance(context, Mapping):
        bundle = context.get("verified_minimal_review")
        target = _target_from_verified_bundle(bundle)
        live_head = context.get("live_head_sha")
        supplied = context.get("current_target")
        supplied_consistent = supplied is None or (
            isinstance(supplied, Mapping)
            and target is not None
            and supplied.get("repository") == target["repository"]
            and supplied.get("repository_id") == target["repository_id"]
            and supplied.get("pull_request") == target["pull_request"]
        )
        if target and isinstance(live_head, str) and _base.SHA40_RE.fullmatch(live_head):
            status = verify_base_review_reference(
                bundle,
                live_head,
                target_repository=target["repository"],
                target_repository_id=target["repository_id"],
                pull_request=target["pull_request"],
            )
            if status.get("status") == "STALE":
                return {
                    "inspection_profile": _base.STRICT,
                    "target": target,
                    "reuse_current_minimal": False,
                    "refresh_minimal": True,
                    "orchestration_state": "head_drift_refresh_required",
                    "missing": [],
                }
            if status.get("status") == "VERIFIED" and supplied_consistent:
                return {
                    "inspection_profile": _base.STRICT,
                    "target": target,
                    "reuse_current_minimal": True,
                    "refresh_minimal": False,
                    "orchestration_state": "same_head_reuse",
                    "missing": [],
                }
            if status.get("status") == "VERIFIED":
                return {
                    "inspection_profile": _base.STRICT,
                    "target": target,
                    "reuse_current_minimal": False,
                    "refresh_minimal": False,
                    "orchestration_state": None,
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
) -> _repair.VerifiedPullRequestHead:
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
    head = payload.get("head")
    if not isinstance(head, Mapping):
        raise ValueError("pull request head is missing or invalid")
    head_sha = head.get("sha")
    if not isinstance(head_sha, str) or not _base.SHA40_RE.fullmatch(head_sha):
        raise ValueError("pull request head must be a 40-character lowercase SHA")
    return _repair.VerifiedPullRequestHead(
        _repair._HEAD_TOKEN,
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
) -> _repair.StrictOrchestrationResult:
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
        strict_result = continue_strict(previous_minimal, target_identity, target["pull_request"], head.head_sha)
        return _repair.StrictOrchestrationResult(
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
        strict_result = continue_strict(refreshed, target_identity, target["pull_request"], head.head_sha)
        return _repair.StrictOrchestrationResult(
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
        return _repair.StrictOrchestrationResult(
            "refresh_failed",
            tuple(history),
            MappingProxyType(target),
            head.head_sha,
            None,
            None,
            str(exc),
        )


def _validate_annotation_payloads(responses: Mapping[str, Any]) -> None:
    by_run = responses.get("check_annotations_by_run")
    if by_run is None:
        return
    if not isinstance(by_run, Mapping):
        raise ValueError("per-check-run annotation responses are malformed")
    for run_id, raw_pages in by_run.items():
        if not isinstance(run_id, int) or run_id <= 0:
            raise ValueError("check-run id is missing or invalid")
        pages = (raw_pages,) if isinstance(raw_pages, GitHubApiResponse) else raw_pages
        if not isinstance(pages, Sequence) or isinstance(pages, (str, bytes)):
            raise ValueError("check-annotation response pages are malformed")
        for response in pages:
            if not isinstance(response, GitHubApiResponse):
                raise ValueError("check-annotation response is not a sealed receipt")
            payload = github_response_payload(response)
            if not isinstance(payload, list):
                raise ValueError("check-annotation payload is malformed")
            for annotation in payload:
                if not isinstance(annotation, Mapping):
                    raise ValueError("check-annotation record is malformed")
                path = annotation.get("path")
                start_line = annotation.get("start_line")
                end_line = annotation.get("end_line")
                level = annotation.get("annotation_level")
                if path is not None and (not isinstance(path, str) or not path):
                    raise ValueError("check-annotation path is invalid")
                if start_line is not None and (not isinstance(start_line, int) or isinstance(start_line, bool)):
                    raise ValueError("check-annotation start_line is invalid")
                if end_line is not None and (not isinstance(end_line, int) or isinstance(end_line, bool)):
                    raise ValueError("check-annotation end_line is invalid")
                if isinstance(start_line, int) and isinstance(end_line, int) and end_line < start_line:
                    raise ValueError("check-annotation line range is invalid")
                if not isinstance(level, str) or not level:
                    raise ValueError("check-annotation level is missing or invalid")


def verify_review_surface_inventory_responses(
    responses: Mapping[str, Any],
    *,
    target_repository: str,
    target_identity: object,
    pull_request: int,
    reviewed_head_sha: str,
) -> object:
    if not isinstance(responses, Mapping):
        raise ValueError("review surface responses must be a mapping")
    _validate_annotation_payloads(responses)
    return _repair.verify_review_surface_inventory_responses(
        responses,
        target_repository=target_repository,
        target_identity=target_identity,
        pull_request=pull_request,
        reviewed_head_sha=reviewed_head_sha,
    )
