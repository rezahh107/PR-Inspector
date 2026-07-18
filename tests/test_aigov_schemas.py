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
    "repository_review_policy",
    "review_policy_resolution",
    "obligation_authority_binding",
    "classification_record",
    "scope_record",
    "review_execution",
    "review_receipt_core",
    "publication_attempt",
    "policy_transition_record",
    "merge_readiness_record",
    "post_merge_closure",
    "tool_execution_attestation",
)

ACTIVE_SCHEMA_SHA256 = {
    "protocols/v1.11.1/schemas/review-package.schema.json":
        "84172bc0f76fc4209e3618fa9847fc2430926ad80bfcf34f54305c8e7d80df47",
    "protocols/v1.11.1/schemas/decision-projection.schema.json":
        "05cca1bed416b6e711511515babfe8f1ee6868f079ac9231ca838566d9d6b3e7",
    "protocols/v1.11.1/schemas/owner-delivery-contract.schema.json":
        "60ad344469699a3988abbb7de22227faaa38f7be7d8269465d3885cb8b71b2ca",
    "protocols/v1.11.1/schemas/ci-identity.schema.json":
        "345cebcaa2ba54dc7c90440866437e46dea3b4f18da633566182ce1383d681c6",
    "protocols/v1.11.1/schemas/rereview-sequence.schema.json":
        "c6cfa2569843d9165baeca6e8077f97ccf057918066fd671f6bc68b5a0ba6a5c",
    "protocols/v1.11.1/schemas/governance-evidence.schema.json":
        "ea108eda28748321dcf928778f8bed384da832884961b151a463072cfc3ddb50",
}


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _schemas() -> dict[str, dict]:
    return {
        name: _load(SCHEMA_DIR / f"{name}.schema.json")
        for name in ("common", *EXPECTED_CONTRACTS)
    }


def _registry(schemas: dict[str, dict]) -> Registry:
    registry = Registry()
    for schema in schemas.values():
        registry = registry.with_resource(
            schema["$id"], Resource.from_contents(schema)
        )
    return registry


def _validator(contract: str) -> Draft202012Validator:
    schemas = _schemas()
    return Draft202012Validator(
        schemas[contract],
        registry=_registry(schemas),
        format_checker=FormatChecker(),
    )


def _fixture_set(directory: Path) -> dict[str, dict]:
    value = {path.stem: _load(path) for path in sorted(directory.glob("*.json"))}
    assert set(value) == set(EXPECTED_CONTRACTS)
    return value


def _valid_fixtures() -> dict[str, dict]:
    return _fixture_set(VALID_DIR)


def _invalid_fixtures() -> dict[str, dict]:
    return _fixture_set(INVALID_DIR)


def _refs(value: object):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "$ref":
                yield item
            yield from _refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from _refs(item)


def _assert_invalid(contract: str, payload: dict) -> None:
    errors = sorted(
        _validator(contract).iter_errors(payload),
        key=lambda item: (tuple(str(part) for part in item.path), item.message),
    )
    assert errors, contract


def test_expected_inactive_schema_inventory_and_index():
    expected_schema_files = {
        "common.schema.json",
        *(f"{name}.schema.json" for name in EXPECTED_CONTRACTS),
        "schema-index.json",
    }
    assert {path.name for path in SCHEMA_DIR.iterdir()} == expected_schema_files

    index = _load(SCHEMA_DIR / "schema-index.json")
    assert index["schema_index_version"] == "1.0"
    assert index["aigov_source_version"] == "2.5.0"
    assert index["activation_state"] == "inactive"
    assert index["authoritative_runtime"] is False
    assert index["active_protocol_integration"] is False
    assert tuple(item["contract_type"] for item in index["schemas"]) == EXPECTED_CONTRACTS


def test_all_schemas_are_valid_unique_versioned_and_locally_resolved():
    schemas = _schemas()
    schema_ids = []
    for name, schema in schemas.items():
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        schema_ids.append(schema["$id"])
        for ref in _refs(schema):
            assert "://" not in ref, f"{name}: remote or absolute $ref is forbidden: {ref}"

        if name != "common":
            assert schema["properties"]["contract_type"]["const"] == name
            assert schema["properties"]["contract_version"]["const"] == "1.0"
            assert "contract_type" in schema["required"]
            assert "contract_version" in schema["required"]
            assert schema["additionalProperties"] is False

    assert len(schema_ids) == len(set(schema_ids))

    registry = _registry(schemas)
    for contract in EXPECTED_CONTRACTS:
        Draft202012Validator(
            schemas[contract], registry=registry
        ).validate(_valid_fixtures()[contract])


def test_every_contract_has_passing_valid_and_failing_invalid_fixture():
    valid_fixtures = _valid_fixtures()
    invalid_fixtures = _invalid_fixtures()
    for contract in EXPECTED_CONTRACTS:
        _validator(contract).validate(valid_fixtures[contract])
        _assert_invalid(contract, invalid_fixtures[contract])


def test_future_profiles_are_exact_and_standard_is_distinct():
    common = _load(SCHEMA_DIR / "common.schema.json")
    assert common["$defs"]["inspection_profile"]["enum"] == [
        "minimal", "standard", "strict"
    ]
    assert common["$defs"]["evidence_profile"]["enum"] == [
        "minimal", "standard", "strict"
    ]
    assert common["$defs"]["execution_urgency"]["enum"] == [
        "routine", "elevated", "urgent"
    ]

    payload = _valid_fixtures()["review_policy_resolution"]
    payload["required_inspection_profile"] = "strict_alias"
    _assert_invalid("review_policy_resolution", payload)


def test_receipt_core_excludes_publication_metadata():
    payload = _valid_fixtures()["review_receipt_core"]
    forbidden = (
        "publication_attempt_id",
        "published_at",
        "publisher_identity",
        "comment_id",
        "comment_url",
        "retry_count",
        "publication_result",
        "readback_result",
    )
    for field in forbidden:
        mutated = copy.deepcopy(payload)
        mutated[field] = "forbidden"
        _assert_invalid("review_receipt_core", mutated)


def test_merge_readiness_is_structurally_separate_from_technical_status():
    schema = _load(SCHEMA_DIR / "merge_readiness_record.schema.json")
    assert "technical_status_reference" in schema["properties"]
    assert "technical_status" not in schema["properties"]
    assert "merge_readiness_result" in schema["properties"]

    payload = _valid_fixtures()["merge_readiness_record"]
    payload["technical_status"] = "GREEN_TECHNICALLY_READY"
    _assert_invalid("merge_readiness_record", payload)


def test_policy_transition_preserves_current_policy_evaluation_role():
    schema = _load(SCHEMA_DIR / "policy_transition_record.schema.json")
    for field in ("current_policy", "target_policy", "evaluation_policy"):
        assert field in schema["required"]
    assert schema["properties"]["evaluation_policy_role"]["const"] == "current_policy"

    payload = _valid_fixtures()["policy_transition_record"]
    payload["evaluation_policy_role"] = "target_policy"
    _assert_invalid("policy_transition_record", payload)


def test_post_merge_closure_supports_approved_outcome_classes():
    common = _load(SCHEMA_DIR / "common.schema.json")
    assert set(common["$defs"]["closure_outcome"]["enum"]) == {
        "content_equivalence_verified",
        "history_topology_verified",
        "history_topology_not_preserved_by_merge_method",
        "content_loss_detected",
        "insufficient_evidence",
        "blocked_status_drift",
    }


def test_tool_attestation_requires_structured_authenticated_identities():
    schema = _load(SCHEMA_DIR / "tool_execution_attestation.schema.json")
    for field in (
        "provider_identity",
        "workflow_identity",
        "run_identity",
        "job_identity",
        "step_identity",
        "command_or_validator_identity",
        "authentication_provenance",
    ):
        assert field in schema["required"]

    payload = _valid_fixtures()["tool_execution_attestation"]
    payload["workflow_identity"] = "caller-authored workflow description"
    _assert_invalid("tool_execution_attestation", payload)

    payload = _valid_fixtures()["tool_execution_attestation"]
    payload["pagination_completeness_reference"] = None
    _assert_invalid("tool_execution_attestation", payload)


def test_authority_progression_requires_structural_carriers():
    payload = _valid_fixtures()["obligation_authority_binding"]
    payload["current_enforcement_status"] = "ci_enforced"
    payload["ci_carrier_reference"] = None
    _assert_invalid("obligation_authority_binding", payload)

    payload = _valid_fixtures()["obligation_authority_binding"]
    payload["current_enforcement_status"] = "downstream_contract_enforced"
    payload["ci_carrier_reference"] = {
        "record_type": "ci_workflow",
        "record_id": "validate-aigov",
        "record_digest": "sha256:" + "a" * 64,
    }
    payload["downstream_consumer"] = None
    _assert_invalid("obligation_authority_binding", payload)


def test_adversarial_identity_evidence_and_authority_mutations_fail():
    payload = _valid_fixtures()["review_policy_resolution"]
    payload["target"]["head_sha"] = "abc123"
    _assert_invalid("review_policy_resolution", payload)

    payload = _valid_fixtures()["repository_review_policy"]
    del payload["repository"]["repository_id"]
    _assert_invalid("repository_review_policy", payload)

    payload = _valid_fixtures()["classification_record"]
    payload["source_evidence"] = ["prose is not evidence"]
    _assert_invalid("classification_record", payload)

    payload = _valid_fixtures()["repository_review_policy"]
    payload["undeclared_authority"] = {"claim": "active"}
    _assert_invalid("repository_review_policy", payload)

    payload = _valid_fixtures()["review_receipt_core"]
    payload["scope_digest"] = "sha256:" + "A" * 64
    _assert_invalid("review_receipt_core", payload)


def test_scope_and_execution_fail_closed_structurally():
    payload = _valid_fixtures()["scope_record"]
    payload["unresolved_scope"] = ["unknown generated output"]
    _assert_invalid("scope_record", payload)

    payload = _valid_fixtures()["review_execution"]
    payload["tool_execution_attestations"] = []
    _assert_invalid("review_execution", payload)

    payload = _valid_fixtures()["post_merge_closure"]
    del payload["merge_method_evidence"]
    _assert_invalid("post_merge_closure", payload)


def test_new_schemas_are_outside_active_runtime_and_load_order():
    manifest = yaml.safe_load(
        (ROOT / "protocol-manifest.yaml").read_text(encoding="utf-8")
    )
    assert manifest["active_version"] == "v1.11.1"
    assert all("schemas/aigov/" not in path for path in manifest["load_order"])

    forbidden = (
        "schemas/aigov/v2.5.0",
        "repository_review_policy.schema.json",
        "review_receipt_core.schema.json",
        "tool_execution_attestation.schema.json",
    )
    for path in (ROOT / "pr_inspector").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"active runtime references inactive schema: {path}: {token}"


def test_active_v1_11_1_schemas_remain_byte_identical_and_do_not_accept_standard():
    for relative, expected in ACTIVE_SCHEMA_SHA256.items():
        path = ROOT / relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected

    active_review_schema = _load(
        ROOT / "protocols/v1.11.1/schemas/review-package.schema.json"
    )
    assert active_review_schema["properties"]["inspection_profile"]["enum"] == [
        "minimal", "strict"
    ]
