from __future__ import annotations

import json
from pathlib import Path

import pytest

from pr_inspector.decision_projection import project_decision
from pr_inspector.official_review import is_verified_review_completion
from pr_inspector.security_profile import assess_security_profile
from pr_inspector.verified_review import ReviewAssemblyError
from pr_inspector.validation_v2 import validate_directory
from tests.verified_review_test_support import complete_fixture_review, fixture_review_runtime

ROOT = Path(__file__).resolve().parents[1]


def package(name: str = "golden-green") -> dict:
    return json.loads((ROOT / "fixtures" / name / "review-package.json").read_text(encoding="utf-8"))


def test_minimal_profile_uses_machine_collected_exact_head_checks_for_correctness():
    runtime = fixture_review_runtime(package())
    value = runtime.package.value()
    assessment = assess_security_profile(value)
    assert assessment.sequence_ci_enforced is True
    assert assessment.blocks_green_merge_recommendation is False
    assert project_decision(value)["technical_status"] == "GREEN_TECHNICALLY_READY"


def test_failed_required_check_still_blocks_green():
    value = package()
    value["checks"][0]["result"] = "FAIL"
    for record in value["evidence_records"]:
        if record["evidence_id"] == value["checks"][0]["evidence_id"]:
            record["result"] = "FAIL"
    runtime = fixture_review_runtime(value)
    projection = project_decision(runtime.package.value())
    assert projection["technical_status"] != "GREEN_TECHNICALLY_READY"
    assert "required_technical_check_failed" in projection["technical_decision"]["reason_codes"]


def test_optional_repository_hardening_does_not_block_minimal_green():
    runtime = fixture_review_runtime(package())
    projection = project_decision(runtime.package.value())
    profile = projection["security_profile"]
    assert profile["repository_hosted_requirement"] == "optional_hardening"
    assert projection["technical_status"] == "GREEN_TECHNICALLY_READY"


def test_strict_profile_requires_governance_evidence():
    value = package()
    value["inspection_profile"] = "strict"
    with pytest.raises(ReviewAssemblyError, match="strict profile requires governance evidence"):
        fixture_review_runtime(value)


def test_reviewer_assessment_cannot_claim_repository_settings_or_merge_authority():
    from pr_inspector.verified_review import parse_review_assessment

    with pytest.raises(ReviewAssemblyError, match="[Aa]dditional properties"):
        parse_review_assessment(
            {
                "review_summary": "review",
                "owner_facing_explanation": "review",
                "findings": [],
                "claim_repository_settings_enforced": True,
                "claim_merge_authorized": True,
            }
        )


def test_official_completion_threads_one_canonical_profile_projection(tmp_path: Path):
    result, _ = complete_fixture_review(package(), tmp_path / "review")
    assert is_verified_review_completion(result)
    projection = result.decision_projection()
    assert projection["technical_status"] == "GREEN_TECHNICALLY_READY"
    assert projection["security_profile"]["sequence_ci_enforced"] is True
    assert validate_directory(tmp_path / "review") == []


def test_profile_projection_is_deterministic():
    runtime = fixture_review_runtime(package())
    first = project_decision(runtime.package.value())
    second = project_decision(runtime.package.value())
    assert first == second


def test_security_framework_is_not_required_for_v1_12_assembly():
    runtime = fixture_review_runtime(package())
    source = (ROOT / "pr_inspector/verified_review.py").read_text(encoding="utf-8")
    assert runtime.package.value()["protocol_version"] == "v1.12.0"
    assert "HMAC" not in source
    assert "private_key" not in source
    assert "capability-token" not in source
