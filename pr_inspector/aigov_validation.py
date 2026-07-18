from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from .aigov_errors import AIGOVDiagnostic, AIGOVValidationError, diagnostic
from .aigov_models import (
    AIGOVContract,
    AIGOVValidationProvenance,
    _MODEL_FACTORY_TOKEN,
    _mint_validated_contract,
)
from .aigov_schema_registry import (
    CONTRACT_TYPES,
    LocalAIGOVSchemaRegistry,
    _canonical_mint_registry,
    local_aigov_schema_registry,
)
from .aigov_semantic_validation import _semantic_diagnostics
from .aigov_validation_support import (
    AIGOVValidationContext,
    SEMANTIC_VALIDATOR_VERSION,
    _pointer,
    canonical_scope_digest,
)


class _BoundaryError(ValueError):
    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(reason)


class _DuplicateJSONKey(ValueError):
    pass


def _plain_json(
    value: object,
    *,
    path: str = "/",
    depth: int = 0,
    nodes: list[int] | None = None,
) -> Any:
    if nodes is None:
        nodes = [0]
    nodes[0] += 1
    if nodes[0] > 20000:
        raise _BoundaryError(path, "payload exceeds the 20000-node safety bound")
    if depth > 32:
        raise _BoundaryError(path, "payload exceeds the 32-level nesting bound")
    if value is None or isinstance(value, (str, bool, int)):
        if isinstance(value, str) and len(value) > 65536:
            raise _BoundaryError(path, "string exceeds the 65536-character safety bound")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise _BoundaryError(path, "non-finite numbers are not valid JSON data")
        return value
    if isinstance(value, Mapping):
        if len(value) > 2048:
            raise _BoundaryError(path, "mapping exceeds the 2048-entry safety bound")
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise _BoundaryError(path, "JSON object keys must be strings")
            result[key] = _plain_json(
                item,
                path=_pointer(path, key),
                depth=depth + 1,
                nodes=nodes,
            )
        return result
    if isinstance(value, (list, tuple)):
        if len(value) > 2048:
            raise _BoundaryError(path, "array exceeds the 2048-item safety bound")
        return [
            _plain_json(
                item,
                path=_pointer(path, index),
                depth=depth + 1,
                nodes=nodes,
            )
            for index, item in enumerate(value)
        ]
    raise _BoundaryError(path, f"unsupported JSON value type: {type(value).__name__}")


def _duplicate_key_object(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONKey(key)
        result[key] = value
    return result


def _canonical_registry_for_mint(
    registry: LocalAIGOVSchemaRegistry | object | None,
) -> LocalAIGOVSchemaRegistry:
    public_canonical = local_aigov_schema_registry()
    if registry is not None and registry is not public_canonical:
        raise TypeError(
            "AIGOV model minting accepts only the canonical pinned schema registry"
        )
    return _canonical_mint_registry()


def load_aigov_json(
    contract_type: str,
    raw_json: str | bytes,
    *,
    context: AIGOVValidationContext | None = None,
    registry: LocalAIGOVSchemaRegistry | object | None = None,
) -> AIGOVContract:
    if isinstance(raw_json, bytes):
        if len(raw_json) > 2_000_000:
            raise AIGOVValidationError(
                (
                    diagnostic(
                        "AIGOV-MODEL-002",
                        contract_type,
                        "/",
                        "bounded JSON input",
                        "raw JSON exceeds the 2 MB safety bound",
                    ),
                )
            )
        try:
            text = raw_json.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AIGOVValidationError(
                (
                    diagnostic(
                        "AIGOV-MODEL-002",
                        contract_type,
                        "/",
                        "UTF-8 JSON input",
                        str(exc),
                    ),
                )
            ) from exc
    elif isinstance(raw_json, str):
        text = raw_json
        if len(text.encode("utf-8")) > 2_000_000:
            raise AIGOVValidationError(
                (
                    diagnostic(
                        "AIGOV-MODEL-002",
                        contract_type,
                        "/",
                        "bounded JSON input",
                        "raw JSON exceeds the 2 MB safety bound",
                    ),
                )
            )
    else:
        raise AIGOVValidationError(
            (
                diagnostic(
                    "AIGOV-MODEL-002",
                    contract_type,
                    "/",
                    "JSON input type",
                    "raw JSON must be str or bytes",
                ),
            )
        )
    try:
        value = json.loads(text, object_pairs_hook=_duplicate_key_object)
    except _DuplicateJSONKey as exc:
        raise AIGOVValidationError(
            (
                diagnostic(
                    "AIGOV-MODEL-004",
                    contract_type,
                    "/",
                    "unambiguous JSON object",
                    f"duplicate JSON key: {exc.args[0]}",
                ),
            )
        ) from exc
    except json.JSONDecodeError as exc:
        raise AIGOVValidationError(
            (
                diagnostic(
                    "AIGOV-MODEL-002",
                    contract_type,
                    "/",
                    "valid JSON input",
                    f"{exc.msg} at line {exc.lineno} column {exc.colno}",
                ),
            )
        ) from exc
    if not isinstance(value, dict):
        raise AIGOVValidationError(
            (
                diagnostic(
                    "AIGOV-MODEL-002",
                    contract_type,
                    "/",
                    "contract object boundary",
                    "AIGOV contract JSON must contain an object",
                ),
            )
        )
    return load_aigov_contract(
        contract_type,
        value,
        context=context,
        registry=registry,
    )


def validate_aigov_contract(
    contract_type: str,
    payload: Mapping[str, object],
    *,
    context: AIGOVValidationContext | None = None,
    registry: LocalAIGOVSchemaRegistry | object | None = None,
) -> tuple[AIGOVDiagnostic, ...]:
    if contract_type not in CONTRACT_TYPES:
        return (
            diagnostic(
                "AIGOV-MODEL-001",
                contract_type,
                "/contract_type",
                "exact contract selection",
                "unknown AIGOV contract type",
            ),
        )
    if not isinstance(payload, Mapping):
        return (
            diagnostic(
                "AIGOV-MODEL-002",
                contract_type,
                "/",
                "contract object boundary",
                "payload must be a mapping",
            ),
        )
    try:
        plain = _plain_json(payload)
    except _BoundaryError as exc:
        return (
            diagnostic(
                "AIGOV-MODEL-002",
                contract_type,
                exc.path,
                "hostile input boundary",
                exc.reason,
            ),
        )
    schema_registry = registry or local_aigov_schema_registry()
    schema_diagnostics = schema_registry.validate(contract_type, plain)  # type: ignore[attr-defined]
    if schema_diagnostics:
        return tuple(schema_diagnostics)
    return tuple(_semantic_diagnostics(contract_type, plain, context))


def load_aigov_contract(
    contract_type: str,
    payload: Mapping[str, object],
    *,
    context: AIGOVValidationContext | None = None,
    registry: LocalAIGOVSchemaRegistry | object | None = None,
) -> AIGOVContract:
    schema_registry = _canonical_registry_for_mint(registry)
    diagnostics = validate_aigov_contract(
        contract_type,
        payload,
        context=context,
        registry=schema_registry,
    )
    if diagnostics:
        raise AIGOVValidationError(diagnostics)
    plain = _plain_json(payload)
    binding = schema_registry._canonical_mint_binding(contract_type)
    canonical = json.dumps(
        plain,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    provenance = AIGOVValidationProvenance(
        contract_type=contract_type,
        contract_version=str(plain["contract_version"]),
        schema_id=binding.schema_id,
        schema_sha256=binding.schema_sha256,
        payload_sha256=hashlib.sha256(canonical).hexdigest(),
        semantic_validator_version=SEMANTIC_VALIDATOR_VERSION,
    )
    return _mint_validated_contract(
        contract_type=contract_type,
        payload=plain,
        provenance=provenance,
        factory_token=_MODEL_FACTORY_TOKEN,
    )


__all__ = [
    "AIGOVValidationContext",
    "canonical_scope_digest",
    "load_aigov_contract",
    "load_aigov_json",
    "validate_aigov_contract",
]
