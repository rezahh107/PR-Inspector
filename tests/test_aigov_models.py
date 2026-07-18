from __future__ import annotations

import copy
import hashlib
import json
import pickle
from pathlib import Path

import pytest

from pr_inspector.aigov_errors import AIGOVValidationError
from pr_inspector.aigov_models import (
    ActivationResult,
    EvidenceProfile,
    ExecutionUrgency,
    FutureEvidenceProfile,
    FutureExecutionUrgency,
    InspectionProfile,
    MODEL_BY_CONTRACT,
    is_validated_aigov_contract,
)
from pr_inspector.aigov_schema_registry import (
    CONTRACT_TYPES,
    LocalAIGOVSchemaRegistry,
    local_aigov_schema_registry,
)
from pr_inspector.aigov_validation import load_aigov_contract, load_aigov_json


ROOT = Path(__file__).resolve().parents[1]
VALID = ROOT / "tests/fixtures/aigov/v2.5.0/schema_valid"
ACTIVE_IMPORT_ROOTS = (
    ROOT / "pr_inspector",
    ROOT / "scripts",
)

def _fixture(contract: str) -> dict:
    value = json.loads((VALID / f"{contract}.json").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _code(exc: AIGOVValidationError) -> str:
    return exc.diagnostics[0].code


def test_exact_model_inventory_and_schema_mapping() -> None:
    registry = local_aigov_schema_registry()
    assert tuple(MODEL_BY_CONTRACT) == CONTRACT_TYPES
    assert registry.contract_types == CONTRACT_TYPES
    assert len(set(MODEL_BY_CONTRACT.values())) == 12
    assert len({registry.schema_id(name) for name in CONTRACT_TYPES}) == 12

    for contract in CONTRACT_TYPES:
        schema = registry.schema(contract)
        model = load_aigov_contract(contract, _fixture(contract), registry=registry)
        assert type(model) is MODEL_BY_CONTRACT[contract]
        assert model.contract_type == contract
        assert model.contract_version == "1.0"
        assert model.activation_state == "inactive"
        assert model.schema_id == schema["$id"]
        assert set(registry.required_fields(contract)) <= set(model.payload)
        assert set(model.to_dict()) == set(schema["properties"])
        assert registry.validate(contract, model.to_dict()) == ()
        assert is_validated_aigov_contract(model)


def test_models_are_immutable_and_detached_from_mutable_input() -> None:
    source = _fixture("review_policy_resolution")
    model = load_aigov_contract("review_policy_resolution", source)
    original = model.to_json()

    source["target_identity"]["repository_full_name"] = "attacker/rewrite"
    source["evidence_refs"].clear()
    assert model.to_json() == original

    with pytest.raises(AttributeError):
        model._payload = {}  # type: ignore[attr-defined]
    with pytest.raises(TypeError):
        model.payload["status"] = "MISSING"  # type: ignore[index]
    with pytest.raises(AttributeError):
        model.payload["evidence_refs"].append({})  # type: ignore[union-attr]


def test_deterministic_equality_serialization_and_provenance() -> None:
    payload = _fixture("classification_record")
    first = load_aigov_contract("classification_record", payload)
    second = load_aigov_contract("classification_record", copy.deepcopy(payload))
    assert first == second
    assert hash(first) == hash(second)
    assert first.to_json() == second.to_json()
    assert first.to_json() == json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    expected = hashlib.sha256(first.to_json().encode("utf-8")).hexdigest()
    assert first.provenance.payload_sha256 == expected
    assert len(first.provenance.schema_sha256) == 64


def test_exact_enum_behavior_and_future_vocabularies_remain_separate() -> None:
    assert [item.value for item in InspectionProfile] == [
        "minimal", "standard", "strict"
    ]
    assert InspectionProfile.STANDARD is not InspectionProfile.STRICT
    assert [item.value for item in EvidenceProfile] == [
        "compact", "full", "high_assurance"
    ]
    assert [item.value for item in ExecutionUrgency] == ["normal", "expedited"]
    assert [item.value for item in FutureEvidenceProfile] == [
        "minimal", "standard", "strict"
    ]
    assert [item.value for item in FutureExecutionUrgency] == [
        "routine", "elevated", "urgent"
    ]
    assert ActivationResult.ACTIVATED.value == "activated"
    with pytest.raises(ValueError):
        InspectionProfile("strict_alias")


def test_direct_construction_subclass_and_copied_objects_do_not_mint_authority() -> None:
    model_type = MODEL_BY_CONTRACT["repository_review_policy"]
    with pytest.raises(TypeError):
        model_type()

    class Forged(model_type):  # type: ignore[misc, valid-type]
        __slots__ = ()

    forged = object.__new__(Forged)
    assert is_validated_aigov_contract(forged) is False

    valid = load_aigov_contract(
        "repository_review_policy", _fixture("repository_review_policy")
    )
    assert copy.copy(valid) is valid
    assert copy.deepcopy(valid) is valid
    with pytest.raises(TypeError):
        pickle.dumps(valid)


def test_unknown_contract_and_explicit_type_mismatch_fail_closed() -> None:
    with pytest.raises(AIGOVValidationError) as unknown:
        load_aigov_contract("unknown_contract", {})
    assert _code(unknown.value) == "AIGOV-MODEL-001"

    payload = _fixture("classification_record")
    with pytest.raises(AIGOVValidationError) as mismatch:
        load_aigov_contract("scope_record", payload)
    assert _code(mismatch.value) == "AIGOV-MODEL-003"


def test_duplicate_json_keys_are_rejected_before_schema_validation() -> None:
    raw = '{"contract_type":"classification_record","contract_type":"scope_record"}'
    with pytest.raises(AIGOVValidationError) as caught:
        load_aigov_json("classification_record", raw)
    assert _code(caught.value) == "AIGOV-MODEL-004"


def test_schema_validation_precedes_semantic_validation() -> None:
    payload = _fixture("scope_record")
    payload["head_sha"] = "short"
    payload["scope_digest"] = "sha256:" + "A" * 64
    with pytest.raises(AIGOVValidationError) as caught:
        load_aigov_contract("scope_record", payload)
    assert {item.code for item in caught.value.diagnostics} == {"AIGOV-MODEL-003"}


def test_local_schema_registry_rejects_remote_or_traversing_refs(tmp_path: Path) -> None:
    source = local_aigov_schema_registry().schema_dir
    target = tmp_path / "schemas"
    import shutil

    shutil.copytree(source, target)
    common = target / "common.schema.json"
    value = json.loads(common.read_text(encoding="utf-8"))
    value["$defs"]["remote_attack"] = {"$ref": "https://attacker.invalid/schema"}
    common.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(RuntimeError, match="non-local resolution"):
        LocalAIGOVSchemaRegistry(target)

    shutil.rmtree(target)
    shutil.copytree(source, target)
    schema = target / "classification_record.schema.json"
    value = json.loads(schema.read_text(encoding="utf-8"))
    value["properties"]["classification_id"] = {"$ref": "../escape.json"}
    schema.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(RuntimeError, match="non-local resolution"):
        LocalAIGOVSchemaRegistry(target)


def test_active_runtime_has_no_inactive_aigov_imports() -> None:
    forbidden = (
        "aigov_models",
        "aigov_validation",
        "aigov_schema_registry",
        "aigov_errors",
    )
    for base in ACTIVE_IMPORT_ROOTS:
        for path in sorted(base.rglob("*.py")):
            if (
                path.parent == ROOT / "pr_inspector"
                and path.name.startswith("aigov_")
            ):
                continue
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                assert token not in text, f"inactive AIGOV import in {path.relative_to(ROOT)}"


def test_active_protocol_and_load_order_remain_unchanged() -> None:
    import yaml

    assert (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip() == "v1.11.1"
    manifest = yaml.safe_load(
        (ROOT / "protocol-manifest.yaml").read_text(encoding="utf-8")
    )
    assert manifest["active_version"] == "v1.11.1"
    assert manifest["operation_mode"] == "read_only_review"
    assert all("aigov" not in path.lower() for path in manifest["load_order"])
