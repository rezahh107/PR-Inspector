from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .derived_outputs import MANIFEST_NAME, PROJECTION_NAME, PROMPT_NAME
from .diagnostics import Diagnostic
from .render import package_sha256
from .validation_v2 import validate_directory
from ._official_head import (
    CompletionError,
    GitHubPullRequestHeadSource,
    VerifiedLivePullRequestHead,
    require_head,
)

_COMPLETION_MARKER = object()
_OFFICIAL = {
    "review-package.json",
    PROJECTION_NAME,
    "OWNER_DECISION_CARD.fa.md",
    "TECHNICAL_HANDOFF.en.md",
    "OWNER_RESULT.fa.txt",
    MANIFEST_NAME,
}
_OWNER_FAILURE = (
    "⚪ وضعیت: بررسی رسمی PR Inspector کامل نشد.\n"
    "هیچ تصمیم معتبر یا پرامپت اقدامی تولید نشد.\n"
)
_TECHNICAL_FAILURE = (
    "The official PR Inspector review did not complete.\n"
    "No valid decision or action prompt was produced.\n"
)


@dataclass(frozen=True)
class IncompleteReview:
    diagnostics: tuple[Diagnostic, ...]
    owner_message: str = _OWNER_FAILURE
    technical_message: str = _TECHNICAL_FAILURE


@dataclass(frozen=True)
class _Bundle:
    directory: Path
    protocol_version: str
    repository: str
    pr_number: int
    head_sha: str
    package_canonical_sha256: str
    package_file_sha256: str
    projection_sha256: str
    manifest_sha256: str
    artifact_sha256: Mapping[str, str]


@dataclass(frozen=True)
class VerifiedReviewCompletion:
    output_directory: Path
    protocol_version: str
    target_repository: str
    pr_number: int
    reviewed_head_sha: str
    review_package_canonical_sha256: str
    review_package_file_sha256: str
    decision_projection_sha256: str
    artifact_manifest_sha256: str
    artifact_sha256: Mapping[str, str]
    target_head_receipt_sha256: str
    _head_source: GitHubPullRequestHeadSource = field(repr=False, compare=False)
    _marker: object = field(repr=False, compare=False)

    def _reverify(self) -> _Bundle:
        if self._marker is not _COMPLETION_MARKER:
            raise CompletionError("review completion proof is not verifier-created")
        require_head(
            self._head_source.fetch(),
            self.target_repository,
            self.pr_number,
            self.reviewed_head_sha,
        )
        bundle = validate_bundle(
            self.output_directory,
            self.target_repository,
            self.pr_number,
            self.reviewed_head_sha,
        )
        expected = (
            self.protocol_version,
            self.review_package_canonical_sha256,
            self.review_package_file_sha256,
            self.decision_projection_sha256,
            self.artifact_manifest_sha256,
            dict(self.artifact_sha256),
        )
        actual = (
            bundle.protocol_version,
            bundle.package_canonical_sha256,
            bundle.package_file_sha256,
            bundle.projection_sha256,
            bundle.manifest_sha256,
            dict(bundle.artifact_sha256),
        )
        if actual != expected:
            raise CompletionError("verified review bundle changed after completion")
        return bundle

    def decision_projection(self) -> dict[str, Any]:
        self._reverify()
        return json_object(self.output_directory / PROJECTION_NAME)

    def owner_result_text(self) -> str:
        self._reverify()
        return utf8(self.output_directory / "OWNER_RESULT.fa.txt")

    def owner_decision_card_text(self) -> str:
        self._reverify()
        return utf8(self.output_directory / "OWNER_DECISION_CARD.fa.md")

    def technical_handoff_text(self) -> str:
        self._reverify()
        return utf8(self.output_directory / "TECHNICAL_HANDOFF.en.md")

    def next_action_prompt_text(self) -> str | None:
        projection = self.decision_projection()
        path = self.output_directory / PROMPT_NAME
        if not projection["next_action"]["prompt_required"]:
            if path.exists():
                raise CompletionError("canonical projection forbids a next-action prompt")
            return None
        if not path.is_file():
            raise CompletionError("canonical projection requires a next-action prompt")
        return utf8(path)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def utf8(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CompletionError(f"cannot read {path.name}: {exc}") from exc


def json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(utf8(path))
    except json.JSONDecodeError as exc:
        raise CompletionError(f"cannot parse {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise CompletionError(f"{path.name} must contain a JSON object")
    return value


def artifact_hashes(directory: Path, projection: Mapping[str, Any]) -> Mapping[str, str]:
    names = set(_OFFICIAL)
    if projection["next_action"]["prompt_required"]:
        names.add(PROMPT_NAME)
    return MappingProxyType(
        {name: sha256((directory / name).read_bytes()) for name in sorted(names)}
    )


def validate_bundle(
    directory: Path,
    repository: str,
    pr_number: int,
    head_sha: str,
) -> _Bundle:
    try:
        diagnostics = validate_directory(directory)
    except Exception as exc:
        raise CompletionError(f"review directory validation failed: {exc}") from exc
    if diagnostics:
        raise CompletionError(
            "review directory validation failed: "
            + "; ".join(item.line() for item in diagnostics)
        )
    package_path = directory / "review-package.json"
    projection_path = directory / PROJECTION_NAME
    manifest_path = directory / MANIFEST_NAME
    package_bytes = package_path.read_bytes()
    projection_bytes = projection_path.read_bytes()
    manifest_bytes = manifest_path.read_bytes()
    package = json_object(package_path)
    projection = json_object(projection_path)
    manifest = json_object(manifest_path)
    identity = package["review_identity"]
    if (
        identity["target_repository"],
        identity["pr_number"],
        identity["reviewed_head_sha"],
    ) != (repository, pr_number, head_sha):
        raise CompletionError("review bundle identity does not match live GitHub identity")
    if identity["review_validity"] != "CURRENT":
        raise CompletionError("official completion requires CURRENT review validity")
    if projection["review_identity"]["reviewed_head_sha"] != head_sha:
        raise CompletionError("projection reviewed head does not match live GitHub head")
    if manifest["canonical_review_package"]["canonical_sha256"] != package_sha256(package):
        raise CompletionError("canonical review package hash is invalid")
    if manifest["canonical_review_package"]["file_sha256"] != sha256(package_bytes):
        raise CompletionError("review package final-file hash is invalid")
    if manifest["decision_projection"]["sha256"] != sha256(projection_bytes):
        raise CompletionError("decision projection final-file hash is invalid")
    return _Bundle(
        directory.resolve(),
        package["protocol_version"],
        repository,
        pr_number,
        head_sha,
        package_sha256(package),
        sha256(package_bytes),
        sha256(projection_bytes),
        sha256(manifest_bytes),
        artifact_hashes(directory, projection),
    )


def completion(
    bundle: _Bundle,
    source: GitHubPullRequestHeadSource,
    receipt: VerifiedLivePullRequestHead,
) -> VerifiedReviewCompletion:
    return VerifiedReviewCompletion(
        bundle.directory,
        bundle.protocol_version,
        bundle.repository,
        bundle.pr_number,
        bundle.head_sha,
        bundle.package_canonical_sha256,
        bundle.package_file_sha256,
        bundle.projection_sha256,
        bundle.manifest_sha256,
        bundle.artifact_sha256,
        receipt.receipt_sha256,
        source,
        _COMPLETION_MARKER,
    )


def verify_completed_review(
    review_directory: Path,
    *,
    head_source: GitHubPullRequestHeadSource,
) -> VerifiedReviewCompletion:
    first = head_source.fetch()
    bundle = validate_bundle(
        Path(review_directory), first.repository, first.pr_number, first.head_sha
    )
    final = head_source.fetch()
    require_head(final, bundle.repository, bundle.pr_number, bundle.head_sha)
    return completion(bundle, head_source, final)


def is_verified_review_completion(value: object) -> bool:
    return isinstance(value, VerifiedReviewCompletion) and value._marker is _COMPLETION_MARKER


def official_owner_result(value: VerifiedReviewCompletion) -> str:
    if not is_verified_review_completion(value):
        raise CompletionError("official owner output requires verified completion")
    return value.owner_result_text()


def official_technical_handoff(value: VerifiedReviewCompletion) -> str:
    if not is_verified_review_completion(value):
        raise CompletionError("official technical output requires verified completion")
    return value.technical_handoff_text()


def official_next_action_prompt(value: VerifiedReviewCompletion) -> str | None:
    if not is_verified_review_completion(value):
        raise CompletionError("official action prompt requires verified completion")
    return value.next_action_prompt_text()
