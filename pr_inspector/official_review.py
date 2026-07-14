"""Supported official review completion boundary.

Low-level projection/rendering helpers do not prove completion. Public official output
is available only through the live-GitHub-bound objects re-exported here.
"""

from __future__ import annotations

import weakref
from pathlib import Path

from ._official_bundle import (
    IncompleteReview,
    VerifiedReviewCompletion,
    is_verified_review_completion,
    official_next_action_prompt,
    official_owner_result,
    official_technical_handoff,
    verify_completed_review as _verify_completed_review,
)
from ._official_complete import complete_review as _complete_review
from ._official_head import (
    CompletionError,
    GitHubPullRequestHeadSource,
    VerifiedLivePullRequestHead,
    github_pull_request_head_source,
)
from .evidence_context import evidence_scope
from .governance import VerifiedGovernanceEvidence
from .sequence_enforcement import VerifiedSequenceEnforcement

_BOUND_EVIDENCE: dict[
    int,
    tuple[
        weakref.ReferenceType[VerifiedReviewCompletion],
        VerifiedGovernanceEvidence | None,
        VerifiedSequenceEnforcement | None,
    ],
] = {}
_ORIGINAL_REVERIFY = VerifiedReviewCompletion._reverify


def _evidence_aware_reverify(self: VerifiedReviewCompletion):
    bound = _BOUND_EVIDENCE.get(id(self))
    if bound is None or bound[0]() is not self:
        return _ORIGINAL_REVERIFY(self)
    with evidence_scope(bound[1], bound[2]):
        return _ORIGINAL_REVERIFY(self)


if not getattr(VerifiedReviewCompletion, "_pr_inspector_evidence_aware", False):
    VerifiedReviewCompletion._reverify = _evidence_aware_reverify
    VerifiedReviewCompletion._pr_inspector_evidence_aware = True


def _bind_evidence(
    result: VerifiedReviewCompletion | IncompleteReview,
    governance_evidence: VerifiedGovernanceEvidence | None,
    sequence_enforcement: VerifiedSequenceEnforcement | None,
) -> None:
    if not is_verified_review_completion(result):
        return
    assert isinstance(result, VerifiedReviewCompletion)
    key = id(result)

    def cleanup(_reference: weakref.ReferenceType[VerifiedReviewCompletion]) -> None:
        _BOUND_EVIDENCE.pop(key, None)

    reference = weakref.ref(result, cleanup)
    _BOUND_EVIDENCE[key] = (
        reference,
        governance_evidence,
        sequence_enforcement,
    )


def complete_review(
    package_path: Path,
    output_directory: Path,
    *,
    head_source: GitHubPullRequestHeadSource,
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> VerifiedReviewCompletion | IncompleteReview:
    """Complete and publish one evidence-consistent official review bundle."""

    with evidence_scope(governance_evidence, sequence_enforcement):
        result = _complete_review(
            package_path,
            output_directory,
            head_source=head_source,
        )
    _bind_evidence(result, governance_evidence, sequence_enforcement)
    return result


def verify_completed_review(
    review_directory: Path,
    *,
    head_source: GitHubPullRequestHeadSource,
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> VerifiedReviewCompletion:
    """Reverify final bytes with the same opaque evidence used for projection."""

    with evidence_scope(governance_evidence, sequence_enforcement):
        result = _verify_completed_review(
            review_directory,
            head_source=head_source,
        )
    _bind_evidence(result, governance_evidence, sequence_enforcement)
    return result


__all__ = [
    "CompletionError",
    "GitHubPullRequestHeadSource",
    "IncompleteReview",
    "VerifiedLivePullRequestHead",
    "VerifiedReviewCompletion",
    "complete_review",
    "github_pull_request_head_source",
    "is_verified_review_completion",
    "official_next_action_prompt",
    "official_owner_result",
    "official_technical_handoff",
    "verify_completed_review",
]
