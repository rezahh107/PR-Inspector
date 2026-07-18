from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .aigov_errors import AIGOVDiagnostic, diagnostic


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "aigov" / "v2.5.0"

CONTRACT_TYPES = (
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

_CANONICAL_REGISTRY_CAPABILITY = object()


@dataclass(frozen=True, slots=True)
class _CanonicalRegistryBinding:
    schema_directory: str
    schema_id: str
    schema_sha256: str
    capability: object


def _json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot load local AIGOV schema {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"local AIGOV schema {path.name} must be a JSON object")
    return value


def _refs(value: object):
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "$ref":
                yield item
            yield from _refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from _refs(item)


class LocalAIGOVSchemaRegistry:
    """Pinned local-only JSON Schema registry for inactive AIGOV contracts.

    Public instances are diagnostic-only. Only a private fresh canonical instance
    carries the capability required by the model-minting path.
    """

    def __init__(self, schema_dir: Path = SCHEMA_DIR):
        self._initialize(schema_dir)
        self._canonical_capability: object | None = None

    @classmethod
    def _canonical_instance(cls) -> LocalAIGOVSchemaRegistry:
        value = cls.__new__(cls)
        value._initialize(SCHEMA_DIR)
        value._canonical_capability = _CANONICAL_REGISTRY_CAPABILITY
        return value

    def _initialize(self, schema_dir: Path) -> None:
        try:
            resolved_schema_dir = schema_dir.resolve(strict=True)
        except OSError as exc:
            raise RuntimeError(f"cannot resolve local AIGOV schema directory: {exc}") from exc
        if not resolved_schema_dir.is_dir():
            raise RuntimeError("local AIGOV schema directory is not a directory")
        self._schema_dir = resolved_schema_dir
        self._schemas: dict[str, dict[str, Any]] = {}
        self._schema_sha256: dict[str, str] = {}
        self._validators: dict[str, Draft202012Validator] = {}
        self._load()

    def _local_regular_file(self, filename: str) -> Path:
        candidate = self._schema_dir / filename
        if candidate.is_symlink():
            raise RuntimeError(f"AIGOV schema file is symlinked: {filename}")
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise RuntimeError(f"cannot resolve local AIGOV schema file {filename}: {exc}") from exc
        try:
            resolved.relative_to(self._schema_dir)
        except ValueError as exc:
            raise RuntimeError(
                f"AIGOV schema file escaped pinned directory: {filename}"
            ) from exc
        if resolved.parent != self._schema_dir:
            raise RuntimeError(
                f"AIGOV schema file is not an exact child of pinned directory: {filename}"
            )
        if not resolved.is_file():
            raise RuntimeError(f"AIGOV schema path is not a regular file: {filename}")
        return resolved

    def _load(self) -> None:
        index_path = self._local_regular_file("schema-index.json")
        index = _json_object(index_path)
        if index.get("activation_state") != "inactive":
            raise RuntimeError("AIGOV schema index must remain inactive")
        if index.get("authoritative_runtime") is not False:
            raise RuntimeError("AIGOV schema index must remain non-authoritative")
        if index.get("active_protocol_integration") is not False:
            raise RuntimeError("AIGOV schema index must remain outside active protocol")
        declared = tuple(
            item.get("contract_type")
            for item in index.get("schemas", [])
            if isinstance(item, Mapping)
        )
        if declared != CONTRACT_TYPES:
            raise RuntimeError("AIGOV schema index contract inventory is not exact")

        names = ("common", *CONTRACT_TYPES)
        for name in names:
            path = self._local_regular_file(f"{name}.schema.json")
            raw = path.read_bytes()
            schema = _json_object(path)
            Draft202012Validator.check_schema(schema)
            schema_id = schema.get("$id")
            if not isinstance(schema_id, str) or not schema_id:
                raise RuntimeError(f"AIGOV schema {name} has no stable $id")
            for ref in _refs(schema):
                if not isinstance(ref, str):
                    raise RuntimeError(f"AIGOV schema {name} has a non-string $ref")
                local_part = ref.split("#", 1)[0]
                if (
                    "://" in ref
                    or ref.startswith(("/", "//"))
                    or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", ref)
                    or ".." in Path(local_part).parts
                ):
                    raise RuntimeError(
                        f"AIGOV schema {name} attempted non-local resolution: {ref}"
                    )
            self._schemas[name] = schema
            self._schema_sha256[name] = hashlib.sha256(raw).hexdigest()

        schema_ids = [schema["$id"] for schema in self._schemas.values()]
        if len(schema_ids) != len(set(schema_ids)):
            raise RuntimeError("AIGOV schema IDs are not unique")

        resources = Registry()
        for schema in self._schemas.values():
            resources = resources.with_resource(
                schema["$id"], Resource.from_contents(schema)
            )
        for contract in CONTRACT_TYPES:
            self._validators[contract] = Draft202012Validator(
                self._schemas[contract],
                registry=resources,
                format_checker=FormatChecker(),
            )

    def _canonical_mint_binding(self, contract_type: str) -> _CanonicalRegistryBinding:
        try:
            canonical_directory = SCHEMA_DIR.resolve(strict=True)
        except OSError as exc:
            raise RuntimeError(f"cannot resolve canonical AIGOV schema directory: {exc}") from exc
        if (
            self._canonical_capability is not _CANONICAL_REGISTRY_CAPABILITY
            or self._schema_dir != canonical_directory
        ):
            raise RuntimeError(
                "AIGOV model minting requires the canonical pinned schema registry"
            )
        if contract_type not in CONTRACT_TYPES:
            raise RuntimeError("unknown AIGOV contract cannot be canonically bound")

        schema_path = self._local_regular_file(f"{contract_type}.schema.json")
        raw = schema_path.read_bytes()
        current_digest = hashlib.sha256(raw).hexdigest()
        current_schema = _json_object(schema_path)
        current_id = current_schema.get("$id")
        if current_id != self.schema_id(contract_type):
            raise RuntimeError("canonical AIGOV schema ID changed after registry load")
        if current_digest != self.schema_sha256(contract_type):
            raise RuntimeError("canonical AIGOV schema digest changed after registry load")
        return _CanonicalRegistryBinding(
            schema_directory=str(canonical_directory),
            schema_id=str(current_id),
            schema_sha256=current_digest,
            capability=_CANONICAL_REGISTRY_CAPABILITY,
        )

    @property
    def contract_types(self) -> tuple[str, ...]:
        return CONTRACT_TYPES

    @property
    def schema_dir(self) -> Path:
        return self._schema_dir

    def schema(self, contract_type: str) -> Mapping[str, Any]:
        return MappingProxyType(copy.deepcopy(self._schemas[contract_type]))

    def schema_id(self, contract_type: str) -> str:
        return str(self._schemas[contract_type]["$id"])

    def schema_sha256(self, contract_type: str) -> str:
        return self._schema_sha256[contract_type]

    def required_fields(self, contract_type: str) -> tuple[str, ...]:
        required = self._schemas[contract_type].get("required", [])
        return tuple(str(item) for item in required)

    def validate(
        self,
        contract_type: str,
        payload: Mapping[str, Any],
    ) -> tuple[AIGOVDiagnostic, ...]:
        if contract_type not in self._validators:
            return (
                diagnostic(
                    "AIGOV-MODEL-001",
                    contract_type,
                    "/contract_type",
                    "known contract selection",
                    "unknown AIGOV contract type",
                ),
            )
        errors = sorted(
            self._validators[contract_type].iter_errors(payload),
            key=lambda item: (
                tuple(str(part) for part in item.absolute_path),
                item.message,
            ),
        )
        return tuple(
            diagnostic(
                "AIGOV-MODEL-003",
                contract_type,
                _json_pointer(error.absolute_path),
                "JSON Schema validation",
                error.message,
                evidence_path=self.schema_id(contract_type),
            )
            for error in errors
        )


def _json_pointer(parts: object) -> str:
    encoded: list[str] = []
    for part in parts:
        text = str(part).replace("~", "~0").replace("/", "~1")
        encoded.append(text)
    return "/" + "/".join(encoded) if encoded else "/"


_DEFAULT_REGISTRY: LocalAIGOVSchemaRegistry | None = None


def local_aigov_schema_registry() -> LocalAIGOVSchemaRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = LocalAIGOVSchemaRegistry()
    return _DEFAULT_REGISTRY


def _canonical_mint_registry() -> LocalAIGOVSchemaRegistry:
    return LocalAIGOVSchemaRegistry._canonical_instance()
