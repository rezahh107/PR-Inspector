from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from . import validation_v2_core as _core
from .diagnostics import Diagnostic
from .semantic_v2 import validate_semantics

ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
EXTENSION_SCHEMA = ROOT / f"protocols/{CURRENT_VERSION}/schemas/review-package.schema.json"
BASE_SCHEMA = ROOT / "protocols/v1.10.0/schemas/review-package.schema.json"


def _schema_diagnostics(
    value: dict[str, Any], schema_path: Path
) -> list[Diagnostic]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    diagnostics: list[Diagnostic] = []
    for error in validator.iter_errors(value):
        path = "/" + "/".join(str(item) for item in error.absolute_path)
        diagnostics.append(Diagnostic("PRI-SCHEMA-001", path, error.message))
    return diagnostics


def validate_package(pkg: dict[str, Any]) -> list[Diagnostic]:
    """Validate v1.10.1 as a strict extension of immutable v1.10.0."""

    diagnostics = _schema_diagnostics(pkg, EXTENSION_SCHEMA)
    if diagnostics:
        return sorted(set(diagnostics))

    base_value = copy.deepcopy(pkg)
    base_value.pop("security_profile", None)
    base_value["protocol_version"] = "v1.10.0"
    diagnostics.extend(_schema_diagnostics(base_value, BASE_SCHEMA))
    if not diagnostics:
        diagnostics.extend(validate_semantics(pkg))
    return sorted(set(diagnostics))


_core.validate_package = validate_package

load_json = _core.load_json
validate_directory = _core.validate_directory
