from pathlib import Path

replacements = {
    Path("tests/test_planning_governance.py"): [
        (
            '''def test_false_completion_in_unbounded_prose_has_no_authority():
    text = (ROOT / "planning/NEXT_WORK.md").read_text(encoding="utf-8") + "\\nPINS-PLAN-001 is complete.\\n"
    assert extract_bounded_json(text, *NEXT_MARKERS)["current_task_status"] == "in_progress"
''',
            '''def test_false_completion_in_unbounded_prose_has_no_authority():
    canonical = (ROOT / "planning/NEXT_WORK.md").read_text(encoding="utf-8")
    expected = extract_bounded_json(canonical, *NEXT_MARKERS)
    text = canonical + "\\nPINS-PLAN-001 is complete.\\n"
    assert extract_bounded_json(text, *NEXT_MARKERS) == expected
''',
        ),
        (
            '''    package = current_package(registry)
    package["status"] = status
    package["current"] = status != "closed"
''',
            '''    package = current_package(registry)
    package["status"] = status
    package["evidence_refs"] = []
    package["current"] = status != "closed"
''',
        ),
        (
            '''def test_evidence_cannot_lead_the_lifecycle_state():
    registry_schema, _, _ = schemas()
    registry = read("planning/tasks/task-registry.v1.json")
    current_package(registry)["evidence_refs"] = ["exact_head:run-1"]
    assert "PINS-WP-LIFECYCLE-INVALID" in codes(validate_registry(registry, registry_schema))
''',
            '''def test_evidence_cannot_lead_the_lifecycle_state():
    registry_schema, _, _ = schemas()
    registry = read("planning/tasks/task-registry.v1.json")
    package = current_package(registry)
    package["status"] = "implementing"
    exact_head_evidence = next(
        record["evidence_id"]
        for record in registry["evidence_records"]
        if record["work_package_id"] == package["work_package_id"]
        and record["evidence_type"] == "exact_head_ci"
    )
    package["evidence_refs"] = [exact_head_evidence]
    assert "PINS-WP-LIFECYCLE-INVALID" in codes(validate_registry(registry, registry_schema))
''',
        ),
    ],
    Path("tests/test_planning_governance_authority.py"): [
        (
            '''def test_fabricated_prefix_shaped_evidence_does_not_resolve():
    registry = read(REGISTRY_PATH)
    package = current_package(registry)
    package["evidence_refs"] = ["exact_head:run-1"]
''',
            '''def test_fabricated_prefix_shaped_evidence_does_not_resolve():
    registry = read(REGISTRY_PATH)
    package = current_package(registry)
    package["status"] = "implementing"
    package["evidence_refs"] = ["exact_head:run-1"]
''',
        ),
    ],
}

for path, pairs in replacements.items():
    text = path.read_text(encoding="utf-8")
    for old, new in pairs:
        count = text.count(old)
        if count != 1:
            raise SystemExit(f"{path}: expected one replacement target, found {count}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
