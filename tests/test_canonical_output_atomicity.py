import copy
import json
from pathlib import Path

from pr_inspector.derived_outputs import build_review_artifacts
from pr_inspector.governance import (
    verify_github_governance_source,
    verify_governance_record,
)
from pr_inspector.official_review import (
    CompletionError,
    IncompleteReview,
    complete_review,
    github_pull_request_head_source,
    is_verified_review_completion,
    verify_completed_review,
)
from pr_inspector.sequence_enforcement import (
    SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
    verify_sequence_ci_enforcement,
    verify_sequence_producer_evidence,
)
from pr_inspector.validation_v2 import validate_directory
from tests.governance_test_support import (
    fixture as governance_fixture,
    responses as governance_responses,
)
from tests.verified_review_test_support import complete_fixture_review

ROOT = Path(__file__).resolve().parents[1]
_ASSEMBLED_PACKAGES = {}
REPOSITORY = "example/project"
REPOSITORY_ID = 4242
PR_NUMBER = 42
HEAD = "1" * 40
OTHER_HEAD = "f" * 40
API_VERSION = "2026-03-10"


def package(name: str = "golden-green") -> dict:
    return json.loads(
        (ROOT / "fixtures" / name / "review-package.json").read_text(
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


def pr_payload(head_sha: str = HEAD) -> dict:
    api_url = f"https://api.github.com/repos/{REPOSITORY}/pulls/{PR_NUMBER}"
    return {
        "number": PR_NUMBER,
        "url": api_url,
        "html_url": f"https://github.com/{REPOSITORY}/pull/{PR_NUMBER}",
        "state": "open",
        "base": {
            "repo": {"id": REPOSITORY_ID, "full_name": REPOSITORY},
            "sha": "2" * 40,
            "ref": "main",
        },
        "head": {"sha": head_sha, "ref": "feature"},
    }


def install_payloads(monkeypatch, payloads: list[dict] | None = None):
    from pr_inspector import _official_head

    queue = list(payloads or [])

    def fake_github_json(url, *, token, api_version):
        if queue:
            return copy.deepcopy(queue.pop(0))
        return pr_payload()

    monkeypatch.setattr(_official_head, "_github_json", fake_github_json)


def source():
    return github_pull_request_head_source(
        REPOSITORY,
        PR_NUMBER,
        token=None,
        api_version=API_VERSION,
    )


def profile_sequence_capability():
    value = governance_fixture()
    value["responses"]["checks"]["payload"]["check_runs"][0]["name"] = (
        SEQUENCE_ENFORCEMENT_CHECK_CONTEXT
    )
    required = value["responses"]["branch_protection"]["payload"][
        "required_status_checks"
    ]
    required["checks"][0]["context"] = SEQUENCE_ENFORCEMENT_CHECK_CONTEXT
    required["contexts"] = [SEQUENCE_ENFORCEMENT_CHECK_CONTEXT]
    source_evidence = verify_github_governance_source(
        governance_responses(value),
        expected_repository=REPOSITORY,
        expected_pr_number=PR_NUMBER,
        expected_head_sha=HEAD,
    )
    governance = verify_governance_record(
        source_evidence,
        expected_repository=REPOSITORY,
        expected_pr_number=PR_NUMBER,
        expected_head_sha=HEAD,
    )
    producer = verify_sequence_producer_evidence(
        governance,
        check_context=SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
        app_id=15368,
        workflow_path=".github/workflows/validate-rereview-sequence.yml",
        workflow_sha="2" * 40,
        validator_command="python scripts/validate_rereview_sequence.py sequence.json --review EVENT=review",
    )
    return verify_sequence_ci_enforcement(
        governance,
        check_context=SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
        app_id=15368,
        producer_evidence=producer,
    )


def sequence_capability_for(value: dict):
    if value["decision"]["technical_status"] != "GREEN_TECHNICALLY_READY":
        return None
    return profile_sequence_capability()


def complete_with_evidence(value: dict, output: Path):
    result, package = complete_fixture_review(
        value,
        output,
        head_source=source(),
        sequence_enforcement=sequence_capability_for(value),
    )
    _ASSEMBLED_PACKAGES[output.resolve()] = package
    return result


def verify_with_evidence(completion):
    return verify_completed_review(completion)


def run_review(
    tmp_path: Path,
    monkeypatch,
    payloads=None,
    output=None,
    fixture: str = "golden-green",
):
    install_payloads(monkeypatch, payloads)
    value = package(fixture)
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    output = output or tmp_path / "review"
    return (
        complete_with_evidence(value, output),
        output,
        value,
    )


def codes(result: IncompleteReview) -> set[str]:
    return {item.code for item in result.diagnostics}


def assert_not_authoritative(path: Path):
    if path.exists():
        assert validate_directory(path) != []


def test_post_publication_failure_without_prior_output_leaves_no_official_bundle(
    tmp_path,
    monkeypatch,
):
    result, output, _ = run_review(
        tmp_path,
        monkeypatch,
        [pr_payload(), pr_payload(), pr_payload(OTHER_HEAD)],
    )
    assert isinstance(result, IncompleteReview)
    assert not output.exists()


def test_existing_valid_output_is_restored_after_post_publication_failure(
    tmp_path,
    monkeypatch,
):
    first, output, value = run_review(tmp_path, monkeypatch)
    assert is_verified_review_completion(first)
    original_manifest = (output / "artifact-manifest.json").read_bytes()

    package_path = tmp_path / "second.json"
    write_package(package_path, value)
    install_payloads(
        monkeypatch,
        [pr_payload(), pr_payload(), pr_payload(OTHER_HEAD)],
    )
    result = complete_with_evidence(value, output)

    assert isinstance(result, IncompleteReview)
    assert (output / "artifact-manifest.json").read_bytes() == original_manifest
    install_payloads(monkeypatch)
    assert verify_with_evidence(first) is first


def test_quarantine_rename_failure_falls_back_to_explicit_delete_and_restore(
    tmp_path,
    monkeypatch,
):
    from pr_inspector import _official_complete

    first, output, value = run_review(tmp_path, monkeypatch)
    assert is_verified_review_completion(first)
    package_path = tmp_path / "second.json"
    write_package(package_path, value)
    install_payloads(
        monkeypatch,
        [pr_payload(), pr_payload(), pr_payload(OTHER_HEAD)],
    )
    real_replace = _official_complete.os.replace

    def fail_quarantine(source_path, destination):
        if Path(source_path) == output and ".quarantine-" in Path(destination).name:
            raise OSError("simulated quarantine rename failure")
        return real_replace(source_path, destination)

    monkeypatch.setattr(_official_complete.os, "replace", fail_quarantine)
    result = complete_with_evidence(value, output)

    assert isinstance(result, IncompleteReview)
    assert "PRI-COMPLETE-ROLLBACK-001" in codes(result)
    assert output.exists()
    install_payloads(monkeypatch)
    assert verify_with_evidence(first) is first


def test_failed_published_directory_deletion_leaves_only_non_authoritative_files(
    tmp_path,
    monkeypatch,
):
    from pr_inspector import _official_complete

    first, output, value = run_review(tmp_path, monkeypatch)
    assert is_verified_review_completion(first)
    package_path = tmp_path / "second.json"
    write_package(package_path, value)
    install_payloads(
        monkeypatch,
        [pr_payload(), pr_payload(), pr_payload(OTHER_HEAD)],
    )
    real_replace = _official_complete.os.replace
    real_rmtree = _official_complete.shutil.rmtree

    def fail_quarantine(source_path, destination):
        if Path(source_path) == output and ".quarantine-" in Path(destination).name:
            raise OSError("simulated quarantine rename failure")
        return real_replace(source_path, destination)

    def fail_delete(path, *args, **kwargs):
        if Path(path) == output:
            raise OSError("simulated deletion failure")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(_official_complete.os, "replace", fail_quarantine)
    monkeypatch.setattr(_official_complete.shutil, "rmtree", fail_delete)
    result = complete_with_evidence(value, output)

    assert isinstance(result, IncompleteReview)
    assert "PRI-COMPLETE-ROLLBACK-002" in codes(result)
    assert output.exists()
    assert not (output / "artifact-manifest.json").exists()
    assert_not_authoritative(output)
    assert list(tmp_path.glob(".review.backup-*"))


def test_backup_restore_failure_keeps_official_path_absent_and_evidence_retained(
    tmp_path,
    monkeypatch,
):
    from pr_inspector import _official_complete

    first, output, value = run_review(tmp_path, monkeypatch)
    assert is_verified_review_completion(first)
    package_path = tmp_path / "second.json"
    write_package(package_path, value)
    install_payloads(
        monkeypatch,
        [pr_payload(), pr_payload(), pr_payload(OTHER_HEAD)],
    )
    real_replace = _official_complete.os.replace

    def fail_restore(source_path, destination):
        if ".backup-" in Path(source_path).name and Path(destination) == output:
            raise OSError("simulated backup restore failure")
        return real_replace(source_path, destination)

    monkeypatch.setattr(_official_complete.os, "replace", fail_restore)
    result = complete_with_evidence(value, output)

    assert isinstance(result, IncompleteReview)
    assert "PRI-COMPLETE-ROLLBACK-009" in codes(result)
    assert not output.exists()
    assert list(tmp_path.glob(".review.backup-*"))
    assert list(tmp_path.glob(".review.quarantine-*"))


def test_unexpected_rollback_exception_is_bounded_and_manifest_invalidated(
    tmp_path,
    monkeypatch,
):
    from pr_inspector import _official_complete

    first, output, value = run_review(tmp_path, monkeypatch)
    assert is_verified_review_completion(first)
    package_path = tmp_path / "second.json"
    write_package(package_path, value)
    install_payloads(
        monkeypatch,
        [pr_payload(), pr_payload(), pr_payload(OTHER_HEAD)],
    )

    def explode(*args, **kwargs):
        raise RuntimeError("simulated unexpected rollback failure")

    monkeypatch.setattr(_official_complete, "restore", explode)
    result = complete_with_evidence(value, output)

    assert isinstance(result, IncompleteReview)
    assert "PRI-COMPLETE-ROLLBACK-999" in codes(result)
    assert_not_authoritative(output)


def test_quarantine_cleanup_failure_is_reported_not_successful_rollback(
    tmp_path,
    monkeypatch,
):
    from pr_inspector import _official_complete

    first, output, value = run_review(tmp_path, monkeypatch)
    assert is_verified_review_completion(first)
    package_path = tmp_path / "second.json"
    write_package(package_path, value)
    install_payloads(
        monkeypatch,
        [pr_payload(), pr_payload(), pr_payload(OTHER_HEAD)],
    )
    real_rmtree = _official_complete.shutil.rmtree

    def fail_quarantine_cleanup(path, *args, **kwargs):
        if ".quarantine-" in Path(path).name:
            raise OSError("simulated quarantine cleanup failure")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(
        _official_complete.shutil,
        "rmtree",
        fail_quarantine_cleanup,
    )
    result = complete_with_evidence(value, output)

    assert isinstance(result, IncompleteReview)
    assert {
        "PRI-COMPLETE-ROLLBACK-010",
        "PRI-COMPLETE-ROLLBACK-011",
    }.issubset(codes(result))
    install_payloads(monkeypatch)
    assert verify_with_evidence(first) is first
    assert list(tmp_path.glob(".review.quarantine-*"))


def test_partial_backup_cleanup_failure_after_commit_keeps_new_official_bundle(
    tmp_path,
    monkeypatch,
):
    from pr_inspector import _official_complete

    first, output, _ = run_review(tmp_path, monkeypatch)
    assert is_verified_review_completion(first)
    previous_owner_result = (output / "OWNER_RESULT.fa.txt").read_bytes()

    second = package("repair-handoff-valid")

    install_payloads(monkeypatch)
    real_rmtree = _official_complete.shutil.rmtree
    observed_backups: list[Path] = []

    def partially_delete_backup(path, *args, **kwargs):
        candidate = Path(path)
        if ".backup-" in candidate.name:
            observed_backups.append(candidate)
            (candidate / "OWNER_RESULT.fa.txt").unlink()
            raise OSError("simulated partial backup cleanup failure")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(
        _official_complete.shutil,
        "rmtree",
        partially_delete_backup,
    )
    result = complete_with_evidence(second, output)
    canonical = _ASSEMBLED_PACKAGES[output.resolve()]
    expected = build_review_artifacts(
        canonical.value(),
        review_package_bytes=canonical.canonical_bytes,
    )
    expected_owner_result = expected["OWNER_RESULT.fa.txt"].encode("utf-8")
    assert expected_owner_result != previous_owner_result

    assert is_verified_review_completion(result)
    assert {item.code for item in result.cleanup_diagnostics} == {
        "PRI-COMPLETE-009"
    }
    assert (output / "OWNER_RESULT.fa.txt").read_bytes() == expected_owner_result
    assert observed_backups
    partial_backup = observed_backups[0]
    assert partial_backup.exists()
    assert not (partial_backup / "OWNER_RESULT.fa.txt").exists()

    install_payloads(monkeypatch)
    verified = verify_with_evidence(result)
    assert is_verified_review_completion(verified)
    assert verified.owner_result_text() == expected["OWNER_RESULT.fa.txt"]


def test_publication_failure_does_not_escape_supported_api(
    tmp_path,
    monkeypatch,
):
    from pr_inspector import _official_complete

    install_payloads(monkeypatch)
    value = package()
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    output = tmp_path / "review"

    def explode(*args, **kwargs):
        raise RuntimeError("simulated publication boundary failure")

    monkeypatch.setattr(_official_complete, "publish", explode)
    result = complete_with_evidence(value, output)
    assert isinstance(result, IncompleteReview)
    assert codes(result) == {"PRI-COMPLETE-999"}
