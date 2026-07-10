from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

from .decision_projection import ProjectionError
from .derived_outputs import write_review_artifacts
from .diagnostics import Diagnostic
from .validation_v2 import validate_package
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


def diagnostic(code: str, path: str, message: str) -> IncompleteReview:
    return IncompleteReview((Diagnostic(code, path, message),))


def stage_directory(output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))


def unused_sibling(output: Path, label: str) -> Path:
    path = Path(tempfile.mkdtemp(prefix=f".{output.name}.{label}-", dir=output.parent))
    path.rmdir()
    return path


def publish(stage: Path, output: Path) -> Path | None:
    backup = None
    if output.exists():
        backup = unused_sibling(output, "backup")
        os.replace(output, backup)
    try:
        os.replace(stage, output)
    except OSError:
        if backup is not None and backup.exists():
            os.replace(backup, output)
        raise
    return backup


def restore(output: Path, backup: Path | None) -> None:
    if output.exists():
        shutil.rmtree(output, ignore_errors=True)
    if backup is not None and backup.exists():
        os.replace(backup, output)


def complete_review(
    package_path: Path,
    output_directory: Path,
    *,
    head_source: GitHubPullRequestHeadSource,
) -> VerifiedReviewCompletion | IncompleteReview:
    package_path = Path(package_path)
    output = Path(output_directory)
    try:
        initial = head_source.fetch()
    except (AttributeError, CompletionError) as exc:
        return diagnostic(
            "PRI-COMPLETE-008",
            "/live-target-head",
            f"official completion requires verified live GitHub evidence: {exc}",
        )
    try:
        package_bytes = package_path.read_bytes()
        package = json.loads(package_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return diagnostic("PRI-COMPLETE-001", "/review-package.json", str(exc))
    if not isinstance(package, dict):
        return diagnostic("PRI-COMPLETE-001", "/review-package.json", "package must be an object")
    try:
        diagnostics = validate_package(package)
    except Exception as exc:
        return diagnostic("PRI-COMPLETE-002", "/package-validation", str(exc))
    if diagnostics:
        return IncompleteReview(tuple(diagnostics))
    identity = package["review_identity"]
    try:
        require_head(
            initial,
            identity["target_repository"],
            identity["pr_number"],
            identity["reviewed_head_sha"],
        )
    except CompletionError as exc:
        return diagnostic("PRI-COMPLETE-007", "/review_identity", str(exc))
    if identity["review_validity"] != "CURRENT":
        return diagnostic(
            "PRI-COMPLETE-007",
            "/review_identity/review_validity",
            "official completion requires CURRENT review validity",
        )
    if output.exists() and not output.is_dir():
        return diagnostic("PRI-COMPLETE-005", f"/{output.name}", "output is not a directory")
    try:
        stage = stage_directory(output)
    except OSError as exc:
        return diagnostic("PRI-COMPLETE-005", f"/{output.name}", str(exc))
    backup = None
    published = False
    try:
        (stage / "review-package.json").write_bytes(package_bytes)
        try:
            write_review_artifacts(package, stage, review_package_bytes=package_bytes)
            staged = validate_bundle(stage, initial.repository, initial.pr_number, initial.head_sha)
        except (OSError, ValueError, KeyError, TypeError, ProjectionError, CompletionError) as exc:
            return diagnostic("PRI-COMPLETE-004", "/artifact-bundle", str(exc))
        try:
            require_head(
                head_source.fetch(), staged.repository, staged.pr_number, staged.head_sha
            )
        except CompletionError as exc:
            return diagnostic("PRI-COMPLETE-008", "/prepublication-head-recheck", str(exc))
        try:
            backup = publish(stage, output)
            published = True
        except OSError as exc:
            return diagnostic("PRI-COMPLETE-005", f"/{output.name}", str(exc))
        try:
            final_bundle = validate_bundle(
                output, initial.repository, initial.pr_number, initial.head_sha
            )
            final_head = head_source.fetch()
            require_head(
                final_head,
                final_bundle.repository,
                final_bundle.pr_number,
                final_bundle.head_sha,
            )
        except CompletionError as exc:
            restore(output, backup)
            published = False
            return diagnostic("PRI-COMPLETE-008", "/final-head-recheck", str(exc))
        if backup is not None:
            shutil.rmtree(backup, ignore_errors=True)
        return completion(final_bundle, head_source, final_head)
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        if not published and backup is not None and backup.exists() and not output.exists():
            os.replace(backup, output)
