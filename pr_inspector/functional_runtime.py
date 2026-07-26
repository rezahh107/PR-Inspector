from __future__ import annotations

import ast, hashlib, json, re, subprocess, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")

class FunctionalBootstrapError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}"); self.code = code

class DuplicateKeyError(ValueError): pass

def _pairs(items):
    out = {}
    for key, value in items:
        if key in out: raise DuplicateKeyError(f"duplicate JSON key: {key}")
        out[key] = value
    return out

def _load_raw(path: Path) -> dict[str, Any]:
    try: value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
        raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-001", str(exc)) from exc
    if not isinstance(value, dict): raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-001", f"{path}: JSON root must be object")
    return value

def resolve_rules(contract: dict[str, Any]) -> tuple[dict[str, str], ...]:
    rules = contract.get("functional_rules", [])
    if not rules or isinstance(rules[0], dict): return tuple(rules)
    defaults = contract["rule_defaults"]
    return tuple({"rule_id": rid, "risk": risk, "validator": defaults["validator"], "positive_control": defaults["positive_control"], "negative_mutation": defaults["negative_prefix"] + mutation, "ci_command": defaults["ci_commands"][ci], "recovery_action": defaults["recovery_action"]} for rid, risk, mutation, ci in rules)

def load_json_strict(path: Path) -> dict[str, Any]:
    value = _load_raw(path)
    if path.name == "functional-runtime-contract.json": value = {**value, "functional_rules": list(resolve_rules(value))}
    return value

def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

def _runtime_digest(root: Path, paths: list[str]) -> str:
    digest = hashlib.sha256()
    for relative in paths:
        path = root / relative
        if not path.is_file(): raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-004", f"missing runtime path: {relative}")
        digest.update(relative.encode() + b"\0"); digest.update(path.read_bytes()); digest.update(b"\0")
    return digest.hexdigest()

def _git(root: Path, *args: str) -> str:
    try: return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc: raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-008", f"local git identity unavailable: {exc}") from exc

def _path(reference: str) -> str: return reference.split(":", 1)[0].split("#", 1)[0]

def _validate_symbol(root: Path, reference: str) -> None:
    path_text, symbol = reference.rsplit(":", 1); path = root / path_text
    if not path.is_file(): raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-004", f"missing executable reference: {reference}")
    try: names = {node.name for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    except (OSError, UnicodeDecodeError, SyntaxError) as exc: raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-005", f"invalid executable reference: {reference}: {exc}") from exc
    if symbol not in names: raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-005", f"missing symbol: {reference}")

def render_rule_view(rules, *, title: str) -> str:
    columns = ("rule_id", "risk", "validator", "positive_control", "negative_mutation", "CI_step", "recovery_action")
    lines = [f"# {title}", "", "Status: generated, non-authoritative view of `../functional-runtime-contract.json`.", "", "| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for rule in rules:
        values = (rule["rule_id"], rule["risk"], rule["validator"], rule["positive_control"], rule["negative_mutation"], rule["ci_command"], rule["recovery_action"])
        if any("|" in str(v) or "\n" in str(v) for v in values): raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-007", f"unsafe Markdown cell: {rule['rule_id']}")
        lines.append("| " + " | ".join(map(str, values)) + " |")
    return "\n".join(lines) + "\n"

@dataclass(frozen=True)
class FunctionalProtocol:
    protocol_version: str; inspector_repository: str; inspector_repository_id: int; inspector_commit_sha: str; required_check_names: tuple[str, ...]; contract_sha256: str; functional_runtime_sha256: str

def validate_runtime_contract(root: Path = ROOT, *, require_git: bool = True) -> FunctionalProtocol:
    root = Path(root).resolve()
    try: current = (root / "CURRENT_VERSION").read_text(encoding="utf-8").strip(); manifest = yaml.safe_load((root / "protocol-manifest.yaml").read_text(encoding="utf-8"))
    except Exception as exc: raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-001", str(exc)) from exc
    if current != "v1.13.0" or not isinstance(manifest, dict) or manifest.get("active_version") != current or manifest.get("status") != "active": raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-002", "active version or manifest mismatch")
    contract_rel, schema_rel = manifest.get("functional_runtime_contract"), manifest.get("functional_runtime_schema")
    if not isinstance(contract_rel, str) or not isinstance(schema_rel, str): raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-003", "functional references missing")
    raw, schema = _load_raw(root / contract_rel), _load_raw(root / schema_rel)
    try: Draft202012Validator.check_schema(schema); errors = sorted(Draft202012Validator(schema).iter_errors(raw), key=lambda e: tuple(map(str, e.absolute_path)))
    except Exception as exc: raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-003", f"invalid functional schema: {exc}") from exc
    if errors: raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-003", f"/{'/'.join(map(str, errors[0].absolute_path))}: {errors[0].message}")
    expected_contract = manifest.get("functional_contract_sha256")
    if not _SHA256.fullmatch(str(expected_contract)) or _sha(root / contract_rel) != expected_contract: raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-006", "functional contract digest mismatch")
    contract = {**raw, "functional_rules": list(resolve_rules(raw))}
    if contract["protocol"]["version"] != current: raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-002", "contract version mismatch")
    refs = list(contract["references"].values())
    for relative in refs:
        if not str(relative).startswith(f"protocols/{current}/") or not (root / relative).is_file(): raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-004", f"invalid reference: {relative}")
        if relative.endswith(".schema.json"):
            candidate = _load_raw(root / relative)
            try: Draft202012Validator.check_schema(candidate)
            except Exception as exc: raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-003", f"invalid referenced schema {relative}: {exc}") from exc
    rules = contract["functional_rules"]; workflow = (root / ".github/workflows/validate-repository.yml").read_text(encoding="utf-8")
    for rule in rules:
        _validate_symbol(root, rule["validator"])
        for key in ("positive_control", "negative_mutation"):
            if not (root / _path(rule[key])).is_file(): raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-004", f"missing rule reference: {rule[key]}")
        if rule["ci_command"] not in workflow: raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-007", f"rule CI command absent: {rule['rule_id']}")
    if len({r["rule_id"] for r in rules}) != len(rules) or len({r["negative_mutation"] for r in rules}) != len(rules): raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-007", "duplicate rule or mutation")
    views = {contract["references"]["coverage_view"]: render_rule_view(rules, title="Behavioral Rule Coverage v1.13.0"), contract["references"]["governance_coverage_view"]: render_rule_view([r for r in rules if r["rule_id"].startswith(("PRR-DOC-", "PRR-GOV-", "PRR-HISTORY-"))], title="Merge Governance Rule Coverage v1.13.0")}
    for relative, expected in views.items():
        if (root / relative).read_text(encoding="utf-8") != expected: raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-007", f"generated rule view drift: {relative}")
    paths = manifest.get("functional_digest_paths")
    if not isinstance(paths, list) or len(paths) != len(set(paths)): raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-006", "invalid runtime paths")
    runtime_sha = _runtime_digest(root, paths)
    if runtime_sha != manifest.get("functional_runtime_sha256"): raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-006", "functional runtime digest mismatch")
    commit = _git(root, "rev-parse", "HEAD") if require_git else "0" * 40
    if require_git and (not _GIT_SHA.fullmatch(commit) or _git(root, "status", "--porcelain", "--", *paths)): raise FunctionalBootstrapError("PRI-FUNCTIONAL-BOOTSTRAP-009", "runtime identity is dirty or invalid")
    protocol = contract["protocol"]
    return FunctionalProtocol(current, protocol["inspector_repository"], protocol["inspector_repository_id"], commit, tuple(contract["required_check_names"]), expected_contract, runtime_sha)

def install_active_protocol_adapters() -> None:
    from . import decision_projection as projection
    from . import verified_review as legacy
    from .functional_review import assemble_review_package
    original = projection.project_decision
    def project(pkg, governance_evidence=None, sequence_enforcement=None):
        result = original(pkg, governance_evidence, sequence_enforcement); version = pkg.get("protocol_version") if isinstance(pkg, dict) else None
        if version in {"v1.12.0", "v1.13.0"}: result["protocol_version"] = version; projection.validate_projection_invariants(result)
        return result
    projection.project_decision = project
    for name, module in tuple(sys.modules.items()):
        if name.startswith("pr_inspector.") and module is not None and getattr(module, "project_decision", None) is original: setattr(module, "project_decision", project)
    legacy_method = legacy.ProtocolContext.from_verified_repository.__func__
    def from_repo(cls, repository_directory=ROOT, *, token=None, api_version="2022-11-28"):
        root = Path(repository_directory).resolve()
        try: active = (root / "CURRENT_VERSION").read_text(encoding="utf-8").strip() == "v1.13.0"
        except Exception: active = False
        if not active: return legacy_method(cls, root, token=token, api_version=api_version)
        p = validate_runtime_contract(root); return cls(p.protocol_version, p.inspector_repository, p.inspector_repository_id, p.inspector_commit_sha, p.required_check_names)
    legacy.ProtocolContext.from_verified_repository = classmethod(from_repo)
    legacy.ProtocolContext.from_repository = classmethod(lambda cls, repository_directory=ROOT: from_repo(cls, repository_directory))
    legacy.ASSESSMENT_SCHEMA = ROOT / "protocols/v1.13.0/schemas/review-assessment.schema.json"
    legacy.assemble_review_package = assemble_review_package
