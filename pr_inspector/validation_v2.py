from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .decision_projection import (
    ProjectionError,
    project_decision,
    projection_json,
    reason_registry_by_code,
)
from .derived_outputs import (
    MANIFEST_NAME,
    PROJECTION_NAME,
    PROMPT_NAME,
    build_review_artifacts,
)
from .diagnostics import Diagnostic
from .render import package_sha256
from .semantic_v2 import validate_semantics

ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
SCHEMA = ROOT / f"protocols/{CURRENT_VERSION}/schemas/review-package.schema.json"
PROJECTION_SCHEMA = (
    ROOT
    / f"protocols/{CURRENT_VERSION}/schemas/decision-projection.schema.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_package(pkg: dict[str, Any]) -> list[Diagnostic]:
    schema = load_json(SCHEMA)
    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )
    diagnostics: list[Diagnostic] = []
    for error in validator.iter_errors(pkg):
        path = "/" + "/".join(str(item) for item in error.absolute_path)
        diagnostics.append(
            Diagnostic("PRI-SCHEMA-001", path, error.message)
        )
    if not diagnostics:
        diagnostics.extend(validate_semantics(pkg))
    return sorted(set(diagnostics))


def _read_json_bytes(
    path: Path,
    code: str,
    diagnostic_path: str,
) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, [Diagnostic(code, diagnostic_path, str(exc))]
    if not isinstance(value, dict):
        return None, [
            Diagnostic(code, diagnostic_path, "JSON artifact must be an object")
        ]
    return value, []


def _projection_diagnostics(
    directory: Path,
    package: dict[str, Any],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    path = directory / PROJECTION_NAME
    if not path.is_file():
        return [
            Diagnostic(
                "PRI-PROJECTION-002",
                f"/{PROJECTION_NAME}",
                "canonical decision projection artifact is missing",
            )
        ]

    actual, parse_diagnostics = _read_json_bytes(
        path,
        "PRI-PROJECTION-002",
        f"/{PROJECTION_NAME}",
    )
    if parse_diagnostics:
        return parse_diagnostics
    assert actual is not None

    try:
        schema = load_json(PROJECTION_SCHEMA)
    except (OSError, json.JSONDecodeError) as exc:
        return [
            Diagnostic(
                "PRI-PROJECTION-001",
                f"/{PROJECTION_SCHEMA.relative_to(ROOT)}",
                str(exc),
            )
        ]

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )
    for error in validator.iter_errors(actual):
        subpath = "/" + "/".join(
            str(item) for item in error.absolute_path
        )
        diagnostics.append(
            Diagnostic(
                "PRI-PROJECTION-002",
                f"/{PROJECTION_NAME}{subpath}",
                error.message,
            )
        )

    try:
        expected = project_decision(package)
    except ProjectionError as exc:
        diagnostics.append(
            Diagnostic(
                "PRI-PROJECTION-001",
                "/decision",
                str(exc),
            )
        )
        return diagnostics

    if actual != expected:
        diagnostics.append(
            Diagnostic(
                "PRI-PROJECTION-003",
                f"/{PROJECTION_NAME}",
                (
                    "projection does not match the single canonical "
                    "decision derivation"
                ),
            )
        )

    registry = reason_registry_by_code()
    codes: list[str] = []
    codes.extend(actual.get("technical_status_reason_codes", []))
    owner = actual.get("owner_readiness")
    if isinstance(owner, dict):
        codes.extend(owner.get("reason_codes", []))
    action = actual.get("next_action")
    if isinstance(action, dict):
        codes.extend(action.get("reason_codes", []))
    unknown = sorted(set(codes) - set(registry))
    if unknown:
        diagnostics.append(
            Diagnostic(
                "PRI-PROJECTION-004",
                f"/{PROJECTION_NAME}",
                (
                    "projection contains unregistered reason codes: "
                    + ", ".join(unknown)
                ),
            )
        )
    return diagnostics


def _manifest_diagnostics(
    directory: Path,
    package: dict[str, Any],
    expected_artifacts: dict[str, str],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    manifest_path = directory / MANIFEST_NAME
    if not manifest_path.is_file():
        return diagnostics

    manifest, parse_diagnostics = _read_json_bytes(
        manifest_path,
        "PRI-MANIFEST-001",
        f"/{MANIFEST_NAME}",
    )
    if parse_diagnostics:
        return parse_diagnostics
    assert manifest is not None

    expected_manifest = json.loads(expected_artifacts[MANIFEST_NAME])
    if manifest != expected_manifest:
        diagnostics.append(
            Diagnostic(
                "PRI-MANIFEST-001",
                f"/{MANIFEST_NAME}",
                (
                    "manifest structure or metadata does not match "
                    "deterministic rendering"
                ),
            )
        )

    package_entry = manifest.get("canonical_review_package")
    package_path = directory / "review-package.json"
    if not isinstance(package_entry, dict):
        diagnostics.append(
            Diagnostic(
                "PRI-MANIFEST-002",
                f"/{MANIFEST_NAME}/canonical_review_package",
                "canonical review package entry is missing or invalid",
            )
        )
    else:
        if package_entry.get("path") != "review-package.json":
            diagnostics.append(
                Diagnostic(
                    "PRI-MANIFEST-002",
                    (
                        f"/{MANIFEST_NAME}/"
                        "canonical_review_package/path"
                    ),
                    "expected path review-package.json",
                )
            )
        if (
            package_entry.get("canonical_sha256")
            != package_sha256(package)
        ):
            diagnostics.append(
                Diagnostic(
                    "PRI-MANIFEST-003",
                    (
                        f"/{MANIFEST_NAME}/"
                        "canonical_review_package/canonical_sha256"
                    ),
                    "canonical package SHA-256 is incorrect",
                )
            )
        if package_path.is_file():
            actual_file_hash = _sha256_bytes(package_path.read_bytes())
            if package_entry.get("file_sha256") != actual_file_hash:
                diagnostics.append(
                    Diagnostic(
                        "PRI-MANIFEST-003",
                        (
                            f"/{MANIFEST_NAME}/"
                            "canonical_review_package/file_sha256"
                        ),
                        (
                            "manifest SHA-256 does not match actual "
                            "review-package.json bytes"
                        ),
                    )
                )

    fixed_entries = {
        "decision_projection": PROJECTION_NAME,
        "owner_decision_card": "OWNER_DECISION_CARD.fa.md",
        "technical_handoff": "TECHNICAL_HANDOFF.en.md",
        "simple_owner_result": "OWNER_RESULT.fa.txt",
    }
    for key, expected_path in fixed_entries.items():
        entry = manifest.get(key)
        if not isinstance(entry, dict):
            diagnostics.append(
                Diagnostic(
                    "PRI-MANIFEST-002",
                    f"/{MANIFEST_NAME}/{key}",
                    "manifest entry is missing or invalid",
                )
            )
            continue
        if entry.get("path") != expected_path:
            diagnostics.append(
                Diagnostic(
                    "PRI-MANIFEST-002",
                    f"/{MANIFEST_NAME}/{key}/path",
                    f"expected path {expected_path}",
                )
            )
            continue
        artifact_path = directory / expected_path
        if not artifact_path.is_file():
            diagnostics.append(
                Diagnostic(
                    "PRI-MANIFEST-002",
                    f"/{expected_path}",
                    "manifest-referenced artifact is missing",
                )
            )
            continue
        if entry.get("hash_scope") != "final_file_bytes":
            diagnostics.append(
                Diagnostic(
                    "PRI-MANIFEST-002",
                    f"/{MANIFEST_NAME}/{key}/hash_scope",
                    "artifact hash scope must be final_file_bytes",
                )
            )
        actual_hash = _sha256_bytes(artifact_path.read_bytes())
        if entry.get("sha256") != actual_hash:
            diagnostics.append(
                Diagnostic(
                    "PRI-MANIFEST-003",
                    f"/{MANIFEST_NAME}/{key}/sha256",
                    (
                        "manifest SHA-256 does not match actual "
                        "artifact bytes"
                    ),
                )
            )

    prompt_entry = manifest.get("next_action_artifact")
    expected_prompt = expected_manifest["next_action_artifact"]
    if not isinstance(prompt_entry, dict):
        diagnostics.append(
            Diagnostic(
                "PRI-MANIFEST-002",
                f"/{MANIFEST_NAME}/next_action_artifact",
                "next action artifact entry is missing or invalid",
            )
        )
        return diagnostics

    routing_fields = (
        "generated",
        "path",
        "action_kind",
        "recipient",
        "may_modify_code",
        "prompt_kind",
    )
    for field in routing_fields:
        if prompt_entry.get(field) != expected_prompt.get(field):
            diagnostics.append(
                Diagnostic(
                    "PRI-MANIFEST-002",
                    f"/{MANIFEST_NAME}/next_action_artifact/{field}",
                    (
                        "next-action metadata diverges from the "
                        "canonical projection"
                    ),
                )
            )

    if expected_prompt["generated"]:
        prompt_path = directory / PROMPT_NAME
        if not prompt_path.is_file():
            diagnostics.append(
                Diagnostic(
                    "PRI-MANIFEST-002",
                    f"/{PROMPT_NAME}",
                    "required next-action artifact is missing",
                )
            )
        else:
            if prompt_entry.get("hash_scope") != "final_file_bytes":
                diagnostics.append(
                    Diagnostic(
                        "PRI-MANIFEST-002",
                        (
                            f"/{MANIFEST_NAME}/"
                            "next_action_artifact/hash_scope"
                        ),
                        "prompt hash scope must be final_file_bytes",
                    )
                )
            actual_hash = _sha256_bytes(prompt_path.read_bytes())
            if prompt_entry.get("sha256") != actual_hash:
                diagnostics.append(
                    Diagnostic(
                        "PRI-MANIFEST-003",
                        (
                            f"/{MANIFEST_NAME}/"
                            "next_action_artifact/sha256"
                        ),
                        (
                            "manifest SHA-256 does not match actual "
                            "next-action artifact bytes"
                        ),
                    )
                )
    else:
        for field in ("path", "sha256", "hash_scope", "prompt_kind"):
            if prompt_entry.get(field) is not None:
                diagnostics.append(
                    Diagnostic(
                        "PRI-MANIFEST-002",
                        (
                            f"/{MANIFEST_NAME}/"
                            f"next_action_artifact/{field}"
                        ),
                        (
                            "non-prompt action metadata must use null "
                            "for prompt-only fields"
                        ),
                    )
                )
    return diagnostics


def validate_directory(
    path: Path,
    compare_rendered: bool = True,
) -> list[Diagnostic]:
    package_path = path / "review-package.json"
    if not package_path.is_file():
        return [
            Diagnostic(
                "PRI-INPUT-001",
                "/review-package.json",
                "canonical package is missing",
            )
        ]

    try:
        package_bytes = package_path.read_bytes()
        package = json.loads(package_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [
            Diagnostic(
                "PRI-INPUT-002",
                "/review-package.json",
                str(exc),
            )
        ]

    diagnostics = validate_package(package)
    if diagnostics or not compare_rendered:
        return diagnostics

    try:
        expected = build_review_artifacts(
            package,
            review_package_bytes=package_bytes,
        )
    except ProjectionError as exc:
        return [
            Diagnostic(
                "PRI-PROJECTION-001",
                "/decision",
                str(exc),
            )
        ]

    for name, text in expected.items():
        artifact = path / name
        if not artifact.is_file():
            diagnostics.append(
                Diagnostic(
                    "PRI-CONSIST-001",
                    f"/{name}",
                    "rendered artifact is missing",
                )
            )
            continue
        try:
            actual_bytes = artifact.read_bytes()
        except OSError as exc:
            diagnostics.append(
                Diagnostic("PRI-CONSIST-001", f"/{name}", str(exc))
            )
            continue
        expected_bytes = text.encode("utf-8")
        if actual_bytes != expected_bytes:
            diagnostics.append(
                Diagnostic(
                    "PRI-CONSIST-001",
                    f"/{name}",
                    (
                        "artifact bytes do not match deterministic "
                        "UTF-8 LF rendering"
                    ),
                )
            )

    if PROMPT_NAME not in expected and (path / PROMPT_NAME).exists():
        diagnostics.append(
            Diagnostic(
                "PRI-CONSIST-002",
                f"/{PROMPT_NAME}",
                (
                    "canonical projection forbids a next-action "
                    "artifact for this action"
                ),
            )
        )

    diagnostics.extend(_projection_diagnostics(path, package))
    diagnostics.extend(
        _manifest_diagnostics(path, package, expected)
    )
    return sorted(set(diagnostics))
