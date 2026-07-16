from types import MappingProxyType

import pytest

from pr_inspector import runtime_v1_11 as runtime
from tests.test_candidate_v1_11 import inspector_commit_receipt


def test_missing_governance_fact_is_a_gap_not_a_key_error():
    facts = {field: True for field in runtime.REQUIRED_GOVERNANCE_FACTS}
    facts.pop("branch_protection_verified")
    capability = runtime.VerifiedGovernanceCapability(
        runtime._CAPABILITY_TOKEN,
        "o/r",
        100,
        7,
        "a" * 40,
        runtime.LOCKED_INSPECTOR_REPOSITORY,
        runtime.LOCKED_INSPECTOR_REPOSITORY_ID,
        "2026-07-16T00:00:00Z",
        MappingProxyType(facts),
        MappingProxyType({}),
    )

    result = runtime.classify_governance(
        capability,
        target_repository="o/r",
        target_repository_id=100,
        pull_request=7,
        reviewed_head_sha="a" * 40,
    )

    assert result["status"] == "GAP_FOUND"
    assert "branch_protection_unavailable" in result["reason_codes"]


def test_missing_base_artifacts_raise_descriptive_value_error():
    with pytest.raises(ValueError, match="missing required artifacts"):
        runtime.verify_candidate_review_artifact_bytes(
            {},
            inspector_commit_receipt(),
        )


def test_profile_commands_invalid_utf8_is_reported_not_raised():
    errors = runtime.validate_owner_profile_commands(b"\xff\n")
    assert "owner profile commands are not valid UTF-8" in errors
