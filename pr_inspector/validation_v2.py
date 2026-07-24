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
from .prompt_semantics import validate_prompt_semantics
from .semantic_v2 import validate_semantics
from .sequence_enforcement import VerifiedSequenceEnforcement

ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
EXTENSION_SCHEMA = ROOT / f"protocols/{CURRENT_VERSION}/schemas/review-package.schema.json"
V1_11_0_SCHEMA = ROOT / "protocols/v1.11.0/schemas/review-package.schema.json"


def _schema_diagnostics(value: dict[str, Any], schema_path: Path) -> list[Diagnostic]:
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
    """Validate the active successor as a strict completion of immutable v1.11.0."""

    with evidence_scope(governance_evidence, sequence_enforcement):
        diagnostics = _schema_diagnostics(pkg, EXTENSION_SCHEMA)
        if diagnostics:
            return sorted(set(diagnostics))
        if pkg.get("protocol_version") != "v1.12.0":
            historical_shape = copy.deepcopy(pkg)
            historical_shape["protocol_version"] = "v1.11.0"
            historical_shape.pop("authority_provenance", None)
            diagnostics.extend(_schema_diagnostics(historical_shape, V1_11_0_SCHEMA))
        if not diagnostics:
            diagnostics.extend(validate_semantics(pkg))
        return sorted(set(diagnostics))


def _prompt_semantic_diagnostics(path: Path) -> list[Diagnostic]:
    package_path = path / "review-package.json"
    projection_path = path / "DECISION_PROJECTION.json"
    if not package_path.is_file() or not projection_path.is_file():
        return []
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
        projection = json.loads(projection_path.read_text(encoding="utf-8"))
        prompt_path = path / "NEXT_ACTION_PROMPT.en.md"
        prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    if not isinstance(package, dict) or not isinstance(projection, dict):
        return []
    return validate_prompt_semantics(package, projection, prompt)


def validate_directory(
    path: Path,
    compare_rendered: bool = True,
    *,
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> list[Diagnostic]:
    with evidence_scope(governance_evidence, sequence_enforcement):
        diagnostics = _core.validate_directory(
            Path(path),
            compare_rendered=compare_rendered,
            package_validator=validate_package,
        )
        diagnostics.extend(_prompt_semantic_diagnostics(Path(path)))
        return sorted(set(diagnostics))


load_json = _core.load_json
