import importlib.util
import json
import sys
from pathlib import Path

import pytest

from pr_inspector.official_review import (
    CompletionError,
    IncompleteReview,
    complete_review,
    verify_completed_review,
)
from pr_inspector.validation_v2 import validate_directory

ROOT = Path(__file__).resolve().parents[1]


def package() -> dict:
    return json.loads(
        (ROOT / "fixtures/golden-green/review-package.json").read_text(
            encoding="utf-8"
        )
    )


def write_package(path: Path, value: dict) -> None:
    path.write_bytes(
        (
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    )


def identity_kwargs(value: dict) -> dict:
    identity = value["review_identity"]
    return {
        "expected_target_repository": identity["target_repository"],
        "expected_pr_number": identity["pr_number"],
        "expected_reviewed_head_sha": identity["reviewed_head_sha"],
    }


def force_post_publication_verification_failure(monkeypatch):
    from pr_inspector import official_review

    real_verify = official_review.verify_completed_review
    calls = 0

    def fail_second_verification(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise CompletionError("simulated post-publication failure")
        return real_verify(*args, **kwargs)

    monkeypatch.setattr(
        official_review,
        "verify_completed_review",
        fail_second_verification,
    )


def create_existing_sentinel(output: Path) -> Path:
    output.mkdir()
    sentinel = output / "existing.txt"
    sentinel.write_text("preserve\n", encoding="utf-8", newline="\n")
    return sentinel


def diagnostic_codes(result: IncompleteReview) -> set[str]:
    return {item.code for item in result.diagnostics}


def assert_not_authoritative(path: Path) -> None:
    if path.exists():
        assert validate_directory(path) != []


def test_atomic_swap_failure_preserves_existing_output(tmp_path, monkeypatch):
    from pr_inspector import official_review

    value = package()
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    output = tmp_path / "review"
    sentinel = create_existing_sentinel(output)
    real_replace = official_review.os.replace

    def fail_before_existing_move(source, destination):
        if Path(source) == output:
            raise OSError("simulated swap failure")
        return real_replace(source, destination)

    monkeypatch.setattr(official_review.os, "replace", fail_before_existing_move)
    result = official_review.complete_review(
        package_path,
        output,
        **identity_kwargs(value),
    )
    assert isinstance(result, IncompleteReview)
    assert sentinel.read_text(encoding="utf-8") == "preserve\n"


def test_post_publish_verification_failure_rolls_back_existing_output(
    tmp_path,
    monkeypatch,
):
    value = package()
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    output = tmp_path / "review"
    sentinel = create_existing_sentinel(output)
    force_post_publication_verification_failure(monkeypatch)

    result = complete_review(package_path, output, **identity_kwargs(value))

    assert isinstance(result, IncompleteReview)
    assert sentinel.read_text(encoding="utf-8") == "preserve\n"
    assert not (output / "OWNER_RESULT.fa.txt").exists()


def test_quarantine_rename_failure_falls_back_to_delete_and_restore(
    tmp_path,
    monkeypatch,
):
    from pr_inspector import official_review

    value = package()
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    output = tmp_path / "review"
    sentinel = create_existing_sentinel(output)
    force_post_publication_verification_failure(monkeypatch)
    real_replace = official_review.os.replace

    def fail_quarantine_only(source, destination):
        destination = Path(destination)
        if Path(source) == output and ".quarantine-" in destination.name:
            raise OSError("simulated quarantine rename failure")
        return real_replace(source, destination)

    monkeypatch.setattr(official_review.os, "replace", fail_quarantine_only)
    result = complete_review(package_path, output, **identity_kwargs(value))

    assert isinstance(result, IncompleteReview)
    assert "PRI-COMPLETE-ROLLBACK-001" in diagnostic_codes(result)
    assert sentinel.read_text(encoding="utf-8") == "preserve\n"
    assert not list(tmp_path.glob(".review.backup-*"))


def test_failed_deletion_leaves_only_a_non_authoritative_directory(
    tmp_path,
    monkeypatch,
):
    from pr_inspector import official_review

    value = package()
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    output = tmp_path / "review"
    create_existing_sentinel(output)
    force_post_publication_verification_failure(monkeypatch)
    real_replace = official_review.os.replace
    real_rmtree = official_review.shutil.rmtree

    def fail_quarantine(source, destination):
        if Path(source) == output and ".quarantine-" in Path(destination).name:
            raise OSError("simulated quarantine rename failure")
        return real_replace(source, destination)

    def fail_published_delete(path, *args, **kwargs):
        if Path(path) == output:
            raise OSError("simulated deletion failure with files left behind")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(official_review.os, "replace", fail_quarantine)
    monkeypatch.setattr(official_review.shutil, "rmtree", fail_published_delete)
    result = complete_review(package_path, output, **identity_kwargs(value))

    assert isinstance(result, IncompleteReview)
    codes = diagnostic_codes(result)
    assert "PRI-COMPLETE-ROLLBACK-001" in codes
    assert "PRI-COMPLETE-ROLLBACK-002" in codes
    assert "PRI-COMPLETE-ROLLBACK-003" in codes
    assert output.exists()
    assert not (output / "artifact-manifest.json").exists()
    assert_not_authoritative(output)
    assert list(tmp_path.glob(".review.backup-*"))


def test_backup_restore_failure_leaves_official_path_absent_and_evidence_retained(
    tmp_path,
    monkeypatch,
):
    from pr_inspector import official_review

    value = package()
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    output = tmp_path / "review"
    create_existing_sentinel(output)
    force_post_publication_verification_failure(monkeypatch)
    real_replace = official_review.os.replace

    def fail_backup_restore(source, destination):
        if ".backup-" in Path(source).name and Path(destination) == output:
            raise OSError("simulated backup restore failure")
        return real_replace(source, destination)

    monkeypatch.setattr(official_review.os, "replace", fail_backup_restore)
    result = complete_review(package_path, output, **identity_kwargs(value))

    assert isinstance(result, IncompleteReview)
    assert "PRI-COMPLETE-ROLLBACK-009" in diagnostic_codes(result)
    assert not output.exists()
    assert list(tmp_path.glob(".review.backup-*"))
    assert list(tmp_path.glob(".review.quarantine-*"))


def test_post_publish_failure_without_prior_output_leaves_no_official_bundle(
    tmp_path,
    monkeypatch,
):
    value = package()
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    output = tmp_path / "review"
    force_post_publication_verification_failure(monkeypatch)

    result = complete_review(package_path, output, **identity_kwargs(value))

    assert isinstance(result, IncompleteReview)
    assert not output.exists()
    assert not list(tmp_path.glob(".review.quarantine-*"))


def test_restore_failure_retains_previous_valid_bundle_as_backup(
    tmp_path,
    monkeypatch,
):
    from pr_inspector import official_review

    value = package()
    first_package = tmp_path / "first.json"
    write_package(first_package, value)
    output = tmp_path / "review"
    first = complete_review(first_package, output, **identity_kwargs(value))
    assert not isinstance(first, IncompleteReview)

    second_package = tmp_path / "second.json"
    write_package(second_package, value)
    force_post_publication_verification_failure(monkeypatch)
    real_replace = official_review.os.replace

    def fail_backup_restore(source, destination):
        if ".backup-" in Path(source).name and Path(destination) == output:
            raise OSError("simulated restore failure")
        return real_replace(source, destination)

    monkeypatch.setattr(official_review.os, "replace", fail_backup_restore)
    result = complete_review(second_package, output, **identity_kwargs(value))

    assert isinstance(result, IncompleteReview)
    assert not output.exists()
    backups = list(tmp_path.glob(".review.backup-*"))
    assert len(backups) == 1
    verify_completed_review(backups[0], **identity_kwargs(value))


def test_rollback_helper_exception_is_bounded_by_supported_api(
    tmp_path,
    monkeypatch,
):
    from pr_inspector import official_review

    value = package()
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    output = tmp_path / "review"
    create_existing_sentinel(output)
    force_post_publication_verification_failure(monkeypatch)

    def unexpected_rollback_failure(*args, **kwargs):
        raise RuntimeError("simulated unexpected rollback exception")

    monkeypatch.setattr(
        official_review,
        "_restore_previous_directory",
        unexpected_rollback_failure,
    )
    result = complete_review(package_path, output, **identity_kwargs(value))

    assert isinstance(result, IncompleteReview)
    assert diagnostic_codes(result) == {"PRI-COMPLETE-999"}


def test_cleanup_failure_is_reported_and_not_called_successful_rollback(
    tmp_path,
    monkeypatch,
):
    from pr_inspector import official_review

    value = package()
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    output = tmp_path / "review"
    sentinel = create_existing_sentinel(output)
    force_post_publication_verification_failure(monkeypatch)
    real_rmtree = official_review.shutil.rmtree

    def fail_quarantine_cleanup(path, *args, **kwargs):
        if ".quarantine-" in Path(path).name:
            raise OSError("simulated quarantine cleanup failure")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(official_review.shutil, "rmtree", fail_quarantine_cleanup)
    result = complete_review(package_path, output, **identity_kwargs(value))

    assert isinstance(result, IncompleteReview)
    codes = diagnostic_codes(result)
    assert "PRI-COMPLETE-ROLLBACK-010" in codes
    assert "PRI-COMPLETE-ROLLBACK-011" in codes
    assert sentinel.read_text(encoding="utf-8") == "preserve\n"
    assert list(tmp_path.glob(".review.quarantine-*"))


def test_cli_converts_unexpected_boundary_exception_to_bounded_failure(
    tmp_path,
    monkeypatch,
    capsys,
):
    script_path = ROOT / "scripts" / "render_review_v2.py"
    spec = importlib.util.spec_from_file_location("render_review_v2_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def fail_boundary(*args, **kwargs):
        raise OSError("simulated CLI boundary failure")

    monkeypatch.setattr(module, "complete_review", fail_boundary)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(script_path),
            str(tmp_path / "review-package.json"),
            "--output-dir",
            str(tmp_path / "review"),
            "--expected-target-repository",
            "example/project",
            "--expected-pr-number",
            "1",
            "--expected-reviewed-head-sha",
            "a" * 40,
        ],
    )

    assert module.main() == 1
    stderr = capsys.readouterr().err
    assert "The official PR Inspector review did not complete." in stderr
    assert "PRI-COMPLETE-999" in stderr
