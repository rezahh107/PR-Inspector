from __future__ import annotations

from dataclasses import replace

import pytest

from pr_inspector.verified_review import ReviewAssemblyError, assemble_review_package
from tests import test_v1_12_verified_review_authority as authority


def _active_context():
    return replace(authority._context(), protocol_version="v1.13.1")


def test_v1_13_missing_evidence_reference_remains_fail_closed():
    finding = authority.ReviewFinding(
        "FND-V113-MISSING",
        "Missing evidence",
        "The evidence reference is absent.",
        "LOW",
        False,
        "The active assembler must reject unresolved evidence.",
        ("EVD-DOES-NOT-EXIST",),
        "CODE_SUPPORTED",
    )
    with pytest.raises(ReviewAssemblyError, match="unknown evidence"):
        assemble_review_package(
            authority._facts(),
            authority._assessment(finding=finding),
            _active_context(),
        )


def test_v1_13_required_check_failure_remains_blocking():
    package = assemble_review_package(
        authority._facts(ci="failure"), authority._assessment(), _active_context()
    ).value()
    assert package["decision"]["technical_status"] != "GREEN_TECHNICALLY_READY"
    assert "required_technical_check_failed" in package["technical_decision"][
        "reason_codes"
    ]


def test_v1_13_cross_identity_evidence_remains_rejected():
    facts = authority._facts()
    forged = replace(facts.evidence_catalog[0], repository="other/repo")
    with pytest.raises(
        ReviewAssemblyError, match="another repository, PR, or Head|deterministic"
    ):
        replace(facts, evidence_catalog=(forged, *facts.evidence_catalog[1:]))
