from __future__ import annotations

import hashlib
import json
import re
import weakref
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from ._governance_transport import (
    GitHubApiResponse,
    github_response_payload,
    is_verified_github_api_response,
)
from .decision_projection import project_decision
from .derived_outputs import MANIFEST_NAME, PROJECTION_NAME
from .render import package_sha256
from .validation_v2 import validate_directory

ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
TRUST_POLICY_PATH = (
    ROOT / f"protocols/{CURRENT_VERSION}/trust/INSPECTOR_TRUST_POLICY.json"
)
_VERIFIED_MARKER = object()
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_EXPECTED_ARTIFACTS = {
    "review-package.json",
    PROJECTION_NAME,
    MANIFEST_NAME,
}
_EXPECTED_HASH_FIELDS = {
    "review_package_canonical_sha256",
    "review_package_file_sha256",
    "decision_projection_sha256",
    "artifact_manifest_sha256",
}


class ProvenanceError(ValueError):
    """Raised when inspector or review provenance cannot be verified."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProvenanceError(f"cannot read {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProvenanceError(f"{path.name} must contain a JSON object")
    return value


def trust_policy() -> dict[str, Any]:
    policy = _load_json(TRUST_POLICY_PATH)
    required = {
        "schema_version",
        "protocol_version",
        "inspector_repository",
        "inspector_repository_id",
        "github_api_version",
        "commit_evidence_source",
        "required_review_artifacts",
        "required_review_hashes",
    }
    missing = required - set(policy)
    if missing:
        raise ProvenanceError(
            "inspector trust policy is missing fields: "
            + ", ".join(sorted(missing))
        )
    if set(policy) != required:
        extras = sorted(set(policy) - required)
        raise ProvenanceError(
            "inspector trust policy has unsupported fields: " + ", ".join(extras)
        )
    if policy["schema_version"] != 1:
        raise ProvenanceError("inspector trust policy schema_version must be 1")
    if policy["protocol_version"] != CURRENT_VERSION:
        raise ProvenanceError(
            "inspector trust policy version must match CURRENT_VERSION"
        )
    if policy["commit_evidence_source"] != "github_rest_api_https":
        raise ProvenanceError("unsupported inspector commit evidence source")
    if not isinstance(policy["inspector_repository_id"], int):
        raise ProvenanceError("inspector_repository_id must be an integer")
    if set(policy["required_review_artifacts"]) != _EXPECTED_ARTIFACTS:
        raise ProvenanceError(
            "required_review_artifacts must name the canonical package, projection, "
            "and manifest exactly"
        )
    if set(policy["required_review_hashes"]) != _EXPECTED_HASH_FIELDS:
        raise ProvenanceError(
            "required_review_hashes must name every canonical provenance hash exactly"
        )
    return policy


class VerifiedInspectorCommit:
    """Opaque capability bound to operational GitHub HTTPS commit evidence."""

    __slots__ = (
        "repository",
        "repository_id",
        "commit_sha",
        "api_url",
        "html_url",
        "evidence_source",
        "repository_response_receipt_id",
        "commit_response_receipt_id",
        "__weakref__",
    )

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError(
            "VerifiedInspectorCommit can only be created from sealed operational "
            "GitHub HTTPS responses"
        )

    def __setattr__(self, _name: str, _value: object) -> None:
        raise AttributeError("VerifiedInspectorCommit is immutable")


_INSPECTOR_COMMIT_CAPABILITIES: weakref.WeakSet[VerifiedInspectorCommit] = (
    weakref.WeakSet()
)


def _mint_verified_inspector_commit(
    *,
    repository: str,
    repository_id: int,
    commit_sha: str,
    api_url: str,
    html_url: str,
    evidence_source: str,
    repository_response_receipt_id: str,
    commit_response_receipt_id: str,
) -> VerifiedInspectorCommit:
    value = object.__new__(VerifiedInspectorCommit)
    for name, item in (
        ("repository", repository),
        ("repository_id", repository_id),
        ("commit_sha", commit_sha),
        ("api_url", api_url),
        ("html_url", html_url),
        ("evidence_source", evidence_source),
        ("repository_response_receipt_id", repository_response_receipt_id),
        ("commit_response_receipt_id", commit_response_receipt_id),
    ):
        object.__setattr__(value, name, item)
    _INSPECTOR_COMMIT_CAPABILITIES.add(value)
    return value


def is_verified_inspector_commit(value: object) -> bool:
    return (
        type(value) is VerifiedInspectorCommit
        and value in _INSPECTOR_COMMIT_CAPABILITIES
    )


@dataclass(frozen=True)
class VerifiedReviewEvidence:
    evidence_id: str
    protocol_version: str
    target_repository: str
    pr_number: int
    reviewed_head_sha: str
    review_validity: str
    inspector_repository: str
    inspector_repository_id: int
    inspector_commit_sha: str
    inspector_commit_api_url: str
    inspector_commit_html_url: str
    inspector_evidence_source: str
    review_package_canonical_sha256: str
    review_package_file_sha256: str
    decision_projection_sha256: str
    artifact_manifest_sha256: str
    technical_status: str
    approval_requirement: str
    next_action_kind: str
    _marker: object = field(repr=False, compare=False)


def is_verified_review_evidence(value: object) -> bool:
    return (
        isinstance(value, VerifiedReviewEvidence)
        and value._marker is _VERIFIED_MARKER
    )


def _require_operational_github_response(
    response: object,
    *,
    expected_url: str,
    label: str,
) -> Mapping[str, Any]:
    if type(response) is not GitHubApiResponse or not is_verified_github_api_response(
        response
    ):
        raise ProvenanceError(
            f"{label} is not a sealed verifier-created GitHub response"
        )
    assert isinstance(response, GitHubApiResponse)
    if response.transport_origin != "github_https":
        raise ProvenanceError(
            f"{label} is not from the operational GitHub HTTPS adapter"
        )
    if response.request_url != expected_url:
        raise ProvenanceError(f"{label} request URL is not canonical")
    if response.response_url != expected_url:
        raise ProvenanceError(f"{label} response URL is not canonical")
    if response.status_code != 200:
        raise ProvenanceError(f"{label} did not succeed")
    payload = github_response_payload(response)
    if not isinstance(payload, Mapping):
        raise ProvenanceError(f"{label} payload is not a JSON object")
    return payload


def verify_github_commit_payload(
    repository_response: GitHubApiResponse,
    commit_response: GitHubApiResponse,
    *,
    expected_commit_sha: str,
) -> VerifiedInspectorCommit:
    """Verify sealed operational GitHub REST repository and commit responses.

    The historical function name is retained for compatibility, but ordinary
    mappings and copied GitHub-looking JSON are never accepted.
    """

    if not isinstance(expected_commit_sha, str) or SHA40_RE.fullmatch(
        expected_commit_sha
    ) is None:
        raise ProvenanceError("expected Inspector commit SHA is malformed")

    policy = trust_policy()
    repository = policy["inspector_repository"]
    repository_id = policy["inspector_repository_id"]
    repository_api_url = f"https://api.github.com/repos/{repository}"
    repository_html_url = f"https://github.com/{repository}"
    commit_api_url = f"{repository_api_url}/commits/{expected_commit_sha}"
    commit_html_url = f"{repository_html_url}/commit/{expected_commit_sha}"

    repository_payload = _require_operational_github_response(
        repository_response,
        expected_url=repository_api_url,
        label="Inspector repository response",
    )
    commit_payload = _require_operational_github_response(
        commit_response,
        expected_url=commit_api_url,
        label="Inspector commit response",
    )

    if repository_payload.get("full_name") != repository:
        raise ProvenanceError(
            "GitHub repository full_name does not match trust policy"
        )
    if repository_payload.get("id") != repository_id:
        raise ProvenanceError("GitHub repository id does not match trust policy")
    if repository_payload.get("url") != repository_api_url:
        raise ProvenanceError("GitHub repository API URL is not canonical")
    if repository_payload.get("html_url") != repository_html_url:
        raise ProvenanceError("GitHub repository HTML URL is not canonical")
    if commit_payload.get("sha") != expected_commit_sha:
        raise ProvenanceError("GitHub commit SHA does not match review identity")
    if commit_payload.get("url") != commit_api_url:
        raise ProvenanceError(
            "GitHub commit API URL does not match canonical repository"
        )
    if commit_payload.get("html_url") != commit_html_url:
        raise ProvenanceError(
            "GitHub commit HTML URL does not match canonical repository"
        )

    return _mint_verified_inspector_commit(
        repository=repository,
        repository_id=repository_id,
        commit_sha=expected_commit_sha,
        api_url=commit_api_url,
        html_url=commit_html_url,
        evidence_source=policy["commit_evidence_source"],
        repository_response_receipt_id=repository_response.receipt_id,
        commit_response_receipt_id=commit_response.receipt_id,
    )


def verify_review_directory(
    review_directory: Path,
    inspector_commit: VerifiedInspectorCommit,
) -> VerifiedReviewEvidence:
    """Validate immutable review artifacts and bind them to inspector identity."""

    if not is_verified_inspector_commit(inspector_commit):
        raise ProvenanceError("inspector commit evidence is not verified")

    policy = trust_policy()
    for name in policy["required_review_artifacts"]:
        if not (review_directory / name).is_file():
            raise ProvenanceError(f"required review artifact is missing: {name}")

    diagnostics = validate_directory(review_directory)
    if diagnostics:
        rendered = "; ".join(item.line() for item in diagnostics)
        raise ProvenanceError(f"review directory validation failed: {rendered}")

    package_path = review_directory / "review-package.json"
    projection_path = review_directory / PROJECTION_NAME
    manifest_path = review_directory / MANIFEST_NAME
    package_bytes = package_path.read_bytes()
    projection_bytes = projection_path.read_bytes()
    manifest_bytes = manifest_path.read_bytes()

    package = json.loads(package_bytes.decode("utf-8"))
    projection = json.loads(projection_bytes.decode("utf-8"))
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    identity = package["review_identity"]

    if package["protocol_version"] != policy["protocol_version"]:
        raise ProvenanceError("review package protocol version is not trusted")
    if identity["inspector_repository"] != inspector_commit.repository:
        raise ProvenanceError("review package inspector repository is not verified")
    if identity["inspector_commit_sha"] != inspector_commit.commit_sha:
        raise ProvenanceError("review package inspector commit is not verified")
    if identity["review_validity"] != "CURRENT":
        raise ProvenanceError("only a CURRENT review can produce verified evidence")
    if projection["review_identity"]["validity"] != "CURRENT":
        raise ProvenanceError("decision projection review validity is not CURRENT")
    if (
        projection["review_identity"]["reviewed_head_sha"]
        != identity["reviewed_head_sha"]
    ):
        raise ProvenanceError("projection reviewed head differs from review package")
    if manifest.get("schema_version") != 2:
        raise ProvenanceError("artifact manifest schema_version must be 2")

    canonical_hash = package_sha256(package)
    package_file_hash = _sha256(package_bytes)
    projection_hash = _sha256(projection_bytes)
    manifest_hash = _sha256(manifest_bytes)

    manifest_package = manifest["canonical_review_package"]
    if manifest_package.get("canonical_sha256") != canonical_hash:
        raise ProvenanceError("manifest canonical package hash does not match package")
    if manifest_package.get("file_sha256") != package_file_hash:
        raise ProvenanceError("manifest package file hash does not match package bytes")
    if manifest["decision_projection"].get("sha256") != projection_hash:
        raise ProvenanceError(
            "manifest projection hash does not match projection bytes"
        )

    canonical_projection = project_decision(package)
    if projection != canonical_projection:
        raise ProvenanceError(
            "decision projection is not the canonical package projection"
        )

    evidence_payload = {
        "protocol_version": package["protocol_version"],
        "target_repository": identity["target_repository"],
        "pr_number": identity["pr_number"],
        "reviewed_head_sha": identity["reviewed_head_sha"],
        "review_validity": identity["review_validity"],
        "inspector_repository": inspector_commit.repository,
        "inspector_repository_id": inspector_commit.repository_id,
        "inspector_commit_sha": inspector_commit.commit_sha,
        "inspector_commit_api_url": inspector_commit.api_url,
        "inspector_commit_html_url": inspector_commit.html_url,
        "inspector_evidence_source": inspector_commit.evidence_source,
        "review_package_canonical_sha256": canonical_hash,
        "review_package_file_sha256": package_file_hash,
        "decision_projection_sha256": projection_hash,
        "artifact_manifest_sha256": manifest_hash,
        "technical_status": projection["technical_status"],
        "approval_requirement": projection["approval_requirement"],
        "next_action_kind": projection["next_action"]["kind"],
    }
    evidence_id = _sha256(
        (
            json.dumps(
                evidence_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    )

    return VerifiedReviewEvidence(
        evidence_id=evidence_id,
        _marker=_VERIFIED_MARKER,
        **evidence_payload,
    )


def event_evidence_fields(evidence: VerifiedReviewEvidence) -> dict[str, Any]:
    if not is_verified_review_evidence(evidence):
        raise ProvenanceError("review evidence is not verified")
    return {
        "review_evidence_id": evidence.evidence_id,
        "protocol_version": evidence.protocol_version,
        "inspector_repository": evidence.inspector_repository,
        "inspector_repository_id": evidence.inspector_repository_id,
        "inspector_commit_sha": evidence.inspector_commit_sha,
        "inspector_commit_api_url": evidence.inspector_commit_api_url,
        "inspector_commit_html_url": evidence.inspector_commit_html_url,
        "inspector_evidence_source": evidence.inspector_evidence_source,
        "review_package_canonical_sha256": (
            evidence.review_package_canonical_sha256
        ),
        "review_package_file_sha256": evidence.review_package_file_sha256,
        "decision_projection_sha256": evidence.decision_projection_sha256,
        "artifact_manifest_sha256": evidence.artifact_manifest_sha256,
    }


def evidence_matches_event(
    evidence: VerifiedReviewEvidence,
    event: Mapping[str, Any],
) -> bool:
    if not is_verified_review_evidence(evidence):
        return False
    expected = {
        **event_evidence_fields(evidence),
        "target_repository": evidence.target_repository,
        "pr_number": evidence.pr_number,
        "resulting_head_sha": evidence.reviewed_head_sha,
        "reviewed_head_sha": evidence.reviewed_head_sha,
        "review_validity": evidence.review_validity,
    }
    return all(event.get(key) == value for key, value in expected.items())
