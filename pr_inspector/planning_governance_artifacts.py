from __future__ import annotations

from .planning_governance_base import *

def validate_scope(
    scope: dict[str, Any],
    schema: dict[str, Any],
    registry: dict[str, Any],
    expected_scope_ref: str | None = None,
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
    expected_ref = expected_scope_ref or SCOPE_PATH.as_posix()
    if package and package["scope_ref"] != expected_ref:
        output.append(
            diagnostic(
                "PINS-CROSS-FILE-BINDING-MISMATCH",
                "/scope/work_package_id",
                f"Work Package scope_ref must equal {expected_ref}",
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
    expected_impact_ref: str | None = None,
    *,
    package_status: str | None = None,
    is_latest: bool = True,
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

    package = None
    if registry is not None:
        packages = {item["work_package_id"]: item for item in registry["work_packages"]}
        package = packages.get(impact["work_package_id"])
        if package is None:
            output.append(diagnostic("PINS-CROSS-FILE-BINDING-MISMATCH", "/impact/work_package_id", "Impact Work Package is not registered"))
        else:
            expected_ref = expected_impact_ref or IMPACT_PATH.as_posix()
            if expected_ref not in package["impact_refs"]:
                output.append(
                    diagnostic(
                        "PINS-CROSS-FILE-BINDING-MISMATCH",
                        "/impact/work_package_id",
                        f"Work Package impact_refs must include {expected_ref}",
                    )
                )
            if package["task_id"] != impact["task_id"]:
                output.append(diagnostic("PINS-CROSS-FILE-BINDING-MISMATCH", "/impact/task_id", "Impact Task does not own Work Package"))
            package_status = package_status or package["status"]

    if impact["sequence"] == 1 and impact["previous_impact_ref"] is not None:
        output.append(diagnostic("PINS-IMPACT-SEQUENCE-MISMATCH", "/impact/previous_impact_ref", "first Impact must not have a predecessor"))
    if impact["sequence"] > 1 and impact["previous_impact_ref"] is None:
        output.append(diagnostic("PINS-IMPACT-SEQUENCE-MISMATCH", "/impact/previous_impact_ref", "later Impact requires predecessor reference"))
    if impact["changed_paths"] != scope["committed_paths"]:
        output.append(diagnostic("PINS-IMPACT-SCOPE-MISMATCH", "/impact/changed_paths", "must equal Scope paths"))
    if impact["material_progress"] == impact["zero_progress"]:
        output.append(diagnostic("PINS-IMPACT-FALSE-PROGRESS", "/impact", "exactly one progress classification must be true"))

    completed_package = package_status in _WP_POST_MERGE_STATES
    if is_latest and completed_package:
        if not impact["completion_claimed"] or impact["state_after"] not in _COMPLETION_IMPACT_STATES:
            output.append(
                diagnostic(
                    "PINS-TASK-COMPLETION-PREDICATE",
                    "/impact",
                    "latest Impact must confirm post-Merge Work Package completion",
                )
            )
    elif impact["completion_claimed"] or impact["state_after"] in _COMPLETION_IMPACT_STATES:
        output.append(diagnostic("PINS-IMPACT-FALSE-COMPLETION", "/impact", "completion is ahead of Work Package lifecycle"))

    if (
        impact["work_package_id"] == "PINS-PLAN-001-WP01"
        and impact["sequence"] == 1
        and package_status == "implementing"
    ):
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


def _safe_markdown_read(root: Path, path: Path) -> tuple[str | None, list[Diagnostic]]:
    try:
        return (root / path).read_text(encoding="utf-8"), []
    except (OSError, UnicodeDecodeError) as exc:
        return None, [diagnostic("PINS-MARKDOWN-INPUT-INVALID", f"/{path}", str(exc))]


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
        text, read_errors = _safe_markdown_read(root, path)
        output += read_errors
        if text is None:
            continue
        try:
            actual = extract_bounded_json(text, *markers)
            if actual != expected:
                raise ValueError("bounded snapshot differs from canonical state")
        except (ValueError, json.JSONDecodeError, DuplicateKeyError) as exc:
            output.append(diagnostic(code, f"/{path}", str(exc)))

    baseline, read_errors = _safe_markdown_read(root, BASELINE_PATH)
    output += read_errors
    if baseline is None:
        return sorted(set(output))
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
    return sorted(set(output))


