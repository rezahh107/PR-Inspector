from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path

import pytest

from pr_inspector.evidence_context import evidence_scope
from tests.governance_test_support import sequence_capability

_LEGACY_GREEN_MODULES = {
    "test_protocol_v1_4.py",
    "test_sensitive_domains.py",
}


@pytest.fixture(autouse=True)
def exact_bound_sequence_for_legacy_green_tests(request):
    """Preserve unrelated legacy Green tests under the evidence-bound profile.

    Security-profile tests are intentionally excluded so bare serialized claims
    continue to exercise the fail-closed path.
    """

    path = Path(str(request.fspath))
    scope = (
        evidence_scope(sequence_enforcement=sequence_capability())
        if path.name in _LEGACY_GREEN_MODULES
        else nullcontext()
    )
    with scope:
        yield
