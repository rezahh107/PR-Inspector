import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from pr_inspector.derived_outputs import (
    MANIFEST_NAME,
    PROJECTION_NAME,
    PROMPT_NAME,
    build_review_artifacts,
)
from pr_inspector.governance import (
    verify_github_governance_source,
    verify_governance_record,
)
from pr_inspector.official_review import (
    CompletionError,
    IncompleteReview,
    VerifiedReviewCompletion,
    complete_review,
    github_pull_request_head_source,
    is_verified_review_completion,
    official_next_action_prompt,
    official_owner_delivery,
    official_owner_result,
    official_technical_handoff,
    verify_completed_review,
)
from pr_inspector.sequence_enforcement import (
    SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
    verify_sequence_ci_enforcement,
    verify_sequence_producer_evidence,
)
from tests.governance_test_support import (
    fixture as governance_fixture,
    responses as governance_responses,
)

ROOT = Path(__file__).resolve().parents[1]
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


def write_package(path: Path, value: dict) -> bytes:
    raw = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    path.write_bytes(raw)
    return raw


def rewrite_json(path: Path, value: dict) -> None:
    path.write_bytes(
        (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
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
        "base": {"repo": {"id": REPOSITORY_ID, "full_name": REPOSITORY}},
        "head": {"sha": head_sha},
    }


def install_live_payloads(monkeypatch, payloads: list[dict] | None = None):
    from pr_inspector import _official_head

    queue = list(payloads or [])

    def fake_github_json(url, *, token, api_version):
        assert url == f"https://api.github.com/repos/{REPOSITORY}/pulls/{PR_NUMBER}"
        assert api_version == API_VERSION
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


def completed_bundle(
    tmp_path: Path,
    monkeypatch,
    name: str = "golden-green",
):
    install_live_payloads(monkeypatch)
    value = package(name)
    package_path = tmp_path / f"{name}.json"
    write_package(package_path, value)
    output = tmp_path / "review"
    sequence_enforcement = (
        profile_sequence_capability() if name == "golden-green" else None
    )
    result = complete_review(
        package_path,
        output,
        head_source=source(),
        sequence_enforcement=sequence_enforcement,
    )
    assert is_verified_review_completion(result)
    assert isinstance(result, VerifiedReviewCompletion)
    return result, output, value


def mutate_after_bundle_verification(
    monkeypatch,
    output: Path,
    artifact_name: str,
    unverified_bytes: bytes,
) -> None:
    from pr_inspector import _official_bundle

    real_validate_bundle = _official_bundle.validate_bundle

    def validate_then_mutate(*args, **kwargs):
        bundle = real_validate_bundle(*args, **kwargs)
        (output / artifact_name).write_bytes(unverified_bytes)
        return bundle

    monkeypatch.setattr(
        _official_bundle,
        "validate_bundle",
        validate_then_mutate,
    )


def test_schema_valid_but_semantically_invalid_package_has_no_completion(
    tmp_path,
    monkeypatch,
):
    install_live_payloads(monkeypatch)
    value = package()
    value["decision"]["technical_status"] = "RED_DO_NOT_MERGE"
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    result = complete_review(
        package_path,
        tmp_path / "review",
        head_source=source(),
    )
    assert isinstance(result, IncompleteReview)
    assert not (tmp_path / "review").exists()
    assert not hasattr(result, "technical_status")
    assert "No valid decision or action prompt was produced." in result.technical_message


@pytest.mark.parametrize(
    "field,value",
    [
        ("technical_status", "RED_DO_NOT_MERGE"),
        ("approval_requirement", "PROJECT_OWNER_CONFIRMATION"),
    ],
)
def test_caller_projection_drift_is_rejected(
    tmp_path,
    monkeypatch,
    field,
    value,
):
    completion, output, _ = completed_bundle(tmp_path, monkeypatch)
    projection_path = output / PROJECTION_NAME
    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    projection[field] = value
    rewrite_json(projection_path, projection)
    with pytest.raises(CompletionError):
        official_owner_result(completion)


def test_manual_action_and_owner_output_are_rejected(tmp_path, monkeypatch):
    completion, output, _ = completed_bundle(
        tmp_path,
        monkeypatch,
        "repair-handoff-valid",
    )
    projection_path = output / PROJECTION_NAME
    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    projection["next_action"]["kind"] = "merge_now"
    rewrite_json(projection_path, projection)
    (output / "OWNER_RESULT.fa.txt").write_text(
        "🟢 وضعیت: آمادهٔ مرج\nمرج کن.\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(CompletionError):
        official_owner_result(completion)


@pytest.mark.parametrize(
    "missing_name",
    [
        PROJECTION_NAME,
        "OWNER_DECISION_CARD.fa.md",
        "TECHNICAL_HANDOFF.en.md",
        "OWNER_RESULT.fa.txt",
        MANIFEST_NAME,
    ],
)
def test_missing_required_artifact_is_rejected(
    tmp_path,
    monkeypatch,
    missing_name,
):
    completion, output, _ = completed_bundle(tmp_path, monkeypatch)
    (output / missing_name).unlink()
    with pytest.raises(CompletionError):
        official_technical_handoff(completion)


def test_forbidden_conditional_prompt_is_rejected(tmp_path, monkeypatch):
    completion, output, _ = completed_bundle(tmp_path, monkeypatch)
    (output / PROMPT_NAME).write_text(
        "manual prompt\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(CompletionError):
        official_next_action_prompt(completion)


def test_required_conditional_prompt_missing_is_rejected(tmp_path, monkeypatch):
    completion, output, _ = completed_bundle(
        tmp_path,
        monkeypatch,
        "repair-handoff-valid",
    )
    (output / PROMPT_NAME).unlink()
    with pytest.raises(CompletionError):
        official_next_action_prompt(completion)


@pytest.mark.parametrize("mutation", ["artifact", "canonical_hash", "file_hash"])
def test_manifest_and_final_byte_drift_is_rejected(
    tmp_path,
    monkeypatch,
    mutation,
):
    completion, output, _ = completed_bundle(tmp_path, monkeypatch)
    manifest_path = output / MANIFEST_NAME
    if mutation == "artifact":
        path = output / "TECHNICAL_HANDOFF.en.md"
        path.write_bytes(path.read_bytes() + b"changed\n")
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        key = "canonical_sha256" if mutation == "canonical_hash" else "file_sha256"
        manifest["canonical_review_package"][key] = "0" * 64
        rewrite_json(manifest_path, manifest)
    with pytest.raises(CompletionError):
        official_technical_handoff(completion)


def test_partial_output_directory_is_not_official(tmp_path, monkeypatch):
    install_live_payloads(monkeypatch)
    output = tmp_path / "partial"
    output.mkdir()
    write_package(output / "review-package.json", package())
    (output / "OWNER_RESULT.fa.txt").write_text(
        "manual\n",
        encoding="utf-8",
    )
    with pytest.raises(CompletionError):
        verify_completed_review(output, head_source=source())


def test_arbitrary_mapping_cannot_supply_live_head_source(tmp_path):
    value = package()
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    result = complete_review(
        package_path,
        tmp_path / "review",
        head_source={},  # type: ignore[arg-type]
    )
    assert isinstance(result, IncompleteReview)
    assert {item.code for item in result.diagnostics} == {"PRI-COMPLETE-008"}


def test_fabricated_completion_marker_and_low_level_renderer_are_not_official(
    tmp_path,
    monkeypatch,
):
    completion, _, _ = completed_bundle(tmp_path, monkeypatch)
    forged = replace(completion, _marker=True)
    assert not is_verified_review_completion(forged)
    with pytest.raises(CompletionError):
        official_owner_result(forged)
    artifacts = build_review_artifacts(package())
    assert not is_verified_review_completion(artifacts)
    with pytest.raises(CompletionError):
        official_owner_result(artifacts)  # type: ignore[arg-type]


def test_partial_or_mismatched_github_payload_fails_closed(tmp_path, monkeypatch):
    install_live_payloads(
        monkeypatch,
        [{"number": PR_NUMBER, "head": {"sha": HEAD}}],
    )
    value = package()
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    result = complete_review(
        package_path,
        tmp_path / "review",
        head_source=source(),
    )
    assert isinstance(result, IncompleteReview)
    assert {item.code for item in result.diagnostics} == {"PRI-COMPLETE-008"}
    assert not (tmp_path / "review").exists()


def test_stale_package_head_is_rejected_against_live_github(
    tmp_path,
    monkeypatch,
):
    install_live_payloads(monkeypatch, [pr_payload(OTHER_HEAD)])
    value = package()
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    capability = profile_sequence_capability()
    result = complete_review(
        package_path,
        tmp_path / "review",
        head_source=source(),
        sequence_enforcement=capability,
    )
    assert isinstance(result, IncompleteReview)
    assert {item.code for item in result.diagnostics} == {"PRI-COMPLETE-007"}


def test_head_change_before_publication_preserves_existing_output(
    tmp_path,
    monkeypatch,
):
    install_live_payloads(
        monkeypatch,
        [pr_payload(), pr_payload(OTHER_HEAD)],
    )
    value = package()
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    output = tmp_path / "review"
    output.mkdir()
    sentinel = output / "existing.txt"
    sentinel.write_text("preserve\n", encoding="utf-8", newline="\n")
    capability = profile_sequence_capability()
    result = complete_review(
        package_path,
        output,
        head_source=source(),
        sequence_enforcement=capability,
    )
    assert isinstance(result, IncompleteReview)
    assert {item.code for item in result.diagnostics} == {"PRI-COMPLETE-008"}
    assert sentinel.read_text(encoding="utf-8") == "preserve\n"
    assert not (output / "OWNER_RESULT.fa.txt").exists()


def test_head_change_after_publication_rolls_back_existing_output(
    tmp_path,
    monkeypatch,
):
    install_live_payloads(
        monkeypatch,
        [pr_payload(), pr_payload(), pr_payload(OTHER_HEAD)],
    )
    value = package()
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    output = tmp_path / "review"
    output.mkdir()
    sentinel = output / "existing.txt"
    sentinel.write_text("preserve\n", encoding="utf-8", newline="\n")
    capability = profile_sequence_capability()
    result = complete_review(
        package_path,
        output,
        head_source=source(),
        sequence_enforcement=capability,
    )
    assert isinstance(result, IncompleteReview)
    assert {item.code for item in result.diagnostics} == {"PRI-COMPLETE-008"}
    assert sentinel.read_text(encoding="utf-8") == "preserve\n"
    assert not (output / "OWNER_RESULT.fa.txt").exists()


def test_official_output_access_rechecks_live_head(tmp_path, monkeypatch):
    completion, _, _ = completed_bundle(tmp_path, monkeypatch)
    install_live_payloads(monkeypatch, [pr_payload(OTHER_HEAD)])
    with pytest.raises(CompletionError, match="live GitHub"):
        official_owner_result(completion)


def test_successful_completion_exposes_only_validated_outputs(
    tmp_path,
    monkeypatch,
):
    completion, output, value = completed_bundle(
        tmp_path,
        monkeypatch,
        "repair-handoff-valid",
    )
    expected = build_review_artifacts(
        copy.deepcopy(value),
        review_package_bytes=(output / "review-package.json").read_bytes(),
    )
    assert {path.name for path in output.iterdir()} == {
        "review-package.json",
        *expected,
    }
    with pytest.raises(CompletionError, match="official_owner_delivery"):
        official_owner_result(completion)
    owner_result = (output / "OWNER_RESULT.fa.txt").read_text(encoding="utf-8")
    prompt = (output / PROMPT_NAME).read_text(encoding="utf-8")
    assert official_owner_delivery(completion) == (
        f"{owner_result}\n## پرامپت اقدام\n\n{prompt}"
    )
    assert official_technical_handoff(completion) == (
        output / "TECHNICAL_HANDOFF.en.md"
    ).read_text(encoding="utf-8")
    assert official_next_action_prompt(completion) == (
        output / PROMPT_NAME
    ).read_text(encoding="utf-8")
    assert len(completion.target_head_receipt_sha256) == 64


def test_owner_result_accessor_returns_verified_snapshot_not_toctou_bytes(
    tmp_path,
    monkeypatch,
):
    completion, output, _ = completed_bundle(tmp_path, monkeypatch)
    expected = (output / "OWNER_RESULT.fa.txt").read_text(encoding="utf-8")
    mutated = "unverified owner result\n".encode("utf-8")
    mutate_after_bundle_verification(
        monkeypatch,
        output,
        "OWNER_RESULT.fa.txt",
        mutated,
    )

    assert official_owner_result(completion) == expected
    assert (output / "OWNER_RESULT.fa.txt").read_bytes() == mutated


def test_technical_handoff_accessor_returns_verified_snapshot_not_toctou_bytes(
    tmp_path,
    monkeypatch,
):
    completion, output, _ = completed_bundle(tmp_path, monkeypatch)
    expected = (output / "TECHNICAL_HANDOFF.en.md").read_text(
        encoding="utf-8"
    )
    mutated = b"unverified technical handoff\n"
    mutate_after_bundle_verification(
        monkeypatch,
        output,
        "TECHNICAL_HANDOFF.en.md",
        mutated,
    )

    assert official_technical_handoff(completion) == expected
    assert (output / "TECHNICAL_HANDOFF.en.md").read_bytes() == mutated


def test_decision_projection_accessor_returns_verified_snapshot_not_toctou_bytes(
    tmp_path,
    monkeypatch,
):
    completion, output, _ = completed_bundle(tmp_path, monkeypatch)
    expected = json.loads((output / PROJECTION_NAME).read_text(encoding="utf-8"))
    mutated = b'{"unverified":true}\n'
    mutate_after_bundle_verification(
        monkeypatch,
        output,
        PROJECTION_NAME,
        mutated,
    )

    assert completion.decision_projection() == expected
    assert (output / PROJECTION_NAME).read_bytes() == mutated


def test_next_action_prompt_accessor_returns_verified_snapshot_not_toctou_bytes(
    tmp_path,
    monkeypatch,
):
    completion, output, _ = completed_bundle(
        tmp_path,
        monkeypatch,
        "repair-handoff-valid",
    )
    expected = (output / PROMPT_NAME).read_text(encoding="utf-8")
    mutated = b"unverified next action prompt\n"
    mutate_after_bundle_verification(
        monkeypatch,
        output,
        PROMPT_NAME,
        mutated,
    )

    assert official_next_action_prompt(completion) == expected
    assert (output / PROMPT_NAME).read_bytes() == mutated


def test_supported_cli_has_no_direct_low_level_render_bypass():
    script = (ROOT / "scripts/render_review_v2.py").read_text(encoding="utf-8")
    assert "write_review_artifacts" not in script
    assert "github_pull_request_head_source" in script
    assert "complete_review" in script
    assert "--target-repository" in script
    assert "--pr-number" in script
    assert "--expected-reviewed-head-sha" not in script


CANONICAL_OUTPUT_RULE_IDS = {
    "PRR-CANONICAL-PACKAGE-001",
    "PRR-CANONICAL-PROJECTION-001",
    "PRR-ARTIFACT-COMPLETENESS-001",
    "PRR-MANIFEST-INTEGRITY-001",
    "PRR-VERIFIED-COMPLETION-001",
    "PRR-FAIL-CLOSED-OUTPUT-001",
    "PRR-FINAL-HEAD-RECHECK-001",
    "PRR-PUBLICATION-COMMIT-POINT-001",
    "PRR-VERIFIED-BYTE-SNAPSHOT-001",
}
FOCUSED_COMMAND = "python -m pytest -q tests/test_canonical_output_enforcement.py"
ATOMICITY_COMMAND = "python -m pytest -q tests/test_canonical_output_atomicity.py"


def test_canonical_output_behavioral_coverage_has_dedicated_mutations_and_ci():
    raw = json.loads(
        (
            ROOT
            / "fixtures/canonical-output-enforcement/mutation-cases.json"
        ).read_text(encoding="utf-8")
    )
    by_rule: dict[str, list[str]] = {}
    for case in raw["cases"]:
        by_rule.setdefault(case["rule_id"], []).append(case["case_id"])
    assert set(by_rule) == CANONICAL_OUTPUT_RULE_IDS
    assert all(len(values) == 1 for values in by_rule.values())
    policy = (
        ROOT
        / "protocols/v1.10.0/policies/"
        "CANONICAL_OUTPUT_BEHAVIORAL_RULE_COVERAGE.md"
    ).read_text(encoding="utf-8")
    assert all(f"`{rule}`" in policy for rule in CANONICAL_OUTPUT_RULE_IDS)
    assert FOCUSED_COMMAND in policy
    assert ATOMICITY_COMMAND in policy
    workflow = (ROOT / ".github/workflows/validate-repository.yml").read_text(
        encoding="utf-8"
    )
    assert FOCUSED_COMMAND in workflow
    assert ATOMICITY_COMMAND in workflow
