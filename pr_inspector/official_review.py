"""Supported v1.12 official review runtime.

Official completion collects facts and assembles the canonical package in process.
Caller-authored package files are accepted only as an explicit migration failure.
"""

from __future__ import annotations

import weakref
from collections.abc import Mapping
from pathlib import Path

from ._official_bundle import (
    IncompleteReview,
    VerifiedReviewCompletion,
    is_verified_review_completion,
    official_next_action_prompt,
    official_technical_handoff,
    verify_completed_review as _verify_completed_review,
)
from ._official_complete import complete_review as _publish_assembled_review
from ._official_head import (
    CompletionError,
    GitHubPullRequestHeadSource,
    VerifiedLivePullRequestHead,
    github_pull_request_head_source,
)
from .diagnostics import Diagnostic
from .evidence_context import evidence_scope
from .governance import VerifiedGovernanceEvidence
from .owner_delivery import (
    official_owner_delivery,
    official_owner_profile_commands,
    official_owner_result,
)
from .sequence_enforcement import VerifiedSequenceEnforcement
from .verified_review import (
    CanonicalReviewPackage,
    ChangedFile,
    CheckFact,
    EvidenceRecord,
    FIELD_AUTHORITY,
    GitHubReviewEvidenceSource,
    ProtocolContext,
    ReviewAssemblyError,
    ReviewAssessment,
    ReviewEvidenceSource,
    ReviewFacts,
    ReviewFinding,
    ReviewRequest,
    assemble_review_package,
    collect_review_facts,
    parse_review_assessment,
    render_unverified_preview,
)

_BOUND_EVIDENCE: weakref.WeakKeyDictionary[
    VerifiedReviewCompletion,
    tuple[VerifiedGovernanceEvidence | None, VerifiedSequenceEnforcement | None],
] = weakref.WeakKeyDictionary()
_ORIGINAL_REVERIFY = VerifiedReviewCompletion._reverify


def _evidence_aware_reverify(self: VerifiedReviewCompletion):
    bound = _BOUND_EVIDENCE.get(self)
    if bound is None:
        return _ORIGINAL_REVERIFY(self)
    with evidence_scope(bound[0], bound[1]):
        return _ORIGINAL_REVERIFY(self)


if not getattr(VerifiedReviewCompletion, "_pr_inspector_evidence_aware", False):
    VerifiedReviewCompletion._reverify = _evidence_aware_reverify
    VerifiedReviewCompletion._pr_inspector_evidence_aware = True


def _bind_evidence(
    result: VerifiedReviewCompletion | IncompleteReview,
    governance_evidence: VerifiedGovernanceEvidence | None,
    sequence_enforcement: VerifiedSequenceEnforcement | None,
) -> None:
    if is_verified_review_completion(result):
        assert isinstance(result, VerifiedReviewCompletion)
        _BOUND_EVIDENCE[result] = (governance_evidence, sequence_enforcement)


def _incomplete(code: str, path: str, message: str) -> IncompleteReview:
    return IncompleteReview((Diagnostic(code, path, message),))


def complete_review(
    request: ReviewRequest | object | None = None,
    assessment: ReviewAssessment | None = None,
    output_directory: Path | None = None,
    *,
    evidence_source: ReviewEvidenceSource | None = None,
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
    package_path: Path | None = None,
    _protocol_context: ProtocolContext | None = None,
) -> VerifiedReviewCompletion | IncompleteReview:
    """Collect, assemble, validate, and publish one official review bundle.

    `package_path` and positional package/path inputs are intentionally retained only
    to return one stable migration diagnostic. They can never publish artifacts.
    """

    if package_path is not None or isinstance(
        request, (str, Path, Mapping, CanonicalReviewPackage)
    ):
        return _incomplete(
            "PRI-PACKAGE-AUTHORITY-001",
            "/review-request",
            (
                "v1.12 official completion no longer accepts caller-authored package "
                "files or package objects; provide ReviewRequest, ReviewAssessment, "
                "and ReviewEvidenceSource"
            ),
        )
    if not isinstance(request, ReviewRequest):
        return _incomplete(
            "PRI-ASSEMBLY-REQUEST-001", "/review-request", "ReviewRequest is required"
        )
    if not isinstance(assessment, ReviewAssessment):
        return _incomplete(
            "PRI-ASSEMBLY-ASSESSMENT-001",
            "/review-assessment",
            "ReviewAssessment is required",
        )
    if output_directory is None:
        return _incomplete(
            "PRI-COMPLETE-005", "/output-directory", "output_directory is required"
        )
    if evidence_source is None:
        return _incomplete(
            "PRI-ASSEMBLY-SOURCE-001",
            "/evidence-source",
            "ReviewEvidenceSource is required",
        )
    try:
        facts = collect_review_facts(request, evidence_source)
        context = _protocol_context or ProtocolContext.from_repository()
        package = assemble_review_package(
            facts,
            assessment,
            context,
            inspection_profile=request.inspection_profile,
            governance_evidence=governance_evidence,
            sequence_enforcement=sequence_enforcement,
        )
    except (ReviewAssemblyError, OSError, ValueError, KeyError, TypeError) as exc:
        return _incomplete("PRI-ASSEMBLY-001", "/review-assembly", str(exc))
    with evidence_scope(governance_evidence, sequence_enforcement):
        result = _publish_assembled_review(
            package,
            Path(output_directory),
            head_source=evidence_source,
        )
    _bind_evidence(result, governance_evidence, sequence_enforcement)
    return result


def verify_completed_review(
    review_directory: Path,
    *,
    head_source: GitHubPullRequestHeadSource,
    package: CanonicalReviewPackage | None = None,
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> VerifiedReviewCompletion:
    """Reverify final bytes against the same assembled package and live Head."""

    with evidence_scope(governance_evidence, sequence_enforcement):
        result = _verify_completed_review(
            review_directory,
            head_source=head_source,
            package=package,
        )
    _bind_evidence(result, governance_evidence, sequence_enforcement)
    return result


__all__ = [
    "CanonicalReviewPackage",
    "ChangedFile",
    "CheckFact",
    "CompletionError",
    "EvidenceRecord",
    "FIELD_AUTHORITY",
    "GitHubPullRequestHeadSource",
    "GitHubReviewEvidenceSource",
    "IncompleteReview",
    "ProtocolContext",
    "ReviewAssemblyError",
    "ReviewAssessment",
    "ReviewEvidenceSource",
    "ReviewFacts",
    "ReviewFinding",
    "ReviewRequest",
    "VerifiedLivePullRequestHead",
    "VerifiedReviewCompletion",
    "assemble_review_package",
    "collect_review_facts",
    "complete_review",
    "github_pull_request_head_source",
    "is_verified_review_completion",
    "official_next_action_prompt",
    "official_owner_delivery",
    "official_owner_profile_commands",
    "official_owner_result",
    "official_technical_handoff",
    "parse_review_assessment",
    "render_unverified_preview",
    "verify_completed_review",
]
