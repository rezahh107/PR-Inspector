from __future__ import annotations

import copy
import inspect
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

import pr_inspector.candidate_v1_11 as candidate
from pr_inspector._governance_transport import _mint_response
from pr_inspector.governance import (
    verify_github_governance_source,
    verify_governance_record,
)
from pr_inspector.official_review import (
    VerifiedReviewCompletion,
    complete_review,
    github_pull_request_head_source,
    is_verified_review_completion,
)
from pr_inspector.review_provenance import verify_github_commit_payload
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
INSPECTOR_REPOSITORY = "rezahh107/PR-Inspector"
INSPECTOR_REPOSITORY_ID = 1288323264
INSPECTOR_COMMIT = "3" * 40
API_VERSION = "2026-03-10"
SHA = "a" * 40


def _replace_exact(value, old: str, new: str):
    if isinstance(value, dict):
        return {key: _replace_exact(child, old, new) for key, child in value.items()}
    if isinstance(value, list):
        return [_replace_exact(child, old, new) for child in value]
    return value.replace(old, new) if isinstance(value, str) else value


def _package(head_sha: str = HEAD) -> dict:
    value = json.loads(
        (ROOT / "fixtures/golden-green/review-package.json").read_text(
            encoding="utf-8"
        )
    )
    value = _replace_exact(value, HEAD, head_sha)
    value["protocol_version"] = candidate.PROTOCOL_VERSION
    return value


def _write_package(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
        newline="",
    )


def _pr_payload(head_sha: str) -> dict:
    url = f"https://api.github.com/repos/{REPOSITORY}/pulls/{PR_NUMBER}"
    return {
        "number": PR_NUMBER,
        "url": url,
        "html_url": f"https://github.com/{REPOSITORY}/pull/{PR_NUMBER}",
        "base": {"repo": {"id": REPOSITORY_ID, "full_name": REPOSITORY}},
        "head": {"sha": head_sha},
    }


def _install_live_head(monkeypatch, head_sha: str) -> None:
    from pr_inspector import _official_head

    def fake_github_json(url, *, token, api_version):
        assert url == f"https://api.github.com/repos/{REPOSITORY}/pulls/{PR_NUMBER}"
        assert api_version == API_VERSION
        return copy.deepcopy(_pr_payload(head_sha))

    monkeypatch.setattr(_official_head, "_github_json", fake_github_json)


def _head_source():
    return github_pull_request_head_source(
        REPOSITORY,
        PR_NUMBER,
        token=None,
        api_version=API_VERSION,
    )


def _sequence_capability(head_sha: str):
    value = _replace_exact(governance_fixture(), HEAD, head_sha)
    value["responses"]["checks"]["payload"]["check_runs"][0]["name"] = (
        SEQUENCE_ENFORCEMENT_CHECK_CONTEXT
    )
    required = value["responses"]["branch_protection"]["payload"][
        "required_status_checks"
    ]
    required["checks"][0]["context"] = SEQUENCE_ENFORCEMENT_CHECK_CONTEXT
    required["contexts"] = [SEQUENCE_ENFORCEMENT_CHECK_CONTEXT]
    source = verify_github_governance_source(
        governance_responses(value),
        expected_repository=REPOSITORY,
        expected_pr_number=PR_NUMBER,
        expected_head_sha=head_sha,
    )
    governance = verify_governance_record(
        source,
        expected_repository=REPOSITORY,
        expected_pr_number=PR_NUMBER,
        expected_head_sha=head_sha,
    )
    producer = verify_sequence_producer_evidence(
        governance,
        check_context=SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
        app_id=15368,
        workflow_path=".github/workflows/validate-rereview-sequence.yml",
        workflow_sha="2" * 40,
        validator_command=(
            "python scripts/validate_rereview_sequence.py sequence.json "
            "--review EVENT=review"
        ),
    )
    return verify_sequence_ci_enforcement(
        governance,
        check_context=SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
        app_id=15368,
        producer_evidence=producer,
    )


def _completion(tmp_path: Path, monkeypatch, head_sha: str) -> VerifiedReviewCompletion:
    _install_live_head(monkeypatch, head_sha)
    package_path = tmp_path / f"package-{head_sha[:8]}.json"
    _write_package(package_path, _package(head_sha))
    result = complete_review(
        package_path,
        tmp_path / f"review-{head_sha[:8]}",
        head_source=_head_source(),
        sequence_enforcement=_sequence_capability(head_sha),
    )
    assert is_verified_review_completion(result)
    assert isinstance(result, VerifiedReviewCompletion)
    return result


def _target_identity():
    url = f"https://api.github.com/repos/{REPOSITORY}"
    response = _mint_response(
        request_url=url,
        response_url=url,
        status_code=200,
        fetched_at=datetime.now(timezone.utc),
        payload={
            "id": REPOSITORY_ID,
            "full_name": REPOSITORY,
            "url": url,
            "html_url": f"https://github.com/{REPOSITORY}",
        },
        transport_origin="github_https",
    )
    return candidate.verify_target_identity_response(
        response,
        expected_repository=REPOSITORY,
    )


def _live_head(head_sha: str):
    url = f"https://api.github.com/repos/{REPOSITORY}/pulls/{PR_NUMBER}"
    response = _mint_response(
        request_url=url,
        response_url=url,
        status_code=200,
        fetched_at=datetime.now(timezone.utc),
        payload=_pr_payload(head_sha),
        transport_origin="github_https",
    )
    return candidate.verify_live_pr_head_response(
        response,
        target_repository=REPOSITORY,
        target_repository_id=REPOSITORY_ID,
        pull_request=PR_NUMBER,
    )


def _inspector_commit():
    repository_url = f"https://api.github.com/repos/{INSPECTOR_REPOSITORY}"
    commit_url = f"{repository_url}/commits/{INSPECTOR_COMMIT}"
    return verify_github_commit_payload(
        {
            "id": INSPECTOR_REPOSITORY_ID,
            "full_name": INSPECTOR_REPOSITORY,
            "url": repository_url,
            "html_url": f"https://github.com/{INSPECTOR_REPOSITORY}",
        },
        {
            "sha": INSPECTOR_COMMIT,
            "url": commit_url,
            "html_url": (
                f"https://github.com/{INSPECTOR_REPOSITORY}/commit/"
                f"{INSPECTOR_COMMIT}"
            ),
        },
        expected_commit_sha=INSPECTOR_COMMIT,
    )


def _genuine_reference(tmp_path: Path, monkeypatch, head_sha: str = HEAD):
    completion = _completion(tmp_path, monkeypatch, head_sha)
    target = _target_identity()
    inspector = _inspector_commit()
    reference = candidate.minimal_reference_from_official_completion(
        completion,
        target_identity=target,
        inspector_commit=inspector,
    )
    return completion, target, inspector, reference


def _reconstruct(reference, **changes):
    forged = object.__new__(candidate.VerifiedMinimalReviewReference)
    for name in candidate.VerifiedMinimalReviewReference.__slots__:
        if name == "__weakref__":
            continue
        object.__setattr__(
            forged,
            name,
            changes.get(name, getattr(reference, name)),
        )
    return forged


def test_candidate_compatibility_preserves_minimal_and_strict_intake():
    minimal = candidate.parse_intake(
        "حداقلی\nhttps://github.com/example/project/pull/42"
    )
    strict = candidate.parse_intake(
        "سخت گیرانه\nhttps://github.com/example/project/pull/42"
    )

    assert minimal == {
        "inspection_profile": "minimal",
        "target": {
            "repository": "example/project",
            "pull_request": 42,
            "url": "https://github.com/example/project/pull/42",
        },
        "reuse_current_minimal": False,
        "missing": [],
    }
    assert strict["inspection_profile"] == "strict"
    assert strict["target"]["repository"] == "example/project"
    assert strict["target"]["pull_request"] == 42


def test_candidate_output_authorities_fail_closed():
    symbols = (
        "project_decision",
        "render_candidate_owner_result",
        "render_candidate_owner_card",
        "render_candidate_technical_handoff",
        "render_candidate_next_action_prompt",
        "build_candidate_review_artifacts",
        "verify_candidate_review_artifact_bytes",
        "verify_minimal_review_artifact_bytes",
        "build_candidate_owner_delivery_artifacts",
    )
    for name in symbols:
        with pytest.raises(candidate.CandidateOutputMigrationError, match="not an output authority"):
            getattr(candidate, name)()
        assert name not in candidate.__all__


def test_candidate_owner_delivery_rejects_unverified_input():
    with pytest.raises(candidate.CandidateOutputMigrationError, match="official_owner_delivery"):
        candidate.candidate_owner_delivery_stdout(object())
    with pytest.raises(candidate.CandidateOutputMigrationError, match="official_owner_delivery"):
        candidate.render_owner_profile_commands(object())


def test_candidate_owner_delivery_delegates_exact_official_bytes(monkeypatch):
    class Completion:
        reviewed_head_sha = SHA

    completion = Completion()
    monkeypatch.setattr(candidate, "is_verified_review_completion", lambda value: value is completion)
    monkeypatch.setattr(candidate, "official_owner_delivery", lambda value: "OFFICIAL\nDELIVERY\n")
    monkeypatch.setattr(candidate, "official_owner_profile_commands", lambda value: "PROFILE\nCOMMANDS\n")

    assert candidate.candidate_owner_delivery_stdout(completion) == b"OFFICIAL\nDELIVERY\n"
    assert candidate.render_owner_profile_commands(completion) == b"PROFILE\nCOMMANDS\n"
    with pytest.raises(ValueError, match="live Head"):
        candidate.candidate_owner_delivery_stdout(completion, live_head_sha="b" * 40)


def test_candidate_module_contains_no_pr22_renderer_or_manual_composition():
    source = inspect.getsource(candidate)
    assert "Repair indepently validated technical findings before rereview." not in source
    assert '"\\n## پرامپت اقدام\\n\\n"' not in source
    assert "raw_owner +" not in source
    assert "build_review_artifacts" not in candidate.__all__
    assert "official_owner_delivery(completion)" in source


def test_candidate_public_surface_is_bounded_prepackage_compatibility():
    allowed = {
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
    }
    assert set(candidate.__all__) == allowed


def test_minimal_reference_direct_construction_and_field_reconstruction_fail_closed(
    tmp_path, monkeypatch
):
    _, _, _, reference = _genuine_reference(tmp_path, monkeypatch)
    with pytest.raises(TypeError, match="verified official review provenance"):
        candidate.VerifiedMinimalReviewReference()

    copied = _reconstruct(reference)
    assert candidate.verify_base_review_reference(
        copied,
        HEAD,
        target_repository=REPOSITORY,
        target_repository_id=REPOSITORY_ID,
        pull_request=PR_NUMBER,
    ) == {"status": "INVALID", "reason": "verified_minimal_review_required"}


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("inspector_repository", "attacker/Inspector"),
        ("inspector_commit_sha", "9" * 40),
        ("protocol_version", "v0.0.0"),
        ("review_package_canonical_sha256", "9" * 64),
        ("review_package_file_sha256", "8" * 64),
        ("decision_projection_sha256", "7" * 64),
        ("artifact_manifest_sha256", "6" * 64),
        ("target_repository_id", REPOSITORY_ID + 1),
        ("pull_request", PR_NUMBER + 1),
        ("reviewed_head_sha", "9" * 40),
    ),
)
def test_reconstructed_or_altered_minimal_reference_never_verifies(
    tmp_path, monkeypatch, field, value
):
    _, _, _, reference = _genuine_reference(tmp_path, monkeypatch)
    forged = _reconstruct(reference, **{field: value})
    result = candidate.verify_base_review_reference(
        forged,
        HEAD,
        target_repository=REPOSITORY,
        target_repository_id=REPOSITORY_ID,
        pull_request=PR_NUMBER,
    )
    assert result["status"] == "INVALID"


def test_genuine_same_head_minimal_completion_is_reused(tmp_path, monkeypatch):
    _, _, _, reference = _genuine_reference(tmp_path, monkeypatch)
    result = candidate.orchestrate_strict_after_minimal(
        {
            "verified_minimal_review": reference,
            "verified_live_pr_head": _live_head(HEAD),
        }
    )
    assert result.state == "same_head_reuse"
    assert result.reference is reference
    assert result.live_head_sha == HEAD


def test_head_drift_requires_refresh_and_unsealed_callback_result_fails(
    tmp_path, monkeypatch
):
    _, _, _, reference = _genuine_reference(tmp_path, monkeypatch)
    context = {
        "verified_minimal_review": reference,
        "verified_live_pr_head": _live_head(OTHER_HEAD),
    }
    missing = candidate.orchestrate_strict_after_minimal(context)
    assert missing.state == "head_drift_refresh_required"
    assert missing.reference is None

    forged = _reconstruct(reference, reviewed_head_sha=OTHER_HEAD)
    invalid = candidate.orchestrate_strict_after_minimal(
        context,
        lambda _target, _head: forged,
    )
    assert invalid.state == "refresh_failed"
    assert invalid.reason == "verified_official_minimal_completion_required"
    assert invalid.reference is None


def test_head_drift_accepts_only_genuine_refreshed_minimal_completion(
    tmp_path, monkeypatch
):
    _, _, _, reference = _genuine_reference(tmp_path, monkeypatch, HEAD)
    refreshed_completion = _completion(tmp_path, monkeypatch, OTHER_HEAD)
    result = candidate.orchestrate_strict_after_minimal(
        {
            "verified_minimal_review": reference,
            "verified_live_pr_head": _live_head(OTHER_HEAD),
        },
        lambda target, head: refreshed_completion,
    )
    assert result.state == "refresh_verified"
    assert result.reference is not None
    assert result.reference.reviewed_head_sha == OTHER_HEAD
    assert result.live_head_sha == OTHER_HEAD


def test_head_drift_with_wrong_refreshed_completion_fails_closed(
    tmp_path, monkeypatch
):
    _, _, _, reference = _genuine_reference(tmp_path, monkeypatch, HEAD)
    stale_completion = _completion(tmp_path, monkeypatch, HEAD)
    result = candidate.orchestrate_strict_after_minimal(
        {
            "verified_minimal_review": reference,
            "verified_live_pr_head": _live_head(OTHER_HEAD),
        },
        lambda target, head: stale_completion,
    )
    assert result.state == "refresh_failed"
    assert result.reason in {
        "head_drift",
        "minimal_refresh_provenance_invalid",
    }
    assert result.reference is None


def test_source_bundle_mutation_invalidates_same_head_reference(
    tmp_path, monkeypatch
):
    completion, _, _, reference = _genuine_reference(tmp_path, monkeypatch)
    package_path = completion.output_directory / "review-package.json"
    package_path.write_bytes(package_path.read_bytes() + b" ")
    result = candidate.verify_base_review_reference(
        reference,
        HEAD,
        target_repository=REPOSITORY,
        target_repository_id=REPOSITORY_ID,
        pull_request=PR_NUMBER,
    )
    assert result == {
        "status": "INVALID",
        "reason": "minimal_review_provenance_invalid",
    }
