from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator, FormatChecker

from .derived_outputs import PROMPT_NAME, build_review_artifacts
from .diagnostics import Diagnostic
from .semantic_v2 import validate_semantics

ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
SCHEMA = ROOT / f"protocols/{CURRENT_VERSION}/schemas/review-package.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_package(pkg: dict[str, Any]) -> list[Diagnostic]:
    schema = load_json(SCHEMA)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    diagnostics = []
    for error in validator.iter_errors(pkg):
        path = "/" + "/".join(str(item) for item in error.absolute_path)
        diagnostics.append(Diagnostic("PRI-SCHEMA-001", path, error.message))
    if not diagnostics:
        diagnostics.extend(validate_semantics(pkg))
    return sorted(set(diagnostics))


def validate_directory(path: Path, compare_rendered: bool = True) -> list[Diagnostic]:
    package_path = path / "review-package.json"
    if not package_path.is_file():
        return [Diagnostic("PRI-INPUT-001", "/review-package.json", "canonical package is missing")]
    try:
        package = load_json(package_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [Diagnostic("PRI-INPUT-002", "/review-package.json", str(exc))]
    diagnostics = validate_package(package)
    if diagnostics or not compare_rendered:
        return diagnostics
    expected = build_review_artifacts(package)
    for name, text in expected.items():
        artifact = path / name
        if not artifact.is_file():
            diagnostics.append(Diagnostic("PRI-CONSIST-001", f"/{name}", "rendered artifact is missing"))
        elif artifact.read_text(encoding="utf-8") != text:
            diagnostics.append(Diagnostic("PRI-CONSIST-001", f"/{name}", "artifact does not match deterministic rendering from review-package.json"))
    if PROMPT_NAME not in expected and (path / PROMPT_NAME).exists():
        diagnostics.append(Diagnostic("PRI-CONSIST-002", f"/{PROMPT_NAME}", "Green review must not contain an action prompt"))
    return sorted(set(diagnostics))
