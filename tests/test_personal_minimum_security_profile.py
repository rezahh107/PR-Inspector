import json
from pathlib import Path

from pr_inspector.decision_projection import owner_result_text, project_decision, reason_registry_by_code
from pr_inspector.derived_outputs import PROJECTION_NAME, render_next_action_prompt, write_review_artifacts
from pr_inspector.governance import verify_github_governance_source, verify_governance_record
from pr_inspector.render import render_handoff
from pr_inspector.security_profile import (
    PERSONAL_MINIMUM_SECURITY_PROFILE,
    RSN_MERGE_AUTHORIZATION_CLAIM_UNVERIFIED,
    RSN_MERGE_ENFORCEMENT_MINIMUM_MISSING,
    RSN_REPOSITORY_HOSTED_REQUIRED,
    RSN_REPOSITORY_SETTINGS_CLAIM_UNVERIFIED,
)
from pr_inspector.validation_v2 import validate_directory, validate_package
from tests.governance_test_support import HEAD, PR_NUMBER, REPOSITORY, responses

ROOT = Path(__file__).resolve().parents[1]


def package() -> dict:
    return json.loads((ROOT / "fixtures/golden-green/review-package.json").read_text(encoding="utf-8"))


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


def test_profile_cases_are_versioned():
    value = json.loads((ROOT / "fixtures/governance/personal-minimum-security-cases.json").read_text(encoding="utf-8"))
    assert value["schema_version"] == 1
    assert value["profile"] == PERSONAL_MINIMUM_SECURITY_PROFILE
    assert len(value["cases"]) == 7


def test_default_profile_preserves_green_without_stronger_claims():
    projection = project_decision(package())
    profile = projection["security_profile"]
    assert projection["technical_status"] == "GREEN_TECHNICALLY_READY"
    assert projection["next_action"]["kind"] == "merge_now"
    assert profile["repository_hosted_requirement"] == "optional_hardening"
    assert profile["repository_settings_enforced"] == "not_claimed"
    assert profile["merge_authorized"] == "not_claimed"
    assert not profile["blocks_green_merge_recommendation"]


def test_missing_sequence_and_repository_enforcement_blocks_green():
    value = package()
    value["security_profile"]["sequence_ci_enforced"] = False
    projection = project_decision(value)
    assert projection["technical_status"] == "YELLOW_CHANGES_OR_VERIFICATION_REQUIRED"
    assert projection["next_action"]["kind"] == "verify"
    assert RSN_MERGE_ENFORCEMENT_MINIMUM_MISSING in projection["security_profile"]["reason_codes"]


def test_explicit_activation_requires_verified_repository_enforcement():
    value = package()
    value["security_profile"]["security_activation_trigger"] = True
    projection = project_decision(value)
    assert projection["security_profile"]["repository_hosted_requirement"] == "required"
    assert RSN_REPOSITORY_HOSTED_REQUIRED in projection["security_profile"]["reason_codes"]
    assert projection["next_action"]["kind"] == "verify"


def test_self_asserted_repository_settings_claim_is_rejected():
    value = package()
    value["security_profile"]["claim_repository_settings_enforced"] = True
    projection = project_decision(value)
    assert projection["security_profile"]["repository_settings_enforced"] == "rejected"
    assert RSN_REPOSITORY_SETTINGS_CLAIM_UNVERIFIED in projection["security_profile"]["reason_codes"]


def test_self_asserted_merge_authorization_claim_is_rejected():
    value = package()
    value["security_profile"]["claim_merge_authorized"] = True
    projection = project_decision(value)
    assert projection["security_profile"]["merge_authorized"] == "rejected"
    assert RSN_MERGE_AUTHORIZATION_CLAIM_UNVERIFIED in projection["security_profile"]["reason_codes"]


def test_verified_exact_bound_governance_evidence_can_support_stronger_claims():
    value = package()
    evidence = verified_governance()
    value["security_profile"].update({
        "security_activation_trigger": True,
        "claim_repository_settings_enforced": True,
        "claim_merge_authorized": True,
        "governance_evidence_id": evidence.evidence_id,
    })
    projection = project_decision(value, evidence)
    profile = projection["security_profile"]
    assert profile["governance_evidence_status"] == "verified"
    assert profile["repository_hosted_enforcement"] == "verified"
    assert profile["repository_settings_enforced"] == "verified"
    assert profile["merge_authorized"] == "verified"
    assert profile["reason_codes"] == []
    assert projection["technical_status"] == "GREEN_TECHNICALLY_READY"


def test_serialized_governance_lookalike_cannot_support_claims():
    value = package()
    evidence = verified_governance()
    value["security_profile"].update({
        "claim_repository_settings_enforced": True,
        "governance_evidence_id": evidence.evidence_id,
    })
    projection = project_decision(value, {"evidence_id": evidence.evidence_id})
    assert projection["security_profile"]["governance_evidence_status"] == "rejected"
    assert projection["security_profile"]["repository_settings_enforced"] == "rejected"


def test_handoff_owner_and_prompt_consume_one_profile_projection():
    value = package()
    value["security_profile"]["sequence_ci_enforced"] = False
    value["decision"]["technical_status"] = "YELLOW_CHANGES_OR_VERIFICATION_REQUIRED"
    projection = project_decision(value)
    handoff = render_handoff(value, projection)
    prompt = render_next_action_prompt(value, projection)
    owner = owner_result_text(projection)
    assert "canonical_next_action_kind: verify" in handoff
    assert "RSN-MERGE-ENFORCEMENT-MINIMUM-MISSING" in prompt
    assert "مدرک" in owner
    assert projection["next_action"]["kind"] == "verify"


def test_manually_injected_projection_cannot_change_official_decision(tmp_path):
    value = package()
    value["security_profile"]["sequence_ci_enforced"] = False
    value["decision"]["technical_status"] = "YELLOW_CHANGES_OR_VERIFICATION_REQUIRED"
    package_bytes = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (tmp_path / "review-package.json").write_bytes(package_bytes)
    write_review_artifacts(value, tmp_path, review_package_bytes=package_bytes)
    path = tmp_path / PROJECTION_NAME
    projection = json.loads(path.read_text(encoding="utf-8"))
    projection["security_profile"].update({"blocks_green_merge_recommendation": False, "reason_codes": []})
    projection["technical_status"] = "GREEN_TECHNICALLY_READY"
    projection["technical_status_reason_codes"] = []
    projection["owner_readiness"].update({"color": "GREEN", "action_kind": "merge_now", "message_key": "green_merge_now", "reason_codes": []})
    projection["next_action"].update({"kind": "merge_now", "recipient": "none", "may_modify_code": False, "prompt_required": False, "prompt_kind": None, "reason_codes": []})
    path.write_text(json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    assert "PRI-PROJECTION-003" in {item.code for item in validate_directory(tmp_path)}


def test_schema_requires_structured_security_profile_carrier():
    value = package()
    value.pop("security_profile")
    assert "PRI-SCHEMA-001" in {item.code for item in validate_package(value)}


def test_semantic_validation_uses_profile_projection_for_status():
    value = package()
    value["security_profile"]["sequence_ci_enforced"] = False
    assert "PRI-STATUS-001" in {item.code for item in validate_package(value)}
    value["decision"]["technical_status"] = "YELLOW_CHANGES_OR_VERIFICATION_REQUIRED"
    assert validate_package(value) == []


def test_profile_reason_codes_are_registered_as_non_modifying_verification():
    registry = reason_registry_by_code()
    for code in (
        RSN_MERGE_ENFORCEMENT_MINIMUM_MISSING,
        RSN_REPOSITORY_HOSTED_REQUIRED,
        RSN_REPOSITORY_SETTINGS_CLAIM_UNVERIFIED,
        RSN_MERGE_AUTHORIZATION_CLAIM_UNVERIFIED,
    ):
        assert registry[code]["technical_status_effect"] == "YELLOW"
        assert registry[code]["action_effect"] == "verify"
        assert registry[code]["recipient"] == "reviewer_model"
        assert registry[code]["may_modify_code"] is False

