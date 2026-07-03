from __future__ import annotations
import hashlib
import json
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

from .diagnostics import Diagnostic

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_lock(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split("  ", 1)
        out[rel] = digest
    return out


def validate_repository(root: Path = ROOT) -> list[Diagnostic]:
    diagnostics = []
    required = [
        "README.md", "BOOTSTRAP.md", "AGENTS.md", "CURRENT_VERSION",
        "protocol-manifest.yaml", "CHANGELOG.md", "LICENSE",
        "requirements.txt", "requirements-dev.txt", "pyproject.toml",
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
    prefix = f"protocols/{current}/"
    for idx, rel in enumerate(load_order):
        if not str(rel).startswith(prefix):
            diagnostics.append(Diagnostic("PRI-REPO-005", f"/protocol-manifest.yaml/load_order/{idx}", "active canonical path is not version-scoped"))
        if not (root / rel).is_file():
            diagnostics.append(Diagnostic("PRI-REPO-006", f"/{rel}", "canonical file is missing"))
    schema_rel = manifest.get("canonical_schema")
    if schema_rel and (root / schema_rel).is_file():
        try:
            Draft202012Validator.check_schema(json.loads((root / schema_rel).read_text(encoding="utf-8")))
        except Exception as exc:
            diagnostics.append(Diagnostic("PRI-REPO-SCHEMA-001", f"/{schema_rel}", str(exc)))
    else:
        diagnostics.append(Diagnostic("PRI-REPO-SCHEMA-002", f"/{schema_rel}", "canonical schema is missing"))
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
