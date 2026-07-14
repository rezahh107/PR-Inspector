import copy
import json
from pathlib import Path

from pr_inspector.decision_projection import (
    owner_result_text,
    project_decision,
    reason_registry_by_code,
)
from pr_inspector.derived_outputs import (
    PROJECTION_NAME,
    render_next_action_prompt,
    write_review_artifacts,
)
from pr_inspector.governance import (
    verify_github_governance_source,
    verify_governance_record,
)
from pr_inspector.official_review import (
    IncompleteReview,
    VerifiedReviewCompletion,
    complete_review,
    github_pull_request_head_source,
    is_verified_review_completion,
    verify_completed_review,
)
from pr_inspector.render import render_handoff
from pr_inspector.security_profile import (
    PERSONAL_MINIMUM_SECURITY_PROFILE,
    RSN_MERGE_AUTHORIZATION_CLAIM_UNVERIFIED,
    RSN_MERGE_ENFORCEMENT_MINIMUM_MISSING,
    RSN_REPOSITORY_HOSTED_REQUIRED,
    RSN_REPOSITORY_SETTINGS_CLAIM_UNVERIFIED,
)
from pr_inspector.sequence_enforcement import (
    verify_sequence_ci_enforcement,
    verify_sequence_producer_evidence,
)
from pr_inspector.validation_v2 import validate_directory, validate_package
from tests.governance_test_support import fixture, responses

ROOT = Path(__file__).resolve().parents[1]
HEAD = "1" * 40
OTHER_HEAD = "f" * 40
REPOSITORY = "example/project"
PR_NUMBER = 42
REPOSITORY_ID = 4242
API_VERSION = "2026-03-10"
SEQUENCE_CONTEXT = "Validate rereview sequence enforcement"
SEQUENCE_APP_ID = 15368


def package() -> dict:
    return json.loads(
        (ROOT / "fixtures/golden-green/review-package.json").read_text(
            encoding="utf-8"
        )
    )


def governance_fixture(
    *,
    head: str = HEAD,
    pr_number: int = PR_NUMBER,
    check_context: str = "Validate PR Inspector repository",
) -> dict:
    value = copy.deepcopy(fixture())
    old_checks_url = value["responses"]["checks"]["url"]
    value["responses"]["pull_request"]["payload"]["number"] = pr_number
    value["responses"]["pull_request"]["payload"]["head"]["sha"] = head
    value["responses"]["pull_request"]["url"] = (
        f"https://api.github.com/repos/{REPOSITORY}/pulls/{pr_number}"
    )
    value["responses"]["reviews"]["payload"][0]["commit_id"] = head
    value["responses"]["reviews"]["url"] = (
        f"https://api.github.com/repos/{REPOSITORY}/pulls/{pr_number}/reviews?per_page=100"
    )
    value["responses"]["checks"]["payload"]["check_runs"][0]["head_sha"] = head
    value["responses"]["checks"]["payload"]["check_runs"][0]["name"] = check_context
    value["responses"]["checks"]["url"] = (
        f"https://api.github.com/repos/{REPOSITORY}/commits/{head}/check-runs?per_page=100"
    )
    checks = value["responses"]["branch_protection"]["payload"][
        "required_status_checks"
    ]
    checks["checks"][0]["context"] = check_context
    checks["contexts"] = [check_context]
    assert old_checks_url != value["responses"]["checks"]["url"] or head == HEAD
    return value


def verified_governance(
    *,
    head: str = HEAD,
    pr_number: int = PR_NUMBER,
    check_context: str = "Validate PR Inspector repository",
):
    source = verify_github_governance_source(
        responses(
            governance_fixture(
                head=head,
                pr_number=pr_number,
                check_context=check_context,
            )
        ),
        expected_repository=REPOSITORY,
        expected_pr_number=pr_number,
        expected_head_sha=head,
    )
    return verify_governance_record(
        source,
        expected_repository=REPOSITORY,
        expected_pr_number=pr_number,
        expected_head_sha=head,
    )


def verified_sequence(*, head: str = HEAD, pr_number: int = PR_NUMBER):
    governance = verified_governance(
        head=head,
        pr_number=pr_number,
        check_context=SEQUENCE_CONTEXT,
    )
    producer = verify_sequence_producer_evidence(
        governance,
        check_context=SEQUENCE_CONTEXT,
        app_id=SEQUENCE_APP_ID,
        workflow_path=".github/workflows/validate-rereview-sequence.yml",
        workflow_sha="2" * 40,
        validator_command="python scripts/validate_rereview_sequence.py sequence.json --review EVENT=review",
    )
    return verify_sequence_ci_enforcement(
        governance,
        check_context=SEQUENCE_CONTEXT,
        app_id=SEQUENCE_APP_ID,
        producer_evidence=producer,
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


def install_live_payloads(monkeypatch, head_sha: str = HEAD):
    from pr_inspector import _official_head

    def fake_github_json(url, *, token, api_version):
        assert url == f"https://api.github.com/repos/{REPOSITORY}/pulls/{PR_NUMBER}"
        assert api_version == API_VERSION
        return pr_payload(head_sha)

    monkeypatch.setattr(_official_head, "_github_json", fake_github_json)


def head_source():
    return github_pull_request_head_source(
        REPOSITORY,
        PR_NUMBER,
        token=None,
        api_version=API_VERSION,
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


def test_profile_cases_are_versioned():
    value = json.loads(
        (
            ROOT
            / "fixtures/governance/personal-minimum-security-cases.json"
        ).read_text(encoding="utf-8")
    )
    assert value["schema_version"] == 1
    assert value["profile"] == PERSONAL_MINIMUM_SECURITY_PROFILE
    assert len(value["cases"]) == 7


def test_bare_sequence_boolean_cannot_produce_green():
    projection = project_decision(package())
    profile = projection["security_profile"]
    assert projection["technical_status"] == "YELLOW_CHANGES_OR_VERIFICATION_REQUIRED"
    assert projection["next_action"]["kind"] == "verify"
    assert profile["sequence_ci_enforced"] is False
    assert RSN_MERGE_ENFORCEMENT_MINIMUM_MISSING in profile["reason_codes"]


def test_verified_exact_bound_sequence_capability_preserves_default_green():
    projection = project_decision(
        package(),
        sequence_enforcement=verified_sequence(),
    )
    profile = projection["security_profile"]
    assert projection["technical_status"] == "GREEN_TECHNICALLY_READY"
    assert projection["next_action"]["kind"] == "merge_now"
    assert profile["sequence_ci_enforced"] is True
    assert profile["reason_codes"] == []


def test_serialized_sequence_lookalike_cannot_support_claim():
    capability = verified_sequence()
    projection = project_decision(
        package(),
        sequence_enforcement={
            "evidence_id": capability.evidence_id,
            "repository": capability.repository,
            "pull_request_number": capability.pull_request_number,
            "exact_head_sha": capability.exact_head_sha,
        },
    )
    assert projection["technical_status"] == "YELLOW_CHANGES_OR_VERIFICATION_REQUIRED"
    assert projection["security_profile"]["sequence_ci_enforced"] is False


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


def test_official_completion_emits_verification_reason_for_bare_sequence_claim(
    tmp_path,
    monkeypatch,
):
    install_live_payloads(monkeypatch)
    value = package()
    value["decision"]["technical_status"] = "YELLOW_CHANGES_OR_VERIFICATION_REQUIRED"
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    output = tmp_path / "review"

    result = complete_review(package_path, output, head_source=head_source())
    assert is_verified_review_completion(result)
    assert isinstance(result, VerifiedReviewCompletion)
    projection = result.decision_projection()
    assert projection["technical_status"] == "YELLOW_CHANGES_OR_VERIFICATION_REQUIRED"
    assert projection["next_action"]["kind"] == "verify"
    assert RSN_MERGE_ENFORCEMENT_MINIMUM_MISSING in projection["security_profile"]["reason_codes"]
    assert validate_directory(output) == []


def test_official_completion_accepts_exact_bound_sequence_capability(
    tmp_path,
    monkeypatch,
):
    install_live_payloads(monkeypatch)
    value = package()
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    output = tmp_path / "review"
    capability = verified_sequence()

    result = complete_review(
        package_path,
        output,
        head_source=head_source(),
        sequence_enforcement=capability,
    )
    assert is_verified_review_completion(result)
    assert isinstance(result, VerifiedReviewCompletion)
    assert result.decision_projection()["technical_status"] == "GREEN_TECHNICALLY_READY"
    assert validate_directory(output, sequence_enforcement=capability) == []
    reverified = verify_completed_review(
        output,
        head_source=head_source(),
        sequence_enforcement=capability,
    )
    assert reverified.decision_projection() == result.decision_projection()


def test_official_completion_threads_governance_evidence_through_final_bytes(
    tmp_path,
    monkeypatch,
):
    install_live_payloads(monkeypatch)
    value = package()
    evidence = verified_governance()
    value["security_profile"].update({
        "security_activation_trigger": True,
        "claim_repository_settings_enforced": True,
        "claim_merge_authorized": True,
        "governance_evidence_id": evidence.evidence_id,
    })
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    output = tmp_path / "review"

    result = complete_review(
        package_path,
        output,
        head_source=head_source(),
        governance_evidence=evidence,
    )
    assert is_verified_review_completion(result)
    assert isinstance(result, VerifiedReviewCompletion)
    projection = result.decision_projection()
    assert projection["security_profile"]["governance_evidence_status"] == "verified"
    assert projection["technical_status"] == "GREEN_TECHNICALLY_READY"
    assert validate_directory(output, governance_evidence=evidence) == []

    reverified = verify_completed_review(
        output,
        head_source=head_source(),
        governance_evidence=evidence,
    )
    assert reverified.decision_projection() == projection
    assert reverified.artifact_sha256 == result.artifact_sha256
    assert reverified.decision_projection_sha256 == result.decision_projection_sha256


def test_official_completion_rejects_missing_governance_capability(
    tmp_path,
    monkeypatch,
):
    install_live_payloads(monkeypatch)
    value = package()
    evidence = verified_governance()
    value["security_profile"].update({
        "security_activation_trigger": True,
        "claim_repository_settings_enforced": True,
        "governance_evidence_id": evidence.evidence_id,
    })
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    result = complete_review(
        package_path,
        tmp_path / "review",
        head_source=head_source(),
    )
    assert isinstance(result, IncompleteReview)


def test_official_completion_rejects_mismatched_governance_capability(
    tmp_path,
    monkeypatch,
):
    install_live_payloads(monkeypatch)
    value = package()
    evidence = verified_governance(pr_number=43)
    value["security_profile"].update({
        "claim_repository_settings_enforced": True,
        "governance_evidence_id": evidence.evidence_id,
    })
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    result = complete_review(
        package_path,
        tmp_path / "review",
        head_source=head_source(),
        governance_evidence=evidence,
    )
    assert isinstance(result, IncompleteReview)


def test_official_completion_rejects_changed_head_governance_capability(
    tmp_path,
    monkeypatch,
):
    install_live_payloads(monkeypatch, OTHER_HEAD)
    value = package()
    evidence = verified_governance()
    value["review_identity"]["reviewed_head_sha"] = OTHER_HEAD
    for record in value["evidence_records"]:
        record["reviewed_head_sha"] = OTHER_HEAD
    value["security_profile"].update({
        "claim_repository_settings_enforced": True,
        "governance_evidence_id": evidence.evidence_id,
    })
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    result = complete_review(
        package_path,
        tmp_path / "review",
        head_source=head_source(),
        governance_evidence=evidence,
    )
    assert isinstance(result, IncompleteReview)


def test_official_completion_rejects_serialized_governance_lookalike(
    tmp_path,
    monkeypatch,
):
    install_live_payloads(monkeypatch)
    value = package()
    evidence = verified_governance()
    value["security_profile"].update({
        "claim_repository_settings_enforced": True,
        "governance_evidence_id": evidence.evidence_id,
    })
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    result = complete_review(
        package_path,
        tmp_path / "review",
        head_source=head_source(),
        governance_evidence={"evidence_id": evidence.evidence_id},
    )
    assert isinstance(result, IncompleteReview)


def test_handoff_owner_and_prompt_consume_one_profile_projection():
    value = package()
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
    value["decision"]["technical_status"] = "YELLOW_CHANGES_OR_VERIFICATION_REQUIRED"
    package_bytes = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    (tmp_path / "review-package.json").write_bytes(package_bytes)
    write_review_artifacts(value, tmp_path, review_package_bytes=package_bytes)
    path = tmp_path / PROJECTION_NAME
    projection = json.loads(path.read_text(encoding="utf-8"))
    projection["security_profile"].update({
        "blocks_green_merge_recommendation": False,
        "reason_codes": [],
    })
    projection["technical_status"] = "GREEN_TECHNICALLY_READY"
    projection["technical_status_reason_codes"] = []
    projection["owner_readiness"].update({
        "color": "GREEN",
        "action_kind": "merge_now",
        "message_key": "green_merge_now",
        "reason_codes": [],
    })
    projection["next_action"].update({
        "kind": "merge_now",
        "recipient": "none",
        "may_modify_code": False,
        "prompt_required": False,
        "prompt_kind": None,
        "reason_codes": [],
    })
    path.write_text(
        json.dumps(
            projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    assert "PRI-PROJECTION-003" in {
        item.code for item in validate_directory(tmp_path)
    }


def test_schema_requires_structured_security_profile_carrier():
    value = package()
    value.pop("security_profile")
    assert "PRI-SCHEMA-001" in {item.code for item in validate_package(value)}


def test_semantic_validation_uses_profile_projection_for_status():
    value = package()
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


def test_same_name_same_app_check_without_producer_evidence_cannot_mint_sequence():
    governance = verified_governance(check_context=SEQUENCE_CONTEXT)
    try:
        verify_sequence_ci_enforcement(
            governance,
            check_context=SEQUENCE_CONTEXT,
            app_id=SEQUENCE_APP_ID,
        )
    except ValueError as exc:
        assert "producer execution evidence" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("same-name same-App check minted sequence without producer proof")


def test_sequence_producer_evidence_requires_validator_execution():
    governance = verified_governance(check_context=SEQUENCE_CONTEXT)
    try:
        verify_sequence_producer_evidence(
            governance,
            check_context=SEQUENCE_CONTEXT,
            app_id=SEQUENCE_APP_ID,
            workflow_path=".github/workflows/validate-rereview-sequence.yml",
            workflow_sha="2" * 40,
            validator_command="python -m pytest",
        )
    except ValueError as exc:
        assert "sequence validator" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("producer proof accepted a non-sequence command")


def test_manifest_validation_cli_replays_opaque_evidence_from_raw_receipts(tmp_path):
    import subprocess
    import sys

    value = package()
    package_path = tmp_path / "review-package.json"
    package_bytes = write_package(package_path, value)
    capability = verified_sequence()
    write_review_artifacts(
        value,
        tmp_path,
        review_package_bytes=package_bytes,
        sequence_enforcement=capability,
    )

    raw = governance_fixture(check_context=SEQUENCE_CONTEXT)
    fixture_path = tmp_path / "governance-responses.json"
    fixture_path.write_text(json.dumps(raw), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_review_v2.py",
            str(tmp_path),
            "--target-repository",
            REPOSITORY,
            "--pr-number",
            str(PR_NUMBER),
            "--reviewed-head-sha",
            HEAD,
            "--governance-fixture",
            str(fixture_path),
            "--sequence-workflow-sha",
            "2" * 40,
            "--sequence-validator-command",
            "python scripts/validate_rereview_sequence.py sequence.json --review EVENT=review",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "OK: review package" in result.stdout


def test_manifest_validation_cli_rejects_wrong_sequence_command(tmp_path):
    import subprocess
    import sys

    value = package()
    package_path = tmp_path / "review-package.json"
    package_bytes = write_package(package_path, value)
    capability = verified_sequence()
    write_review_artifacts(
        value,
        tmp_path,
        review_package_bytes=package_bytes,
        sequence_enforcement=capability,
    )

    raw = governance_fixture(check_context=SEQUENCE_CONTEXT)
    fixture_path = tmp_path / "governance-responses.json"
    fixture_path.write_text(json.dumps(raw), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_review_v2.py",
            str(tmp_path),
            "--target-repository",
            REPOSITORY,
            "--pr-number",
            str(PR_NUMBER),
            "--reviewed-head-sha",
            HEAD,
            "--governance-fixture",
            str(fixture_path),
            "--sequence-workflow-sha",
            "2" * 40,
            "--sequence-validator-command",
            "python -m pytest",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "sequence validator" in (result.stderr + result.stdout)
