from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas/aigov/v2.5.0"
VALID_DIR = ROOT / "tests/fixtures/aigov/v2.5.0/schema_valid"
INVALID_DIR = ROOT / "tests/fixtures/aigov/v2.5.0/schema_invalid"
EXPECTED_CONTRACTS = (
    "repository_review_policy", "review_policy_resolution", "obligation_authority_binding",
    "classification_record", "scope_record", "review_execution", "review_receipt_core",
    "publication_attempt", "policy_transition_record", "merge_readiness_record",
    "post_merge_closure", "tool_execution_attestation",
)
HISTORICAL_SCHEMA_SHA256 = {
    "protocols/v1.11.1/schemas/review-package.schema.json": "84172bc0f76fc4209e3618fa9847fc2430926ad80bfcf34f54305c8e7d80df47",
    "protocols/v1.11.1/schemas/decision-projection.schema.json": "05cca1bed416b6e711511515babfe8f1ee6868f079ac9231ca838566d9d6b3e7",
    "protocols/v1.11.1/schemas/owner-delivery-contract.schema.json": "60ad344469699a3988abbb7de22227faaa38f7be7d8269465d3885cb8b71b2ca",
    "protocols/v1.11.1/schemas/ci-identity.schema.json": "345cebcaa2ba54dc7c90440866437e46dea3b4f18da633566182ce1383d681c6",
    "protocols/v1.11.1/schemas/rereview-sequence.schema.json": "c6cfa2569843d9165baeca6e8077f97ccf057918066fd671f6bc68b5a0ba6a5c",
    "protocols/v1.11.1/schemas/governance-evidence.schema.json": "ea108eda28748321dcf928778f8bed384da832884961b151a463072cfc3ddb50",
}


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8")); assert isinstance(value, dict); return value


def _schemas() -> dict[str, dict]:
    return {name: _load(SCHEMA_DIR / f"{name}.schema.json") for name in ("common", *EXPECTED_CONTRACTS)}


def _registry(schemas: dict[str, dict]) -> Registry:
    registry = Registry()
    for schema in schemas.values():
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return registry


def _validator(contract: str) -> Draft202012Validator:
    schemas = _schemas()
    return Draft202012Validator(schemas[contract], registry=_registry(schemas), format_checker=FormatChecker())


def _fixtures(directory: Path) -> dict[str, dict]:
    value = {path.stem: _load(path) for path in sorted(directory.glob("*.json"))}
    assert set(value) == set(EXPECTED_CONTRACTS)
    return value


def _assert_invalid(contract: str, payload: dict) -> None:
    assert list(_validator(contract).iter_errors(payload)), contract


def _refs(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "$ref": yield item
            yield from _refs(item)
    elif isinstance(value, list):
        for item in value: yield from _refs(item)


def test_expected_inactive_schema_inventory_and_index():
    expected = {"common.schema.json", "schema-index.json", *(f"{name}.schema.json" for name in EXPECTED_CONTRACTS)}
    assert {path.name for path in SCHEMA_DIR.glob("*.json")} == expected
    index = _load(SCHEMA_DIR / "schema-index.json")
    assert index["activation_state"] == "inactive"
    assert index["authoritative_runtime"] is False
    assert index["active_protocol_integration"] is False
    assert tuple(item["contract_type"] for item in index["schemas"]) == EXPECTED_CONTRACTS


def test_all_schemas_are_valid_unique_versioned_and_locally_resolved():
    schemas = _schemas(); ids = []
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema); ids.append(schema["$id"])
        assert all("://" not in ref for ref in _refs(schema))
        if name != "common":
            assert schema["properties"]["contract_type"]["const"] == name
            assert schema["properties"]["activation_state"]["const"] == "inactive"
            assert schema["additionalProperties"] is False
    assert len(ids) == len(set(ids))


def test_every_contract_has_passing_valid_and_failing_invalid_fixture():
    valid, invalid = _fixtures(VALID_DIR), _fixtures(INVALID_DIR)
    for contract in EXPECTED_CONTRACTS:
        _validator(contract).validate(valid[contract])
        _assert_invalid(contract, invalid[contract])


def test_canonical_vocabularies_and_minimum_carriers():
    common = _load(SCHEMA_DIR / "common.schema.json")
    assert common["$defs"]["inspection_profile"]["enum"] == ["minimal", "standard", "strict"]
    assert common["$defs"]["merge_method"]["enum"] == ["merge_commit", "squash_merge", "rebase_merge"]
    required = {
        "review_execution": {"review_id", "reviewed_head_sha", "protocol_version", "canonical_package_digest", "completion_claim"},
        "obligation_authority_binding": {"carrier_id", "governed_rules", "authority_ref", "resolution_status"},
        "tool_execution_attestation": {"carrier_id", "governed_rule_id", "selected_tool", "invocation_record", "execution_result", "readback_status"},
    }
    for name, fields in required.items():
        assert fields <= set(_load(SCHEMA_DIR / f"{name}.schema.json")["required"])


def test_adversarial_authority_and_identity_mutations_fail():
    valid = _fixtures(VALID_DIR)
    payload = copy.deepcopy(valid["review_policy_resolution"])
    payload["target_identity"]["reviewed_head_sha"] = "abc123"
    _assert_invalid("review_policy_resolution", payload)
    payload = copy.deepcopy(valid["review_receipt_core"])
    payload["publication_status"] = "published"
    _assert_invalid("review_receipt_core", payload)
    payload = copy.deepcopy(valid["tool_execution_attestation"])
    payload["state_changed"] = True; payload["readback_status"] = "NOT_PERFORMED"; payload["readback_ref"] = None
    _assert_invalid("tool_execution_attestation", payload)


def test_aigov_schemas_remain_outside_successor_runtime_and_load_order():
    manifest = yaml.safe_load((ROOT / "protocol-manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["active_version"] == "v1.13.0"
    assert all("schemas/aigov/" not in path for path in manifest["load_order"])
    forbidden = ("schemas/aigov/v2.5.0", "repository_review_policy.schema.json", "review_receipt_core.schema.json")
    for path in (ROOT / "pr_inspector").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert all(token not in text for token in forbidden)


def test_historical_v1_11_1_schemas_remain_byte_identical():
    for relative, expected in HISTORICAL_SCHEMA_SHA256.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
