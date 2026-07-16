"""Hardened private implementation boundary for the active v1.11 runtime.

The unchanged implementation body lives in ``_runtime_v1_11_core``. This
module owns fail-closed hardening and is safe for legacy private imports.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from types import MappingProxyType
from typing import Any

from . import _runtime_v1_11_core as _impl


def _validate_annotation_metadata(ann: Mapping[str, Any]) -> None:
    annotation_id = ann.get("id")
    if annotation_id is not None and (
        not isinstance(annotation_id, int)
        or isinstance(annotation_id, bool)
        or annotation_id <= 0
    ):
        raise ValueError("check annotation id is malformed")

    path = ann.get("path")
    if path is not None and (not isinstance(path, str) or not path):
        raise ValueError("check annotation path is malformed")

    start_line = ann.get("start_line")
    end_line = ann.get("end_line")
    for name, value in (("start_line", start_line), ("end_line", end_line)):
        if value is not None and (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value <= 0
        ):
            raise ValueError(f"check annotation {name} is malformed")
    if start_line is not None and end_line is not None and end_line < start_line:
        raise ValueError("check annotation line range is malformed")

    level = ann.get("annotation_level")
    if not isinstance(level, str) or not level:
        raise ValueError("check annotation level is malformed")


_original_classify_governance = _impl.classify_governance


def classify_governance(
    evidence: object,
    *,
    target_repository: str | None = None,
    target_repository_id: int | None = None,
    pull_request: int | None = None,
    reviewed_head_sha: str | None = None,
) -> dict[str, Any]:
    """Treat every absent required governance fact as an explicit gap."""

    if _impl.is_verified_governance_capability(evidence):
        missing = _impl.REQUIRED_GOVERNANCE_FACTS - set(evidence.facts)
        if missing:
            facts = dict(evidence.facts)
            facts.update({field: False for field in missing})
            evidence = replace(evidence, facts=MappingProxyType(facts))
    return _original_classify_governance(
        evidence,
        target_repository=target_repository,
        target_repository_id=target_repository_id,
        pull_request=pull_request,
        reviewed_head_sha=reviewed_head_sha,
    )


_original_verify_candidate_review_artifact_bytes = (
    _impl.verify_candidate_review_artifact_bytes
)


def verify_candidate_review_artifact_bytes(
    artifact_bytes: Mapping[str, bytes],
    inspector_commit: _impl.VerifiedInspectorCommit,
    *,
    governance_evidence: object | None = None,
    review_surface_inventory: object | None = None,
    live_head_sha: str | None = None,
) -> _impl.VerifiedCandidateReviewBundle:
    """Reject incomplete artifact sets before parsing any required file."""

    if not isinstance(artifact_bytes, Mapping):
        raise ValueError("review artifacts must be a mapping")
    missing = _impl.BASE_REQUIRED_ARTIFACTS - set(artifact_bytes)
    if missing:
        raise ValueError(
            "missing required artifacts: " + ", ".join(sorted(missing))
        )
    return _original_verify_candidate_review_artifact_bytes(
        artifact_bytes,
        inspector_commit,
        governance_evidence=governance_evidence,
        review_surface_inventory=review_surface_inventory,
        live_head_sha=live_head_sha,
    )


def validate_owner_profile_commands(raw: bytes) -> list[str]:
    """Validate canonical profile guidance without leaking decode errors."""

    errors: list[str] = []
    if raw != _impl.PROFILE_COMMANDS_BYTES:
        errors.append("owner profile commands bytes differ from canonical text")
    if raw.startswith(b"\xef\xbb\xbf"):
        errors.append("owner profile commands must not contain BOM")
    if b"\r\n" in raw:
        errors.append("owner profile commands must use LF newlines")
    if not raw.endswith(b"\n"):
        errors.append("owner profile commands must end with LF")
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        errors.append("owner profile commands are not valid UTF-8")
        lines = []
    if len(lines) != 2:
        errors.append("owner profile commands must contain exactly two visible lines")
    return errors


# Functions defined in the implementation resolve globals in that module.
# Replace the hardened boundaries before exporting the active runtime surface.
_impl._validate_annotation_metadata = _validate_annotation_metadata
_impl.classify_governance = classify_governance
_impl.verify_candidate_review_artifact_bytes = verify_candidate_review_artifact_bytes
_impl.validate_owner_profile_commands = validate_owner_profile_commands

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals().setdefault(_name, getattr(_impl, _name))

for _name in (
    "_validate_annotation_metadata",
    "classify_governance",
    "verify_candidate_review_artifact_bytes",
    "validate_owner_profile_commands",
):
    globals()[_name] = locals()[_name]

__all__ = sorted(name for name in globals() if not name.startswith("__"))
