from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .diagnostics import Diagnostic

REGISTRY_PATH = Path("planning/tasks/task-registry.v1.json")
SCOPE_PATH = Path("planning/scopes/PINS-VERIFIED-REVIEW-001.scope.json")
IMPACT_PATH = Path("planning/progress/impacts/PINS-VERIFIED-REVIEW-001.implementation.json")
NEXT_WORK_PATH = Path("planning/NEXT_WORK.md")
PLAN_PATH = Path("planning/PR_INSPECTOR_EXECUTION_PLAN.md")
BASELINE_PATH = Path("planning/PR_INSPECTOR_EXECUTION_PLAN_BASELINE.md")
SCHEMAS = {
    "registry": Path("schemas/planning/task-registry.v1.schema.json"),
    "scope": Path("schemas/planning/work-package-scope.v1.schema.json"),
    "impact": Path("schemas/planning/progress-impact.v1.schema.json"),
}
PLANNING_ALLOWED_EXACT = {
    ".github/workflows/validate-repository.yml",
    "AGENTS.md",
    "README.md",
    "docs/MAINTENANCE.md",
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
}
PLANNING_ALLOWED_PREFIXES = ("planning/", "schemas/planning/", "tests/fixtures/planning/")
_PINNED_GOVERNANCE_EXCLUSION = "/".join(("governance", "aigov")) + "/**"
PLANNING_REQUIRED_EXCLUDED = {
    "CURRENT_VERSION",
    _PINNED_GOVERNANCE_EXCLUSION,
    "protocol-manifest.yaml",
    "protocols/**",
    "release-locks/**",
}
PLANNING_REQUIRED_FORBIDDEN = {
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
PROTOCOL_ALLOWED_EXACT = {
    ".github/workflows/export-pr21-rerepair.yml",
    ".github/workflows/validate-repository.yml",
    "CHANGELOG.md",
    "CURRENT_VERSION",
    "README.md",
    "protocol-manifest.yaml",
    "pyproject.toml",
}
PROTOCOL_ALLOWED_PREFIXES = (
    "docs/",
    "fixtures/behavioral-rules/",
    "planning/",
    "pr_inspector/",
    "protocols/v1.12.0/",
    "release-locks/",
    "schemas/planning/",
    "scripts/",
    "tests/",
)
PROTOCOL_REQUIRED_EXCLUDED = {
    _PINNED_GOVERNANCE_EXCLUSION,
    "protocols/v1.11.1/**",
    "release-locks/v1.11.1.sha256",
}
PROTOCOL_REQUIRED_FORBIDDEN = {
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
REQUIRED_REMAINING = {
    "exact_head_github_actions_validation",
    "independent_review_if_required_by_repository_policy",
    "owner_only_merge",
    "successful_push_validation_on_exact_main",
    "bounded_post_merge_lifecycle_reconciliation",
}

SCOPE_POLICIES = {
    "planning_infrastructure": {
        "allowed_exact": PLANNING_ALLOWED_EXACT,
        "allowed_prefixes": PLANNING_ALLOWED_PREFIXES,
        "required_excluded": PLANNING_REQUIRED_EXCLUDED,
        "required_forbidden": PLANNING_REQUIRED_FORBIDDEN,
    },
    "protocol_authority_migration": {
        "allowed_exact": PROTOCOL_ALLOWED_EXACT,
        "allowed_prefixes": PROTOCOL_ALLOWED_PREFIXES,
        "required_excluded": PROTOCOL_REQUIRED_EXCLUDED,
        "required_forbidden": PROTOCOL_REQUIRED_FORBIDDEN,
    },
}

NEXT_MARKERS = ("<!-- PINS:NEXT-WORK:BEGIN -->", "<!-- PINS:NEXT-WORK:END -->")
PLAN_MARKERS = ("<!-- PINS:PLAN-SNAPSHOT:BEGIN -->", "<!-- PINS:PLAN-SNAPSHOT:END -->")

_SCHEMA_ERROR = "PINS-REGISTRY-SCHEMA-INVALID"
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_SUPPORTED_GIT_STATUSES = {"A", "C", "D", "M", "R", "T"}
_WP_ACTIVE_STATES = {
    "ready",
    "implementing",
    "implemented_pending_exact_head_validation",
    "exact_head_validated",
    "merged",
    "post_merge_verified",
    "closed",
}
_WP_IMPLEMENTED_STATES = {
    "implemented_pending_exact_head_validation",
    "exact_head_validated",
    "merged",
    "post_merge_verified",
    "closed",
}
_WP_EXACT_HEAD_STATES = {"exact_head_validated", "merged", "post_merge_verified", "closed"}
_WP_MERGED_STATES = {"merged", "post_merge_verified", "closed"}
_WP_POST_MERGE_STATES = {"post_merge_verified", "closed"}
_WP_DEPENDENCY_COMPLETE_STATES = {"post_merge_verified", "closed"}
_COMPLETION_IMPACT_STATES = {"post_merge_verified", "closed", "complete"}
_EVIDENCE_TYPE_BY_STAGE = {
    "exact_head": "exact_head_ci",
    "merge": "merge",
    "post_merge": "post_merge_verification",
}


class DuplicateKeyError(ValueError):
    pass


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_strict(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)


def loads_json_strict(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_pairs)


def diagnostic(code: str, path: str, message: str) -> Diagnostic:
    return Diagnostic(code, path, message)


def canonical_scope_revision(scope: dict[str, Any]) -> str:
    payload = copy.deepcopy(scope)
    payload.pop("scope_revision", None)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def validate_repo_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return "path must be a non-empty string"
    if "\x00" in value:
        return "path contains a NUL byte"
    if "\\" in value:
        return "path contains a backslash"
    if value.startswith("/"):
        return "path must be repository-relative"
    parts = value.split("/")
    if any(not part for part in parts):
        return "path contains an empty segment"
    if any(part in {".", ".."} for part in parts):
        return "path contains a dot segment"
    if any("*" in part for part in parts):
        return "committed path must be exact"
    return None


def _pattern_error(value: str) -> str | None:
    candidate = value[:-3] if value.endswith("/**") else value
    return validate_repo_path(candidate)


def pattern_matches(pattern: str, path: str) -> bool:
    if pattern.endswith("/**"):
        root = pattern[:-3]
        return path == root or path.startswith(root + "/")
    return path == pattern


def _schema(instance: Any, schema: dict[str, Any], label: str) -> list[Diagnostic]:
    try:
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        errors = sorted(
            validator.iter_errors(instance),
            key=lambda error: [str(item) for item in error.absolute_path],
        )
    except Exception as exc:
        return [diagnostic(_SCHEMA_ERROR, f"/{label}/schema", str(exc))]
    return [
        diagnostic(
            _SCHEMA_ERROR,
            f"/{label}/" + "/".join(map(str, error.absolute_path)),
            error.message,
        )
        for error in errors
    ]


def _cycles(graph: dict[str, list[str]]) -> list[str]:
    active: list[str] = []
    finished: set[str] = set()

    def visit(node: str) -> list[str]:
        if node in active:
            return active[active.index(node) :] + [node]
        if node in finished:
            return []
        active.append(node)
        for dependency in graph.get(node, []):
            found = visit(dependency)
            if found:
                return found
        active.pop()
        finished.add(node)
        return []

    for node in sorted(graph):
        found = visit(node)
        if found:
            return found
    return []


def _records_for_refs(
    refs: list[str],
    evidence: dict[str, dict[str, Any]],
    path: str,
    output: list[Diagnostic],
    *,
    task_id: str,
    work_package_id: str | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for ref in refs:
        record = evidence.get(ref)
        if record is None:
            output.append(diagnostic("PINS-EVIDENCE-REFERENCE-INVALID", path, f"unresolved evidence ref {ref}"))
            continue
        if record["task_id"] != task_id:
            output.append(diagnostic("PINS-EVIDENCE-PROVENANCE-MISMATCH", path, f"{ref} belongs to another Task"))
        if work_package_id is not None and record["work_package_id"] != work_package_id:
            output.append(
                diagnostic(
                    "PINS-EVIDENCE-PROVENANCE-MISMATCH",
                    path,
                    f"{ref} belongs to another Work Package",
                )
            )
        records.append(record)
    return records


def _record_types(records: list[dict[str, Any]]) -> set[str]:
    return {record["evidence_type"] for record in records}


def _task_registry_completion_eligible(
    task_id: str,
    tasks: dict[str, dict[str, Any]],
    packages: dict[str, dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
) -> bool:
    task = tasks.get(task_id)
    if task is None or task["status"] != "complete" or not task["completion_claimed"]:
        return False
    owned = [package for package in packages.values() if package["task_id"] == task_id]
    if not owned or any(package["status"] not in _WP_POST_MERGE_STATES for package in owned):
        return False
    task_refs = set(task["evidence_refs"])
    for package in owned:
        records = [evidence.get(ref) for ref in package["evidence_refs"]]
        if any(record is None for record in records):
            return False
        typed = [record for record in records if record is not None]
        types = _record_types(typed)
        if not {"exact_head_ci", "merge", "post_merge_verification"} <= types:
            return False
        post_ids = {
            record["evidence_id"]
            for record in typed
            if record["evidence_type"] == "post_merge_verification"
        }
        if not post_ids or not post_ids <= task_refs:
            return False
    return True



__all__ = [name for name in globals() if not name.startswith("__")]
