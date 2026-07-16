from __future__ import annotations

import json
from types import MappingProxyType
from typing import Any, Callable, Mapping

from .candidate_v1_11_base import *  # noqa: F401,F403
from .candidate_v1_11_base import (
    _TARGET_TOKEN,
    _json_object,
    verify_base_review_reference as _base_verify_base_review_reference,
)
from .candidate_v1_11_repair import (
    ORCHESTRATION_STATES,
    StrictOrchestrationResult,
    VerifiedPullRequestHead,
    verify_pull_request_head_response,
)


def _verified_target_from_bundle(bundle: object) -> dict[str, Any] | None:
    if not is_verified_minimal_review_bundle(bundle):
        return None
    reference = bundle.reference
    if bundle.inspector_commit.repository != LOCKED_INSPECTOR_REPOSITORY:
        return None
    if bundle.inspector_commit.repository_id != LOCKED_INSPECTOR_REPOSITORY_ID:
        return None
    if bundle.inspector_commit.commit_sha != reference.get("inspector_commit_sha"):
        return None
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


def _reference_hashes_are_current(bundle: object) -> tuple[bool, str | None]:
    if not is_verified_minimal_review_bundle(bundle):
        return False, "verified_minimal_review_required"
    artifacts = bundle.artifact_bytes
    if not isinstance(artifacts, Mapping):
        return False, "artifact_bytes_required"
    required = {
        "review-package.json",
        "DECISION_PROJECTION.json",
        "artifact-manifest.json",
    }
    if required - set(artifacts):
        return False, "incomplete_artifact_bundle"
    try:
        package_raw = artifacts["review-package.json"]
        projection_raw = artifacts["DECISION_PROJECTION.json"]
        manifest_raw = artifacts["artifact-manifest.json"]
        if not all(isinstance(raw, bytes) for raw in (package_raw, projection_raw, manifest_raw)):
            return False, "artifact_bytes_required"
        package = _json_object("review-package.json", package_raw)
        _json_object("DECISION_PROJECTION.json", projection_raw)
        _json_object("artifact-manifest.json", manifest_raw)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False, "artifact_integrity_invalid"
    reference = bundle.reference
    if reference.get("review_package_sha256") != canonical_sha256(package):
        return False, "review_package_hash_mismatch"
    if reference.get("decision_projection_sha256") != bytes_sha256(projection_raw):
        return False, "decision_projection_hash_mismatch"
    if reference.get("artifact_manifest_sha256") != bytes_sha256(manifest_raw):
        return False, "artifact_manifest_hash_mismatch"
    return True, None


def verify_base_review_reference(
    evidence: object,
    live_head_sha: str,
    *,
    target_repository: str | None = None,
    target_repository_id: int | None = None,
    pull_request: int | None = None,
) -> dict[str, Any]:
    valid, reason = _reference_hashes_are_current(evidence)
    if not valid:
        return {"status": "INVALID", "reason": reason}
    return _base_verify_base_review_reference(
        evidence,
        live_head_sha,
        target_repository=target_repository,
        target_repository_id=target_repository_id,
        pull_request=pull_request,
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
    if profile == STRICT and url is None and context:
        bundle = context.get("verified_minimal_review")
        target = _verified_target_from_bundle(bundle)
        live_head = context.get("live_head_sha")
        supplied = context.get("current_target")
        if supplied is not None:
            consistent = (
                isinstance(supplied, dict)
                and target is not None
                and supplied.get("repository") == target["repository"]
                and supplied.get("repository_id") == target["repository_id"]
                and supplied.get("pull_request") == target["pull_request"]
            )
            if not consistent:
                target = None
        if target and isinstance(live_head, str) and SHA40_RE.fullmatch(live_head):
            status = verify_base_review_reference(
                bundle,
                live_head,
                target_repository=target["repository"],
                target_repository_id=target["repository_id"],
                pull_request=target["pull_request"],
            )
            if status.get("status") == "VERIFIED":
                return {
                    "inspection_profile": STRICT,
                    "target": target,
                    "reuse_current_minimal": True,
                    "refresh_minimal": False,
                    "orchestration_state": "same_head_reuse",
                    "missing": [],
                }
            if status.get("status") == "STALE":
                return {
                    "inspection_profile": STRICT,
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
    match = PR_URL_RE.match(url)
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


def orchestrate_strict_review(
    *,
    previous_minimal: object,
    target_identity: object,
    pull_request_response: object,
    refresh_minimal: Callable[[object, int, str], object],
    continue_strict: Callable[[object, object, int, str], object],
) -> StrictOrchestrationResult:
    target = _verified_target_from_bundle(previous_minimal)
    if target is None:
        raise ValueError("verified previous Minimal review is required")
    if not isinstance(target_identity, VerifiedTargetIdentity) or target_identity._token is not _TARGET_TOKEN:
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
        strict_result = continue_strict(refreshed, target_identity, target["pull_request"], head.head_sha)
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
