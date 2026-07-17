"""Bounded compatibility surface for the former v1.11 Candidate module.

The Candidate rollout is not an output authority. This module retains only
minimal/strict intake and verified-Minimal Head-drift routing. After a
canonical review package exists, callers must use ``pr_inspector.official_review``.
"""
from __future__ import annotations

import hashlib
import json
import re
import weakref
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable

from ._governance_transport import (
    GitHubApiResponse,
    github_response_payload,
    is_verified_github_api_response,
)
from .official_review import (
    CompletionError,
    VerifiedReviewCompletion,
    is_verified_review_completion,
    official_owner_delivery,
    official_owner_profile_commands,
)
from .review_provenance import (
    ProvenanceError,
    VerifiedInspectorCommit,
    is_verified_inspector_commit,
    trust_policy,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
PR_URL_RE = re.compile(r"https://github\.com/([^/\s]+/[^/\s]+)/pull/(\d+)")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
MINIMAL = "minimal"
STRICT = "strict"
_TARGET_TOKEN = object()
_REFRESH_TOKEN = object()
_MINIMAL_REFERENCE_TOKEN = object()


class CandidateOutputMigrationError(RuntimeError):
    """Legacy Candidate output calls are unsupported after v1.11.1 activation."""


@dataclass(frozen=True)
class VerifiedTargetIdentity:
    _token: object
    repository: str
    repository_id: int


@dataclass(frozen=True)
class VerifiedLivePrHead:
    _token: object
    repository: str
    repository_id: int
    pull_request: int
    head_sha: str
    receipt_id: str


class VerifiedMinimalReviewReference:
    """Opaque, verifier-created capability for reusing one Minimal review."""

    __slots__ = (
        "_token",
        "target_repository",
        "target_repository_id",
        "pull_request",
        "reviewed_head_sha",
        "protocol_version",
        "inspector_repository",
        "inspector_repository_id",
        "inspector_commit_sha",
        "review_package_canonical_sha256",
        "review_package_file_sha256",
        "decision_projection_sha256",
        "artifact_manifest_sha256",
        "__weakref__",
    )

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError(
            "VerifiedMinimalReviewReference can only be created from "
            "verified official review provenance"
        )

    def __setattr__(self, _name: str, _value: object) -> None:
        raise AttributeError("VerifiedMinimalReviewReference is immutable")


@dataclass(frozen=True)
class _MinimalReferenceProof:
    fingerprint: tuple[Any, ...]
    completion: VerifiedReviewCompletion
    target_identity: VerifiedTargetIdentity
    inspector_commit: VerifiedInspectorCommit


_MINIMAL_REFERENCE_PROOFS: weakref.WeakKeyDictionary[
    VerifiedMinimalReviewReference, _MinimalReferenceProof
] = weakref.WeakKeyDictionary()


@dataclass(frozen=True)
class MinimalRefreshResult:
    _token: object
    state: str
    target: Mapping[str, Any]
    live_head_sha: str
    reference: VerifiedMinimalReviewReference | None
    reason: str | None = None


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _migration_error(symbol: str) -> CandidateOutputMigrationError:
    return CandidateOutputMigrationError(
        f"{symbol} is not an output authority in {PROTOCOL_VERSION}; "
        "use complete_review/verify_completed_review and official_owner_delivery"
    )


def _require_operational_response(
    response: GitHubApiResponse, label: str
) -> Mapping[str, Any]:
    if not is_verified_github_api_response(response):
        raise ValueError(f"{label} is not a sealed GitHub API response receipt")
    if getattr(response, "transport_origin", None) != "github_https":
        raise ValueError(
            f"{label} is not from the operational GitHub HTTPS adapter"
        )
    payload = github_response_payload(response)
    if not isinstance(payload, Mapping):
        raise ValueError(f"{label} payload is malformed")
    return payload


def verify_target_identity_response(
    response: GitHubApiResponse, *, expected_repository: str
) -> VerifiedTargetIdentity:
    payload = _require_operational_response(response, "target repository response")
    expected = f"https://api.github.com/repos/{expected_repository}"
    if (
        response.request_url != expected
        or response.response_url != expected
        or response.status_code != 200
    ):
        raise ValueError("target repository response is not authoritative")
    repository_id = payload.get("id")
    if (
        payload.get("full_name") != expected_repository
        or payload.get("url") != expected
        or payload.get("html_url")
        != f"https://github.com/{expected_repository}"
        or not isinstance(repository_id, int)
        or isinstance(repository_id, bool)
        or repository_id <= 0
    ):
        raise ValueError("target repository identity mismatch")
    return VerifiedTargetIdentity(_TARGET_TOKEN, expected_repository, repository_id)


def verify_live_pr_head_response(
    response: GitHubApiResponse,
    *,
    target_repository: str,
    target_repository_id: int,
    pull_request: int,
) -> VerifiedLivePrHead:
    payload = _require_operational_response(response, "live PR response")
    expected = (
        f"https://api.github.com/repos/{target_repository}/pulls/{pull_request}"
    )
    if (
        response.request_url != expected
        or response.response_url != expected
        or response.status_code != 200
    ):
        raise ValueError("live PR response is not authoritative")
    base = payload.get("base")
    repository = base.get("repo") if isinstance(base, Mapping) else None
    head = payload.get("head")
    head_sha = head.get("sha") if isinstance(head, Mapping) else None
    if payload.get("number") != pull_request or not isinstance(
        repository, Mapping
    ):
        raise ValueError("live PR identity is malformed")
    if (
        repository.get("full_name") != target_repository
        or repository.get("id") != target_repository_id
    ):
        raise ValueError("live PR repository identity mismatch")
    if not isinstance(head_sha, str) or SHA40_RE.fullmatch(head_sha) is None:
        raise ValueError("live PR Head SHA is malformed")
    return VerifiedLivePrHead(
        _TARGET_TOKEN,
        target_repository,
        target_repository_id,
        pull_request,
        head_sha,
        response.receipt_id,
    )


def _reference_fingerprint(
    reference: VerifiedMinimalReviewReference,
) -> tuple[Any, ...]:
    return (
        reference.target_repository,
        reference.target_repository_id,
        reference.pull_request,
        reference.reviewed_head_sha,
        reference.protocol_version,
        reference.inspector_repository,
        reference.inspector_repository_id,
        reference.inspector_commit_sha,
        reference.review_package_canonical_sha256,
        reference.review_package_file_sha256,
        reference.decision_projection_sha256,
        reference.artifact_manifest_sha256,
    )


def _is_verified_minimal_reference(value: object) -> bool:
    if not isinstance(value, VerifiedMinimalReviewReference):
        return False
    if getattr(value, "_token", None) is not _MINIMAL_REFERENCE_TOKEN:
        return False
    proof = _MINIMAL_REFERENCE_PROOFS.get(value)
    return proof is not None and proof.fingerprint == _reference_fingerprint(value)


def _completion_reference_fields(
    completion: VerifiedReviewCompletion,
    *,
    target_identity: VerifiedTargetIdentity,
    inspector_commit: VerifiedInspectorCommit,
) -> dict[str, Any]:
    if not is_verified_review_completion(completion):
        raise ValueError("verified official review completion is required")
    if (
        not isinstance(target_identity, VerifiedTargetIdentity)
        or target_identity._token is not _TARGET_TOKEN
    ):
        raise ValueError("verified target repository identity is required")
    if not is_verified_inspector_commit(inspector_commit):
        raise ValueError("verified Inspector commit identity is required")

    try:
        bundle = completion._reverify()
        package_bytes = bundle.artifact_bytes["review-package.json"]
        package = json.loads(package_bytes.decode("utf-8"))
        projection = completion.decision_projection()
    except (
        CompletionError,
        KeyError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ProvenanceError(
            f"cannot reverify official Minimal completion: {exc}"
        ) from exc
    if not isinstance(package, dict):
        raise ProvenanceError("verified review package must be a JSON object")
    if projection.get("inspection_profile") != MINIMAL:
        raise ValueError("official completion is not a minimal review")

    identity = package.get("review_identity")
    if not isinstance(identity, Mapping):
        raise ProvenanceError("verified review identity is malformed")
    policy = trust_policy()
    fields = {
        "target_repository": completion.target_repository,
        "target_repository_id": target_identity.repository_id,
        "pull_request": completion.pr_number,
        "reviewed_head_sha": completion.reviewed_head_sha,
        "protocol_version": completion.protocol_version,
        "inspector_repository": inspector_commit.repository,
        "inspector_repository_id": inspector_commit.repository_id,
        "inspector_commit_sha": inspector_commit.commit_sha,
        "review_package_canonical_sha256": (
            completion.review_package_canonical_sha256
        ),
        "review_package_file_sha256": completion.review_package_file_sha256,
        "decision_projection_sha256": completion.decision_projection_sha256,
        "artifact_manifest_sha256": completion.artifact_manifest_sha256,
    }

    if completion.protocol_version != PROTOCOL_VERSION:
        raise ProvenanceError("minimal review protocol version is not active")
    if (
        target_identity.repository != completion.target_repository
        or identity.get("target_repository") != completion.target_repository
        or identity.get("target_repository_id") != target_identity.repository_id
        or identity.get("pr_number") != completion.pr_number
        or identity.get("reviewed_head_sha") != completion.reviewed_head_sha
    ):
        raise ProvenanceError("minimal review target identity is not verified")
    if (
        policy.get("inspector_repository") != inspector_commit.repository
        or policy.get("inspector_repository_id") != inspector_commit.repository_id
        or identity.get("inspector_repository") != inspector_commit.repository
        or identity.get("inspector_commit_sha") != inspector_commit.commit_sha
    ):
        raise ProvenanceError("minimal review Inspector identity is not verified")

    actual_bundle = (
        bundle.protocol_version,
        bundle.repository,
        bundle.pr_number,
        bundle.head_sha,
        bundle.package_canonical_sha256,
        bundle.package_file_sha256,
        bundle.projection_sha256,
        bundle.manifest_sha256,
        bytes_sha256(package_bytes),
    )
    expected_bundle = (
        completion.protocol_version,
        completion.target_repository,
        completion.pr_number,
        completion.reviewed_head_sha,
        completion.review_package_canonical_sha256,
        completion.review_package_file_sha256,
        completion.decision_projection_sha256,
        completion.artifact_manifest_sha256,
        completion.review_package_file_sha256,
    )
    if actual_bundle != expected_bundle:
        raise ProvenanceError("minimal review artifact provenance does not match")

    for name in (
        "reviewed_head_sha",
        "inspector_commit_sha",
    ):
        if SHA40_RE.fullmatch(str(fields[name])) is None:
            raise ProvenanceError(f"{name} is malformed")
    for name in (
        "review_package_canonical_sha256",
        "review_package_file_sha256",
        "decision_projection_sha256",
        "artifact_manifest_sha256",
    ):
        if re.fullmatch(r"[0-9a-f]{64}", str(fields[name])) is None:
            raise ProvenanceError(f"{name} is malformed")
    return fields


def _mint_minimal_reference(
    fields: Mapping[str, Any],
    *,
    completion: VerifiedReviewCompletion,
    target_identity: VerifiedTargetIdentity,
    inspector_commit: VerifiedInspectorCommit,
) -> VerifiedMinimalReviewReference:
    reference = object.__new__(VerifiedMinimalReviewReference)
    object.__setattr__(reference, "_token", _MINIMAL_REFERENCE_TOKEN)
    for name, value in fields.items():
        object.__setattr__(reference, name, value)
    fingerprint = _reference_fingerprint(reference)
    _MINIMAL_REFERENCE_PROOFS[reference] = _MinimalReferenceProof(
        fingerprint,
        completion,
        target_identity,
        inspector_commit,
    )
    return reference


def minimal_reference_from_official_completion(
    completion: VerifiedReviewCompletion,
    *,
    target_identity: VerifiedTargetIdentity,
    inspector_commit: VerifiedInspectorCommit,
) -> VerifiedMinimalReviewReference:
    fields = _completion_reference_fields(
        completion,
        target_identity=target_identity,
        inspector_commit=inspector_commit,
    )
    return _mint_minimal_reference(
        fields,
        completion=completion,
        target_identity=target_identity,
        inspector_commit=inspector_commit,
    )


def verify_base_review_reference(
    reference: object,
    live_head_sha: str,
    *,
    target_repository: str,
    target_repository_id: int,
    pull_request: int,
) -> dict[str, Any]:
    if not _is_verified_minimal_reference(reference):
        return {"status": "INVALID", "reason": "verified_minimal_review_required"}
    assert isinstance(reference, VerifiedMinimalReviewReference)

    policy = trust_policy()
    if reference.protocol_version != PROTOCOL_VERSION:
        return {"status": "INVALID", "reason": "protocol_version_mismatch"}
    if reference.inspector_repository != policy.get("inspector_repository"):
        return {"status": "INVALID", "reason": "inspector_repository_mismatch"}
    if reference.inspector_repository_id != policy.get("inspector_repository_id"):
        return {"status": "INVALID", "reason": "inspector_repository_id_mismatch"}
    if reference.target_repository != target_repository:
        return {"status": "INVALID", "reason": "target_repository_mismatch"}
    if reference.target_repository_id != target_repository_id:
        return {"status": "INVALID", "reason": "target_repository_id_mismatch"}
    if reference.pull_request != pull_request:
        return {"status": "INVALID", "reason": "pull_request_mismatch"}
    if reference.reviewed_head_sha != live_head_sha:
        return {
            "status": "STALE",
            "reason": "head_drift",
            "action": "rerun_minimal_then_strict",
        }

    proof = _MINIMAL_REFERENCE_PROOFS.get(reference)
    assert proof is not None
    try:
        current = _completion_reference_fields(
            proof.completion,
            target_identity=proof.target_identity,
            inspector_commit=proof.inspector_commit,
        )
    except (CompletionError, ProvenanceError, ValueError):
        return {"status": "INVALID", "reason": "minimal_review_provenance_invalid"}
    expected = {
        name: getattr(reference, name)
        for name in (
            "target_repository",
            "target_repository_id",
            "pull_request",
            "reviewed_head_sha",
            "protocol_version",
            "inspector_repository",
            "inspector_repository_id",
            "inspector_commit_sha",
            "review_package_canonical_sha256",
            "review_package_file_sha256",
            "decision_projection_sha256",
            "artifact_manifest_sha256",
        )
    }
    if current != expected:
        return {"status": "INVALID", "reason": "minimal_review_provenance_mismatch"}
    return {
        "status": "VERIFIED",
        "reason": "same_head",
        "action": "reuse_technical_decision",
    }


def orchestrate_strict_after_minimal(
    context: Mapping[str, Any],
    refresh_minimal_review: Callable[
        [Mapping[str, Any], str], VerifiedReviewCompletion
    ]
    | None = None,
) -> MinimalRefreshResult:
    reference = (
        context.get("verified_minimal_review")
        if isinstance(context, Mapping)
        else None
    )
    live = (
        context.get("verified_live_pr_head")
        if isinstance(context, Mapping)
        else None
    )
    if not _is_verified_minimal_reference(reference):
        return MinimalRefreshResult(
            _REFRESH_TOKEN,
            "refresh_failed",
            MappingProxyType({}),
            "",
            None,
            "verified_minimal_review_required",
        )
    assert isinstance(reference, VerifiedMinimalReviewReference)
    proof = _MINIMAL_REFERENCE_PROOFS.get(reference)
    assert proof is not None
    target = MappingProxyType(
        {
            "repository": reference.target_repository,
            "repository_id": reference.target_repository_id,
            "pull_request": reference.pull_request,
            "url": (
                f"https://github.com/{reference.target_repository}/pull/"
                f"{reference.pull_request}"
            ),
        }
    )
    if not isinstance(live, VerifiedLivePrHead) or live._token is not _TARGET_TOKEN:
        return MinimalRefreshResult(
            _REFRESH_TOKEN,
            "refresh_failed",
            target,
            "",
            None,
            "sealed_live_pr_head_required",
        )
    status = verify_base_review_reference(
        reference,
        live.head_sha,
        target_repository=live.repository,
        target_repository_id=live.repository_id,
        pull_request=live.pull_request,
    )
    if status["status"] == "VERIFIED":
        return MinimalRefreshResult(
            _REFRESH_TOKEN,
            "same_head_reuse",
            target,
            live.head_sha,
            reference,
        )
    if status["status"] != "STALE":
        return MinimalRefreshResult(
            _REFRESH_TOKEN,
            "refresh_failed",
            target,
            live.head_sha,
            None,
            status["reason"],
        )
    if refresh_minimal_review is None:
        return MinimalRefreshResult(
            _REFRESH_TOKEN,
            "head_drift_refresh_required",
            target,
            live.head_sha,
            None,
            "minimal_refresh_required",
        )

    refreshed_completion = refresh_minimal_review(target, live.head_sha)
    if not is_verified_review_completion(refreshed_completion):
        return MinimalRefreshResult(
            _REFRESH_TOKEN,
            "refresh_failed",
            target,
            live.head_sha,
            None,
            "verified_official_minimal_completion_required",
        )
    try:
        refreshed = minimal_reference_from_official_completion(
            refreshed_completion,
            target_identity=proof.target_identity,
            inspector_commit=proof.inspector_commit,
        )
    except (CompletionError, ProvenanceError, ValueError):
        return MinimalRefreshResult(
            _REFRESH_TOKEN,
            "refresh_failed",
            target,
            live.head_sha,
            None,
            "minimal_refresh_provenance_invalid",
        )
    verified = verify_base_review_reference(
        refreshed,
        live.head_sha,
        target_repository=live.repository,
        target_repository_id=live.repository_id,
        pull_request=live.pull_request,
    )
    if verified["status"] != "VERIFIED":
        return MinimalRefreshResult(
            _REFRESH_TOKEN,
            "refresh_failed",
            target,
            live.head_sha,
            None,
            verified["reason"],
        )
    return MinimalRefreshResult(
        _REFRESH_TOKEN,
        "refresh_verified",
        target,
        live.head_sha,
        refreshed,
    )


def parse_intake(
    text: str, context: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    if context is not None and not isinstance(context, Mapping):
        return {
            "inspection_profile": MINIMAL,
            "target": None,
            "reuse_current_minimal": False,
            "missing": ["valid_context"],
            "error": "context_malformed",
        }
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    profile = MINIMAL
    if lines and lines[0] == "حداقلی":
        lines = lines[1:]
    elif lines and lines[0] == "سخت گیرانه":
        profile = STRICT
        lines = lines[1:]
    url = next((line for line in lines if PR_URL_RE.fullmatch(line)), None)
    if profile == STRICT and url is None and context is not None:
        result = orchestrate_strict_after_minimal(
            context, context.get("refresh_minimal_review")
        )
        return {
            "inspection_profile": STRICT,
            "target": dict(result.target) if result.target else None,
            "reuse_current_minimal": result.state == "same_head_reuse",
            "minimal_refresh_state": result.state,
            "continue_strict": result.state
            in {"same_head_reuse", "refresh_verified"},
            "missing": [],
            **(
                {"error": result.reason}
                if result.state == "refresh_failed"
                else {}
            ),
        }
    if url is None:
        return {
            "inspection_profile": profile,
            "target": None,
            "reuse_current_minimal": False,
            "missing": ["pull_request_url"],
        }
    match = PR_URL_RE.fullmatch(url)
    assert match is not None
    return {
        "inspection_profile": profile,
        "target": {
            "repository": match.group(1),
            "pull_request": int(match.group(2)),
            "url": url,
        },
        "reuse_current_minimal": False,
        "missing": [],
    }


# Legacy Candidate output entrypoints remain only to fail closed deterministically.
def project_decision(*args: Any, **kwargs: Any) -> Any:
    raise _migration_error("candidate_v1_11.project_decision")


def render_candidate_owner_result(*args: Any, **kwargs: Any) -> bytes:
    raise _migration_error("render_candidate_owner_result")


def render_candidate_owner_card(*args: Any, **kwargs: Any) -> bytes:
    raise _migration_error("render_candidate_owner_card")


def render_candidate_technical_handoff(*args: Any, **kwargs: Any) -> bytes:
    raise _migration_error("render_candidate_technical_handoff")


def render_candidate_next_action_prompt(*args: Any, **kwargs: Any) -> bytes:
    raise _migration_error("render_candidate_next_action_prompt")


def build_candidate_review_artifacts(*args: Any, **kwargs: Any) -> Mapping[str, bytes]:
    raise _migration_error("build_candidate_review_artifacts")


def verify_candidate_review_artifact_bytes(*args: Any, **kwargs: Any) -> Any:
    raise _migration_error("verify_candidate_review_artifact_bytes")


def verify_minimal_review_artifact_bytes(*args: Any, **kwargs: Any) -> Any:
    raise _migration_error("verify_minimal_review_artifact_bytes")


def build_candidate_owner_delivery_artifacts(*args: Any, **kwargs: Any) -> Mapping[str, bytes]:
    raise _migration_error("build_candidate_owner_delivery_artifacts")


def candidate_owner_delivery_stdout(
    completion: VerifiedReviewCompletion,
    *,
    live_head_sha: str | None = None,
) -> bytes:
    if not is_verified_review_completion(completion):
        raise _migration_error("candidate_owner_delivery_stdout")
    if (
        live_head_sha is not None
        and completion.reviewed_head_sha != live_head_sha
    ):
        raise ValueError("verified completion does not match live Head")
    return official_owner_delivery(completion).encode("utf-8")


def render_owner_profile_commands(
    completion: VerifiedReviewCompletion,
) -> bytes:
    if not is_verified_review_completion(completion):
        raise _migration_error("render_owner_profile_commands")
    return official_owner_profile_commands(completion).encode("utf-8")


__all__ = [
    "CandidateOutputMigrationError",
    "MINIMAL",
    "MinimalRefreshResult",
    "PROTOCOL_VERSION",
    "STRICT",
    "VerifiedLivePrHead",
    "VerifiedMinimalReviewReference",
    "VerifiedTargetIdentity",
    "bytes_sha256",
    "candidate_owner_delivery_stdout",
    "canonical_sha256",
    "minimal_reference_from_official_completion",
    "orchestrate_strict_after_minimal",
    "parse_intake",
    "render_owner_profile_commands",
    "verify_base_review_reference",
    "verify_live_pr_head_response",
    "verify_target_identity_response",
]
