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
SCOPE_PATH = Path("planning/scopes/PINS-PLAN-001.scope.json")
IMPACT_PATH = Path("planning/progress/impacts/PINS-PLAN-001.implementation.json")
NEXT_WORK_PATH = Path("planning/NEXT_WORK.md")
PLAN_PATH = Path("planning/PR_INSPECTOR_EXECUTION_PLAN.md")
BASELINE_PATH = Path("planning/PR_INSPECTOR_EXECUTION_PLAN_BASELINE.md")
SCHEMAS = {
    "registry": Path("schemas/planning/task-registry.v1.schema.json"),
    "scope": Path("schemas/planning/work-package-scope.v1.schema.json"),
    "impact": Path("schemas/planning/progress-impact.v1.schema.json"),
}
ALLOWED_EXACT = {
    ".github/workflows/validate-repository.yml",
    "AGENTS.md",
    "README.md",
    "docs/MAINTENANCE.md",
    "pr_inspector/planning_governance.py",
    "pr_inspector/repository.py",
    "scripts/validate_planning_governance.py",
    "scripts/validate_repository_v2.py",
    "tests/test_planning_governance.py",
}
ALLOWED_PREFIXES = ("planning/", "schemas/planning/", "tests/fixtures/planning/")
_PINNED_GOVERNANCE_EXCLUSION = "/".join(("governance", "aigov")) + "/**"
REQUIRED_EXCLUDED = {
    "CURRENT_VERSION",
    _PINNED_GOVERNANCE_EXCLUSION,
    "protocol-manifest.yaml",
    "protocols/**",
    "release-locks/**",
}
REQUIRED_FORBIDDEN = {
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
REQUIRED_REMAINING = {
    "exact_head_github_actions_validation",
    "independent_review_if_required_by_repository_policy",
    "owner_only_merge",
    "successful_push_validation_on_exact_main",
    "bounded_post_merge_lifecycle_reconciliation",
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
_EVIDENCE_PREFIXES = {
    "exact_head": "exact_head:",
    "merge": "merge:",
    "post_merge": "post_merge:",
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


def _has_evidence(refs: list[str], kind: str) -> bool:
    prefix = _EVIDENCE_PREFIXES[kind]
    return any(ref.startswith(prefix) and len(ref) > len(prefix) for ref in refs)


def validate_registry(registry: dict[str, Any], schema: dict[str, Any]) -> list[Diagnostic]:
    output = _schema(registry, schema, "registry")
    if output:
        return output

    seen: dict[str, str] = {}
    for collection, key in (
        ("programs", "program_id"),
        ("initiatives", "initiative_id"),
        ("tasks", "task_id"),
        ("work_packages", "work_package_id"),
    ):
        for index, item in enumerate(registry[collection]):
            identifier = item[key]
            path = f"/{collection}/{index}/{key}"
            if identifier in seen:
                output.append(diagnostic("PINS-DUPLICATE-ID", path, f"also appears at {seen[identifier]}"))
            else:
                seen[identifier] = path

    programs = {item["program_id"]: item for item in registry["programs"]}
    initiatives = {item["initiative_id"]: item for item in registry["initiatives"]}
    tasks = {item["task_id"]: item for item in registry["tasks"]}
    packages = {item["work_package_id"]: item for item in registry["work_packages"]}

    for index, item in enumerate(registry["initiatives"]):
        if item["program_id"] not in programs:
            output.append(diagnostic("PINS-UNKNOWN-PARENT", f"/initiatives/{index}/program_id", item["program_id"]))

    for index, item in enumerate(registry["tasks"]):
        path = f"/tasks/{index}"
        if item["initiative_id"] not in initiatives:
            output.append(diagnostic("PINS-UNKNOWN-PARENT", path + "/initiative_id", item["initiative_id"]))
        dependencies = item["depends_on"]
        if len(dependencies) != len(set(dependencies)):
            output.append(diagnostic("PINS-UNKNOWN-DEPENDENCY", path + "/depends_on", "duplicate dependency"))
        for dependency in dependencies:
            if dependency == item["task_id"]:
                output.append(diagnostic("PINS-DEPENDENCY-CYCLE", path + "/depends_on", "self-dependency"))
            elif dependency not in tasks:
                output.append(diagnostic("PINS-UNKNOWN-DEPENDENCY", path + "/depends_on", dependency))
        if item["status"] in {"authorized", "in_progress", "implemented", "complete"} and not item["implementation_authorized"]:
            output.append(diagnostic("PINS-UNAUTHORIZED-IMPLEMENTATION", path, "state requires authorization"))
        incomplete = [dependency for dependency in dependencies if tasks.get(dependency, {}).get("status") != "complete"]
        if item["status"] in {"in_progress", "implemented", "complete"} and incomplete:
            output.append(diagnostic("PINS-DEPENDENCY-NOT-COMPLETE", path + "/depends_on", ", ".join(incomplete)))
        if item["status"] == "complete" and (not item["completion_claimed"] or not item["evidence_refs"]):
            output.append(diagnostic("PINS-FALSE-COMPLETION", path, "completion requires evidence"))
        if item["status"] != "complete" and item["completion_claimed"]:
            output.append(diagnostic("PINS-FALSE-COMPLETION", path, "completion claimed before complete state"))

    task_graph = {
        task_id: [dependency for dependency in task["depends_on"] if dependency in tasks]
        for task_id, task in tasks.items()
    }
    task_cycle = _cycles(task_graph)
    if task_cycle:
        output.append(diagnostic("PINS-DEPENDENCY-CYCLE", "/tasks", " -> ".join(task_cycle)))

    foundation = tasks.get("PINS-PLAN-001")
    if foundation and foundation["status"] != "complete":
        for index, item in enumerate(registry["tasks"]):
            is_future_domain_task = item["task_id"].startswith("PINS-AIGOV-")
            is_started = item["status"] not in {"registered", "blocked"}
            if is_future_domain_task and (item["implementation_authorized"] or is_started):
                output.append(
                    diagnostic(
                        "PINS-UNAUTHORIZED-IMPLEMENTATION",
                        f"/tasks/{index}",
                        "future AIGOV task is not eligible",
                    )
                )

    for index, item in enumerate(registry["work_packages"]):
        path = f"/work_packages/{index}"
        task = tasks.get(item["task_id"])
        if task is None:
            output.append(diagnostic("PINS-UNKNOWN-PARENT", path + "/task_id", item["task_id"]))

        dependencies = item["depends_on"]
        if len(dependencies) != len(set(dependencies)):
            output.append(diagnostic("PINS-UNKNOWN-DEPENDENCY", path + "/depends_on", "duplicate dependency"))
        for dependency in dependencies:
            if dependency == item["work_package_id"]:
                output.append(diagnostic("PINS-DEPENDENCY-CYCLE", path + "/depends_on", "self-dependency"))
            elif dependency not in packages:
                output.append(diagnostic("PINS-UNKNOWN-DEPENDENCY", path + "/depends_on", dependency))

        incomplete_packages = [
            dependency
            for dependency in dependencies
            if packages.get(dependency, {}).get("status") not in _WP_DEPENDENCY_COMPLETE_STATES
        ]
        if item["status"] == "dependency_blocked" and not incomplete_packages:
            output.append(
                diagnostic(
                    "PINS-WP-LIFECYCLE-INVALID",
                    path + "/status",
                    "dependency_blocked requires an incomplete Work Package dependency",
                )
            )
        if item["status"] in _WP_ACTIVE_STATES and incomplete_packages:
            output.append(
                diagnostic(
                    "PINS-DEPENDENCY-NOT-COMPLETE",
                    path + "/depends_on",
                    ", ".join(incomplete_packages),
                )
            )

        if task is not None and item["status"] in _WP_ACTIVE_STATES:
            incomplete_tasks = [
                dependency
                for dependency in task["depends_on"]
                if tasks.get(dependency, {}).get("status") != "complete"
            ]
            if not task["implementation_authorized"]:
                output.append(diagnostic("PINS-UNAUTHORIZED-IMPLEMENTATION", path, "Task is not authorized"))
            if incomplete_tasks:
                output.append(diagnostic("PINS-DEPENDENCY-NOT-COMPLETE", path, ", ".join(incomplete_tasks)))

        refs = item["evidence_refs"]
        if item["status"] in _WP_IMPLEMENTED_STATES and not item["impact_refs"]:
            output.append(diagnostic("PINS-WP-EVIDENCE-MISSING", path + "/impact_refs", "implemented state requires Impact evidence"))
        for kind, states in (
            ("exact_head", _WP_EXACT_HEAD_STATES),
            ("merge", _WP_MERGED_STATES),
            ("post_merge", _WP_POST_MERGE_STATES),
        ):
            has_evidence = _has_evidence(refs, kind)
            if item["status"] in states and not has_evidence:
                output.append(
                    diagnostic(
                        "PINS-WP-EVIDENCE-MISSING",
                        path + "/evidence_refs",
                        f"{item['status']} requires {kind} evidence",
                    )
                )
            if item["status"] not in states and has_evidence:
                output.append(
                    diagnostic(
                        "PINS-WP-LIFECYCLE-INVALID",
                        path + "/evidence_refs",
                        f"{kind} evidence is ahead of lifecycle state {item['status']}",
                    )
                )

    package_graph = {
        package_id: [dependency for dependency in package["depends_on"] if dependency in packages]
        for package_id, package in packages.items()
    }
    package_cycle = _cycles(package_graph)
    if package_cycle:
        output.append(diagnostic("PINS-DEPENDENCY-CYCLE", "/work_packages", " -> ".join(package_cycle)))

    current = [item for item in registry["work_packages"] if item["current"]]
    current_id = registry["current_work_package_id"]
    invalid_current = (
        len(current) != 1
        or current_id not in packages
        or (current and current[0]["work_package_id"] != current_id)
        or (current and current[0]["status"] == "closed")
    )
    if invalid_current:
        output.append(
            diagnostic(
                "PINS-CURRENT-WORK-PACKAGE-INVALID",
                "/current_work_package_id",
                "exactly one existing non-closed Work Package must be current",
            )
        )
    return sorted(set(output))


def validate_scope(
    scope: dict[str, Any],
    schema: dict[str, Any],
    registry: dict[str, Any],
) -> list[Diagnostic]:
    output = _schema(scope, schema, "scope")
    if output:
        return output
    if scope["scope_revision"] != canonical_scope_revision(scope):
        output.append(diagnostic("PINS-SCOPE-REVISION-MISMATCH", "/scope/scope_revision", "canonical hash mismatch"))

    programs = {item["program_id"]: item for item in registry["programs"]}
    initiatives = {item["initiative_id"]: item for item in registry["initiatives"]}
    tasks = {item["task_id"]: item for item in registry["tasks"]}
    packages = {item["work_package_id"]: item for item in registry["work_packages"]}
    known = {
        "program_id": programs,
        "initiative_id": initiatives,
        "task_id": tasks,
        "work_package_id": packages,
    }
    for field, identifiers in known.items():
        if scope[field] not in identifiers:
            output.append(diagnostic("PINS-UNKNOWN-PARENT", f"/scope/{field}", scope[field]))

    program = programs.get(scope["program_id"])
    initiative = initiatives.get(scope["initiative_id"])
    task = tasks.get(scope["task_id"])
    package = packages.get(scope["work_package_id"])
    if program and initiative and initiative["program_id"] != program["program_id"]:
        output.append(diagnostic("PINS-CROSS-FILE-BINDING-MISMATCH", "/scope/initiative_id", "Initiative is not bound to Scope Program"))
    if initiative and task and task["initiative_id"] != initiative["initiative_id"]:
        output.append(diagnostic("PINS-CROSS-FILE-BINDING-MISMATCH", "/scope/task_id", "Task is not bound to Scope Initiative"))
    if task and package and package["task_id"] != task["task_id"]:
        output.append(diagnostic("PINS-CROSS-FILE-BINDING-MISMATCH", "/scope/work_package_id", "Work Package is not bound to Scope Task"))
    if package and package["scope_ref"] != SCOPE_PATH.as_posix():
        output.append(
            diagnostic(
                "PINS-CROSS-FILE-BINDING-MISMATCH",
                "/scope/work_package_id",
                f"Work Package scope_ref must equal {SCOPE_PATH.as_posix()}",
            )
        )

    paths = scope["committed_paths"]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        output.append(diagnostic("PINS-SCOPE-PATH-INVALID", "/scope/committed_paths", "paths must be unique and sorted"))
    for path in paths:
        error = validate_repo_path(path)
        if error:
            output.append(diagnostic("PINS-SCOPE-PATH-INVALID", "/scope/committed_paths", f"{path}: {error}"))
        elif path not in ALLOWED_EXACT and not path.startswith(ALLOWED_PREFIXES):
            output.append(diagnostic("PINS-SCOPE-FORBIDDEN-PATH", f"/{path}", "path is outside the authorized boundary"))

    if not REQUIRED_EXCLUDED <= set(scope["excluded_paths"]):
        output.append(diagnostic("PINS-SCOPE-FORBIDDEN-PATH", "/scope/excluded_paths", "required exclusions are missing"))
    if not REQUIRED_FORBIDDEN <= set(scope["forbidden_changes"]):
        output.append(diagnostic("PINS-SCOPE-FORBIDDEN-PATH", "/scope/forbidden_changes", "required forbidden operations are missing"))
    for pattern in scope["excluded_paths"]:
        error = _pattern_error(pattern)
        if error:
            output.append(diagnostic("PINS-SCOPE-PATH-INVALID", "/scope/excluded_paths", f"{pattern}: {error}"))
        elif any(pattern_matches(pattern, path) for path in paths):
            output.append(diagnostic("PINS-SCOPE-FORBIDDEN-PATH", "/scope/committed_paths", f"path matches {pattern}"))
    return sorted(set(output))


def validate_impact(
    impact: dict[str, Any],
    schema: dict[str, Any],
    scope: dict[str, Any],
    registry: dict[str, Any] | None = None,
) -> list[Diagnostic]:
    output = _schema(impact, schema, "impact")
    if output:
        return output
    for field in (
        "program_id",
        "initiative_id",
        "task_id",
        "work_package_id",
        "scope_id",
        "repository",
        "base_sha",
    ):
        if impact[field] != scope[field]:
            output.append(diagnostic("PINS-IMPACT-SCOPE-MISMATCH", f"/impact/{field}", f"expected {scope[field]}"))
    if registry is not None:
        packages = {item["work_package_id"]: item for item in registry["work_packages"]}
        package = packages.get(impact["work_package_id"])
        if package is None:
            output.append(diagnostic("PINS-CROSS-FILE-BINDING-MISMATCH", "/impact/work_package_id", "Impact Work Package is not registered"))
        else:
            expected_ref = IMPACT_PATH.as_posix()
            if package["impact_refs"] != [expected_ref]:
                output.append(
                    diagnostic(
                        "PINS-CROSS-FILE-BINDING-MISMATCH",
                        "/impact/work_package_id",
                        f"Work Package impact_refs must bind exactly to {expected_ref}",
                    )
                )
    if impact["sequence"] != 1 or impact["previous_impact_ref"] is not None:
        output.append(diagnostic("PINS-IMPACT-SEQUENCE-MISMATCH", "/impact/sequence", "bootstrap Impact must start at sequence 1"))
    if impact["changed_paths"] != scope["committed_paths"]:
        output.append(diagnostic("PINS-IMPACT-SCOPE-MISMATCH", "/impact/changed_paths", "must equal Scope paths"))
    if not impact["material_progress"] or impact["zero_progress"]:
        output.append(diagnostic("PINS-IMPACT-FALSE-PROGRESS", "/impact", "material progress must be true and zero progress false"))
    if impact["completion_claimed"] or impact["state_after"] == "complete":
        output.append(diagnostic("PINS-IMPACT-FALSE-COMPLETION", "/impact", "completion is not available"))
    missing = REQUIRED_REMAINING - set(impact["remaining_obligations"])
    if missing or impact["next_lifecycle_action"] != "exact_head_validation":
        output.append(
            diagnostic(
                "PINS-IMPACT-FALSE-COMPLETION",
                "/impact/remaining_obligations",
                "required lifecycle obligations are missing or misordered",
            )
        )
    return sorted(set(output))


def extract_bounded_json(text: str, begin: str, end: str) -> dict[str, Any]:
    if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) >= text.index(end):
        raise ValueError("bounded markers must occur exactly once in order")
    payload = loads_json_strict(text.split(begin, 1)[1].split(end, 1)[0].strip())
    if not isinstance(payload, dict):
        raise ValueError("bounded payload must be an object")
    return payload


def expected_snapshot(
    registry: dict[str, Any],
    scope: dict[str, Any],
    impact: dict[str, Any],
) -> dict[str, Any]:
    package = next(item for item in registry["work_packages"] if item["current"])
    task = next(item for item in registry["tasks"] if item["task_id"] == package["task_id"])
    program = registry["programs"][0]
    return {
        "program_id": program["program_id"],
        "program_status": program["status"],
        "initiative_ids": sorted(item["initiative_id"] for item in registry["initiatives"]),
        "task_ids": sorted(item["task_id"] for item in registry["tasks"]),
        "current_work_package_id": package["work_package_id"],
        "current_task_id": task["task_id"],
        "current_task_status": task["status"],
        "current_work_package_status": package["status"],
        "scope_id": scope["scope_id"],
        "scope_revision": scope["scope_revision"],
        "next_lifecycle_action": impact["next_lifecycle_action"],
    }


def validate_markdown(
    root: Path,
    registry: dict[str, Any],
    scope: dict[str, Any],
    impact: dict[str, Any],
) -> list[Diagnostic]:
    output: list[Diagnostic] = []
    expected = expected_snapshot(registry, scope, impact)
    for path, markers, code in (
        (NEXT_WORK_PATH, NEXT_MARKERS, "PINS-DASHBOARD-REGISTRY-DRIFT"),
        (PLAN_PATH, PLAN_MARKERS, "PINS-PLAN-REGISTRY-DRIFT"),
    ):
        try:
            actual = extract_bounded_json((root / path).read_text(encoding="utf-8"), *markers)
            if actual != expected:
                raise ValueError("bounded snapshot differs from canonical state")
        except Exception as exc:
            output.append(diagnostic(code, f"/{path}", str(exc)))

    baseline = (root / BASELINE_PATH).read_text(encoding="utf-8")
    for phrase in (
        "documented != implemented",
        "registered != authorized",
        "implemented != exact-head validated",
        "CI green != Merge enforcement",
        "outside the active protocol `load_order`",
        "does not activate AIGOV",
        "Closed PR #33 remains closed and unmerged",
    ):
        if phrase not in baseline:
            output.append(diagnostic("PINS-PLAN-REGISTRY-DRIFT", f"/{BASELINE_PATH}", f"missing invariant: {phrase}"))
    return output


def _material(
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    registry = load_json_strict(root / REGISTRY_PATH)
    scope = load_json_strict(root / SCOPE_PATH)
    impact = load_json_strict(root / IMPACT_PATH)
    schemas = {name: load_json_strict(root / path) for name, path in SCHEMAS.items()}
    return registry, scope, impact, schemas


def validate_planning_repository(root: Path) -> list[Diagnostic]:
    required = [
        REGISTRY_PATH,
        SCOPE_PATH,
        IMPACT_PATH,
        NEXT_WORK_PATH,
        PLAN_PATH,
        BASELINE_PATH,
        *SCHEMAS.values(),
    ]
    missing = [path for path in required if not (root / path).is_file()]
    if missing:
        return [
            diagnostic(_SCHEMA_ERROR, f"/{path}", "required artifact is missing")
            for path in missing
        ]
    try:
        registry, scope, impact, schemas = _material(root)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
        return [diagnostic(_SCHEMA_ERROR, "/planning", str(exc))]

    output = validate_registry(registry, schemas["registry"])
    if output:
        return sorted(set(output))
    scope_output = validate_scope(scope, schemas["scope"], registry)
    output += scope_output
    if scope_output:
        return sorted(set(output))
    impact_output = validate_impact(impact, schemas["impact"], scope, registry)
    output += impact_output
    if impact_output:
        return sorted(set(output))
    output += validate_markdown(root, registry, scope, impact)
    for path in scope["committed_paths"]:
        if validate_repo_path(path) is None and not (root / path).is_file():
            output.append(diagnostic("PINS-SCOPE-DISCLOSURE-MISMATCH", f"/{path}", "declared path is missing"))
    return sorted(set(output))


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git failed")
    return result.stdout.strip()


def parse_git_name_status(raw: str) -> tuple[list[str], dict[str, str], list[Diagnostic]]:
    fields = raw.split("\x00")
    if fields and fields[-1] == "":
        fields.pop()
    paths: list[str] = []
    statuses: dict[str, str] = {}
    diagnostics: list[Diagnostic] = []
    index = 0
    while index < len(fields):
        token = fields[index]
        index += 1
        status = token[:1]
        path_count = 2 if status in {"C", "R"} else 1
        if not token or index + path_count > len(fields):
            diagnostics.append(diagnostic("PINS-GIT-STATUS-UNSUPPORTED", "/git/diff", f"malformed name-status record: {token!r}"))
            break
        record_paths = fields[index : index + path_count]
        index += path_count
        if status not in _SUPPORTED_GIT_STATUSES:
            diagnostics.append(
                diagnostic(
                    "PINS-GIT-STATUS-UNSUPPORTED",
                    "/git/diff",
                    f"unsupported Git status {token}",
                )
            )
        for path in record_paths:
            paths.append(path)
            statuses[path] = token
    return sorted(set(paths)), dict(sorted(statuses.items())), sorted(set(diagnostics))


def validate_git_diff(
    root: Path,
    authoritative_base_sha: str,
    head_sha: str,
) -> tuple[list[Diagnostic], dict[str, Any]]:
    output: list[Diagnostic] = []
    report: dict[str, Any] = {
        "authoritative_base_sha": authoritative_base_sha,
        "head_sha": head_sha,
        "declared_base_sha": None,
        "merge_base_sha": None,
        "actual_changed_paths": [],
        "changed_path_statuses": {},
        "declared_changed_paths": [],
        "status": "invalid",
    }
    try:
        scope = load_json_strict(root / SCOPE_PATH)
        if not isinstance(scope, dict):
            raise ValueError("Scope must be a JSON object")
        declared = scope.get("committed_paths", [])
        if not isinstance(declared, list):
            raise ValueError("Scope committed_paths must be an array")
        report["declared_base_sha"] = scope.get("base_sha")
        report["declared_changed_paths"] = declared

        if not _FULL_SHA.fullmatch(authoritative_base_sha):
            output.append(diagnostic("PINS-SCOPE-BASE-MISMATCH", "/git/base", "authoritative PR base must be an exact 40-character SHA"))
        if not _FULL_SHA.fullmatch(head_sha):
            output.append(diagnostic("PINS-SCOPE-DISCLOSURE-MISMATCH", "/git/head", "runtime Head must be an exact 40-character SHA"))
        if scope.get("base_sha") != authoritative_base_sha:
            output.append(
                diagnostic(
                    "PINS-SCOPE-BASE-MISMATCH",
                    "/scope/base_sha",
                    "declared base does not equal authoritative pull-request base",
                )
            )

        resolved_base = _git(root, "rev-parse", f"{authoritative_base_sha}^{{commit}}")
        resolved_head = _git(root, "rev-parse", f"{head_sha}^{{commit}}")
        checkout = _git(root, "rev-parse", "HEAD")
        if resolved_base != authoritative_base_sha:
            output.append(diagnostic("PINS-SCOPE-BASE-MISMATCH", "/git/base", f"resolved {resolved_base}"))
        if resolved_head != head_sha or checkout != head_sha:
            output.append(diagnostic("PINS-SCOPE-DISCLOSURE-MISMATCH", "/git/head", "runtime Head identity mismatch"))

        merge_base = _git(root, "merge-base", authoritative_base_sha, head_sha)
        report["merge_base_sha"] = merge_base
        if merge_base != authoritative_base_sha:
            output.append(
                diagnostic(
                    "PINS-SCOPE-BASE-MISMATCH",
                    "/git/merge-base",
                    f"authoritative base is not the exact merge base; observed {merge_base}",
                )
            )
        try:
            _git(root, "merge-base", "--is-ancestor", authoritative_base_sha, head_sha)
        except RuntimeError:
            output.append(
                diagnostic(
                    "PINS-SCOPE-BASE-MISMATCH",
                    "/git/ancestry",
                    "authoritative base is not an ancestor of Head",
                )
            )

        raw = _git(
            root,
            "diff",
            "--name-status",
            "-z",
            "--find-renames",
            "--find-copies",
            f"{authoritative_base_sha}..{head_sha}",
        )
        actual, statuses, status_diagnostics = parse_git_name_status(raw)
        output += status_diagnostics
    except Exception as exc:
        output.append(diagnostic("PINS-SCOPE-BASE-MISMATCH", "/git", str(exc)))
        return sorted(set(output)), report

    report["actual_changed_paths"] = actual
    report["changed_path_statuses"] = statuses
    for path in actual:
        error = validate_repo_path(path)
        if error:
            output.append(diagnostic("PINS-SCOPE-PATH-INVALID", f"/{path}", error))
    for path in sorted(set(actual) - set(declared)):
        output.append(diagnostic("PINS-SCOPE-UNDECLARED-PATH", f"/{path}", "changed path is not declared"))
    for path in sorted(set(declared) - set(actual)):
        output.append(diagnostic("PINS-SCOPE-DECLARED-PATH-UNCHANGED", f"/{path}", "declared path is unchanged"))
    for path in actual:
        for pattern in scope.get("excluded_paths", []):
            if _pattern_error(pattern) is None and pattern_matches(pattern, path):
                output.append(diagnostic("PINS-SCOPE-FORBIDDEN-PATH", f"/{path}", f"matches {pattern}"))
    if actual != declared:
        output.append(diagnostic("PINS-SCOPE-DISCLOSURE-MISMATCH", "/git/diff", "actual paths differ from declared paths"))
    if not output:
        report["status"] = "valid"
    return sorted(set(output)), report
