from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/validate-repository.yml"


def test_pull_request_ci_checks_out_and_asserts_exact_head_sha():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["validate"]["steps"]

    checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["ref"] == "${{ github.event.pull_request.head.sha || github.sha }}"
    assert checkout["with"]["persist-credentials"] is False

    identity = next(step for step in steps if step.get("name") == "Verify exact checkout identity")
    assert identity["env"]["EXPECTED_SHA"] == "${{ github.event.pull_request.head.sha || github.sha }}"
    assert "git rev-parse HEAD" in identity["run"]
    assert 'test "${actual_sha}" = "${EXPECTED_SHA}"' in identity["run"]
