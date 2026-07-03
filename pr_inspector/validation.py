from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator, FormatChecker

from .diagnostics import Diagnostic
from .semantic import validate_semantics
from .render import render_owner, render_handoff

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "protocols/v1.4.0/schemas/review-package.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_package(pkg: dict[str, Any]) -> list[Diagnostic]:
    schema = load_json(SCHEMA)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    diagnostics: list[Diagnostic] = []
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
        pkg = load_json(package_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [Diagnostic("PRI-INPUT-002", "/review-package.json", str(exc))]
    diagnostics = validate_package(pkg)
    if diagnostics or not compare_rendered:
        return diagnostics
    expected = {
        "OWNER_DECISION_CARD.fa.md": render_owner(pkg),
        "TECHNICAL_HANDOFF.en.md": render_handoff(pkg),
    }
    for name, text in expected.items():
        artifact = path / name
        if not artifact.is_file():
            diagnostics.append(Diagnostic("PRI-CONSIST-001", f"/{name}", "rendered artifact is missing"))
        elif artifact.read_text(encoding="utf-8") != text:
            diagnostics.append(Diagnostic("PRI-CONSIST-001", f"/{name}", "artifact does not match deterministic rendering from review-package.json"))
    return sorted(set(diagnostics))
