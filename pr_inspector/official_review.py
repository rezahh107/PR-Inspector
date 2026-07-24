"""Supported v1.12 official review runtime.

The public completion boundary accepts only caller intent, bounded assessment, and an
output directory.  Official evidence and protocol context are constructed internally.
"""

from __future__ import annotations

import os
import weakref
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ._official_bundle import (
    IncompleteReview,
    VerifiedReviewCompletion,
    is_verified_review_completion,
    official_next_action_prompt,
    official_technical_handoff,
    reverify_completed_review as _reverify_completed_review,
)
from ._official_complete import complete_review as _publish_assembled_review
from ._official_head import CompletionError
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
    ExternalReviewDisposition,
    GitHubReviewEvidenceSource,
    ProtocolContext,
    ReviewAssemblyError,
    ReviewAssessment,
    ReviewEvidenceSource,
    ReviewFacts,
    ReviewFinding,
    ReviewRequest,
    assemble_review_package,
    collect_review_facts as _collect_review_facts_from_source,
    parse_review_assessment,
    render_unverified_preview,
)
from ._official_head import github_pull_request_head_source

ROOT = Path(__file__).resolve().parents[1]
_GITHUB_API_VERSION = "2022-11-28"

_BOUND_EVIDENCE: weakref.WeakKeyDictionary[
    VerifiedReviewCompletion,
    tuple[VerifiedGovernanceEvidence | None, VerifiedSequenceEnforcement | None],
] = weakref.WeakKeyDictionary()
_ORIGINAL_REVERIFY = VerifiedReviewCompletion._reverify


@dataclass(frozen=True)
class OfficialReviewRuntime:
    """Internal runtime bundle; intentionally excluded from the public API export list."""

    evidence_source: ReviewEvidenceSource
    protocol_context: ProtocolContext
    governance_evidence: VerifiedGovernanceEvidence | None = None
    sequence_enforcement: VerifiedSequenceEnforcement | None = None


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


def _create_official_runtime(request: ReviewRequest) -> OfficialReviewRuntime:
    """Construct the sole production runtime from verified local and GitHub state."""

    if not isinstance(request, ReviewRequest):
        raise ReviewAssemblyError("ReviewRequest is required")
    checkout_hint = request.execution_options.get("repository_directory", Path.cwd())
    repository_directory = Path(checkout_hint).expanduser().resolve()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    protocol_context = ProtocolContext.from_verified_repository(
        ROOT,
        token=token,
        api_version=_GITHUB_API_VERSION,
    )
    head_source = github_pull_request_head_source(
        request.target_repository,
        request.pr_number,
        token=token,
        api_version=_GITHUB_API_VERSION,
    )
    evidence_source = GitHubReviewEvidenceSource(
        repository_directory=repository_directory,
        head_source=head_source,
        token=token,
        api_version=_GITHUB_API_VERSION,
        required_check_names=protocol_context.required_check_names,
    )
    return OfficialReviewRuntime(evidence_source, protocol_context)


def collect_review_facts(request: ReviewRequest) -> ReviewFacts:
    """Collect a read-only evidence catalog through the internal official runtime."""

    runtime = _create_official_runtime(request)
    return _collect_review_facts_from_source(request, runtime.evidence_source)


def _complete_review_with_runtime(
    request: ReviewRequest,
    assessment: ReviewAssessment,
    output_directory: Path,
    *,
    runtime: OfficialReviewRuntime,
) -> VerifiedReviewCompletion | IncompleteReview:
    """Private deterministic seam used by production and internal tests."""

    if not isinstance(runtime, OfficialReviewRuntime):
        return _incomplete(
            "PRI-ASSEMBLY-RUNTIME-001", "/review-runtime", "OfficialReviewRuntime is required"
        )
    try:
        facts = _collect_review_facts_from_source(request, runtime.evidence_source)
        package = assemble_review_package(
            facts,
            assessment,
            runtime.protocol_context,
            inspection_profile=request.inspection_profile,
            governance_evidence=runtime.governance_evidence,
            sequence_enforcement=runtime.sequence_enforcement,
        )
    except (ReviewAssemblyError, OSError, ValueError, KeyError, TypeError) as exc:
        return _incomplete("PRI-ASSEMBLY-001", "/review-assembly", str(exc))
    with evidence_scope(runtime.governance_evidence, runtime.sequence_enforcement):
        result = _publish_assembled_review(
            package,
            Path(output_directory),
            head_source=runtime.evidence_source,
        )
    _bind_evidence(result, runtime.governance_evidence, runtime.sequence_enforcement)
    return result


def complete_review(
    request: ReviewRequest | object | None = None,
    assessment: ReviewAssessment | None = None,
    output_directory: Path | None = None,
    *,
    package_path: Path | None = None,
) -> VerifiedReviewCompletion | IncompleteReview:
    """Create and execute the internal official runtime for one review.

    `package_path` and positional package/path inputs are retained only as a stable
    migration failure.  Caller-provided sources, facts, heads, or protocol contexts are
    not parameters of this public API.
    """

    if package_path is not None or isinstance(
        request, (str, Path, Mapping, CanonicalReviewPackage)
    ):
        return _incomplete(
            "PRI-PACKAGE-AUTHORITY-001",
            "/review-request",
            (
                "v1.12 official completion no longer accepts caller-authored package "
                "files or package objects; provide ReviewRequest and ReviewAssessment"
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
    try:
        runtime = _create_official_runtime(request)
    except (ReviewAssemblyError, CompletionError, OSError, ValueError, KeyError, TypeError) as exc:
        return _incomplete("PRI-ASSEMBLY-RUNTIME-001", "/review-runtime", str(exc))
    return _complete_review_with_runtime(
        request,
        assessment,
        Path(output_directory),
        runtime=runtime,
    )


def reverify_completed_review(
    completion: VerifiedReviewCompletion,
) -> VerifiedReviewCompletion:
    """Revalidate the original genuine completion without minting a replacement."""

    return _reverify_completed_review(completion)


def verify_completed_review(
    completion: VerifiedReviewCompletion,
) -> VerifiedReviewCompletion:
    """Compatibility name for completion-centric re-verification."""

    return reverify_completed_review(completion)


__all__ = [
    "CompletionError",
    "ExternalReviewDisposition",
    "IncompleteReview",
    "ReviewAssemblyError",
    "ReviewAssessment",
    "ReviewFinding",
    "ReviewRequest",
    "VerifiedReviewCompletion",
    "collect_review_facts",
    "complete_review",
    "is_verified_review_completion",
    "official_next_action_prompt",
    "official_owner_delivery",
    "official_owner_profile_commands",
    "official_owner_result",
    "official_technical_handoff",
    "parse_review_assessment",
    "render_unverified_preview",
    "reverify_completed_review",
    "verify_completed_review",
]
