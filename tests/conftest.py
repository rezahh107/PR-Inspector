from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path

import pytest

from pr_inspector.evidence_context import evidence_scope
from pr_inspector.governance import (
    verify_github_governance_source,
    verify_governance_record,
)
from pr_inspector.sequence_enforcement import (
    SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
    verify_sequence_ci_enforcement,
)
from tests.governance_test_support import fixture, responses

_LEGACY_GREEN_MODULES = {
    "test_dual_audience_outputs.py",
    "test_protocol_v1_4.py",
}


def _sequence_capability():
    value = fixture()
    value["responses"]["checks"]["payload"]["check_runs"][0]["name"] = (
        SEQUENCE_ENFORCEMENT_CHECK_CONTEXT
    )
    required = value["responses"]["branch_protection"]["payload"][
        "required_status_checks"
    ]
    required["checks"][0]["context"] = SEQUENCE_ENFORCEMENT_CHECK_CONTEXT
    required["contexts"] = [SEQUENCE_ENFORCEMENT_CHECK_CONTEXT]
    source = verify_github_governance_source(
        responses(value),
        expected_repository="example/project",
        expected_pr_number=42,
        expected_head_sha="1" * 40,
    )
    governance = verify_governance_record(
        source,
        expected_repository="example/project",
        expected_pr_number=42,
        expected_head_sha="1" * 40,
    )
    return verify_sequence_ci_enforcement(
        governance,
        check_context=SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
        app_id=15368,
    )


@pytest.fixture(autouse=True)
def exact_bound_sequence_for_legacy_green_tests(request):
    """Preserve unrelated legacy Green tests under the evidence-bound profile.

    Security-profile tests are intentionally excluded so bare serialized claims
    continue to exercise the fail-closed path.
    """

    path = Path(str(request.fspath))
    scope = (
        evidence_scope(sequence_enforcement=_sequence_capability())
        if path.name in _LEGACY_GREEN_MODULES
        else nullcontext()
    )
    with scope:
        yield
