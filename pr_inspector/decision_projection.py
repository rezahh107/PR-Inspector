"""Active decision projection with v1.11 post-activation hardening."""

from __future__ import annotations

from typing import Any

from . import _decision_projection_impl as _impl
from .governance import VerifiedGovernanceEvidence, is_verified_governance_evidence
from .runtime_v1_11 import (
    MINIMAL,
    STRICT,
    collect_candidate_technical_reasons,
    project_decision as project_profile_decision,
)
from .sequence_enforcement import VerifiedSequenceEnforcement

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

ProjectionError = _impl.ProjectionError
_original_project_decision = _impl.project_decision
_original_validate_projection_invariants = _impl.validate_projection_invariants

_PROFILE_TO_CANONICAL_STATUS = {
    "GREEN": _impl._core.STATUS_GREEN,
    "YELLOW": _impl._core.STATUS_YELLOW,
    "RED": _impl._core.STATUS_RED,
}


def _technical_decision(pkg: dict[str, Any]) -> dict[str, Any]:
    try:
        reason_codes = collect_candidate_technical_reasons(pkg)
        decision = project_profile_decision(MINIMAL, reason_codes)[
            "technical_decision"
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectionError(
            f"cannot derive v1.11 technical decision: {exc}"
        ) from exc
    return {
        "status": decision["status"],
        "reason_codes": list(decision["reason_codes"]),
    }


def _governance_decision(
    profile: str,
    evidence: VerifiedGovernanceEvidence | None,
    pkg: dict[str, Any],
) -> dict[str, Any]:
    if profile == MINIMAL:
        return {"status": "NOT_REQUESTED", "reason_codes": []}
    if profile != STRICT:
        raise ProjectionError("unknown inspection_profile")
    if not is_verified_governance_evidence(evidence):
        return {
            "status": "NOT_VERIFIABLE",
            "reason_codes": ["repository_settings_not_verified"],
        }
    identity = pkg.get("review_identity")
    if not isinstance(identity, dict):
        raise ProjectionError("review identity is missing for Strict governance")
    if (
        evidence.repository != identity.get("target_repository")
        or evidence.pull_request_number != identity.get("pr_number")
        or evidence.exact_head_sha != identity.get("reviewed_head_sha")
    ):
        return {
            "status": "NOT_VERIFIABLE",
            "reason_codes": ["repository_settings_not_verified"],
        }
    if evidence.merge_authorized:
        return {"status": "VERIFIED", "reason_codes": []}
    return {
        "status": "GAP_FOUND",
        "reason_codes": ["merge_authorization_unverified"],
    }


def project_decision(
    pkg: dict[str, Any],
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> dict[str, Any]:
    governance_evidence, sequence_enforcement = _impl._resolved_evidence(
        governance_evidence,
        sequence_enforcement,
    )
    projection = _original_project_decision(
        pkg,
        governance_evidence,
        sequence_enforcement,
    )
    profile = pkg.get("inspection_profile", MINIMAL)
    technical = _technical_decision(pkg)
    governance = _governance_decision(profile, governance_evidence, pkg)
    if _PROFILE_TO_CANONICAL_STATUS[technical["status"]] != projection[
        "technical_status"
    ]:
        raise ProjectionError(
            "v1.11 technical decision disagrees with canonical technical status"
        )

    projection["inspection_profile"] = profile
    projection["technical_decision"] = technical
    projection["governance_decision"] = governance
    projection["overall_recommendation"] = {
        "technical_ready": technical["status"] == "GREEN",
        "merge_governance_verified": governance["status"] == "VERIFIED",
    }
    projection["governance_follow_up"] = {
        "kind": (
            "none"
            if governance["status"] in {"NOT_REQUESTED", "VERIFIED"}
            else "access_limitation"
            if governance["status"] == "NOT_VERIFIABLE"
            else "informational_gap"
        ),
        "may_modify_code": False,
        "prompt_required": False,
    }
    validate_projection_invariants(projection)
    return projection


def validate_projection_invariants(projection: dict[str, Any]) -> None:
    _original_validate_projection_invariants(projection)
    technical = projection.get("technical_decision")
    governance = projection.get("governance_decision")
    overall = projection.get("overall_recommendation")
    follow_up = projection.get("governance_follow_up")
    if not all(isinstance(item, dict) for item in (technical, governance, overall, follow_up)):
        raise ProjectionError("active v1.11 projection fields are incomplete")
    if _PROFILE_TO_CANONICAL_STATUS.get(technical.get("status")) != projection[
        "technical_status"
    ]:
        raise ProjectionError(
            "active technical decision contradicts canonical technical status"
        )
    if overall.get("technical_ready") is not (technical.get("status") == "GREEN"):
        raise ProjectionError("technical_ready contradicts technical decision")
    if overall.get("merge_governance_verified") is not (
        governance.get("status") == "VERIFIED"
    ):
        raise ProjectionError(
            "merge_governance_verified contradicts governance decision"
        )
    if (
        projection.get("inspection_profile") == MINIMAL
        and governance != {"status": "NOT_REQUESTED", "reason_codes": []}
    ):
        raise ProjectionError("Minimal governance must be NOT_REQUESTED")
    if follow_up.get("may_modify_code") is not False or follow_up.get(
        "prompt_required"
    ) is not False:
        raise ProjectionError("governance follow-up cannot grant repair authority")


_impl.project_decision = project_decision
_impl.validate_projection_invariants = validate_projection_invariants

for _name in (
    "projection_json",
    "owner_result_text",
    "owner_status_text",
    "owner_action_text",
    "expected_technical_status",
):
    globals()[_name] = getattr(_impl, _name)

__all__ = sorted(name for name in globals() if not name.startswith("__"))
