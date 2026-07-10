from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .decision_projection import ProjectionError
from .derived_outputs import (
    MANIFEST_NAME,
    PROJECTION_NAME,
    PROMPT_NAME,
    write_review_artifacts,
)
from .diagnostics import Diagnostic
from .render import package_sha256
from .validation_v2 import validate_directory, validate_package

_COMPLETION_MARKER = object()
_OFFICIAL_ARTIFACTS = {
    "review-package.json",
    PROJECTION_NAME,
    "OWNER_DECISION_CARD.fa.md",
    "TECHNICAL_HANDOFF.en.md",
    "OWNER_RESULT.fa.txt",
    MANIFEST_NAME,
}
_INCOMPLETE_OWNER_MESSAGE = (
    "⚪ وضعیت: بررسی رسمی PR Inspector کامل نشد.\n"
    "هیچ تصمیم معتبر یا پرامپت اقدامی تولید نشد.\n"
)
_INCOMPLETE_TECHNICAL_MESSAGE = (
    "The official PR Inspector review did not complete.\n"
    "No valid decision or action prompt was produced.\n"
)


class CompletionError(ValueError):
    """Raised when an official review bundle cannot prove verified completion."""


@dataclass(frozen=True)
class IncompleteReview:
    """Bounded fail-closed result that carries diagnostics but no decision fields."""

    diagnostics: tuple[Diagnostic, ...]
    owner_message: str = _INCOMPLETE_OWNER_MESSAGE
    technical_message: str = _INCOMPLETE_TECHNICAL_MESSAGE


@dataclass(frozen=True)
class RollbackOutcome:
    """Observable rollback result; failures are diagnostics, never silent success."""

    restored_previous: bool
    official_path_authoritative: bool
    backup_path: Path | None
    quarantine_path: Path | None
    diagnostics: tuple[Diagnostic, ...]


@dataclass(frozen=True)
class VerifiedReviewCompletion:
    """Opaque in-process proof that one canonical review bundle fully validated."""

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
    _marker: object = field(repr=False, compare=False)

    def _reverify(self) -> "VerifiedReviewCompletion":
        if self._marker is not _COMPLETION_MARKER:
            raise CompletionError("review completion proof is not verifier-created")
        current = verify_completed_review(
            self.output_directory,
            expected_target_repository=self.target_repository,
            expected_pr_number=self.pr_number,
            expected_reviewed_head_sha=self.reviewed_head_sha,
        )
        expected = (
            self.protocol_version,
            self.review_package_canonical_sha256,
            self.review_package_file_sha256,
            self.decision_projection_sha256,
            self.artifact_manifest_sha256,
            dict(self.artifact_sha256),
        )
        observed = (
            current.protocol_version,
            current.review_package_canonical_sha256,
            current.review_package_file_sha256,
            current.decision_projection_sha256,
            current.artifact_manifest_sha256,
            dict(current.artifact_sha256),
        )
        if observed != expected:
            raise CompletionError("verified review bundle changed after completion")
        return current

    def decision_projection(self) -> dict[str, Any]:
        self._reverify()
        return _load_json_object(self.output_directory / PROJECTION_NAME)

    def owner_result_text(self) -> str:
        self._reverify()
        return _read_utf8(self.output_directory / "OWNER_RESULT.fa.txt")

    def owner_decision_card_text(self) -> str:
        self._reverify()
        return _read_utf8(self.output_directory / "OWNER_DECISION_CARD.fa.md")

    def technical_handoff_text(self) -> str:
        self._reverify()
        return _read_utf8(self.output_directory / "TECHNICAL_HANDOFF.en.md")

    def next_action_prompt_text(self) -> str | None:
        projection = self.decision_projection()
        prompt_required = projection["next_action"]["prompt_required"]
        prompt_path = self.output_directory / PROMPT_NAME
        if not prompt_required:
            if prompt_path.exists():
                raise CompletionError(
                    "canonical projection forbids a next-action prompt artifact"
                )
            return None
        if not prompt_path.is_file():
            raise CompletionError(
                "canonical projection requires a validated next-action prompt artifact"
            )
        return _read_utf8(prompt_path)


def is_verified_review_completion(value: object) -> bool:
    return (
        isinstance(value, VerifiedReviewCompletion)
        and value._marker is _COMPLETION_MARKER
    )


def official_owner_result(value: VerifiedReviewCompletion) -> str:
    if not is_verified_review_completion(value):
        raise CompletionError("official owner output requires verified completion")
    return value.owner_result_text()


def official_technical_handoff(value: VerifiedReviewCompletion) -> str:
    if not is_verified_review_completion(value):
        raise CompletionError("official technical output requires verified completion")
    return value.technical_handoff_text()


def official_next_action_prompt(
    value: VerifiedReviewCompletion,
) -> str | None:
    if not is_verified_review_completion(value):
        raise CompletionError("official action prompt requires verified completion")
    return value.next_action_prompt_text()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_utf8(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CompletionError(f"cannot read {path.name}: {exc}") from exc


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(_read_utf8(path))
    except json.JSONDecodeError as exc:
        raise CompletionError(f"cannot parse {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise CompletionError(f"{path.name} must contain a JSON object")
    return value


def _diagnostic(code: str, path: str, message: str) -> Diagnostic:
    return Diagnostic(code, path, message)


def _incomplete(code: str, path: str, message: str) -> IncompleteReview:
    return IncompleteReview((_diagnostic(code, path, message),))


def _artifact_hashes(
    directory: Path,
    projection: Mapping[str, Any],
) -> Mapping[str, str]:
    names = set(_OFFICIAL_ARTIFACTS)
    if projection["next_action"]["prompt_required"]:
        names.add(PROMPT_NAME)
    try:
        hashes = {
            name: _sha256((directory / name).read_bytes())
            for name in sorted(names)
        }
    except OSError as exc:
        raise CompletionError(f"cannot hash completed artifact set: {exc}") from exc
    return MappingProxyType(hashes)


def verify_completed_review(
    review_directory: Path,
    *,
    expected_target_repository: str,
    expected_pr_number: int,
    expected_reviewed_head_sha: str,
) -> VerifiedReviewCompletion:
    """Validate one complete artifact bundle and bind it to expected review identity."""

    review_directory = Path(review_directory)
    try:
        diagnostics = validate_directory(review_directory)
    except Exception as exc:
        raise CompletionError(f"review directory validation failed: {exc}") from exc
    if diagnostics:
        rendered = "; ".join(item.line() for item in diagnostics)
        raise CompletionError(f"review directory validation failed: {rendered}")

    package_path = review_directory / "review-package.json"
    projection_path = review_directory / PROJECTION_NAME
    manifest_path = review_directory / MANIFEST_NAME
    try:
        package_bytes = package_path.read_bytes()
        projection_bytes = projection_path.read_bytes()
        manifest_bytes = manifest_path.read_bytes()
    except OSError as exc:
        raise CompletionError(f"cannot read completed artifact bytes: {exc}") from exc
    package = _load_json_object(package_path)
    projection = _load_json_object(projection_path)
    manifest = _load_json_object(manifest_path)
    try:
        identity = package["review_identity"]
        expected_identity = (
            expected_target_repository,
            expected_pr_number,
            expected_reviewed_head_sha,
        )
        observed_identity = (
            identity["target_repository"],
            identity["pr_number"],
            identity["reviewed_head_sha"],
        )
        if observed_identity != expected_identity:
            raise CompletionError(
                "review bundle identity does not match the expected repository, PR, and head"
            )
        if projection["review_identity"]["reviewed_head_sha"] != expected_reviewed_head_sha:
            raise CompletionError("projection reviewed head does not match expected head")
        if projection["review_identity"]["validity"] != identity["review_validity"]:
            raise CompletionError("projection validity does not match review package")
        if manifest["canonical_review_package"]["canonical_sha256"] != package_sha256(
            package
        ):
            raise CompletionError("canonical review package hash is invalid")
        if manifest["canonical_review_package"]["file_sha256"] != _sha256(package_bytes):
            raise CompletionError("review package final-file hash is invalid")
        if manifest["decision_projection"]["sha256"] != _sha256(projection_bytes):
            raise CompletionError("decision projection final-file hash is invalid")
    except (KeyError, TypeError) as exc:
        raise CompletionError(f"completed artifact metadata is invalid: {exc}") from exc

    return VerifiedReviewCompletion(
        output_directory=review_directory.resolve(),
        protocol_version=package["protocol_version"],
        target_repository=identity["target_repository"],
        pr_number=identity["pr_number"],
        reviewed_head_sha=identity["reviewed_head_sha"],
        review_package_canonical_sha256=package_sha256(package),
        review_package_file_sha256=_sha256(package_bytes),
        decision_projection_sha256=_sha256(projection_bytes),
        artifact_manifest_sha256=_sha256(manifest_bytes),
        artifact_sha256=_artifact_hashes(review_directory, projection),
        _marker=_COMPLETION_MARKER,
    )


def _staging_directory(output_directory: Path) -> Path:
    output_directory.parent.mkdir(parents=True, exist_ok=True)
    return Path(
        tempfile.mkdtemp(
            prefix=f".{output_directory.name}.staging-",
            dir=output_directory.parent,
        )
    )


def _unused_sibling_path(output_directory: Path, label: str) -> Path:
    path = Path(
        tempfile.mkdtemp(
            prefix=f".{output_directory.name}.{label}-",
            dir=output_directory.parent,
        )
    )
    path.rmdir()
    return path


def _is_authoritative_bundle(path: Path) -> bool:
    if not path.is_dir():
        return False
    try:
        return validate_directory(path) == []
    except Exception:
        return False


def _invalidate_official_bundle(output_directory: Path) -> tuple[Diagnostic, ...]:
    """Break manifest completeness when a failed directory cannot be quarantined."""

    diagnostics: list[Diagnostic] = []
    if not output_directory.exists():
        return ()
    manifest = output_directory / MANIFEST_NAME
    if not manifest.exists():
        return ()

    try:
        manifest.unlink()
    except Exception as unlink_exc:
        diagnostics.append(
            _diagnostic(
                "PRI-COMPLETE-ROLLBACK-004",
                f"/{output_directory.name}/{MANIFEST_NAME}",
                f"could not remove manifest while invalidating failed output: {unlink_exc}",
            )
        )
        try:
            manifest.write_bytes(b'{"incomplete_review":true}\n')
        except Exception as overwrite_exc:
            diagnostics.append(
                _diagnostic(
                    "PRI-COMPLETE-ROLLBACK-005",
                    f"/{output_directory.name}/{MANIFEST_NAME}",
                    "could not overwrite manifest while invalidating failed output: "
                    f"{overwrite_exc}",
                )
            )

    if _is_authoritative_bundle(output_directory):
        diagnostics.append(
            _diagnostic(
                "PRI-COMPLETE-ROLLBACK-006",
                f"/{output_directory.name}",
                "failed output could not be made non-authoritative",
            )
        )
    return tuple(diagnostics)


def _restore_previous_directory(
    output_directory: Path,
    backup: Path | None,
) -> RollbackOutcome:
    """Quarantine failed publication, restore backup, and report every recovery failure."""

    diagnostics: list[Diagnostic] = []
    quarantine: Path | None = None
    restored_previous = False

    if output_directory.exists():
        try:
            quarantine = _unused_sibling_path(output_directory, "quarantine")
            os.replace(output_directory, quarantine)
        except Exception as exc:
            diagnostics.append(
                _diagnostic(
                    "PRI-COMPLETE-ROLLBACK-001",
                    f"/{output_directory.name}",
                    f"could not quarantine failed published directory: {exc}",
                )
            )
            diagnostics.extend(_invalidate_official_bundle(output_directory))
            try:
                shutil.rmtree(output_directory)
            except Exception as delete_exc:
                diagnostics.append(
                    _diagnostic(
                        "PRI-COMPLETE-ROLLBACK-002",
                        f"/{output_directory.name}",
                        f"could not delete non-authoritative failed directory: {delete_exc}",
                    )
                )
            if output_directory.exists():
                diagnostics.append(
                    _diagnostic(
                        "PRI-COMPLETE-ROLLBACK-003",
                        f"/{output_directory.name}",
                        "failed directory remains at the official path after deletion attempt",
                    )
                )
                diagnostics.extend(_invalidate_official_bundle(output_directory))

    if backup is not None:
        if not backup.exists():
            diagnostics.append(
                _diagnostic(
                    "PRI-COMPLETE-ROLLBACK-007",
                    f"/{backup.name}",
                    "previous-output backup is missing; restoration was not completed",
                )
            )
        elif output_directory.exists():
            diagnostics.append(
                _diagnostic(
                    "PRI-COMPLETE-ROLLBACK-008",
                    f"/{output_directory.name}",
                    "official path is still occupied; previous-output backup was retained",
                )
            )
        else:
            try:
                os.replace(backup, output_directory)
                restored_previous = output_directory.exists() and not backup.exists()
                if not restored_previous:
                    raise OSError("backup rename did not establish the official path")
            except Exception as exc:
                diagnostics.append(
                    _diagnostic(
                        "PRI-COMPLETE-ROLLBACK-009",
                        f"/{output_directory.name}",
                        f"could not restore previous-output backup: {exc}",
                    )
                )

    official_authoritative = _is_authoritative_bundle(output_directory)
    if backup is None and official_authoritative:
        diagnostics.extend(_invalidate_official_bundle(output_directory))
        official_authoritative = _is_authoritative_bundle(output_directory)
    if backup is not None and not restored_previous and official_authoritative:
        diagnostics.extend(_invalidate_official_bundle(output_directory))
        official_authoritative = _is_authoritative_bundle(output_directory)

    cleanup_allowed = restored_previous or (
        backup is None and not official_authoritative
    )
    if quarantine is not None and quarantine.exists() and cleanup_allowed:
        try:
            shutil.rmtree(quarantine)
        except Exception as exc:
            diagnostics.append(
                _diagnostic(
                    "PRI-COMPLETE-ROLLBACK-010",
                    f"/{quarantine.name}",
                    f"rollback quarantine cleanup failed and was retained: {exc}",
                )
            )
        if quarantine.exists():
            diagnostics.append(
                _diagnostic(
                    "PRI-COMPLETE-ROLLBACK-011",
                    f"/{quarantine.name}",
                    "rollback quarantine remains after cleanup attempt",
                )
            )

    return RollbackOutcome(
        restored_previous=restored_previous,
        official_path_authoritative=official_authoritative,
        backup_path=backup if backup is not None and backup.exists() else None,
        quarantine_path=(
            quarantine if quarantine is not None and quarantine.exists() else None
        ),
        diagnostics=tuple(diagnostics),
    )


def _swap_staged_directory(
    staging: Path,
    output_directory: Path,
) -> tuple[Path | None, tuple[Diagnostic, ...]]:
    """Publish staging atomically or return bounded publication/rollback diagnostics."""

    backup: Path | None = None
    if output_directory.exists():
        try:
            backup = _unused_sibling_path(output_directory, "backup")
            os.replace(output_directory, backup)
        except Exception as exc:
            return None, (
                _diagnostic(
                    "PRI-COMPLETE-005",
                    f"/{output_directory.name}",
                    f"could not move existing output to backup: {exc}",
                ),
            )

    try:
        os.replace(staging, output_directory)
    except Exception as exc:
        rollback = _restore_previous_directory(output_directory, backup)
        return None, (
            _diagnostic(
                "PRI-COMPLETE-005",
                f"/{output_directory.name}",
                f"could not publish validated staging directory: {exc}",
            ),
            *rollback.diagnostics,
        )
    return backup, ()


def _cleanup_directory(path: Path, *, code: str, context: str) -> tuple[Diagnostic, ...]:
    if not path.exists():
        return ()
    try:
        shutil.rmtree(path)
    except Exception as exc:
        return (
            _diagnostic(code, f"/{path.name}", f"{context}: {exc}"),
        )
    if path.exists():
        return (
            _diagnostic(code, f"/{path.name}", f"{context}: path still exists"),
        )
    return ()


def complete_review(
    package_path: Path,
    output_directory: Path,
    *,
    expected_target_repository: str,
    expected_pr_number: int,
    expected_reviewed_head_sha: str,
) -> VerifiedReviewCompletion | IncompleteReview:
    """Run the sole supported official package-to-output completion boundary."""

    package_path = Path(package_path)
    output_directory = Path(output_directory)
    try:
        package_bytes = package_path.read_bytes()
        package = json.loads(package_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _incomplete("PRI-COMPLETE-001", "/review-package.json", str(exc))
    if not isinstance(package, dict):
        return _incomplete(
            "PRI-COMPLETE-001",
            "/review-package.json",
            "canonical review package must be a JSON object",
        )

    try:
        package_diagnostics = validate_package(package)
    except Exception as exc:
        return _incomplete("PRI-COMPLETE-002", "/package-validation", str(exc))
    if package_diagnostics:
        return IncompleteReview(tuple(package_diagnostics))

    try:
        identity = package["review_identity"]
        package_identity = (
            identity["target_repository"],
            identity["pr_number"],
            identity["reviewed_head_sha"],
        )
    except (KeyError, TypeError) as exc:
        return _incomplete("PRI-COMPLETE-002", "/review_identity", str(exc))
    expected_identity = (
        expected_target_repository,
        expected_pr_number,
        expected_reviewed_head_sha,
    )
    if package_identity != expected_identity:
        return _incomplete(
            "PRI-COMPLETE-007",
            "/review_identity",
            "canonical package identity does not match the expected repository, PR, and head",
        )

    try:
        staging = _staging_directory(output_directory)
    except Exception as exc:
        return _incomplete(
            "PRI-COMPLETE-005",
            f"/{output_directory.name}",
            str(exc),
        )

    try:
        if output_directory.exists() and not output_directory.is_dir():
            return _incomplete(
                "PRI-COMPLETE-005",
                f"/{output_directory.name}",
                "output path exists and is not a directory",
            )

        try:
            (staging / "review-package.json").write_bytes(package_bytes)
            write_review_artifacts(
                package,
                staging,
                review_package_bytes=package_bytes,
            )
        except (OSError, ValueError, KeyError, TypeError, ProjectionError) as exc:
            return _incomplete("PRI-COMPLETE-003", "/artifact-render", str(exc))

        try:
            diagnostics = validate_directory(staging)
        except Exception as exc:
            return _incomplete("PRI-COMPLETE-004", "/artifact-validation", str(exc))
        if diagnostics:
            return IncompleteReview(tuple(diagnostics))

        try:
            verify_completed_review(
                staging,
                expected_target_repository=expected_target_repository,
                expected_pr_number=expected_pr_number,
                expected_reviewed_head_sha=expected_reviewed_head_sha,
            )
        except Exception as exc:
            return _incomplete("PRI-COMPLETE-004", "/artifact-bundle", str(exc))

        backup, publication_diagnostics = _swap_staged_directory(
            staging,
            output_directory,
        )
        if publication_diagnostics:
            return IncompleteReview(publication_diagnostics)

        try:
            completed = verify_completed_review(
                output_directory,
                expected_target_repository=expected_target_repository,
                expected_pr_number=expected_pr_number,
                expected_reviewed_head_sha=expected_reviewed_head_sha,
            )
        except Exception as exc:
            rollback = _restore_previous_directory(output_directory, backup)
            return IncompleteReview(
                (
                    _diagnostic(
                        "PRI-COMPLETE-006",
                        "/published-artifact-bundle",
                        str(exc),
                    ),
                    *rollback.diagnostics,
                )
            )

        if backup is not None:
            cleanup = _cleanup_directory(
                backup,
                code="PRI-COMPLETE-008",
                context="validated publication succeeded but previous backup cleanup failed",
            )
            if cleanup:
                return IncompleteReview(cleanup)
        return completed
    except Exception as exc:
        return _incomplete(
            "PRI-COMPLETE-999",
            "/official-review-boundary",
            f"unexpected handled completion failure: {exc}",
        )
    finally:
        if staging.exists():
            try:
                shutil.rmtree(staging)
            except Exception:
                # Staging is never authoritative. Publication and rollback paths above
                # report authoritative-path failures explicitly.
                pass
