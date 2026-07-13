import json
from pathlib import Path

from pr_inspector.decision_projection import project_decision, reason_registry_by_code
from pr_inspector.governance import (
    verify_github_governance_source,
    verify_governance_record,
)
from pr_inspector.security_profile import (
    OPTIONAL_HARDENING_CONTROLS,
    PERSONAL_MINIMUM_SECURITY_PROFILE,
    RSN_MERGE_AUTHORIZATION_CLAIM_UNVERIFIED,
    RSN_MERGE_ENFORCEMENT_MINIMUM_MISSING,
    RSN_REPOSITORY_HOSTED_REQUIRED,
    RSN_REPOSITORY_SETTINGS_CLAIM_UNVERIFIED,
    assess_security_profile,
    classify_governance_claim,
    green_merge_recommended,
)
from tests.governance_test_support import (
    HEAD,
    PR_NUMBER,
    REPOSITORY,
    responses,
)

ROOT = Path(__file__).resolve().parents[1]


def golden_package() -> dict:
    return json.loads(
        (ROOT / "fixtures/golden-green/review-package.json").read_text(
            encoding="utf-8"
        )
    )


def verified_governance():
    source = verify_github_governance_source(
        responses(),
        expected_repository=REPOSITORY,
        expected_pr_number=PR_NUMBER,
        expected_head_sha=HEAD,
    )
    return verify_governance_record(
        source,
        expected_repository=REPOSITORY,
        expected_pr_number=PR_NUMBER,
        expected_head_sha=HEAD,
    )


def test_required_profile_cases_are_versioned():
    value = json.loads(
        (
            ROOT
            / "fixtures/governance/personal-minimum-security-cases.json"
        ).read_text(encoding="utf-8")
    )
    assert value["schema_version"] == 1
    assert value["profile"] == PERSONAL_MINIMUM_SECURITY_PROFILE
    assert {item["case_id"] for item in value["cases"]} == {
        "personal_without_github_app",
        "false_repository_settings_claim",
        "false_merge_authorization_claim",
        "explicit_higher_security_activation",
        "optional_hardening",
        "prior_guarantees_preserved",
    }


def test_personal_profile_without_github_app_does_not_block_green():
    assessment = assess_security_profile(sequence_ci_enforced=True)
    projection = project_decision(golden_package())

    assert assessment.repository_hosted_enforcement == "optional_hardening"
    assert assessment.github_app_exact_source_enforcement == "optional_hardening"
    assert assessment.repository_settings_enforced == "not_claimed"
    assert assessment.merge_authorized == "not_claimed"
    assert assessment.reason_codes == ()
    assert not assessment.blocks_green_merge_recommendation
    assert projection["technical_status"] == "GREEN_TECHNICALLY_READY"
    assert projection["next_action"]["kind"] == "merge_now"
    assert green_merge_recommended(projection, assessment)


def test_all_repository_hosted_controls_are_optional_hardening_by_default():
    assessment = assess_security_profile()
    assert {name for name, _ in assessment.controls} == set(
        OPTIONAL_HARDENING_CONTROLS
    )
    assert {status for _, status in assessment.controls} == {
        "optional_hardening"
    }


def test_false_repository_settings_claim_is_rejected_fail_closed():
    assessment = assess_security_profile(
        claim_repository_settings_enforced=True
    )
    assert assessment.repository_settings_enforced == "rejected"
    assert assessment.blocks_green_merge_recommendation
    assert RSN_REPOSITORY_SETTINGS_CLAIM_UNVERIFIED in assessment.reason_codes
    assert RSN_REPOSITORY_HOSTED_REQUIRED in assessment.reason_codes

    assert (
        classify_governance_claim(
            "repository_settings_enforced",
            claimed=True,
            governance_evidence={"status": "verified_enforced"},
        )
        == "rejected"
    )


def test_false_merge_authorization_claim_is_rejected_fail_closed():
    assessment = assess_security_profile(claim_merge_authorized=True)
    assert assessment.merge_authorized == "rejected"
    assert assessment.blocks_green_merge_recommendation
    assert RSN_MERGE_AUTHORIZATION_CLAIM_UNVERIFIED in assessment.reason_codes
    assert RSN_REPOSITORY_HOSTED_REQUIRED in assessment.reason_codes


def test_explicit_higher_security_activation_keeps_missing_enforcement_blocking():
    assessment = assess_security_profile(
        sequence_ci_enforced=True,
        security_activation_trigger=True,
    )
    assert assessment.repository_hosted_enforcement == "required"
    assert assessment.github_app_exact_source_enforcement == "required"
    assert assessment.blocks_green_merge_recommendation
    assert assessment.reason_codes == (RSN_REPOSITORY_HOSTED_REQUIRED,)


def test_aigov_merge_minimum_requires_sequence_or_repository_hosted_enforcement():
    assessment = assess_security_profile(sequence_ci_enforced=False)
    assert assessment.repository_hosted_enforcement == "optional_hardening"
    assert assessment.blocks_green_merge_recommendation
    assert assessment.reason_codes == (
        RSN_MERGE_ENFORCEMENT_MINIMUM_MISSING,
    )


def test_opaque_governance_evidence_can_verify_stronger_claims():
    evidence = verified_governance()
    assert (
        classify_governance_claim(
            "repository_settings_enforced",
            claimed=True,
            governance_evidence=evidence,
        )
        == "verified"
    )
    assert (
        classify_governance_claim(
            "merge_authorized",
            claimed=True,
            governance_evidence=evidence,
        )
        == "verified"
    )

    assessment = assess_security_profile(
        claim_repository_settings_enforced=True,
        claim_merge_authorized=True,
        governance_evidence=evidence,
    )
    assert assessment.repository_settings_enforced == "verified"
    assert assessment.merge_authorized == "verified"
    assert not assessment.blocks_green_merge_recommendation
    assert assessment.reason_codes == ()


def test_profile_reason_codes_are_registered_with_non_modifying_verification():
    registry = reason_registry_by_code()
    for code in (
        RSN_MERGE_ENFORCEMENT_MINIMUM_MISSING,
        RSN_REPOSITORY_HOSTED_REQUIRED,
        RSN_REPOSITORY_SETTINGS_CLAIM_UNVERIFIED,
        RSN_MERGE_AUTHORIZATION_CLAIM_UNVERIFIED,
    ):
        assert registry[code]["technical_status_effect"] == "NONE"
        assert registry[code]["action_effect"] == "verify"
        assert registry[code]["recipient"] == "reviewer_model"
        assert registry[code]["may_modify_code"] is False


def test_prior_exact_head_and_evidence_guarantees_remain_in_projection():
    projection = project_decision(golden_package())
    assert projection["review_identity"] == {
        "validity": "CURRENT",
        "reviewed_head_sha": "1" * 40,
    }
    assert projection["technical_status_reason_codes"] == []
    assert projection["approval_requirement"] == (
        "NO_ADDITIONAL_TECHNICAL_APPROVAL"
    )
