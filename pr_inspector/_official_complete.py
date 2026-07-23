from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .decision_projection import ProjectionError
from .derived_outputs import MANIFEST_NAME, write_review_artifacts
from .diagnostics import Diagnostic
from .validation_v2 import validate_directory, validate_package
from .verified_review import (
    ReviewAssemblyError,
    CanonicalReviewPackage,
    is_verified_review_package,
    verified_review_package_bytes,
    verified_review_package_value,
)
from ._official_bundle import (
    IncompleteReview,
    VerifiedReviewCompletion,
    completion,
    validate_bundle,
)
from ._official_head import (
    CompletionError,
    GitHubPullRequestHeadSource,
    require_head,
)


@dataclass(frozen=True)
class RollbackOutcome:
    """Filesystem-observed rollback result; no failure is treated as success."""

    restored_previous: bool
    official_path_authoritative: bool
    backup_path: Path | None
    quarantine_path: Path | None
    diagnostics: tuple[Diagnostic, ...]


def _item(code: str, path: str, message: str) -> Diagnostic:
    return Diagnostic(code, path, message)


def diagnostic(code: str, path: str, message: str) -> IncompleteReview:
    return IncompleteReview((_item(code, path, message),))


def stage_directory(output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    return Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent)
    )


def unused_sibling(output: Path, label: str) -> Path:
    path = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.{label}-", dir=output.parent)
    )
    path.rmdir()
    return path


def _authoritative(path: Path) -> bool:
    if not path.is_dir():
        return False
    try:
        return validate_directory(path) == []
    except Exception:
        return False


def _invalidate_manifest(output: Path) -> tuple[Diagnostic, ...]:
    """Make a stranded failed directory non-authoritative before deletion fallback."""

    if not output.exists():
        return ()
    manifest = output / MANIFEST_NAME
    if not manifest.exists():
        return ()
    diagnostics: list[Diagnostic] = []
    try:
        marker = unused_sibling(output, "invalid-manifest")
        os.replace(manifest, marker)
    except Exception as rename_exc:
        diagnostics.append(
            _item(
                "PRI-COMPLETE-ROLLBACK-004",
                f"/{output.name}/{MANIFEST_NAME}",
                f"could not quarantine the failed manifest: {rename_exc}",
            )
        )
        try:
            manifest.unlink()
        except Exception as unlink_exc:
            diagnostics.append(
                _item(
                    "PRI-COMPLETE-ROLLBACK-005",
                    f"/{output.name}/{MANIFEST_NAME}",
                    f"could not remove the failed manifest: {unlink_exc}",
                )
            )
    if _authoritative(output):
        diagnostics.append(
            _item(
                "PRI-COMPLETE-ROLLBACK-006",
                f"/{output.name}",
                "failed output could not be made non-authoritative",
            )
        )
    return tuple(diagnostics)


def _remove_tree(
    path: Path,
    *,
    code: str,
    context: str,
) -> tuple[Diagnostic, ...]:
    if not path.exists():
        return ()
    try:
        shutil.rmtree(path)
    except Exception as exc:
        return (_item(code, f"/{path.name}", f"{context}: {exc}"),)
    if path.exists():
        return (_item(code, f"/{path.name}", f"{context}: path still exists"),)
    return ()


def restore(output: Path, backup: Path | None) -> RollbackOutcome:
    """Quarantine failed publication, restore backup, then clean quarantine.

    Recursive deletion is a cleanup mechanism, never the authoritative rollback
    decision. Failure paths retain backup/quarantine evidence and diagnostics.
    """

    diagnostics: list[Diagnostic] = []
    quarantine: Path | None = None
    restored = False

    if output.exists():
        try:
            quarantine = unused_sibling(output, "quarantine")
            os.replace(output, quarantine)
        except Exception as exc:
            diagnostics.append(
                _item(
                    "PRI-COMPLETE-ROLLBACK-001",
                    f"/{output.name}",
                    f"could not quarantine failed published directory: {exc}",
                )
            )
            diagnostics.extend(_invalidate_manifest(output))
            diagnostics.extend(
                _remove_tree(
                    output,
                    code="PRI-COMPLETE-ROLLBACK-002",
                    context=(
                        "could not delete non-authoritative failed directory"
                    ),
                )
            )
            if output.exists():
                diagnostics.append(
                    _item(
                        "PRI-COMPLETE-ROLLBACK-003",
                        f"/{output.name}",
                        (
                            "failed directory remains at official path after "
                            "deletion attempt"
                        ),
                    )
                )
                diagnostics.extend(_invalidate_manifest(output))

    if backup is not None:
        if not backup.exists():
            diagnostics.append(
                _item(
                    "PRI-COMPLETE-ROLLBACK-007",
                    f"/{backup.name}",
                    "previous-output backup is missing; restoration did not complete",
                )
            )
        elif output.exists():
            diagnostics.append(
                _item(
                    "PRI-COMPLETE-ROLLBACK-008",
                    f"/{output.name}",
                    "official path is occupied; previous-output backup was retained",
                )
            )
        else:
            try:
                os.replace(backup, output)
                restored = output.exists() and not backup.exists()
                if not restored:
                    raise OSError(
                        "backup rename did not establish the official path"
                    )
            except Exception as exc:
                diagnostics.append(
                    _item(
                        "PRI-COMPLETE-ROLLBACK-009",
                        f"/{output.name}",
                        f"could not restore previous-output backup: {exc}",
                    )
                )

    authoritative = _authoritative(output)
    if backup is None and authoritative:
        diagnostics.extend(_invalidate_manifest(output))
        authoritative = _authoritative(output)
    if backup is not None and not restored and authoritative:
        diagnostics.extend(_invalidate_manifest(output))
        authoritative = _authoritative(output)

    cleanup_allowed = restored or (backup is None and not authoritative)
    if quarantine is not None and quarantine.exists() and cleanup_allowed:
        cleanup = _remove_tree(
            quarantine,
            code="PRI-COMPLETE-ROLLBACK-010",
            context="rollback quarantine cleanup failed",
        )
        diagnostics.extend(cleanup)
        if quarantine.exists():
            diagnostics.append(
                _item(
                    "PRI-COMPLETE-ROLLBACK-011",
                    f"/{quarantine.name}",
                    "rollback quarantine remains after cleanup attempt",
                )
            )

    return RollbackOutcome(
        restored_previous=restored,
        official_path_authoritative=authoritative,
        backup_path=backup if backup is not None and backup.exists() else None,
        quarantine_path=(
            quarantine if quarantine is not None and quarantine.exists() else None
        ),
        diagnostics=tuple(diagnostics),
    )


def publish(
    stage: Path,
    output: Path,
) -> tuple[Path | None, tuple[Diagnostic, ...]]:
    backup: Path | None = None
    if output.exists():
        try:
            backup = unused_sibling(output, "backup")
            os.replace(output, backup)
        except Exception as exc:
            return None, (
                _item(
                    "PRI-COMPLETE-005",
                    f"/{output.name}",
                    f"could not move existing output to backup: {exc}",
                ),
            )
    try:
        os.replace(stage, output)
    except Exception as exc:
        rollback = restore(output, backup)
        return None, (
            _item(
                "PRI-COMPLETE-005",
                f"/{output.name}",
                f"could not publish validated staging directory: {exc}",
            ),
            *rollback.diagnostics,
        )
    return backup, ()


def _bounded_restore(
    output: Path,
    backup: Path | None,
) -> RollbackOutcome:
    try:
        return restore(output, backup)
    except Exception as exc:
        diagnostics = [
            _item(
                "PRI-COMPLETE-ROLLBACK-999",
                f"/{output.name}",
                f"unexpected rollback failure was bounded: {exc}",
            )
        ]
        try:
            diagnostics.extend(_invalidate_manifest(output))
        except Exception as invalidate_exc:
            diagnostics.append(
                _item(
                    "PRI-COMPLETE-ROLLBACK-998",
                    f"/{output.name}",
                    f"emergency non-authoritative marking failed: {invalidate_exc}",
                )
            )
        return RollbackOutcome(
            restored_previous=False,
            official_path_authoritative=_authoritative(output),
            backup_path=backup if backup is not None and backup.exists() else None,
            quarantine_path=None,
            diagnostics=tuple(diagnostics),
        )


def complete_review(
    package: CanonicalReviewPackage,
    output_directory: Path,
    *,
    head_source: GitHubPullRequestHeadSource,
) -> VerifiedReviewCompletion | IncompleteReview:
    """Publish one package assembled by the in-process official runtime."""

    if not is_verified_review_package(package):
        return diagnostic(
            "PRI-PACKAGE-AUTHORITY-001",
            "/verified-review-package",
            (
                "official completion requires CanonicalReviewPackage from the in-process assembler; raw JSON, paths, mappings, and legacy package files are non-authoritative"
            ),
        )
    output = Path(output_directory)
    try:
        initial = head_source.fetch()
    except Exception as exc:
        return diagnostic(
            "PRI-COMPLETE-008",
            "/live-target-head",
            f"official completion requires verified live GitHub evidence: {exc}",
        )
    try:
        package_bytes = verified_review_package_bytes(package)
        package_value = verified_review_package_value(package)
    except ReviewAssemblyError as exc:
        return diagnostic("PRI-PACKAGE-AUTHORITY-002", "/verified-review-package", str(exc))
    if package.protocol_version != "v1.12.0":
        return diagnostic(
            "PRI-PACKAGE-AUTHORITY-003",
            "/verified-review-package/protocol-version",
            "official completion accepts only an active v1.12.0 canonical assembled package",
        )
    try:
        require_head(initial, package.repository, package.pr_number, package.head_sha)
        if initial.repository_id != package.repository_id:
            raise CompletionError("live repository id does not match verified package")
        if initial.base_sha != package.base_sha:
            raise CompletionError("live PR base does not match verified package")
    except CompletionError as exc:
        return diagnostic("PRI-COMPLETE-007", "/review_identity", str(exc))
    try:
        diagnostics = validate_package(package_value)
    except Exception as exc:
        return diagnostic("PRI-COMPLETE-002", "/package-validation", str(exc))
    if diagnostics:
        return IncompleteReview(tuple(diagnostics))
    identity = package_value["review_identity"]
    if identity["review_validity"] != "CURRENT":
        return diagnostic(
            "PRI-COMPLETE-007",
            "/review_identity/review_validity",
            "official completion requires CURRENT review validity",
        )
    if output.exists() and not output.is_dir():
        return diagnostic(
            "PRI-COMPLETE-005",
            f"/{output.name}",
            "output is not a directory",
        )
    try:
        stage = stage_directory(output)
    except Exception as exc:
        return diagnostic("PRI-COMPLETE-005", f"/{output.name}", str(exc))

    result: VerifiedReviewCompletion | IncompleteReview
    try:
        try:
            (stage / "review-package.json").write_bytes(package_bytes)
            write_review_artifacts(
                package_value,
                stage,
                review_package_bytes=package_bytes,
            )
            staged = validate_bundle(
                stage,
                initial.repository,
                initial.pr_number,
                initial.head_sha,
            )
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            ProjectionError,
            CompletionError,
        ) as exc:
            return diagnostic("PRI-COMPLETE-004", "/artifact-bundle", str(exc))
        try:
            require_head(
                head_source.fetch(),
                staged.repository,
                staged.pr_number,
                staged.head_sha,
            )
        except Exception as exc:
            return diagnostic(
                "PRI-COMPLETE-008",
                "/prepublication-head-recheck",
                str(exc),
            )

        backup, publication_diagnostics = publish(stage, output)
        if publication_diagnostics:
            return IncompleteReview(publication_diagnostics)

        try:
            final_bundle = validate_bundle(
                output,
                initial.repository,
                initial.pr_number,
                initial.head_sha,
            )
            final_head = head_source.fetch()
            require_head(
                final_head,
                final_bundle.repository,
                final_bundle.pr_number,
                final_bundle.head_sha,
            )
        except Exception as exc:
            rollback = _bounded_restore(output, backup)
            return IncompleteReview(
                (
                    _item(
                        "PRI-COMPLETE-008",
                        "/final-head-recheck",
                        str(exc),
                    ),
                    *rollback.diagnostics,
                )
            )

        # Publication is committed after post-publication bundle validation and the
        # final live-head check. The obsolete backup is cleanup-only from here on;
        # it may already be partially mutated by a failed recursive deletion and
        # must never be used as rollback evidence after this point.
        cleanup_diagnostics: tuple[Diagnostic, ...] = ()
        if backup is not None:
            cleanup_diagnostics = _remove_tree(
                backup,
                code="PRI-COMPLETE-009",
                context="previous-output backup cleanup failed",
            )
        result = completion(
            final_bundle,
            head_source,
            final_head,
            cleanup_diagnostics=cleanup_diagnostics,
        )
        return result
    except Exception as exc:
        return diagnostic(
            "PRI-COMPLETE-999",
            "/official-review-boundary",
            f"unexpected handled completion failure: {exc}",
        )
    finally:
        if stage.exists():
            try:
                shutil.rmtree(stage)
            except Exception:
                # Staging is never an official output path. All authoritative-path
                # failures are reported by publish/restore before this cleanup.
                pass
