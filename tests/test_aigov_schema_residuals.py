from __future__ import annotations
import copy
import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / 'schemas/aigov/v2.5.0'
VALID_DIR = ROOT / 'tests/fixtures/aigov/v2.5.0/schema_valid'
INVALID_DIR = ROOT / 'tests/fixtures/aigov/v2.5.0/schema_invalid'
CONTRACTS = ('publication_attempt', 'policy_transition_record', 'classification_record', 'tool_execution_attestation')

def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    assert isinstance(value, dict)
    return value

def _schemas() -> dict[str, dict]:
    return {name: _load(SCHEMA_DIR / f'{name}.schema.json') for name in ('common', *CONTRACTS)}

def _validator(contract: str) -> Draft202012Validator:
    schemas = _schemas()
    registry = Registry()
    for schema in schemas.values():
        registry = registry.with_resource(schema['$id'], Resource.from_contents(schema))
    return Draft202012Validator(schemas[contract], registry=registry, format_checker=FormatChecker())

def _fixture(kind: str, contract: str) -> dict:
    return _load(ROOT / 'tests/fixtures/aigov/v2.5.0' / kind / f'{contract}.json')

def _valid(contract: str) -> dict:
    return _fixture('schema_valid', contract)

def _invalid(contract: str) -> dict:
    return _fixture('schema_invalid', contract)

def _assert_valid(contract: str, payload: dict) -> None:
    _validator(contract).validate(payload)

def _assert_invalid(contract: str, payload: dict) -> None:
    errors = list(_validator(contract).iter_errors(payload))
    assert errors, contract

def _record_reference(record_id: str) -> dict:
    return {'record_type': 'review_receipt_core', 'record_id': record_id, 'record_digest': 'sha256:' + 'f' * 64}

def _tool_authorizes_consequential_action(payload: dict) -> bool:
    parameter_statuses = {item.get('binding_status') for item in payload.get('parameter_bindings', [])}
    claim_statuses = {item.get('binding_status') for item in payload.get('final_claim_bindings', [])}
    invocation = payload.get('invocation_record', {})
    verified_parameters = parameter_statuses <= {'VERIFIED_SOURCE_BOUND', 'VERIFIED_TRANSFORMATION_BOUND'}
    verified_claims = claim_statuses <= {'VERIFIED_RESULT_BOUND', 'VERIFIED_READBACK_BOUND'}
    return bool(parameter_statuses) and verified_parameters and (invocation.get('claimed_execution') is True) and (invocation.get('execution_status') == 'success') and (payload.get('readback_status') in {'VERIFIED', 'READBACK_NOT_REQUIRED'}) and verified_claims

def _tool_supports_successful_completion(payload: dict) -> bool:
    return _tool_authorizes_consequential_action(payload) and payload.get('execution_result', {}).get('result_identity') is not None and all((item.get('binding_status') in {'VERIFIED_RESULT_BOUND', 'VERIFIED_READBACK_BOUND'} for item in payload.get('final_claim_bindings', [])))

def test_changed_schemas_and_baseline_fixtures_are_valid() -> None:
    for schema in _schemas().values():
        Draft202012Validator.check_schema(schema)
    for contract in CONTRACTS:
        _assert_valid(contract, _valid(contract))
        _assert_invalid(contract, _invalid(contract))

def test_publication_and_validation_status_domains_are_separate() -> None:
    schema = _load(SCHEMA_DIR / 'publication_attempt.schema.json')
    assert schema['properties']['publication_status']['$ref'].endswith('/receipt_publication_status')
    assert schema['properties']['receipt_validation_status']['enum'] == ['not_checked', 'current_valid', 'stale', 'invalid', 'conflicting']
    payload = _valid('publication_attempt')
    payload['publication_status'] = 'RECEIPT_CONFLICT'
    _assert_invalid('publication_attempt', payload)
    for status in ('not_required', 'not_attempted', 'publishing', 'published_verified', 'publication_failed'):
        payload = _valid('publication_attempt')
        payload['publication_status'] = status
        if status == 'publication_failed':
            payload['failure_reason'] = 'platform write failed'
        _assert_valid('publication_attempt', payload)
    payload = _valid('publication_attempt')
    payload['receipt_validation_status'] = 'conflicting'
    payload['conflicting_receipt_ref'] = None
    _assert_invalid('publication_attempt', payload)
    payload['conflicting_receipt_ref'] = _record_reference('conflict-1')
    _assert_valid('publication_attempt', payload)
    assert payload['publication_status'] == 'published_verified'
    payload = _valid('publication_attempt')
    payload['publication_status'] = 'conflicting'
    _assert_invalid('publication_attempt', payload)
    payload = _valid('publication_attempt')
    payload['receipt_validation_status'] = 'publication_failed'
    _assert_invalid('publication_attempt', payload)

def _policy_transition_identity_errors(payload: dict) -> list[str]:
    errors = []
    if payload.get('evaluation_policy_role') != 'current_policy':
        errors.append('evaluation_policy_role must be current_policy')
    if payload.get('evaluation_policy_identity') != payload.get('current_policy_identity'):
        errors.append('evaluation_policy_identity must equal current_policy_identity')
    return errors

def test_policy_transition_identity_is_semantically_bound_to_current_policy() -> None:
    schema = _load(SCHEMA_DIR / 'policy_transition_record.schema.json')
    assert {'current_policy_identity', 'target_policy_identity', 'evaluation_policy_identity', 'evaluation_policy_role'}.issubset(schema['required'])
    assert schema['properties']['evaluation_policy_role']['const'] == 'current_policy'
    payload = _valid('policy_transition_record')
    _assert_valid('policy_transition_record', payload)
    assert _policy_transition_identity_errors(payload) == []
    mutated = copy.deepcopy(payload)
    mutated['evaluation_policy_identity'] = mutated['target_policy_identity']
    _assert_valid('policy_transition_record', mutated)
    assert _policy_transition_identity_errors(mutated) == ['evaluation_policy_identity must equal current_policy_identity']

@pytest.mark.parametrize('status', ['INVALID_SOURCE_DETACHED', 'INVALID_UNDECLARED_TRANSFORMATION'])
def test_tool_parameter_failure_states_are_representable_but_not_authorizing(status: str) -> None:
    payload = _valid('tool_execution_attestation')
    payload['parameter_bindings'][0]['binding_status'] = status
    payload['state_changed'] = False
    payload['readback_status'] = 'NOT_PERFORMED'
    payload['readback_ref'] = None
    payload['final_claim_bindings'] = [{'claim_id': 'claim-detached', 'result_field_refs': ['comment_id'], 'binding_status': 'INVALID_RESULT_DETACHED'}]
    _assert_valid('tool_execution_attestation', payload)
    assert _tool_authorizes_consequential_action(payload) is False
    assert _tool_supports_successful_completion(payload) is False
    payload['final_claim_bindings'][0]['binding_status'] = 'VERIFIED_RESULT_BOUND'
    _assert_invalid('tool_execution_attestation', payload)

@pytest.mark.parametrize('readback_status', ['FAILED', 'NOT_PERFORMED'])
def test_tool_readback_failures_are_representable_without_success_claims(readback_status: str) -> None:
    payload = _valid('tool_execution_attestation')
    payload['state_changed'] = False
    payload['readback_status'] = readback_status
    payload['readback_ref'] = None
    payload['final_claim_bindings'] = [{'claim_id': 'claim-detached', 'result_field_refs': ['comment_id'], 'binding_status': 'INVALID_RESULT_DETACHED'}]
    _assert_valid('tool_execution_attestation', payload)
    assert _tool_authorizes_consequential_action(payload) is False
    assert _tool_supports_successful_completion(payload) is False

def test_tool_execution_and_readback_invariants_remain_fail_closed() -> None:
    payload = _valid('tool_execution_attestation')
    payload['invocation_record']['invocation_id'] = None
    _assert_invalid('tool_execution_attestation', payload)
    payload = _valid('tool_execution_attestation')
    payload['state_changed'] = True
    payload['readback_status'] = 'NOT_PERFORMED'
    payload['readback_ref'] = None
    _assert_invalid('tool_execution_attestation', payload)
    payload = _valid('tool_execution_attestation')
    payload['state_changed'] = False
    payload['readback_status'] = 'READBACK_NOT_REQUIRED'
    payload['readback_ref'] = None
    payload['readback_not_required_authority_ref'] = None
    _assert_invalid('tool_execution_attestation', payload)

def test_terminal_l0_is_rejected_but_general_change_class_preserved() -> None:
    common = _load(SCHEMA_DIR / 'common.schema.json')
    classification = _load(SCHEMA_DIR / 'classification_record.schema.json')
    assert common['$defs']['change_class']['enum'] == ['L0', 'L1', 'L2', 'L3', 'L4']
    assert classification['$defs']['classification_terminal_class']['enum'] == ['L1', 'L2', 'L3', 'L4']
    payload = _valid('classification_record')
    payload['final_class'] = 'L0'
    _assert_invalid('classification_record', payload)
    payload = _valid('classification_record')
    payload['classification_resolution_status'] = 'blocked_insufficient_evidence'
    payload['final_class'] = None
    payload['classification_outcome'] = 'blocked_insufficient_evidence'
    payload['evidence_sufficiency'] = 'insufficient'
    payload['recovery_condition'] = 'Collect exact boundary evidence.'
    _assert_valid('classification_record', payload)
    payload['recovery_condition'] = None
    _assert_invalid('classification_record', payload)
