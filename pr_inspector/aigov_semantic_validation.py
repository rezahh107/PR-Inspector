from __future__ import annotations

from typing import Any

from .aigov_errors import AIGOVDiagnostic
from .aigov_validation_support import AIGOVValidationContext, _global_diagnostics
from .aigov_validators_policy import _classification_record, _obligation_authority_binding, _repository_review_policy, _review_policy_resolution, _scope_record
from .aigov_validators_review import _publication_attempt, _review_execution, _review_receipt_core
from .aigov_validators_lifecycle import _merge_readiness_record, _policy_transition_record, _post_merge_closure
from .aigov_validators_tool import _tool_execution_attestation

def _semantic_diagnostics(
    contract_type: str,
    payload: dict[str, Any],
    context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    diagnostics: list[AIGOVDiagnostic] = []
    diagnostics.extend(_global_diagnostics(contract_type, payload, context))
    validator = _CONTRACT_VALIDATORS[contract_type]
    diagnostics.extend(validator(payload, context))
    return sorted(
        diagnostics,
        key=lambda item: (
            item.code,
            item.contract_type,
            item.path,
            item.invariant,
            item.reason,
            item.evidence_path,
        ),
    )

_CONTRACT_VALIDATORS = {
    "repository_review_policy": _repository_review_policy,
    "review_policy_resolution": _review_policy_resolution,
    "obligation_authority_binding": _obligation_authority_binding,
    "classification_record": _classification_record,
    "scope_record": _scope_record,
    "review_execution": _review_execution,
    "review_receipt_core": _review_receipt_core,
    "publication_attempt": _publication_attempt,
    "policy_transition_record": _policy_transition_record,
    "merge_readiness_record": _merge_readiness_record,
    "post_merge_closure": _post_merge_closure,
    "tool_execution_attestation": _tool_execution_attestation,
}
