from __future__ import annotations

from fnmatch import fnmatchcase
from typing import Any, Mapping

from .aigov_errors import AIGOVDiagnostic, diagnostic
from .aigov_validation_support import (
    AIGOVValidationContext,
    _EXECUTABLE_EXPRESSION,
    _global_diagnostics,
    _pointer,
)
from .aigov_validators_policy import (
    _classification_record,
    _obligation_authority_binding,
    _repository_review_policy,
    _review_policy_resolution,
    _scope_record as _scope_record_base,
)
from .aigov_validators_review import (
    _publication_attempt,
    _review_execution,
    _review_receipt_core,
)
from .aigov_validators_lifecycle import (
    _merge_readiness_record,
    _policy_transition_record,
    _post_merge_closure,
)
from .aigov_validators_tool import _tool_execution_attestation


def _list_string_diagnostics(
    contract_type: str,
    value: object,
    path: str = "/",
) -> list[AIGOVDiagnostic]:
    """Cover primitive strings stored directly in arrays.

    `_global_diagnostics` already handles mapping values, including mappings nested
    in arrays. This helper closes the direct-list-element gap without duplicating
    diagnostics for ordinary object fields.
    """

    out: list[AIGOVDiagnostic] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            out.extend(
                _list_string_diagnostics(
                    contract_type,
                    item,
                    _pointer(path, key),
                )
            )
    elif isinstance(value, list):
        for index, item in enumerate(value):
            item_path = _pointer(path, index)
            if isinstance(item, str) and _EXECUTABLE_EXPRESSION.search(item):
                out.append(
                    diagnostic(
                        "AIGOV-SEM-006",
                        contract_type,
                        item_path,
                        "non-executable authority data",
                        "embedded executable expression or command marker is forbidden",
                    )
                )
            else:
                out.extend(
                    _list_string_diagnostics(contract_type, item, item_path)
                )
    return out


def _normalized_path(value: str) -> str:
    while value.startswith("./"):
        value = value[2:]
    return value.replace("\\", "/")


def _precise_path_overlap(left: str, right: str) -> bool:
    left = _normalized_path(left)
    right = _normalized_path(right)
    if left == right:
        return True
    if left.endswith("/**"):
        directory = left[:-3]
        prefix = left[:-2]
        if right == directory or right.startswith(prefix):
            return True
    if right.endswith("/**"):
        directory = right[:-3]
        prefix = right[:-2]
        if left == directory or left.startswith(prefix):
            return True
    return fnmatchcase(left, right) or fnmatchcase(right, left)


def _scope_record(
    payload: dict[str, Any],
    context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    # Retain all base scope semantics except its broad wildcard-prefix overlap
    # diagnostic, then re-apply overlap detection with directory-boundary rules.
    out = [
        item
        for item in _scope_record_base(payload, context)
        if item.code != "AIGOV-SEM-144"
    ]
    for left_index, left in enumerate(payload["included_paths"]):
        for right_index, right in enumerate(payload["excluded_paths"]):
            if _precise_path_overlap(left, right):
                out.append(
                    diagnostic(
                        "AIGOV-SEM-144",
                        payload["contract_type"],
                        f"/included_paths/{left_index}",
                        "non-contradictory scope",
                        f"included path overlaps excluded path at index {right_index}",
                        evidence_path=f"/excluded_paths/{right_index}",
                    )
                )
    return out


def _semantic_diagnostics(
    contract_type: str,
    payload: dict[str, Any],
    context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    diagnostics: list[AIGOVDiagnostic] = []
    diagnostics.extend(_global_diagnostics(contract_type, payload, context))
    diagnostics.extend(_list_string_diagnostics(contract_type, payload))
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
