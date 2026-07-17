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
from .prompt_semantics import validate_prompt_directory
from .semantic_v2 import validate_semantics
from .sequence_enforcement import VerifiedSequenceEnforcement

ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
EXTENSION_SCHEMA = ROOT / f"protocols/{CURRENT_VERSION}/schemas/review-package.schema.json"


def _schema_diagnostics(value: dict[str, Any], schema_path: Path) -> list[Diagnostic]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    candidate = value
    if CURRENT_VERSION == "v1.11.1" and schema_path.name == "review-package.schema.json" and value.get("protocol_version") == CURRENT_VERSION:
        candidate = copy.deepcopy(value)
        candidate["protocol_version"] = "v1.11.0"
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    diagnostics: list[Diagnostic] = []
    for error in validator.iter_errors(candidate):
        path = "/" + "/".join(str(item) for item in error.absolute_path)
        diagnostics.append(Diagnostic("PRI-SCHEMA-001", path, error.message))
    return diagnostics


def validate_package(
    pkg: dict[str, Any],
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> list[Diagnostic]:
    with evidence_scope(governance_evidence, sequence_enforcement):
        diagnostics = _schema_diagnostics(pkg, EXTENSION_SCHEMA)
        if diagnostics:
            return sorted(set(diagnostics))
        diagnostics.extend(validate_semantics(pkg))
        return sorted(set(diagnostics))


def validate_directory(
    path: Path,
    compare_rendered: bool = True,
    *,
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> list[Diagnostic]:
    directory = Path(path)
    with evidence_scope(governance_evidence, sequence_enforcement):
        diagnostics = _core.validate_directory(directory, compare_rendered=compare_rendered, package_validator=validate_package)
        diagnostics.extend(validate_prompt_directory(directory))
        return sorted(set(diagnostics))


load_json = _core.load_json
