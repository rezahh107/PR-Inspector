from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .derived_outputs import PROMPT_NAME, build_review_artifacts
from .diagnostics import Diagnostic
from .render import package_sha256
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


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _manifest_diagnostics(
    directory: Path,
    package: dict[str, Any],
    expected_artifacts: dict[str, str],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    manifest_path = directory / "artifact-manifest.json"
    if not manifest_path.is_file():
        return diagnostics

    try:
        raw = manifest_path.read_bytes()
        manifest = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [Diagnostic("PRI-MANIFEST-001", "/artifact-manifest.json", str(exc))]

    expected_manifest = json.loads(expected_artifacts["artifact-manifest.json"])
    if manifest != expected_manifest:
        diagnostics.append(
            Diagnostic(
                "PRI-MANIFEST-001",
                "/artifact-manifest.json",
                "manifest structure or metadata does not match deterministic rendering",
            )
        )

    fixed_entries = {
        "canonical_review_package": "review-package.json",
        "owner_decision_card": "OWNER_DECISION_CARD.fa.md",
        "technical_handoff": "TECHNICAL_HANDOFF.en.md",
        "simple_owner_result": "OWNER_RESULT.fa.txt",
    }
    for key, expected_path in fixed_entries.items():
        entry = manifest.get(key)
        if not isinstance(entry, dict):
            diagnostics.append(
                Diagnostic("PRI-MANIFEST-002", f"/artifact-manifest.json/{key}", "manifest entry is missing or invalid")
            )
            continue
        if entry.get("path") != expected_path:
            diagnostics.append(
                Diagnostic(
                    "PRI-MANIFEST-002",
                    f"/artifact-manifest.json/{key}/path",
                    f"expected path {expected_path}",
                )
            )
            continue
        artifact_path = directory / expected_path
        if not artifact_path.is_file():
            diagnostics.append(
                Diagnostic("PRI-MANIFEST-002", f"/{expected_path}", "manifest-referenced artifact is missing")
            )
            continue
        actual_hash = (
            package_sha256(package)
            if key == "canonical_review_package"
            else _sha256_bytes(artifact_path.read_bytes())
        )
        if entry.get("sha256") != actual_hash:
            diagnostics.append(
                Diagnostic(
                    "PRI-MANIFEST-003",
                    f"/artifact-manifest.json/{key}/sha256",
                    "manifest SHA-256 does not match the actual artifact bytes",
                )
            )

    prompt_entry = manifest.get("next_action_prompt")
    expected_prompt_entry = expected_manifest["next_action_prompt"]
    if not isinstance(prompt_entry, dict):
        diagnostics.append(
            Diagnostic(
                "PRI-MANIFEST-002",
                "/artifact-manifest.json/next_action_prompt",
                "next_action_prompt entry is missing or invalid",
            )
        )
        return diagnostics

    if prompt_entry.get("generated") != expected_prompt_entry["generated"]:
        diagnostics.append(
            Diagnostic(
                "PRI-MANIFEST-002",
                "/artifact-manifest.json/next_action_prompt/generated",
                "prompt generation flag does not match the validated decision",
            )
        )

    if expected_prompt_entry["generated"]:
        if prompt_entry.get("path") != PROMPT_NAME:
            diagnostics.append(
                Diagnostic(
                    "PRI-MANIFEST-002",
                    "/artifact-manifest.json/next_action_prompt/path",
                    f"expected path {PROMPT_NAME}",
                )
            )
        else:
            prompt_path = directory / PROMPT_NAME
            if not prompt_path.is_file():
                diagnostics.append(
                    Diagnostic("PRI-MANIFEST-002", f"/{PROMPT_NAME}", "manifest-referenced action prompt is missing")
                )
            elif prompt_entry.get("sha256") != _sha256_bytes(prompt_path.read_bytes()):
                diagnostics.append(
                    Diagnostic(
                        "PRI-MANIFEST-003",
                        "/artifact-manifest.json/next_action_prompt/sha256",
                        "manifest SHA-256 does not match the actual action-prompt bytes",
                    )
                )
        if prompt_entry.get("action_mode") != expected_prompt_entry["action_mode"]:
            diagnostics.append(
                Diagnostic(
                    "PRI-MANIFEST-002",
                    "/artifact-manifest.json/next_action_prompt/action_mode",
                    "action mode does not match structured package fields",
                )
            )
    else:
        for field in ("path", "sha256", "action_mode"):
            if prompt_entry.get(field) is not None:
                diagnostics.append(
                    Diagnostic(
                        "PRI-MANIFEST-002",
                        f"/artifact-manifest.json/next_action_prompt/{field}",
                        "Green prompt metadata must be null",
                    )
                )
    return diagnostics


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
            continue
        try:
            actual_bytes = artifact.read_bytes()
        except OSError as exc:
            diagnostics.append(Diagnostic("PRI-CONSIST-001", f"/{name}", str(exc)))
            continue
        expected_bytes = text.encode("utf-8")
        if actual_bytes != expected_bytes:
            diagnostics.append(
                Diagnostic(
                    "PRI-CONSIST-001",
                    f"/{name}",
                    "artifact bytes do not match deterministic UTF-8 LF rendering from review-package.json",
                )
            )

    if PROMPT_NAME not in expected and (path / PROMPT_NAME).exists():
        diagnostics.append(
            Diagnostic("PRI-CONSIST-002", f"/{PROMPT_NAME}", "Green review must not contain an action prompt")
        )

    diagnostics.extend(_manifest_diagnostics(path, package, expected))
    return sorted(set(diagnostics))
