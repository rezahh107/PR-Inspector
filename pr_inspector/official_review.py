"""Supported official review completion boundary.

Low-level projection/rendering helpers do not prove completion. Public official output
is available only through the live-GitHub-bound objects re-exported here.
"""

from ._official_bundle import (
    IncompleteReview,
    VerifiedReviewCompletion,
    is_verified_review_completion,
    official_next_action_prompt,
    official_owner_result,
    official_technical_handoff,
    verify_completed_review,
)
from ._official_complete import complete_review
from ._official_head import (
    CompletionError,
    GitHubPullRequestHeadSource,
    VerifiedLivePullRequestHead,
    github_pull_request_head_source,
)

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
