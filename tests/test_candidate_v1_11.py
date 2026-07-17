from __future__ import annotations

import inspect

import pytest

import pr_inspector.candidate_v1_11 as candidate


SHA = "a" * 40


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
