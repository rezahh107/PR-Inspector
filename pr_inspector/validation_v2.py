from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from . import validation_v2_core as _core
from .diagnostics import Diagnostic
from .evidence_context import evidence_scope
from .governance import VerifiedGovernanceEvidence
from .semantic_v2 import validate_semantics
from .sequence_enforcement import VerifiedSequenceEnforcement

ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
EXTENSION_SCHEMA = ROOT / f"protocols/{CURRENT_VERSION}/schemas/review-package.schema.json"
BASE_SCHEMA = ROOT / "protocols/v1.10.1/schemas/review-package.schema.json"


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


def validate_package(
    pkg: dict[str, Any],
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> list[Diagnostic]:
    """Validate the active protocol package schema and semantic gates."""

    with evidence_scope(governance_evidence, sequence_enforcement):
        diagnostics = _schema_diagnostics(pkg, EXTENSION_SCHEMA)
        if diagnostics:
            return sorted(set(diagnostics))

        if CURRENT_VERSION in {"v1.10.1", "v1.10.2"}:
            base_value = copy.deepcopy(pkg)
            base_value["protocol_version"] = "v1.10.1"
            diagnostics.extend(_schema_diagnostics(base_value, BASE_SCHEMA))
        if not diagnostics:
            diagnostics.extend(validate_semantics(pkg))
        return sorted(set(diagnostics))


def validate_directory(
    path: Path,
    compare_rendered: bool = True,
    *,
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> list[Diagnostic]:
    with evidence_scope(governance_evidence, sequence_enforcement):
        return _core.validate_directory(
            Path(path),
            compare_rendered=compare_rendered,
            package_validator=validate_package,
        )



load_json = _core.load_json
