from __future__ import annotations

from fnmatch import fnmatchcase
from typing import Any, Mapping

from .aigov_errors import AIGOVDiagnostic, diagnostic
from .aigov_paths import normalize_repository_relative_path
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
    """Cover primitive strings stored directly in arrays."""

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


def _precise_path_overlap(left: str, right: str) -> bool:
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


def _validated_scope_paths(
    payload: dict[str, Any],
) -> tuple[list[AIGOVDiagnostic], dict[int, str], dict[int, str]]:
    out: list[AIGOVDiagnostic] = []
    normalized: dict[str, dict[int, str]] = {
        "included_paths": {},
        "excluded_paths": {},
    }
    for field in ("included_paths", "excluded_paths"):
        for index, value in enumerate(payload[field]):
            try:
                normalized[field][index] = normalize_repository_relative_path(value)
            except (TypeError, ValueError) as exc:
                out.append(
                    diagnostic(
                        "AIGOV-SEM-143",
                        payload["contract_type"],
                        f"/{field}/{index}",
                        "bounded repository-relative path",
                        str(exc),
                    )
                )
    return out, normalized["included_paths"], normalized["excluded_paths"]


def _scope_record(
    payload: dict[str, Any],
    context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    # Retain base scope identity and digest semantics, but replace both legacy path
    # checks with one deterministic repository-relative path validator.
    out = [
        item
        for item in _scope_record_base(payload, context)
        if item.code not in {"AIGOV-SEM-143", "AIGOV-SEM-144"}
    ]
    path_diagnostics, included, excluded = _validated_scope_paths(payload)
    out.extend(path_diagnostics)
    for left_index, left in included.items():
        for right_index, right in excluded.items():
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
