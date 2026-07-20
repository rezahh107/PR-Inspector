from __future__ import annotations

from .planning_governance_base import *

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
        ("evidence_records", "evidence_id"),
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
    evidence = {item["evidence_id"]: item for item in registry["evidence_records"]}

    for index, item in enumerate(registry["initiatives"]):
        if item["program_id"] not in programs:
            output.append(diagnostic("PINS-UNKNOWN-PARENT", f"/initiatives/{index}/program_id", item["program_id"]))

    for index, record in enumerate(registry["evidence_records"]):
        path = f"/evidence_records/{index}"
        package = packages.get(record["work_package_id"])
        task = tasks.get(record["task_id"])
        if package is None or task is None:
            output.append(diagnostic("PINS-EVIDENCE-PROVENANCE-MISMATCH", path, "evidence owner is not registered"))
            continue
        if package["task_id"] != task["task_id"]:
            output.append(diagnostic("PINS-EVIDENCE-PROVENANCE-MISMATCH", path, "Task/Work Package identity mismatch"))
        if record["scope_ref"] != package["scope_ref"]:
            output.append(diagnostic("PINS-EVIDENCE-PROVENANCE-MISMATCH", path + "/scope_ref", "must equal Work Package scope_ref"))
        if record["impact_ref"] not in package["impact_refs"]:
            output.append(diagnostic("PINS-EVIDENCE-PROVENANCE-MISMATCH", path + "/impact_ref", "must resolve to a Work Package Impact"))

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

        task_records = _records_for_refs(
            item["evidence_refs"],
            evidence,
            path + "/evidence_refs",
            output,
            task_id=item["task_id"],
        )
        if item["status"] == "complete":
            owned = [package for package in packages.values() if package["task_id"] == item["task_id"]]
            if not item["completion_claimed"]:
                output.append(diagnostic("PINS-FALSE-COMPLETION", path, "completion requires completion_claimed"))
            if not item["evidence_refs"]:
                output.append(diagnostic("PINS-FALSE-COMPLETION", path, "completion requires authoritative evidence refs"))
            if not owned:
                output.append(diagnostic("PINS-TASK-COMPLETION-PREDICATE", path, "complete Task has no Work Packages"))
            incomplete_packages = [
                package["work_package_id"]
                for package in owned
                if package["status"] not in _WP_POST_MERGE_STATES
            ]
            if incomplete_packages:
                output.append(
                    diagnostic(
                        "PINS-TASK-COMPLETION-PREDICATE",
                        path,
                        "Work Packages are not post-Merge verified: " + ", ".join(incomplete_packages),
                    )
                )
            task_record_ids = {record["evidence_id"] for record in task_records}
            for package in owned:
                post_ids = {
                    ref
                    for ref in package["evidence_refs"]
                    if evidence.get(ref, {}).get("evidence_type") == "post_merge_verification"
                }
                if not post_ids or not post_ids <= task_record_ids:
                    output.append(
                        diagnostic(
                            "PINS-TASK-COMPLETION-PREDICATE",
                            path + "/evidence_refs",
                            f"Task completion must include post-Merge evidence for {package['work_package_id']}",
                        )
                    )
        elif item["completion_claimed"]:
            output.append(diagnostic("PINS-FALSE-COMPLETION", path, "completion claimed before complete state"))

    task_graph = {
        task_id: [dependency for dependency in task["depends_on"] if dependency in tasks]
        for task_id, task in tasks.items()
    }
    task_cycle = _cycles(task_graph)
    if task_cycle:
        output.append(diagnostic("PINS-DEPENDENCY-CYCLE", "/tasks", " -> ".join(task_cycle)))

    for index, item in enumerate(registry["tasks"]):
        path = f"/tasks/{index}"
        requires_dependencies = item["implementation_authorized"] or item["status"] in {
            "authorized",
            "in_progress",
            "implemented",
            "complete",
        }
        if requires_dependencies:
            incomplete = [
                dependency
                for dependency in item["depends_on"]
                if not _task_registry_completion_eligible(dependency, tasks, packages, evidence)
            ]
            if incomplete:
                output.append(diagnostic("PINS-DEPENDENCY-NOT-COMPLETE", path + "/depends_on", ", ".join(incomplete)))

    foundation_complete = _task_registry_completion_eligible("PINS-PLAN-001", tasks, packages, evidence)
    if not foundation_complete:
        for index, item in enumerate(registry["tasks"]):
            is_future_domain_task = item["task_id"].startswith("PINS-AIGOV-")
            is_started = item["status"] not in {"registered", "blocked"}
            if is_future_domain_task and (item["implementation_authorized"] or is_started):
                output.append(
                    diagnostic(
                        "PINS-UNAUTHORIZED-IMPLEMENTATION",
                        f"/tasks/{index}",
                        "future AIGOV task is not eligible until Foundation completion is authoritative",
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
            output.append(diagnostic("PINS-DEPENDENCY-NOT-COMPLETE", path + "/depends_on", ", ".join(incomplete_packages)))

        if task is not None and item["status"] in _WP_ACTIVE_STATES:
            incomplete_tasks = [
                dependency
                for dependency in task["depends_on"]
                if not _task_registry_completion_eligible(dependency, tasks, packages, evidence)
            ]
            if not task["implementation_authorized"]:
                output.append(diagnostic("PINS-UNAUTHORIZED-IMPLEMENTATION", path, "Task is not authorized"))
            if incomplete_tasks:
                output.append(diagnostic("PINS-DEPENDENCY-NOT-COMPLETE", path, ", ".join(incomplete_tasks)))

        records = _records_for_refs(
            item["evidence_refs"],
            evidence,
            path + "/evidence_refs",
            output,
            task_id=item["task_id"],
            work_package_id=item["work_package_id"],
        )
        types = _record_types(records)
        if item["evidence_refs"] and item["status"] not in _WP_EXACT_HEAD_STATES and not types:
            output.append(
                diagnostic(
                    "PINS-WP-LIFECYCLE-INVALID",
                    path + "/evidence_refs",
                    f"unresolved evidence is not valid for lifecycle state {item['status']}",
                )
            )
        if item["status"] in _WP_IMPLEMENTED_STATES and not item["impact_refs"]:
            output.append(diagnostic("PINS-WP-EVIDENCE-MISSING", path + "/impact_refs", "implemented state requires Impact evidence"))
        for stage, states in (
            ("exact_head", _WP_EXACT_HEAD_STATES),
            ("merge", _WP_MERGED_STATES),
            ("post_merge", _WP_POST_MERGE_STATES),
        ):
            evidence_type = _EVIDENCE_TYPE_BY_STAGE[stage]
            has_evidence = evidence_type in types
            if item["status"] in states and not has_evidence:
                output.append(
                    diagnostic(
                        "PINS-WP-EVIDENCE-MISSING",
                        path + "/evidence_refs",
                        f"{item['status']} requires typed {stage} evidence",
                    )
                )
            if item["status"] not in states and has_evidence:
                output.append(
                    diagnostic(
                        "PINS-WP-LIFECYCLE-INVALID",
                        path + "/evidence_refs",
                        f"{stage} evidence is ahead of lifecycle state {item['status']}",
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


