from __future__ import annotations

import copy
import hashlib
import json
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
    ".github/workflows/validate-repository.yml", "AGENTS.md", "README.md",
    "docs/MAINTENANCE.md", "pr_inspector/planning_governance.py",
    "pr_inspector/repository.py", "scripts/validate_planning_governance.py",
    "scripts/validate_repository_v2.py", "tests/test_planning_governance.py",
}
ALLOWED_PREFIXES = ("planning/", "schemas/planning/", "tests/fixtures/planning/")
REQUIRED_EXCLUDED = {"CURRENT_VERSION", "governance/aigov/**", "protocol-manifest.yaml", "protocols/**", "release-locks/**"}
REQUIRED_FORBIDDEN = {
    "AIGOV adoption", "AIGOV implementation", "AIGOV activation",
    "Receipt publication activation", "active protocol behavior", "auto-merge",
    "branch protection", "bypass configuration", "deployment", "force push",
    "history rewrite", "merge", "permissions", "release", "repository settings",
    "Rulesets", "teams",
}
REQUIRED_REMAINING = {
    "exact_head_github_actions_validation",
    "independent_review_if_required_by_repository_policy", "owner_only_merge",
    "successful_push_validation_on_exact_main",
    "bounded_post_merge_lifecycle_reconciliation",
}
NEXT_MARKERS = ("<!-- PINS:NEXT-WORK:BEGIN -->", "<!-- PINS:NEXT-WORK:END -->")
PLAN_MARKERS = ("<!-- PINS:PLAN-SNAPSHOT:BEGIN -->", "<!-- PINS:PLAN-SNAPSHOT:END -->")


class DuplicateKeyError(ValueError):
    pass


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        if key in out:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_json_strict(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)


def loads_json_strict(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_pairs)


def diagnostic(code: str, path: str, message: str) -> Diagnostic:
    return Diagnostic(code, path, message)


def canonical_scope_revision(scope: dict[str, Any]) -> str:
    payload = copy.deepcopy(scope)
    payload.pop("scope_revision", None)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


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
    return validate_repo_path(value[:-3] if value.endswith("/**") else value)


def pattern_matches(pattern: str, path: str) -> bool:
    if pattern.endswith("/**"):
        root = pattern[:-3]
        return path == root or path.startswith(root + "/")
    return path == pattern


def _schema(instance: Any, schema: dict[str, Any], label: str) -> list[Diagnostic]:
    try:
        Draft202012Validator.check_schema(schema)
        errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.absolute_path))
    except Exception as exc:
        return [diagnostic("PINS-REGISTRY-SCHEMA-INVALID", f"/{label}/schema", str(exc))]
    return [diagnostic("PINS-REGISTRY-SCHEMA-INVALID", f"/{label}/" + "/".join(map(str, e.absolute_path)), e.message) for e in errors]


def _cycles(graph: dict[str, list[str]]) -> list[str]:
    active: list[str] = []
    done: set[str] = set()
    def visit(node: str) -> list[str]:
        if node in active:
            return active[active.index(node):] + [node]
        if node in done:
            return []
        active.append(node)
        for dep in graph.get(node, []):
            found = visit(dep)
            if found:
                return found
        active.pop(); done.add(node)
        return []
    for node in sorted(graph):
        found = visit(node)
        if found:
            return found
    return []


def validate_registry(registry: dict[str, Any], schema: dict[str, Any]) -> list[Diagnostic]:
    out = _schema(registry, schema, "registry")
    if out:
        return out
    collections = (("programs", "program_id"), ("initiatives", "initiative_id"), ("tasks", "task_id"), ("work_packages", "work_package_id"))
    seen: dict[str, str] = {}
    for name, key in collections:
        for index, item in enumerate(registry[name]):
            ident, path = item[key], f"/{name}/{index}/{key}"
            if ident in seen:
                out.append(diagnostic("PINS-DUPLICATE-ID", path, f"also appears at {seen[ident]}"))
            else:
                seen[ident] = path
    programs = {x["program_id"]: x for x in registry["programs"]}
    initiatives = {x["initiative_id"]: x for x in registry["initiatives"]}
    tasks = {x["task_id"]: x for x in registry["tasks"]}
    packages = {x["work_package_id"]: x for x in registry["work_packages"]}
    for i, item in enumerate(registry["initiatives"]):
        if item["program_id"] not in programs:
            out.append(diagnostic("PINS-UNKNOWN-PARENT", f"/initiatives/{i}/program_id", item["program_id"]))
    for i, item in enumerate(registry["tasks"]):
        path = f"/tasks/{i}"
        if item["initiative_id"] not in initiatives:
            out.append(diagnostic("PINS-UNKNOWN-PARENT", path + "/initiative_id", item["initiative_id"]))
        deps = item["depends_on"]
        if len(deps) != len(set(deps)):
            out.append(diagnostic("PINS-UNKNOWN-DEPENDENCY", path + "/depends_on", "duplicate dependency"))
        for dep in deps:
            if dep == item["task_id"]:
                out.append(diagnostic("PINS-DEPENDENCY-CYCLE", path + "/depends_on", "self-dependency"))
            elif dep not in tasks:
                out.append(diagnostic("PINS-UNKNOWN-DEPENDENCY", path + "/depends_on", dep))
        if item["status"] in {"authorized", "in_progress", "implemented", "complete"} and not item["implementation_authorized"]:
            out.append(diagnostic("PINS-UNAUTHORIZED-IMPLEMENTATION", path, "state requires authorization"))
        incomplete = [d for d in deps if tasks.get(d, {}).get("status") != "complete"]
        if item["status"] in {"in_progress", "implemented", "complete"} and incomplete:
            out.append(diagnostic("PINS-DEPENDENCY-NOT-COMPLETE", path + "/depends_on", ", ".join(incomplete)))
        if item["status"] == "complete" and (not item["completion_claimed"] or not item["evidence_refs"]):
            out.append(diagnostic("PINS-FALSE-COMPLETION", path, "completion requires evidence"))
        if item["status"] != "complete" and item["completion_claimed"]:
            out.append(diagnostic("PINS-FALSE-COMPLETION", path, "completion claimed before complete state"))
    graph = {k: [d for d in v["depends_on"] if d in tasks] for k, v in tasks.items()}
    cycle = _cycles(graph)
    if cycle:
        out.append(diagnostic("PINS-DEPENDENCY-CYCLE", "/tasks", " -> ".join(cycle)))
    plan = tasks.get("PINS-PLAN-001")
    if plan and plan["status"] != "complete":
        for i, item in enumerate(registry["tasks"]):
            if item["task_id"].startswith("PINS-AIGOV-") and (item["implementation_authorized"] or item["status"] not in {"registered", "blocked"}):
                out.append(diagnostic("PINS-UNAUTHORIZED-IMPLEMENTATION", f"/tasks/{i}", "future AIGOV task is not eligible"))
    for i, item in enumerate(registry["work_packages"]):
        path = f"/work_packages/{i}"
        task = tasks.get(item["task_id"])
        if task is None:
            out.append(diagnostic("PINS-UNKNOWN-PARENT", path + "/task_id", item["task_id"]))
        elif item["status"] in {"ready", "implementing", "implemented_pending_exact_head_validation", "exact_head_validated", "merged", "post_merge_verified", "closed"}:
            incomplete = [d for d in task["depends_on"] if tasks.get(d, {}).get("status") != "complete"]
            if not task["implementation_authorized"]:
                out.append(diagnostic("PINS-UNAUTHORIZED-IMPLEMENTATION", path, "Task is not authorized"))
            if incomplete:
                out.append(diagnostic("PINS-DEPENDENCY-NOT-COMPLETE", path, ", ".join(incomplete)))
    current = [x for x in registry["work_packages"] if x["current"]]
    current_id = registry["current_work_package_id"]
    if len(current) != 1 or current_id not in packages or current[0]["work_package_id"] != current_id or current[0]["status"] == "closed":
        out.append(diagnostic("PINS-CURRENT-WORK-PACKAGE-INVALID", "/current_work_package_id", "exactly one existing non-closed Work Package must be current"))
    return sorted(set(out))


def validate_scope(scope: dict[str, Any], schema: dict[str, Any], registry: dict[str, Any]) -> list[Diagnostic]:
    out = _schema(scope, schema, "scope")
    if out:
        return out
    if scope["scope_revision"] != canonical_scope_revision(scope):
        out.append(diagnostic("PINS-SCOPE-REVISION-MISMATCH", "/scope/scope_revision", "canonical hash mismatch"))
    programs = {x["program_id"] for x in registry["programs"]}; initiatives = {x["initiative_id"] for x in registry["initiatives"]}; tasks = {x["task_id"] for x in registry["tasks"]}; packages = {x["work_package_id"] for x in registry["work_packages"]}
    for field, known in (("program_id", programs), ("initiative_id", initiatives), ("task_id", tasks), ("work_package_id", packages)):
        if scope[field] not in known:
            out.append(diagnostic("PINS-UNKNOWN-PARENT", f"/scope/{field}", scope[field]))
    paths = scope["committed_paths"]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        out.append(diagnostic("PINS-SCOPE-PATH-INVALID", "/scope/committed_paths", "paths must be unique and sorted"))
    for path in paths:
        error = validate_repo_path(path)
        if error:
            out.append(diagnostic("PINS-SCOPE-PATH-INVALID", "/scope/committed_paths", f"{path}: {error}"))
        elif path not in ALLOWED_EXACT and not path.startswith(ALLOWED_PREFIXES):
            out.append(diagnostic("PINS-SCOPE-FORBIDDEN-PATH", f"/{path}", "path is outside the authorized boundary"))
    if not REQUIRED_EXCLUDED <= set(scope["excluded_paths"]):
        out.append(diagnostic("PINS-SCOPE-FORBIDDEN-PATH", "/scope/excluded_paths", "required exclusions are missing"))
    if not REQUIRED_FORBIDDEN <= set(scope["forbidden_changes"]):
        out.append(diagnostic("PINS-SCOPE-FORBIDDEN-PATH", "/scope/forbidden_changes", "required forbidden operations are missing"))
    for pattern in scope["excluded_paths"]:
        error = _pattern_error(pattern)
        if error:
            out.append(diagnostic("PINS-SCOPE-PATH-INVALID", "/scope/excluded_paths", f"{pattern}: {error}"))
        elif any(pattern_matches(pattern, path) for path in paths):
            out.append(diagnostic("PINS-SCOPE-FORBIDDEN-PATH", "/scope/committed_paths", f"path matches {pattern}"))
    return sorted(set(out))


def validate_impact(impact: dict[str, Any], schema: dict[str, Any], scope: dict[str, Any]) -> list[Diagnostic]:
    out = _schema(impact, schema, "impact")
    if out:
        return out
    for field in ("program_id", "initiative_id", "task_id", "work_package_id", "scope_id", "repository", "base_sha"):
        if impact[field] != scope[field]:
            out.append(diagnostic("PINS-IMPACT-SCOPE-MISMATCH", f"/impact/{field}", f"expected {scope[field]}"))
    if impact["sequence"] != 1 or impact["previous_impact_ref"] is not None:
        out.append(diagnostic("PINS-IMPACT-SEQUENCE-MISMATCH", "/impact/sequence", "bootstrap Impact must start at sequence 1"))
    if impact["changed_paths"] != scope["committed_paths"]:
        out.append(diagnostic("PINS-IMPACT-SCOPE-MISMATCH", "/impact/changed_paths", "must equal Scope paths"))
    if not impact["material_progress"] or impact["zero_progress"]:
        out.append(diagnostic("PINS-IMPACT-FALSE-PROGRESS", "/impact", "material progress must be true and zero progress false"))
    if impact["completion_claimed"] or impact["state_after"] == "complete":
        out.append(diagnostic("PINS-IMPACT-FALSE-COMPLETION", "/impact", "completion is not available"))
    missing = REQUIRED_REMAINING - set(impact["remaining_obligations"])
    if missing or impact["next_lifecycle_action"] != "exact_head_validation":
        out.append(diagnostic("PINS-IMPACT-FALSE-COMPLETION", "/impact/remaining_obligations", "required lifecycle obligations are missing or misordered"))
    return sorted(set(out))


def extract_bounded_json(text: str, begin: str, end: str) -> dict[str, Any]:
    if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) >= text.index(end):
        raise ValueError("bounded markers must occur exactly once in order")
    payload = loads_json_strict(text.split(begin, 1)[1].split(end, 1)[0].strip())
    if not isinstance(payload, dict):
        raise ValueError("bounded payload must be an object")
    return payload


def expected_snapshot(registry: dict[str, Any], scope: dict[str, Any], impact: dict[str, Any]) -> dict[str, Any]:
    package = next(x for x in registry["work_packages"] if x["current"])
    task = next(x for x in registry["tasks"] if x["task_id"] == package["task_id"])
    program = registry["programs"][0]
    return {
        "program_id": program["program_id"], "program_status": program["status"],
        "initiative_ids": sorted(x["initiative_id"] for x in registry["initiatives"]),
        "task_ids": sorted(x["task_id"] for x in registry["tasks"]),
        "current_work_package_id": package["work_package_id"], "current_task_id": task["task_id"],
        "current_task_status": task["status"], "current_work_package_status": package["status"],
        "scope_id": scope["scope_id"], "scope_revision": scope["scope_revision"],
        "next_lifecycle_action": impact["next_lifecycle_action"],
    }


def validate_markdown(root: Path, registry: dict[str, Any], scope: dict[str, Any], impact: dict[str, Any]) -> list[Diagnostic]:
    out: list[Diagnostic] = []; expected = expected_snapshot(registry, scope, impact)
    for path, markers, code in ((NEXT_WORK_PATH, NEXT_MARKERS, "PINS-DASHBOARD-REGISTRY-DRIFT"), (PLAN_PATH, PLAN_MARKERS, "PINS-PLAN-REGISTRY-DRIFT")):
        try:
            actual = extract_bounded_json((root / path).read_text(encoding="utf-8"), *markers)
            if actual != expected:
                raise ValueError("bounded snapshot differs from canonical state")
        except Exception as exc:
            out.append(diagnostic(code, f"/{path}", str(exc)))
    baseline = (root / BASELINE_PATH).read_text(encoding="utf-8")
    for phrase in ("documented != implemented", "registered != authorized", "implemented != exact-head validated", "CI green != Merge enforcement", "outside the active protocol `load_order`", "does not activate AIGOV", "Closed PR #33 remains closed and unmerged"):
        if phrase not in baseline:
            out.append(diagnostic("PINS-PLAN-REGISTRY-DRIFT", f"/{BASELINE_PATH}", f"missing invariant: {phrase}"))
    return out


def _material(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    return load_json_strict(root / REGISTRY_PATH), load_json_strict(root / SCOPE_PATH), load_json_strict(root / IMPACT_PATH), {k: load_json_strict(root / v) for k, v in SCHEMAS.items()}


def validate_planning_repository(root: Path) -> list[Diagnostic]:
    required = [REGISTRY_PATH, SCOPE_PATH, IMPACT_PATH, NEXT_WORK_PATH, PLAN_PATH, BASELINE_PATH, *SCHEMAS.values()]
    missing = [x for x in required if not (root / x).is_file()]
    if missing:
        return [diagnostic("PINS-REGISTRY-SCHEMA-INVALID", f"/{x}", "required artifact is missing") for x in missing]
    try:
        registry, scope, impact, schemas = _material(root)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
        return [diagnostic("PINS-REGISTRY-SCHEMA-INVALID", "/planning", str(exc))]
    out = validate_registry(registry, schemas["registry"]) + validate_scope(scope, schemas["scope"], registry) + validate_impact(impact, schemas["impact"], scope) + validate_markdown(root, registry, scope, impact)
    for path in scope.get("committed_paths", []):
        if validate_repo_path(path) is None and not (root / path).is_file():
            out.append(diagnostic("PINS-SCOPE-DISCLOSURE-MISMATCH", f"/{path}", "declared path is missing"))
    return sorted(set(out))


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git failed")
    return result.stdout.strip()


def validate_git_diff(root: Path, base_sha: str, head_sha: str) -> tuple[list[Diagnostic], dict[str, Any]]:
    out: list[Diagnostic] = []
    report: dict[str, Any] = {"base_sha": base_sha, "head_sha": head_sha, "actual_changed_paths": [], "declared_changed_paths": [], "status": "invalid"}
    try:
        scope = load_json_strict(root / SCOPE_PATH)
        report["declared_changed_paths"] = scope.get("committed_paths", [])
        if scope.get("base_sha") != base_sha:
            out.append(diagnostic("PINS-SCOPE-BASE-MISMATCH", "/scope/base_sha", "runtime base differs from declared base"))
        resolved_base = _git(root, "rev-parse", f"{base_sha}^{{commit}}")
        resolved_head = _git(root, "rev-parse", f"{head_sha}^{{commit}}")
        checkout = _git(root, "rev-parse", "HEAD")
        if resolved_base != base_sha:
            out.append(diagnostic("PINS-SCOPE-BASE-MISMATCH", "/git/base", f"resolved {resolved_base}"))
        if resolved_head != head_sha or checkout != head_sha:
            out.append(diagnostic("PINS-SCOPE-DISCLOSURE-MISMATCH", "/git/head", "runtime Head identity mismatch"))
        actual = sorted(x for x in _git(root, "diff", "--name-only", "--diff-filter=ACMRD", f"{base_sha}..{head_sha}").splitlines() if x)
    except Exception as exc:
        out.append(diagnostic("PINS-SCOPE-BASE-MISMATCH", "/git", str(exc)))
        return sorted(set(out)), report
    report["actual_changed_paths"] = actual; declared = scope.get("committed_paths", [])
    for path in actual:
        error = validate_repo_path(path)
        if error:
            out.append(diagnostic("PINS-SCOPE-PATH-INVALID", f"/{path}", error))
    for path in sorted(set(actual) - set(declared)):
        out.append(diagnostic("PINS-SCOPE-UNDECLARED-PATH", f"/{path}", "changed path is not declared"))
    for path in sorted(set(declared) - set(actual)):
        out.append(diagnostic("PINS-SCOPE-DECLARED-PATH-UNCHANGED", f"/{path}", "declared path is unchanged"))
    for path in actual:
        for pattern in scope.get("excluded_paths", []):
            if _pattern_error(pattern) is None and pattern_matches(pattern, path):
                out.append(diagnostic("PINS-SCOPE-FORBIDDEN-PATH", f"/{path}", f"matches {pattern}"))
    if actual != declared:
        out.append(diagnostic("PINS-SCOPE-DISCLOSURE-MISMATCH", "/git/diff", "actual paths differ from declared paths"))
    if not out:
        report["status"] = "valid"
    return sorted(set(out)), report
