from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

ACTIVE_VERSION = "v1.13.1"
REGISTRY_PATH = Path("planning/tasks/task-registry.v1.json")
_PINNED_GOVERNANCE_EXCLUSION = "/".join(("governance", "aigov")) + "/**"

_PLANNING_ALLOWED_EXACT = frozenset(
    {
        ".github/workflows/validate-repository.yml",
        "AGENTS.md",
        "README.md",
        "docs/MAINTENANCE.md",
        "pr_inspector/planning_authority.py",
        "pr_inspector/planning_governance.py",
        "pr_inspector/planning_governance_artifacts.py",
        "pr_inspector/planning_governance_base.py",
        "pr_inspector/planning_governance_git.py",
        "pr_inspector/planning_governance_registry.py",
        "pr_inspector/planning_governance_repository.py",
        "pr_inspector/repository.py",
        "scripts/validate_planning_governance.py",
        "scripts/validate_repository_v2.py",
        "tests/test_planning_governance.py",
        "tests/test_planning_governance_authority.py",
        "tests/test_v1_13_planning_governance.py",
    }
)
_PLANNING_ALLOWED_PREFIXES = (
    "planning/",
    "schemas/planning/",
    "tests/fixtures/planning/",
)
_PLANNING_REQUIRED_EXCLUDED = frozenset(
    {
        "CURRENT_VERSION",
        _PINNED_GOVERNANCE_EXCLUSION,
        "protocol-manifest.yaml",
        "protocols/**",
        "release-locks/**",
    }
)
_PLANNING_REQUIRED_FORBIDDEN = frozenset(
    {
        "AIGOV adoption",
        "AIGOV implementation",
        "AIGOV activation",
        "Receipt publication activation",
        "active protocol behavior",
        "auto-merge",
        "branch protection",
        "bypass configuration",
        "deployment",
        "force push",
        "history rewrite",
        "merge",
        "permissions",
        "release",
        "repository settings",
        "Rulesets",
        "teams",
    }
)

_PROTOCOL_ALLOWED_EXACT = frozenset(
    {
        ".github/workflows/export-pr21-rerepair.yml",
        ".github/workflows/validate-repository.yml",
        "AGENTS.md",
        "BOOTSTRAP.md",
        "CHANGELOG.md",
        "CURRENT_VERSION",
        "README.md",
        "protocol-manifest.yaml",
        "pyproject.toml",
    }
)
_PROTOCOL_ALLOWED_PREFIXES = (
    "docs/",
    "fixtures/behavioral-rules/",
    "planning/",
    "pr_inspector/",
    "protocols/v1.13.0/",
    "protocols/v1.13.1/",
    "release-locks/",
    "schemas/planning/",
    "scripts/",
    "tests/",
)
_PROTOCOL_REQUIRED_EXCLUDED = frozenset(
    {
        _PINNED_GOVERNANCE_EXCLUSION,
        "protocols/v1.12.0/**",
        "release-locks/v1.12.0.sha256",
    }
)
_PROTOCOL_REQUIRED_FORBIDDEN = frozenset(
    {
        "AIGOV activation",
        "Receipt publication activation",
        "auto-merge",
        "branch protection",
        "bypass configuration",
        "deployment",
        "external repository modification",
        "force push",
        "historical protocol mutation",
        "history rewrite",
        "merge",
        "permissions",
        "repository settings",
        "Rulesets",
        "teams",
    }
)


class PlanningAuthorityError(ValueError):
    def __init__(self, code: str, path: str, message: str):
        super().__init__(f"{code} {path}: {message}")
        self.code = code
        self.path = path
        self.message = message


@dataclass(frozen=True)
class ScopePolicy:
    allowed_exact: frozenset[str]
    allowed_prefixes: tuple[str, ...]
    required_excluded: frozenset[str]
    required_forbidden: frozenset[str]


@dataclass(frozen=True)
class PlanningAuthority:
    active_version: str
    planning_policy: ScopePolicy
    protocol_policies: Mapping[str, ScopePolicy]


@dataclass(frozen=True)
class CurrentPlanningArtifacts:
    work_package_id: str
    task_id: str
    scope_ref: str
    impact_refs: tuple[str, ...]


def _freeze_scope_policies(
    values: dict[str, ScopePolicy],
) -> Mapping[str, ScopePolicy]:
    return MappingProxyType(dict(values))


_V1_12_PROTOCOL_POLICY = ScopePolicy(
    frozenset(
        {
            ".github/workflows/export-pr21-rerepair.yml",
            ".github/workflows/validate-repository.yml",
            "CHANGELOG.md",
            "CURRENT_VERSION",
            "README.md",
            "protocol-manifest.yaml",
            "pyproject.toml",
        }
    ),
    (
        "docs/",
        "fixtures/behavioral-rules/",
        "planning/",
        "pr_inspector/",
        "protocols/v1.12.0/",
        "release-locks/",
        "schemas/planning/",
        "scripts/",
        "tests/",
    ),
    frozenset(
        {
            _PINNED_GOVERNANCE_EXCLUSION,
            "protocols/v1.11.1/**",
            "release-locks/v1.11.1.sha256",
        }
    ),
    _PROTOCOL_REQUIRED_FORBIDDEN,
)


_V1_13_PROTOCOL_POLICY = ScopePolicy(
    _PROTOCOL_ALLOWED_EXACT,
    _PROTOCOL_ALLOWED_PREFIXES,
    _PROTOCOL_REQUIRED_EXCLUDED,
    _PROTOCOL_REQUIRED_FORBIDDEN,
)


_V1_13_AUTHORITY = PlanningAuthority(
    active_version=ACTIVE_VERSION,
    planning_policy=ScopePolicy(
        _PLANNING_ALLOWED_EXACT,
        _PLANNING_ALLOWED_PREFIXES,
        _PLANNING_REQUIRED_EXCLUDED,
        _PLANNING_REQUIRED_FORBIDDEN,
    ),
    protocol_policies=_freeze_scope_policies(
        {
            "v1.12.0": _V1_12_PROTOCOL_POLICY,
            "v1.13.0": _V1_13_PROTOCOL_POLICY,
            "v1.13.1": _V1_13_PROTOCOL_POLICY,
        }
    ),
)


def _load_registry(root: Path) -> dict[str, Any]:
    try:
        value = json.loads((root / REGISTRY_PATH).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PlanningAuthorityError(
            "PINS-PLANNING-AUTHORITY-001",
            f"/{REGISTRY_PATH.as_posix()}",
            str(exc),
        ) from exc
    if not isinstance(value, dict):
        raise PlanningAuthorityError(
            "PINS-PLANNING-AUTHORITY-001",
            f"/{REGISTRY_PATH.as_posix()}",
            "registry root must be an object",
        )
    return value


def resolve_planning_authority(root: Path) -> PlanningAuthority:
    root = Path(root).resolve()
    try:
        active_version = (root / "CURRENT_VERSION").read_text(
            encoding="utf-8"
        ).strip()
    except (OSError, UnicodeDecodeError) as exc:
        raise PlanningAuthorityError(
            "PINS-PLANNING-AUTHORITY-001",
            "/CURRENT_VERSION",
            str(exc),
        ) from exc
    if active_version != ACTIVE_VERSION:
        raise PlanningAuthorityError(
            "PINS-PLANNING-AUTHORITY-002",
            "/CURRENT_VERSION",
            f"unsupported active planning policy version: {active_version!r}",
        )
    return _V1_13_AUTHORITY


def resolve_current_planning_artifacts(
    root: Path,
    registry: dict[str, Any] | None = None,
) -> CurrentPlanningArtifacts:
    root = Path(root).resolve()
    value = _load_registry(root) if registry is None else registry
    packages = value.get("work_packages")
    current_id = value.get("current_work_package_id")
    if not isinstance(packages, list) or not isinstance(current_id, str):
        raise PlanningAuthorityError(
            "PINS-PLANNING-BINDING-001",
            "/work_packages",
            "registry must declare work_packages and current_work_package_id",
        )
    current_flags = [
        item
        for item in packages
        if isinstance(item, dict) and item.get("current") is True
    ]
    by_id = [
        item
        for item in packages
        if isinstance(item, dict)
        and item.get("work_package_id") == current_id
    ]
    if len(current_flags) != 1 or len(by_id) != 1 or current_flags[0] is not by_id[0]:
        raise PlanningAuthorityError(
            "PINS-PLANNING-BINDING-002",
            "/current_work_package_id",
            "current Work Package identity is missing, ambiguous, or inconsistent",
        )
    package = by_id[0]
    scope_ref = package.get("scope_ref")
    impact_refs = package.get("impact_refs")
    task_id = package.get("task_id")
    if (
        not isinstance(scope_ref, str)
        or not scope_ref.startswith("planning/scopes/")
        or not isinstance(impact_refs, list)
        or not impact_refs
        or any(
            not isinstance(item, str)
            or not item.startswith("planning/progress/impacts/")
            for item in impact_refs
        )
        or len(impact_refs) != len(set(impact_refs))
        or not isinstance(task_id, str)
    ):
        raise PlanningAuthorityError(
            "PINS-PLANNING-BINDING-003",
            f"/work_packages/{current_id}",
            "current Work Package has invalid scope_ref, impact_refs, or task_id",
        )
    return CurrentPlanningArtifacts(
        work_package_id=current_id,
        task_id=task_id,
        scope_ref=scope_ref,
        impact_refs=tuple(impact_refs),
    )


def _scope_protocol_versions(scope: dict[str, Any]) -> set[str]:
    versions: set[str] = set()
    for value in (
        *scope.get("committed_paths", []),
        *scope.get("deleted_paths", []),
    ):
        if not isinstance(value, str) or not value.startswith("protocols/"):
            continue
        parts = value.split("/", 2)
        if len(parts) >= 2:
            versions.add(parts[1])
    return versions


def resolve_scope_policy(
    root: Path,
    registry: dict[str, Any],
    scope: dict[str, Any],
) -> ScopePolicy:
    authority = resolve_planning_authority(root)
    change_class = scope.get("change_class")
    if change_class == "planning_infrastructure":
        return authority.planning_policy
    if change_class != "protocol_authority_migration":
        raise PlanningAuthorityError(
            "PINS-PLANNING-AUTHORITY-003",
            "/scope/change_class",
            f"unsupported planning change class: {change_class!r}",
        )

    current = resolve_current_planning_artifacts(root, registry)
    work_package_id = scope.get("work_package_id")
    if work_package_id == current.work_package_id:
        version = authority.active_version
    else:
        packages = {
            item.get("work_package_id"): item
            for item in registry.get("work_packages", [])
            if isinstance(item, dict)
        }
        package = packages.get(work_package_id)
        if not isinstance(package, dict) or package.get("current") is True:
            raise PlanningAuthorityError(
                "PINS-PLANNING-AUTHORITY-004",
                "/scope/work_package_id",
                "historical Scope is not bound to a non-current Work Package",
            )
        versions = _scope_protocol_versions(scope)
        if len(versions) != 1:
            raise PlanningAuthorityError(
                "PINS-PLANNING-AUTHORITY-004",
                "/scope/committed_paths",
                "historical protocol Scope must identify exactly one version",
            )
        version = next(iter(versions))

    policy = authority.protocol_policies.get(version)
    if policy is None:
        raise PlanningAuthorityError(
            "PINS-PLANNING-AUTHORITY-003",
            "/scope/committed_paths",
            f"unsupported protocol Scope version: {version!r}",
        )
    return policy
