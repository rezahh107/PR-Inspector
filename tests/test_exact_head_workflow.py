from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/validate-repository.yml"


def test_pull_request_ci_checks_out_and_asserts_exact_head_sha():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["validate"]["steps"]

    checkout = next(
        step for step in steps if step.get("uses", "").startswith("actions/checkout@")
    )
    assert checkout["with"]["ref"] == "${{ github.event.pull_request.head.sha || github.sha }}"
    assert checkout["with"]["persist-credentials"] is False
    assert checkout["uses"] == "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0"

    identity = next(step for step in steps if step.get("name") == "Verify exact checkout identity")
    assert identity["env"]["EXPECTED_SHA"] == "${{ github.event.pull_request.head.sha || github.sha }}"
    assert "git rev-parse HEAD" in identity["run"]
    assert 'test "${actual_sha}" = "${EXPECTED_SHA}"' in identity["run"]


def test_ci_records_object_identity_and_runs_focused_behavioral_enforcement():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["validate"]["steps"]
    by_name = {step["name"]: step for step in steps if "name" in step}

    record = by_name["Record and validate tested object identity"]["run"]
    assert "scripts/record_ci_identity.py" in record
    assert "--tested-sha" in record
    assert "--tested-tree-sha" in record
    assert "--reviewed-head-sha" in record
    assert "--synthetic-merge false" in record
    assert "--claim-exact-head" in record
    assert "--workflow-run-id" in record
    assert "--job-id" in record

    assert by_name["Run focused Behavioral Rule Coverage mutations"]["run"] == "python -m pytest -q tests/test_behavioral_rule_coverage.py"
    assert "tests/test_dual_audience_outputs.py" in by_name["Run focused artifact byte-consistency tests"]["run"]
    assert by_name["Run semantic and rendering tests"]["run"] == "python -m pytest"
