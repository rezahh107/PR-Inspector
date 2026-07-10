import copy
import json
from pathlib import Path

import pytest

from pr_inspector.governance import (
    GovernanceEvidenceError,
    derive_enforcement_status,
    verify_github_governance_source,
    verify_governance_record,
)
from pr_inspector.sequence_policy import validate_rereview_sequence

ROOT = Path(__file__).resolve().parents[1]
HEAD = "1" * 40
REPOSITORY = "example/project"
REPOSITORY_ID = 4242


def record() -> dict:
    return json.loads(
        (ROOT / "fixtures/governance/verified-enforced.json").read_text(
            encoding="utf-8"
        )
    )


def repository_payload() -> dict:
    return {
        "id": REPOSITORY_ID,
        "full_name": REPOSITORY,
        "url": f"https://api.github.com/repos/{REPOSITORY}",
        "html_url": f"https://github.com/{REPOSITORY}",
    }


def response_urls(value: dict) -> list[str]:
    base = f"https://api.github.com/repos/{REPOSITORY}"
    return [
        base,
        f"{base}/branches/{value['default_branch']}/protection",
        f"{base}/rulesets",
        f"{base}/pulls/{value['pull_request_number']}/reviews",
        f"{base}/commits/{value['exact_head_sha']}/check-runs",
    ]


def authoritative_source(value: dict | None = None):
    value = value or record()
    return verify_github_governance_source(
        value,
        repository_payload=repository_payload(),
        response_urls=response_urls(value),
        expected_repository=REPOSITORY,
    )


def verified(value: dict | None = None):
    value = value or record()
    return verify_governance_record(
        authoritative_source(value),
        expected_repository=REPOSITORY,
        expected_pr_number=42,
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
    assert "authoritative `main`" in readme


def test_pr12_history_preserves_uncertainty():
    current = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
    text = (ROOT / f"protocols/{current}/PR_REVIEW_CONTRACT.md").read_text(
        encoding="utf-8"
    )
    assert "PR #12 is historical provenance" in text
    assert "state `COMMENTED`" in text
    assert "did not prove completion" in text
    assert "PR #12 received all required approvals" not in text


def test_bot_commented_review_does_not_satisfy_human_approval():
    value = record()
    value["reviews"] = [
        {
            "reviewer": "review-bot",
            "state": "COMMENTED",
            "commit_id": HEAD,
            "is_bot": True,
            "is_author": False,
        }
    ]
    evidence = verified(value)
    assert not evidence.approval_complete
    assert not evidence.merge_authorized


def test_pr_author_review_does_not_satisfy_independent_review():
    value = record()
    value["reviews"][0]["is_author"] = True
    evidence = verified(value)
    assert evidence.valid_approval_reviewers == ()
    assert not evidence.merge_authorized


def test_raw_repository_json_cannot_create_verified_governance_evidence():
    with pytest.raises(GovernanceEvidenceError, match="not verified official GitHub API"):
        verify_governance_record(
            record(),  # type: ignore[arg-type]
            expected_repository=REPOSITORY,
            expected_pr_number=42,
            expected_head_sha=HEAD,
        )


def test_self_asserted_status_is_rejected():
    value = record()
    value["pull_request_required"]["value"] = None
    with pytest.raises(GovernanceEvidenceError, match="does not match derived"):
        verified(value)


def test_missing_repository_settings_is_insufficient_evidence():
    value = record()
    value["required_approvals"]["value"] = None
    value["status"] = "insufficient_evidence"
    evidence = verified(value)
    assert evidence.enforcement_status == "insufficient_evidence"
    assert not evidence.merge_authorized
    assert (
        evidence.conclusion
        == "merge readiness appears satisfied, but repository-level enforcement is unverified"
    )


def test_branch_protection_without_required_reviews_is_not_verified_enforced():
    value = record()
    value["required_approvals"]["value"] = 0
    value["status"] = "partially_enforced"
    assert derive_enforcement_status(value) == "partially_enforced"
    assert not verified(value).merge_authorized


def test_required_ci_without_required_approval_is_not_authorized():
    value = record()
    value["reviews"] = []
    assert not verified(value).merge_authorized


def test_required_approval_without_exact_head_ci_is_not_authorized():
    value = record()
    value["checks"][0]["head_sha"] = "2" * 40
    assert not verified(value).merge_authorized


def test_stale_approval_does_not_satisfy_current_head():
    value = record()
    value["reviews"][0]["commit_id"] = "2" * 40
    assert not verified(value).approval_complete


def test_specialist_review_without_identity_fails():
    value = record()
    value["specialist_review"] = {
        "required": True,
        "reviewer_identity_observed": False,
        "qualification_verified": False,
        "reviewer": None,
        "enforcement_status": "human_governance_required",
    }
    assert not verified(value).specialist_satisfied


def test_specialist_identity_without_qualification_is_honest():
    value = record()
    value["specialist_review"] = {
        "required": True,
        "reviewer_identity_observed": True,
        "qualification_verified": False,
        "reviewer": "independent-reviewer",
        "enforcement_status": "human_governance_required",
    }
    evidence = verified(value)
    assert not evidence.specialist_satisfied
    assert not evidence.merge_authorized


def test_bypass_actors_are_recorded_and_block_full_enforcement():
    value = record()
    value["bypass_actors"]["value"] = ["repository_admins"]
    value["status"] = "partially_enforced"
    evidence = verified(value)
    assert evidence.bypass_actors == ("repository_admins",)
    assert not evidence.merge_authorized


def test_governance_source_rejects_unavailable_or_self_authored_source():
    value = record()
    value["source"] = "unavailable"
    value["status"] = "unavailable"
    with pytest.raises(GovernanceEvidenceError, match="only official GitHub REST API"):
        authoritative_source(value)


def test_governance_source_requires_every_fetched_response_receipt():
    value = record()
    urls = response_urls(value)
    urls.remove(
        f"https://api.github.com/repos/{REPOSITORY}/commits/{HEAD}/check-runs"
    )
    with pytest.raises(GovernanceEvidenceError, match="missing fetched response receipts"):
        verify_github_governance_source(
            value,
            repository_payload=repository_payload(),
            response_urls=urls,
            expected_repository=REPOSITORY,
        )


def test_governance_source_rejects_noncanonical_evidence_reference():
    value = record()
    value["required_approvals"]["evidence"] = ["self-authored-approval.json"]
    with pytest.raises(GovernanceEvidenceError, match="not an official GitHub API URL"):
        authoritative_source(value)


def test_governance_source_rejects_forged_repository_identity():
    payload = repository_payload()
    payload["id"] = 0
    with pytest.raises(GovernanceEvidenceError, match="repository id"):
        verify_github_governance_source(
            record(),
            repository_payload=payload,
            response_urls=response_urls(record()),
            expected_repository=REPOSITORY,
        )


def test_governance_evidence_identity_is_exact_head_bound():
    source = authoritative_source(record())
    with pytest.raises(GovernanceEvidenceError, match="exact target head"):
        verify_governance_record(
            source,
            expected_repository=REPOSITORY,
            expected_pr_number=42,
            expected_head_sha="2" * 40,
        )


def test_governance_behavioral_matrix_and_mutations_are_complete():
    current = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
    text = (
        ROOT
        / f"protocols/{current}/policies/GOVERNANCE_BEHAVIORAL_RULE_COVERAGE.md"
    ).read_text(encoding="utf-8")
    mutations = json.loads(
        (ROOT / "fixtures/governance/mutation-cases.json").read_text(
            encoding="utf-8"
        )
    )
    required = {
        "PRR-DOC-LIFECYCLE-001",
        "PRR-GOV-CLAIM-001",
        "PRR-GOV-REVIEW-001",
        "PRR-GOV-SPECIALIST-001",
        "PRR-GOV-AUTHORIZATION-001",
        "PRR-GOV-BYPASS-001",
        "PRR-HISTORY-NOFABRICATION-001",
    }
    assert required == {case["rule_id"] for case in mutations["cases"]}
    assert all(rule in text for rule in required)
    assert "repository_settings_enforced" in text


def test_release_v18_snapshot_remains_locked_and_unchanged():
    from pr_inspector.repository import parse_lock, sha256

    lock = ROOT / "release-locks/v1.8.0.sha256"
    for rel, digest in parse_lock(lock).items():
        assert sha256(ROOT / rel) == digest
