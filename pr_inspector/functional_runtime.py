from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_VERSION = "v1.13.0"
ENTRYPOINT = "BOOTSTRAP.md"
CONTRACT_PATH = "protocols/v1.13.0/functional-runtime-contract.json"
CONTRACT_SCHEMA_PATH = (
    "protocols/v1.13.0/schemas/functional-runtime-contract.schema.json"
)
CI_WORKFLOW_PATH = ".github/workflows/validate-repository.yml"
RUNTIME_SCRIPT_PATH = "scripts/validate_runtime_contract.py"
PYPROJECT_PATH = "pyproject.toml"
RUNTIME_BOOTSTRAP_INPUTS = (
    "CURRENT_VERSION",
    "protocol-manifest.yaml",
    CONTRACT_PATH,
    CONTRACT_SCHEMA_PATH,
    "protocols/v1.13.0/prompts/INTAKE_RESPONSE.fa.md",
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


class FunctionalBootstrapError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


class DuplicateKeyError(ValueError):
    pass


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        if key in out:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _load_raw(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_pairs,
        )
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        DuplicateKeyError,
    ) as exc:
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-001", str(exc)
        ) from exc
    if not isinstance(value, dict):
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-001",
            f"{path}: JSON root must be object",
        )
    return value


def resolve_rules(
    contract: dict[str, Any],
) -> tuple[dict[str, str], ...]:
    rules = contract.get("functional_rules", [])
    if not rules or isinstance(rules[0], dict):
        return tuple(rules)
    defaults = contract["rule_defaults"]
    return tuple(
        {
            "rule_id": rule_id,
            "risk": risk,
            "validator": defaults["validator"],
            "positive_control": defaults["positive_control"],
            "negative_mutation": defaults["negative_prefix"] + mutation,
            "ci_command": defaults["ci_commands"][ci_key],
            "recovery_action": defaults["recovery_action"],
        }
        for rule_id, risk, mutation, ci_key in rules
    )


def load_json_strict(path: Path) -> dict[str, Any]:
    value = _load_raw(path)
    if path.name == "functional-runtime-contract.json":
        value = {
            **value,
            "functional_rules": list(resolve_rules(value)),
        }
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runtime_digest(root: Path, paths: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for relative in paths:
        path = root / relative
        if not path.is_file():
            raise FunctionalBootstrapError(
                "PRI-FUNCTIONAL-BOOTSTRAP-004",
                f"missing runtime path: {relative}",
            )
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git(root: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", None) or str(exc)
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-008",
            f"local git identity unavailable: {detail}",
        ) from exc


def _reference_path(reference: str) -> str:
    return reference.rsplit(":", 1)[0].split("#", 1)[0]


def _normalize_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-004",
            f"authority path must be a non-empty string: {value!r}",
        )
    if "\\" in value or value.startswith("/"):
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-004",
            f"authority path is not repository-relative POSIX: {value}",
        )
    pure = PurePosixPath(value)
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-004",
            f"authority path has a noncanonical segment: {value}",
        )
    normalized = pure.as_posix()
    if normalized != value:
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-004",
            f"authority path is not canonical: {value}",
        )
    return normalized


def _assert_regular_authority_file(root: Path, relative: str) -> None:
    normalized = _normalize_path(relative)
    path = root / normalized
    try:
        resolved_root = root.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-004",
            f"missing authority path: {normalized}: {exc}",
        ) from exc
    if path.is_symlink():
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-004",
            f"symlinked authority path is forbidden: {normalized}",
        )
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-004",
            f"authority path escapes repository root: {normalized}",
        )
    if not path.is_file():
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-004",
            f"authority path is not a regular file: {normalized}",
        )


def _validate_symbol(root: Path, reference: str) -> None:
    if ":" not in reference:
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-005",
            f"executable reference lacks symbol: {reference}",
        )
    path_text, symbol = reference.rsplit(":", 1)
    path_text = _normalize_path(path_text)
    _assert_regular_authority_file(root, path_text)
    path = root / path_text
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-005",
            f"invalid executable reference: {reference}: {exc}",
        ) from exc
    names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        )
    }
    if symbol not in names:
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-005",
            f"missing symbol: {reference}",
        )


def _python_authority_sources(root: Path, directory: str) -> list[str]:
    base = root / directory
    if not base.is_dir() or base.is_symlink():
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-004",
            f"{directory} authority directory is missing or symlinked",
        )
    paths: list[str] = []
    for candidate in base.rglob("*"):
        relative = candidate.relative_to(root).as_posix()
        if candidate.is_symlink():
            raise FunctionalBootstrapError(
                "PRI-FUNCTIONAL-BOOTSTRAP-004",
                f"symlinked authority path is forbidden: {relative}",
            )
        if candidate.is_file() and candidate.suffix == ".py":
            _assert_regular_authority_file(root, relative)
            paths.append(relative)
    return sorted(paths)


def _python_runtime_sources(root: Path) -> list[str]:
    return _python_authority_sources(root, "pr_inspector")


def _python_script_sources(root: Path) -> list[str]:
    return _python_authority_sources(root, "scripts")


def _derived_integrity_inventory(
    root: Path,
    contract: dict[str, Any],
    rules: tuple[dict[str, str], ...],
) -> tuple[str, ...]:
    candidates: set[str] = {
        ENTRYPOINT,
        "CURRENT_VERSION",
        CI_WORKFLOW_PATH,
        PYPROJECT_PATH,
        RUNTIME_SCRIPT_PATH,
    }
    candidates.update(
        item
        for item in RUNTIME_BOOTSTRAP_INPUTS
        if item != "protocol-manifest.yaml"
    )

    references = contract.get("references")
    if not isinstance(references, dict):
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-003",
            "contract references must be an object",
        )
    candidates.update(_normalize_path(item) for item in references.values())

    stages = contract.get("pipeline_stages")
    if not isinstance(stages, list):
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-003",
            "pipeline_stages must be an array",
        )
    executable_references: list[str] = []
    for stage in stages:
        if not isinstance(stage, dict) or not isinstance(
            stage.get("function"), str
        ):
            raise FunctionalBootstrapError(
                "PRI-FUNCTIONAL-BOOTSTRAP-003",
                "pipeline stage function is missing",
            )
        executable_references.append(stage["function"])

    for rule in rules:
        for field in ("validator", "positive_control"):
            reference = rule.get(field)
            if not isinstance(reference, str):
                raise FunctionalBootstrapError(
                    "PRI-FUNCTIONAL-BOOTSTRAP-003",
                    f"rule executable reference is missing: {field}",
                )
            executable_references.append(reference)

    for reference in executable_references:
        _validate_symbol(root, reference)
        candidates.add(_reference_path(reference))

    candidates.update(_python_runtime_sources(root))
    candidates.update(_python_script_sources(root))
    inventory = tuple(sorted(_normalize_path(item) for item in candidates))
    if len(inventory) != len(set(inventory)):
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-006",
            "derived authority inventory contains duplicates",
        )
    for relative in inventory:
        _assert_regular_authority_file(root, relative)
    return inventory


def render_rule_view(
    rules: Iterable[dict[str, str]],
    *,
    title: str,
) -> str:
    columns = (
        "rule_id",
        "risk",
        "validator",
        "positive_control",
        "negative_mutation",
        "CI_step",
        "recovery_action",
    )
    lines = [
        f"# {title}",
        "",
        (
            "Status: generated, non-authoritative view of "
            "`../functional-runtime-contract.json`."
        ),
        "",
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for rule in rules:
        values = (
            rule["rule_id"],
            rule["risk"],
            rule["validator"],
            rule["positive_control"],
            rule["negative_mutation"],
            rule["ci_command"],
            rule["recovery_action"],
        )
        if any("|" in str(value) or "\n" in str(value) for value in values):
            raise FunctionalBootstrapError(
                "PRI-FUNCTIONAL-BOOTSTRAP-007",
                f"unsafe Markdown cell: {rule['rule_id']}",
            )
        lines.append("| " + " | ".join(map(str, values)) + " |")
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class FunctionalProtocol:
    protocol_version: str
    inspector_repository: str
    inspector_repository_id: int
    inspector_commit_sha: str
    required_check_names: tuple[str, ...]
    contract_sha256: str
    functional_runtime_sha256: str


def validate_runtime_contract(
    root: Path = ROOT,
    *,
    require_git: bool = True,
) -> FunctionalProtocol:
    root = Path(root).resolve()
    try:
        current = (root / "CURRENT_VERSION").read_text(
            encoding="utf-8"
        ).strip()
        manifest = yaml.safe_load(
            (root / "protocol-manifest.yaml").read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-001", str(exc)
        ) from exc

    if not isinstance(manifest, dict):
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-001",
            "protocol manifest must be an object",
        )
    canonical = {
        "entrypoint": ENTRYPOINT,
        "active_version": ACTIVE_VERSION,
        "functional_runtime_contract": CONTRACT_PATH,
        "functional_runtime_schema": CONTRACT_SCHEMA_PATH,
    }
    for key, expected in canonical.items():
        if manifest.get(key) != expected:
            raise FunctionalBootstrapError(
                "PRI-FUNCTIONAL-BOOTSTRAP-002",
                f"{key} must equal {expected!r}",
            )
    if current != ACTIVE_VERSION or manifest.get("status") != "active":
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-002",
            "active version or manifest status mismatch",
        )
    if manifest.get("runtime_bootstrap_inputs") != list(
        RUNTIME_BOOTSTRAP_INPUTS
    ):
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-003",
            (
                "runtime_bootstrap_inputs must equal "
                f"{json.dumps(RUNTIME_BOOTSTRAP_INPUTS)}"
            ),
        )

    raw = _load_raw(root / CONTRACT_PATH)
    schema = _load_raw(root / CONTRACT_SCHEMA_PATH)
    try:
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema).iter_errors(raw),
            key=lambda error: tuple(map(str, error.absolute_path)),
        )
    except Exception as exc:
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-003",
            f"invalid functional schema: {exc}",
        ) from exc
    if errors:
        path = "/".join(map(str, errors[0].absolute_path))
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-003",
            f"/{path}: {errors[0].message}",
        )

    expected_contract = manifest.get("functional_contract_sha256")
    if (
        not _SHA256.fullmatch(str(expected_contract))
        or _sha(root / CONTRACT_PATH) != expected_contract
    ):
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-006",
            "functional contract digest mismatch",
        )

    contract = {
        **raw,
        "functional_rules": list(resolve_rules(raw)),
    }
    if contract["protocol"]["version"] != current:
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-002",
            "contract version mismatch",
        )

    references = list(contract["references"].values())
    for relative in references:
        relative = _normalize_path(relative)
        if not relative.startswith(f"protocols/{current}/"):
            raise FunctionalBootstrapError(
                "PRI-FUNCTIONAL-BOOTSTRAP-004",
                f"reference is outside active protocol: {relative}",
            )
        _assert_regular_authority_file(root, relative)
        if relative.endswith(".schema.json"):
            candidate = _load_raw(root / relative)
            try:
                Draft202012Validator.check_schema(candidate)
            except Exception as exc:
                raise FunctionalBootstrapError(
                    "PRI-FUNCTIONAL-BOOTSTRAP-003",
                    f"invalid referenced schema {relative}: {exc}",
                ) from exc

    rules = resolve_rules(raw)
    workflow = (root / CI_WORKFLOW_PATH).read_text(encoding="utf-8")
    for rule in rules:
        if not (root / _reference_path(rule["negative_mutation"])).is_file():
            raise FunctionalBootstrapError(
                "PRI-FUNCTIONAL-BOOTSTRAP-004",
                f"missing rule reference: {rule['negative_mutation']}",
            )
        if rule["ci_command"] not in workflow:
            raise FunctionalBootstrapError(
                "PRI-FUNCTIONAL-BOOTSTRAP-007",
                f"rule CI command absent: {rule['rule_id']}",
            )
    if (
        len({rule["rule_id"] for rule in rules}) != len(rules)
        or len({rule["negative_mutation"] for rule in rules}) != len(rules)
    ):
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-007",
            "duplicate rule or mutation",
        )

    views = {
        contract["references"]["coverage_view"]: render_rule_view(
            rules,
            title="Behavioral Rule Coverage v1.13.0",
        ),
        contract["references"]["governance_coverage_view"]: render_rule_view(
            [
                rule
                for rule in rules
                if rule["rule_id"].startswith(
                    ("PRR-DOC-", "PRR-GOV-", "PRR-HISTORY-")
                )
            ],
            title="Merge Governance Rule Coverage v1.13.0",
        ),
    }
    for relative, expected in views.items():
        if (root / relative).read_text(encoding="utf-8") != expected:
            raise FunctionalBootstrapError(
                "PRI-FUNCTIONAL-BOOTSTRAP-007",
                f"generated rule view drift: {relative}",
            )

    inventory = _derived_integrity_inventory(root, contract, rules)
    declared = manifest.get("functional_digest_paths")
    if (
        not isinstance(declared, list)
        or declared != sorted(declared)
        or len(declared) != len(set(declared))
        or declared != list(inventory)
    ):
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-006",
            (
                "functional_digest_paths must equal the derived inventory: "
                f"{json.dumps(list(inventory), separators=(',', ':'))}"
            ),
        )

    runtime_sha = _runtime_digest(root, inventory)
    expected_runtime_sha = manifest.get("functional_runtime_sha256")
    if (
        not _SHA256.fullmatch(str(expected_runtime_sha))
        or runtime_sha != expected_runtime_sha
    ):
        raise FunctionalBootstrapError(
            "PRI-FUNCTIONAL-BOOTSTRAP-006",
            (
                "functional runtime digest mismatch; "
                f"observed_runtime_sha256={runtime_sha}"
            ),
        )

    commit = "0" * 40
    if require_git:
        commit = _git(root, "rev-parse", "HEAD")
        controls = tuple(
            sorted(
                {
                    ENTRYPOINT,
                    "CURRENT_VERSION",
                    "protocol-manifest.yaml",
                    *inventory,
                }
            )
        )
        dirty = _git(
            root,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--",
            *controls,
        )
        if not _GIT_SHA.fullmatch(commit) or dirty:
            raise FunctionalBootstrapError(
                "PRI-FUNCTIONAL-BOOTSTRAP-009",
                (
                    "runtime identity is dirty or invalid"
                    + (f": {dirty}" if dirty else "")
                ),
            )

    protocol = contract["protocol"]
    return FunctionalProtocol(
        current,
        protocol["inspector_repository"],
        protocol["inspector_repository_id"],
        commit,
        tuple(contract["required_check_names"]),
        str(expected_contract),
        runtime_sha,
    )


def install_active_protocol_adapters() -> None:
    from . import decision_projection as projection
    from . import verified_review as legacy
    from .functional_review import assemble_review_package

    original = projection.project_decision

    def project(
        package: Any,
        governance_evidence: Any = None,
        sequence_enforcement: Any = None,
    ) -> Any:
        result = original(
            package,
            governance_evidence,
            sequence_enforcement,
        )
        version = (
            package.get("protocol_version")
            if isinstance(package, dict)
            else None
        )
        if version in {"v1.12.0", "v1.13.0"}:
            result["protocol_version"] = version
            projection.validate_projection_invariants(result)
        return result

    projection.project_decision = project
    for name, module in tuple(sys.modules.items()):
        if (
            name.startswith("pr_inspector.")
            and module is not None
            and getattr(module, "project_decision", None) is original
        ):
            setattr(module, "project_decision", project)

    legacy_method = legacy.ProtocolContext.from_verified_repository.__func__

    def from_repo(
        cls: Any,
        repository_directory: Path = ROOT,
        *,
        token: str | None = None,
        api_version: str = "2022-11-28",
    ) -> Any:
        candidate_root = Path(repository_directory).resolve()
        try:
            active = (
                candidate_root / "CURRENT_VERSION"
            ).read_text(encoding="utf-8").strip() == ACTIVE_VERSION
        except Exception:
            active = False
        if not active:
            return legacy_method(
                cls,
                candidate_root,
                token=token,
                api_version=api_version,
            )
        protocol = validate_runtime_contract(candidate_root)
        return cls(
            protocol.protocol_version,
            protocol.inspector_repository,
            protocol.inspector_repository_id,
            protocol.inspector_commit_sha,
            protocol.required_check_names,
        )

    legacy.ProtocolContext.from_verified_repository = classmethod(from_repo)
    legacy.ProtocolContext.from_repository = classmethod(
        lambda cls, repository_directory=ROOT: from_repo(
            cls, repository_directory
        )
    )
    legacy.ASSESSMENT_SCHEMA = (
        ROOT / "protocols/v1.13.0/schemas/review-assessment.schema.json"
    )
    legacy.assemble_review_package = assemble_review_package
