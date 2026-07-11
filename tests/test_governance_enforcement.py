import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from pr_inspector.governance import (
    GovernanceEvidenceError,
    SpecialistRequirement,
    VerifiedGitHubGovernanceSource,
    VerifiedGovernanceEvidence,
    derive_enforcement_status,
    verify_github_governance_source,
    verify_governance_record,
)
from tests.governance_test_support import (
    HEAD,
    PR_NUMBER,
    REPOSITORY,
    fixture,
    membership_response,
    responses,
)

ROOT = Path(__file__).resolve().parents[1]


def source(value=None, *, specialist=None, fetched_at=None):
    response_map = responses(value, fetched_at=fetched_at)
    if specialist is not None:
        response_map["specialist:independent-reviewer"] = membership_response(
            fetched_at=fetched_at
        )
    return verify_github_governance_source(
        response_map,
        expected_repository=REPOSITORY,
        expected_pr_number=PR_NUMBER,
        expected_head_sha=HEAD,
        specialist_requirement=specialist,
    )


def verified(value=None, *, specialist=None):
    return verify_governance_record(
        source(value, specialist=specialist),
        expected_repository=REPOSITORY,
        expected_pr_number=PR_NUMBER,
        expected_head_sha=HEAD,
    )


def test_active_lifecycle_documentation_is_not_candidate_wording():
    current = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
    paths = [ROOT / "README.md", ROOT / f"protocols/{current}/PR_REVIEW_CONTRACT.md"]
    forbidden = (
        "active candidate on the unmerged pr branch",
        "default branch remains authoritative until this pr is merged",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8").lower()
        assert all(phrase not in text for phrase in forbidden)


def test_readme_no_longer_describes_active_protocol_as_unmerged():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "unmerged pr" not in readme
    assert "repository authority is determined from live `main`" in readme


def test_pr12_history_preserves_uncertainty():
    current = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
    text = (ROOT / f"protocols/{current}/PR_REVIEW_CONTRACT.md").read_text(
        encoding="utf-8"
    )
    assert "PR #12 is historical provenance" in text
    assert "state `COMMENTED`" in text
    assert "did not prove completion" in text
    assert "PR #12 received all required approvals" not in text


def test_complete_payload_derived_evidence_is_verified():
    evidence = verified()
    assert evidence.enforcement_status == "verified_enforced"
    assert evidence.valid_approval_reviewers == ("independent-reviewer",)
    assert evidence.required_status_checks == (
        ("Validate PR Inspector repository", 15368),
    )
    assert evidence.exact_head_checks_satisfied
    assert evidence.approval_complete
    assert evidence.merge_authorized


def test_sealed_capability_constructors_reject_caller_values():
    with pytest.raises(TypeError):
        VerifiedGitHubGovernanceSource()
    with pytest.raises(TypeError):
        VerifiedGovernanceEvidence()


def test_raw_normalized_json_and_url_lists_cannot_mint_source():
    with pytest.raises(GovernanceEvidenceError, match="verifier-created GitHub response"):
        verify_github_governance_source(
            {"repository": {"url": f"https://api.github.com/repos/{REPOSITORY}"}},
            expected_repository=REPOSITORY,
            expected_pr_number=PR_NUMBER,
            expected_head_sha=HEAD,
        )


def test_bot_commented_review_does_not_satisfy_human_approval():
    value = fixture()
    value["responses"]["reviews"]["payload"] = [
        {
            "user": {"login": "review-bot[bot]", "type": "Bot"},
            "state": "COMMENTED",
            "commit_id": HEAD,
            "submitted_at": "2026-07-10T18:02:00Z",
        }
    ]
    evidence = verified(value)
    assert not evidence.approval_complete
    assert not evidence.merge_authorized


def test_pr_author_review_does_not_satisfy_independent_review():
    value = fixture()
    value["responses"]["reviews"]["payload"][0]["user"]["login"] = (
        "pull-request-author"
    )
    evidence = verified(value)
    assert evidence.valid_approval_reviewers == ()
    assert not evidence.merge_authorized


def test_stale_approval_does_not_satisfy_current_head():
    value = fixture()
    value["responses"]["reviews"]["payload"][0]["commit_id"] = "2" * 40
    assert not verified(value).approval_complete


def test_required_check_requires_configured_app_identity():
    value = fixture()
    value["responses"]["checks"]["payload"]["check_runs"][0]["app"]["id"] = 999
    evidence = verified(value)
    assert not evidence.exact_head_checks_satisfied
    assert not evidence.merge_authorized


def test_required_check_requires_exact_head():
    value = fixture()
    value["responses"]["checks"]["payload"]["check_runs"][0]["head_sha"] = "2" * 40
    assert not verified(value).exact_head_checks_satisfied


def test_missing_settings_payload_is_insufficient_evidence():
    value = fixture()
    value["responses"]["branch_protection"].update(
        {"status_code": 404, "payload": {"message": "Not Found"}}
    )
    evidence = verified(value)
    assert evidence.enforcement_status == "insufficient_evidence"
    assert not evidence.merge_authorized
    assert (
        evidence.conclusion
        == "merge readiness appears satisfied, but repository-level enforcement is unverified"
    )


def test_branch_protection_without_required_reviews_is_not_enforced():
    value = fixture()
    value["responses"]["branch_protection"]["payload"][
        "required_pull_request_reviews"
    ] = None
    evidence = verified(value)
    assert evidence.enforcement_status != "verified_enforced"
    assert not evidence.merge_authorized


def test_bypass_actor_blocks_verified_enforcement():
    value = fixture()
    value["responses"]["branch_protection"]["payload"]["enforce_admins"][
        "enabled"
    ] = False
    evidence = verified(value)
    assert "repository_admins" in evidence.bypass_actors
    assert not evidence.merge_authorized


def test_specialist_boolean_or_identity_without_membership_is_not_qualification():
    requirement = SpecialistRequirement("example-org", "security-reviewers")
    evidence = verify_governance_record(
        verify_github_governance_source(
            responses(),
            expected_repository=REPOSITORY,
            expected_pr_number=PR_NUMBER,
            expected_head_sha=HEAD,
            specialist_requirement=requirement,
        ),
        expected_repository=REPOSITORY,
        expected_pr_number=PR_NUMBER,
        expected_head_sha=HEAD,
    )
    assert not evidence.specialist_satisfied
    assert evidence.specialist_status == "human_governance_required"
    assert not evidence.merge_authorized


def test_active_team_membership_can_satisfy_specialist_gate():
    requirement = SpecialistRequirement("example-org", "security-reviewers")
    evidence = verified(specialist=requirement)
    assert evidence.specialist_satisfied
    assert evidence.specialist_status == "repository_team_enforced"
    assert evidence.merge_authorized


@pytest.mark.parametrize(
    "fetched_at",
    [
        datetime.now(timezone.utc) - timedelta(minutes=10),
        datetime.now(timezone.utc) + timedelta(minutes=2),
    ],
)
def test_stale_or_future_response_receipts_fail_closed(fetched_at):
    with pytest.raises(GovernanceEvidenceError, match="stale|future-dated"):
        source(fetched_at=fetched_at)


def test_missing_required_response_receipt_fails_closed():
    value = responses()
    value.pop("checks")
    with pytest.raises(GovernanceEvidenceError, match="required GitHub endpoint checks"):
        verify_github_governance_source(
            value,
            expected_repository=REPOSITORY,
            expected_pr_number=PR_NUMBER,
            expected_head_sha=HEAD,
        )


def test_forged_repository_identity_is_rejected():
    value = fixture()
    value["responses"]["repository"]["payload"]["id"] = 0
    with pytest.raises(GovernanceEvidenceError, match="repository id"):
        source(value)


def test_governance_evidence_is_exact_head_bound():
    verified_source = source()
    with pytest.raises(GovernanceEvidenceError, match="exact target head"):
        verify_governance_record(
            verified_source,
            expected_repository=REPOSITORY,
            expected_pr_number=PR_NUMBER,
            expected_head_sha="2" * 40,
        )


def test_derive_enforcement_status_rejects_unbound_required_check_identity():
    record = {
        "limitations": [],
        "pull_request_required": {"value": True},
        "required_status_checks": {"value": ["name-only"]},
        "required_approvals": {"value": 1},
        "dismiss_stale_approvals": {"value": True},
        "code_owner_review_required": {"value": True},
        "bypass_actors": {"value": []},
    }
    assert derive_enforcement_status(record) != "verified_enforced"


def test_governance_behavioral_matrix_and_mutations_are_complete():
    current = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
    text = (
        ROOT
        / f"protocols/{current}/policies/GOVERNANCE_BEHAVIORAL_RULE_COVERAGE.md"
    ).read_text(encoding="utf-8")
    mutation = json.loads(
        (ROOT / "fixtures/governance/mutation-cases.json").read_text(
            encoding="utf-8"
        )
    )
    rule_ids = {case["rule_id"] for case in mutation["cases"]}
    assert mutation["schema_version"] == 2
    assert len(rule_ids) == len(mutation["cases"])
    for rule_id in rule_ids:
        assert f"`{rule_id}`" in text
    assert "python -m pytest -q tests/test_governance_enforcement.py" in text


def test_release_v18_snapshot_remains_locked_and_unchanged():
    lock = (ROOT / "release-locks/v1.8.0.sha256").read_bytes()
    assert lock
    assert not any(
        path.is_relative_to(ROOT / "protocols/v1.8.0")
        for path in []
    )
