from __future__ import annotations

from .planning_governance_base import *
from .planning_governance_artifacts import validate_impact, validate_markdown, validate_scope
from .planning_governance_registry import validate_registry

def _safe_artifact_path(root: Path, ref: str, prefix: str) -> tuple[Path | None, list[Diagnostic]]:
    error = validate_repo_path(ref)
    if error or not ref.startswith(prefix):
        return None, [diagnostic("PINS-REFERENCE-PATH-INVALID", f"/{ref}", error or f"must be below {prefix}")]
    root_resolved = root.resolve()
    candidate = root / ref
    try:
        resolved = candidate.resolve(strict=False)
    except OSError as exc:
        return None, [diagnostic("PINS-REFERENCE-PATH-INVALID", f"/{ref}", str(exc))]
    if resolved != root_resolved and root_resolved not in resolved.parents:
        return None, [diagnostic("PINS-REFERENCE-PATH-INVALID", f"/{ref}", "reference escapes repository root")]
    if candidate.is_symlink():
        return None, [diagnostic("PINS-REFERENCE-PATH-INVALID", f"/{ref}", "planning artifact reference must not be a symlink")]
    if not candidate.is_file():
        return None, [diagnostic("PINS-CROSS-FILE-BINDING-MISMATCH", f"/{ref}", "referenced artifact is missing")]
    return candidate, []


def _load_referenced_json(root: Path, ref: str, prefix: str) -> tuple[Any | None, list[Diagnostic]]:
    path, output = _safe_artifact_path(root, ref, prefix)
    if path is None:
        return None, output
    try:
        return load_json_strict(path), output
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
        output.append(diagnostic(_SCHEMA_ERROR, f"/{ref}", str(exc)))
        return None, output


def _validate_evidence_chain(
    registry: dict[str, Any],
    package: dict[str, Any],
    scope: dict[str, Any],
    latest_impact_ref: str,
) -> list[Diagnostic]:
    output: list[Diagnostic] = []
    evidence = {item["evidence_id"]: item for item in registry["evidence_records"]}
    records = [evidence[ref] for ref in package["evidence_refs"] if ref in evidence]
    by_type: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_type.setdefault(record["evidence_type"], []).append(record)
        if record["repository"] != scope["repository"] or record["base_sha"] != scope["base_sha"]:
            output.append(diagnostic("PINS-EVIDENCE-PROVENANCE-MISMATCH", f"/evidence_records/{record['evidence_id']}", "repository/base identity mismatch"))
        if record["scope_ref"] != package["scope_ref"] or record["impact_ref"] not in package["impact_refs"]:
            output.append(diagnostic("PINS-EVIDENCE-PROVENANCE-MISMATCH", f"/evidence_records/{record['evidence_id']}", "artifact reference mismatch"))

    exact = by_type.get("exact_head_ci", [])
    merges = by_type.get("merge", [])
    posts = by_type.get("post_merge_verification", [])
    if len(exact) > 1 or len(merges) > 1 or len(posts) > 1:
        output.append(diagnostic("PINS-EVIDENCE-PROVENANCE-MISMATCH", f"/work_packages/{package['work_package_id']}/evidence_refs", "each lifecycle evidence type must be singular"))
    if exact:
        head_sha = exact[0]["head_sha"]
        for record in merges + posts:
            if record["head_sha"] != head_sha:
                output.append(diagnostic("PINS-EVIDENCE-PROVENANCE-MISMATCH", f"/evidence_records/{record['evidence_id']}/head_sha", "Head differs from exact-head evidence"))
    if merges and posts and merges[0]["merge_commit_sha"] != posts[0]["merge_commit_sha"]:
        output.append(diagnostic("PINS-EVIDENCE-PROVENANCE-MISMATCH", f"/evidence_records/{posts[0]['evidence_id']}/merge_commit_sha", "Merge identity differs from merge evidence"))
    if posts and posts[0]["impact_ref"] != latest_impact_ref:
        output.append(diagnostic("PINS-EVIDENCE-PROVENANCE-MISMATCH", f"/evidence_records/{posts[0]['evidence_id']}/impact_ref", "post-Merge evidence must bind the latest Impact"))
    return output


def _validate_registered_artifacts(
    root: Path,
    registry: dict[str, Any],
    schemas: dict[str, dict[str, Any]],
) -> tuple[list[Diagnostic], dict[str, dict[str, Any]], dict[str, list[tuple[str, dict[str, Any]]]]]:
    output: list[Diagnostic] = []
    scopes: dict[str, dict[str, Any]] = {}
    impacts: dict[str, list[tuple[str, dict[str, Any]]]] = {}

    for package in registry["work_packages"]:
        package_id = package["work_package_id"]
        scope_ref = package["scope_ref"]
        scope, load_errors = _load_referenced_json(root, scope_ref, "planning/scopes/")
        output += load_errors
        if scope is None:
            continue
        scope_errors = validate_scope(scope, schemas["scope"], registry, scope_ref)
        output += scope_errors
        if any(item.code == _SCHEMA_ERROR for item in scope_errors):
            continue
        scopes[package_id] = scope

        if len(package["impact_refs"]) != len(set(package["impact_refs"])):
            output.append(diagnostic("PINS-CROSS-FILE-BINDING-MISMATCH", f"/work_packages/{package_id}/impact_refs", "duplicate Impact reference"))
        loaded: list[tuple[str, dict[str, Any]]] = []
        for impact_ref in package["impact_refs"]:
            impact, impact_load_errors = _load_referenced_json(root, impact_ref, "planning/progress/impacts/")
            output += impact_load_errors
            if impact is None:
                continue
            schema_errors = _schema(impact, schemas["impact"], "impact")
            output += schema_errors
            if schema_errors:
                continue
            loaded.append((impact_ref, impact))

        loaded.sort(key=lambda item: (item[1]["sequence"], item[0]))
        impacts[package_id] = loaded
        sequences = [item[1]["sequence"] for item in loaded]
        expected_sequences = list(range(1, len(loaded) + 1))
        if sequences != expected_sequences:
            output.append(diagnostic("PINS-IMPACT-SEQUENCE-MISMATCH", f"/work_packages/{package_id}/impact_refs", f"expected contiguous sequences {expected_sequences}, observed {sequences}"))
        ordered_refs = [item[0] for item in loaded]
        if ordered_refs and package["impact_refs"] != ordered_refs:
            output.append(diagnostic("PINS-IMPACT-SEQUENCE-MISMATCH", f"/work_packages/{package_id}/impact_refs", "Impact refs must be ordered by sequence"))

        for index, (impact_ref, impact) in enumerate(loaded):
            expected_previous = None if index == 0 else loaded[index - 1][0]
            if impact["previous_impact_ref"] != expected_previous:
                output.append(diagnostic("PINS-IMPACT-SEQUENCE-MISMATCH", f"/{impact_ref}/previous_impact_ref", f"expected {expected_previous}"))
            output += validate_impact(
                impact,
                schemas["impact"],
                scope,
                registry,
                impact_ref,
                package_status=package["status"],
                is_latest=index == len(loaded) - 1,
            )

        if package["status"] in _WP_IMPLEMENTED_STATES and not loaded:
            output.append(diagnostic("PINS-WP-EVIDENCE-MISSING", f"/work_packages/{package_id}/impact_refs", "implemented Work Package has no resolvable Impact"))
        if loaded:
            output += _validate_evidence_chain(registry, package, scope, loaded[-1][0])

    return sorted(set(output)), scopes, impacts


def _full_task_completion_eligible(
    task_id: str,
    registry: dict[str, Any],
    scopes: dict[str, dict[str, Any]],
    impacts: dict[str, list[tuple[str, dict[str, Any]]]],
) -> bool:
    tasks = {item["task_id"]: item for item in registry["tasks"]}
    packages = {item["work_package_id"]: item for item in registry["work_packages"]}
    evidence = {item["evidence_id"]: item for item in registry["evidence_records"]}
    if not _task_registry_completion_eligible(task_id, tasks, packages, evidence):
        return False
    owned = [package for package in packages.values() if package["task_id"] == task_id]
    for package in owned:
        package_id = package["work_package_id"]
        if package_id not in scopes or not impacts.get(package_id):
            return False
        latest = impacts[package_id][-1][1]
        if not latest["completion_claimed"] or latest["state_after"] not in _COMPLETION_IMPACT_STATES:
            return False
    return True


def _validate_task_completion_and_dependencies(
    registry: dict[str, Any],
    scopes: dict[str, dict[str, Any]],
    impacts: dict[str, list[tuple[str, dict[str, Any]]]],
) -> list[Diagnostic]:
    output: list[Diagnostic] = []
    for index, task in enumerate(registry["tasks"]):
        path = f"/tasks/{index}"
        if task["status"] == "complete" and not _full_task_completion_eligible(task["task_id"], registry, scopes, impacts):
            output.append(diagnostic("PINS-TASK-COMPLETION-PREDICATE", path, "Task completion lacks authoritative artifact/evidence closure"))
        requires_dependencies = task["implementation_authorized"] or task["status"] in {
            "authorized",
            "in_progress",
            "implemented",
            "complete",
        }
        if requires_dependencies:
            incomplete = [
                dependency
                for dependency in task["depends_on"]
                if not _full_task_completion_eligible(dependency, registry, scopes, impacts)
            ]
            if incomplete:
                output.append(diagnostic("PINS-DEPENDENCY-NOT-COMPLETE", path + "/depends_on", ", ".join(incomplete)))
    return sorted(set(output))


def validate_planning_repository(root: Path) -> list[Diagnostic]:
    required = [REGISTRY_PATH, NEXT_WORK_PATH, PLAN_PATH, BASELINE_PATH, *SCHEMAS.values()]
    missing = [path for path in required if not (root / path).is_file()]
    if missing:
        return [diagnostic(_SCHEMA_ERROR, f"/{path}", "required artifact is missing") for path in missing]
    try:
        registry = load_json_strict(root / REGISTRY_PATH)
        schemas = {name: load_json_strict(root / path) for name, path in SCHEMAS.items()}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
        return [diagnostic(_SCHEMA_ERROR, "/planning", str(exc))]

    output = validate_registry(registry, schemas["registry"])
    if any(item.code == _SCHEMA_ERROR for item in output):
        return sorted(set(output))

    artifact_output, scopes, impacts = _validate_registered_artifacts(root, registry, schemas)
    output += artifact_output
    if any(item.code == _SCHEMA_ERROR for item in artifact_output):
        return sorted(set(output))
    output += _validate_task_completion_and_dependencies(registry, scopes, impacts)

    current_id = registry["current_work_package_id"]
    current_scope = scopes.get(current_id)
    current_impacts = impacts.get(current_id, [])
    if current_scope is not None and current_impacts:
        output += validate_markdown(root, registry, current_scope, current_impacts[-1][1])

    for scope in scopes.values():
        for path in scope["committed_paths"]:
            if validate_repo_path(path) is None and not (root / path).is_file():
                output.append(diagnostic("PINS-SCOPE-DISCLOSURE-MISMATCH", f"/{path}", "declared path is missing"))
        for path in scope.get("deleted_paths", []):
            if validate_repo_path(path) is None and (root / path).exists():
                output.append(diagnostic("PINS-SCOPE-DISCLOSURE-MISMATCH", f"/{path}", "declared deleted path still exists"))
    return sorted(set(output))


