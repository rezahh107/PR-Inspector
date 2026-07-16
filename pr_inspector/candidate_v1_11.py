from __future__ import annotations

from typing import Any

from .candidate_v1_11_base import *  # noqa: F401,F403
from .candidate_v1_11_repair import (
    ORCHESTRATION_STATES,
    StrictOrchestrationResult,
    VerifiedPullRequestHead,
    _target_from_verified_bundle,
    orchestrate_strict_review,
    parse_intake as _repaired_parse_intake,
    verify_pull_request_head_response,
)


def parse_intake(text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Route Candidate intake while treating caller context only as a consistency guard."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    strict_without_url = bool(lines and lines[0] == STRICT and not any(PR_URL_RE.match(line) for line in lines[1:]))
    if strict_without_url and context and "current_target" in context:
        verified_target = _target_from_verified_bundle(context.get("verified_minimal_review"))
        supplied = context.get("current_target")
        supplied_valid = (
            isinstance(supplied, dict)
            and isinstance(supplied.get("repository_id"), int)
            and supplied.get("repository_id") > 0
            and verified_target is not None
            and supplied.get("repository") == verified_target["repository"]
            and supplied.get("repository_id") == verified_target["repository_id"]
            and supplied.get("pull_request") == verified_target["pull_request"]
        )
        if not supplied_valid:
            return {
                "inspection_profile": STRICT,
                "target": None,
                "reuse_current_minimal": False,
                "refresh_minimal": False,
                "orchestration_state": None,
                "missing": ["pull_request_url"],
            }
    return _repaired_parse_intake(text, context)
