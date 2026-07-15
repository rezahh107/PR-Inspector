"""Supported official review completion boundary.

Low-level projection/rendering helpers do not prove completion. Public official output
is available only through the live-GitHub-bound objects re-exported here.
"""

from __future__ import annotations

import weakref
from pathlib import Path

from ._official_bundle import (
    PROMPT_NAME,
    PROJECTION_NAME,
    IncompleteReview,
    VerifiedReviewCompletion,
    is_verified_review_completion,
    json_object_bytes,
    official_next_action_prompt,
    official_technical_handoff,
    required_artifact_bytes,
    utf8_bytes,
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

_BOUND_EVIDENCE: weakref.WeakKeyDictionary[
    VerifiedReviewCompletion,
    tuple[VerifiedGovernanceEvidence | None, VerifiedSequenceEnforcement | None],
] = weakref.WeakKeyDictionary()
_ORIGINAL_REVERIFY = VerifiedReviewCompletion._reverify
_OWNER_DELIVERY_HEADING = "\n## متن کامل اقدام بعدی\n\n"


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
    if not is_verified_review_completion(result):
        return
    assert isinstance(result, VerifiedReviewCompletion)
    _BOUND_EVIDENCE[result] = (governance_evidence, sequence_enforcement)


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


def _verified_bundle_snapshot(value: VerifiedReviewCompletion):
    if not is_verified_review_completion(value):
        raise CompletionError("official owner output requires verified completion")
    return value._reverify()


def _owner_result_from_bundle(bundle) -> str:
    return utf8_bytes(
        "OWNER_RESULT.fa.txt",
        required_artifact_bytes(bundle.artifact_bytes, "OWNER_RESULT.fa.txt"),
    )


def _projection_from_bundle(bundle) -> dict:
    return json_object_bytes(
        PROJECTION_NAME,
        required_artifact_bytes(bundle.artifact_bytes, PROJECTION_NAME),
    )


def official_owner_result(value: VerifiedReviewCompletion) -> str:
    """Return owner-only output only when no conditional action prompt is required.

    Human-facing callers must use ``official_owner_delivery`` for prompt-required
    decisions so the status message cannot be delivered without its verified prompt.
    """

    bundle = _verified_bundle_snapshot(value)
    projection = _projection_from_bundle(bundle)
    if projection["next_action"]["prompt_required"]:
        raise CompletionError(
            "prompt-required owner output must use official_owner_delivery"
        )
    return _owner_result_from_bundle(bundle)


def official_owner_delivery(value: VerifiedReviewCompletion) -> str:
    """Return one atomic owner-facing delivery from one verified byte snapshot."""

    bundle = _verified_bundle_snapshot(value)
    owner_result = _owner_result_from_bundle(bundle)
    projection = _projection_from_bundle(bundle)
    prompt_required = projection["next_action"]["prompt_required"]
    prompt_bytes = bundle.artifact_bytes.get(PROMPT_NAME)

    if not prompt_required:
        if prompt_bytes is not None:
            raise CompletionError(
                "canonical projection forbids a next-action prompt"
            )
        return owner_result

    if prompt_bytes is None:
        raise CompletionError(
            "canonical projection requires a next-action prompt"
        )
    prompt = utf8_bytes(PROMPT_NAME, prompt_bytes)
    return owner_result + _OWNER_DELIVERY_HEADING + prompt


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
    "official_owner_delivery",
    "official_owner_result",
    "official_technical_handoff",
    "verify_completed_review",
]
