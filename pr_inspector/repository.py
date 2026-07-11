from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from .behavioral_coverage import validate_behavioral_coverage
from .decision_projection import ProjectionError, reason_registry_entries
from .diagnostics import Diagnostic

ROOT = Path(__file__).resolve().parents[1]
QUALITY_FOUNDATION = "docs/QUALITY_ATTRIBUTE_MODEL.md"
QUALITY_REQUIRED_PHRASES = {
    "Status: repository-required planning infrastructure.": "must be marked as repository-required planning infrastructure",
    "It is not part of the active protocol `load_order`.": "must state it is outside the active protocol load_order",
    "It defines no active review rule.": "must state it defines no active review rule",
    "Its seed rules are planning-only until promoted through a new protocol snapshot, schema/validator/fixture, and release lock.": "must state seed rules are planning-only until properly promoted",
    "Repository validation keeps this document guarded and outside the active protocol `load_order`.": "must state repository validation guards the protocol boundary",
    "If this document conflicts with the active protocol, the active protocol wins.": "must state active-protocol precedence",
    "COR-INTENT-001": "must include the intent-fit seed rule",
    "PRR-INTENT-001": "must record that intent-fit has a promoted active protocol rule",
    "COR-REG-001": "must include the regression-risk seed rule",
    "COR-STATE-001": "must include the consistency seed rule",
    "COR-TEST-001": "must include the validation-adequacy seed rule",
    "COR-RESEARCH-001": "must include the research-backed-claims seed rule",
    "Validation does not make this document part of the active protocol and does not make the seed rules active review rules.": "must distinguish repository validation from active review-rule enforcement",
    "No active protocol behavior is changed": "must not claim the planning document itself changes active protocol enforcement",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_lock(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split("  ", 1)
        out[rel] = digest
    return out


def validate_quality_foundation(root: Path, load_order: list[str]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    path = root / QUALITY_FOUNDATION
    if not path.is_file():
        return [Diagnostic("PRI-QUAL-001", f"/{QUALITY_FOUNDATION}", "repository-required quality foundation planning infrastructure is missing")]
    if QUALITY_FOUNDATION in load_order:
        diagnostics.append(Diagnostic("PRI-QUAL-002", f"/{QUALITY_FOUNDATION}", "repository-required planning infrastructure must not be listed in active protocol load_order"))
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [Diagnostic("PRI-QUAL-003", f"/{QUALITY_FOUNDATION}", str(exc))]
    for phrase, message in QUALITY_REQUIRED_PHRASES.items():
        if phrase not in text:
            diagnostics.append(Diagnostic("PRI-QUAL-004", f"/{QUALITY_FOUNDATION}", message))
    return diagnostics


def validate_active_release_lock(
    root: Path,
    current: str,
    manifest: dict,
    load_order: list[str],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    expected_rel = f"release-locks/{current}.sha256"
    declared_rel = manifest.get("release_lock")
    if declared_rel != expected_rel:
        diagnostics.append(Diagnostic("PRI-LOCK-002", "/protocol-manifest.yaml/release_lock", f"active release lock must be {expected_rel}"))
        return diagnostics

    lock_path = root / expected_rel
    if not lock_path.is_file():
        diagnostics.append(Diagnostic("PRI-LOCK-002", f"/{expected_rel}", "active release lock is missing"))
        return diagnostics

    try:
        locked_paths = set(parse_lock(lock_path))
    except (OSError, ValueError) as exc:
        diagnostics.append(Diagnostic("PRI-LOCK-002", f"/{expected_rel}", str(exc)))
        return diagnostics

    canonical_paths = set(load_order)
    if locked_paths != canonical_paths:
        missing = sorted(canonical_paths - locked_paths)
        extra = sorted(locked_paths - canonical_paths)
        details: list[str] = []
        if missing:
            details.append(f"missing canonical paths: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected locked paths: {', '.join(extra)}")
        diagnostics.append(Diagnostic("PRI-LOCK-003", f"/{expected_rel}", "; ".join(details)))
    return diagnostics


def validate_active_schemas(root: Path, load_order: list[str]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    schema_paths = [rel for rel in load_order if str(rel).endswith(".schema.json")]
    if not schema_paths:
        return [Diagnostic("PRI-REPO-SCHEMA-002", "/protocol-manifest.yaml/load_order", "active load_order contains no JSON Schema")]
    for rel in schema_paths:
        path = root / rel
        if not path.is_file():
            continue
        try:
            Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:
            diagnostics.append(Diagnostic("PRI-REPO-SCHEMA-001", f"/{rel}", str(exc)))
    return diagnostics


def validate_reason_registry() -> list[Diagnostic]:
    try:
        reason_registry_entries.cache_clear()
        reason_registry_entries()
    except ProjectionError as exc:
        return [Diagnostic("PRI-REASON-001", "/decision-reason-registry", str(exc))]
    return []


def validate_repository(root: Path = ROOT) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    required = [
        "README.md", "BOOTSTRAP.md", "AGENTS.md", "CURRENT_VERSION",
        "protocol-manifest.yaml", "CHANGELOG.md", "LICENSE",
        "requirements.txt", "requirements-dev.txt", "pyproject.toml",
        QUALITY_FOUNDATION,
    ]
    for rel in required:
        if not (root / rel).is_file():
            diagnostics.append(Diagnostic("PRI-REPO-001", f"/{rel}", "required file is missing"))
    if diagnostics:
        return sorted(diagnostics)

    try:
        manifest = yaml.safe_load((root / "protocol-manifest.yaml").read_text(encoding="utf-8"))
    except Exception as exc:
        return [Diagnostic("PRI-REPO-002", "/protocol-manifest.yaml", str(exc))]
    current = (root / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
    if manifest.get("active_version") != current:
        diagnostics.append(Diagnostic("PRI-REPO-003", "/protocol-manifest.yaml", "active_version does not match CURRENT_VERSION"))
    load_order = manifest.get("load_order") or []
    if len(load_order) != len(set(load_order)):
        diagnostics.append(Diagnostic("PRI-REPO-004", "/protocol-manifest.yaml/load_order", "duplicate canonical path"))
    diagnostics.extend(validate_quality_foundation(root, load_order))

    prefix = f"protocols/{current}/"
    for idx, rel in enumerate(load_order):
        if not str(rel).startswith(prefix):
            diagnostics.append(Diagnostic("PRI-REPO-005", f"/protocol-manifest.yaml/load_order/{idx}", "active canonical path is not version-scoped"))
        if not (root / rel).is_file():
            diagnostics.append(Diagnostic("PRI-REPO-006", f"/{rel}", "canonical file is missing"))

    diagnostics.extend(validate_active_release_lock(root, current, manifest, load_order))
    diagnostics.extend(validate_active_schemas(root, load_order))
    diagnostics.extend(validate_reason_registry())
    diagnostics.extend(validate_behavioral_coverage(root))

    lifecycle_paths = [
        root / "README.md",
        root / f"protocols/{current}/PR_REVIEW_CONTRACT.md",
    ]
    forbidden_lifecycle = (
        "active candidate on the unmerged pr branch",
        "default branch remains authoritative until this pr is merged",
    )
    for lifecycle_path in lifecycle_paths:
        text = lifecycle_path.read_text(encoding="utf-8").lower()
        for phrase in forbidden_lifecycle:
            if phrase in text:
                diagnostics.append(
                    Diagnostic("PRI-LIFECYCLE-001", f"/{lifecycle_path.relative_to(root)}", f"stale lifecycle wording remains: {phrase}")
                )

    lock_dir = root / "release-locks"
    if not lock_dir.is_dir():
        diagnostics.append(Diagnostic("PRI-LOCK-000", "/release-locks", "release lock directory is missing"))
    else:
        for lock in sorted(lock_dir.glob("v*.sha256")):
            for rel, digest in parse_lock(lock).items():
                path = root / rel
                if not path.is_file():
                    diagnostics.append(Diagnostic("PRI-LOCK-001", f"/{rel}", f"file listed by {lock.name} is missing"))
                elif sha256(path) != digest:
                    diagnostics.append(Diagnostic("PRI-LOCK-001", f"/{rel}", f"SHA-256 differs from {lock.name}"))
    return sorted(set(diagnostics))
