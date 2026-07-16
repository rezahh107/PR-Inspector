from __future__ import annotations

import json
from typing import Any

from . import decision_projection_core as _core
from .evidence_context import current_evidence
from .governance import (
    VerifiedGovernanceEvidence,
    is_verified_governance_evidence,
)
from .security_profile import SecurityProfileAssessment, assess_security_profile
from .sequence_enforcement import VerifiedSequenceEnforcement

ProjectionError = _core.ProjectionError
ACTION_ROUTING = _core.ACTION_ROUTING
OWNER_RESULT_REGISTRY = _core.OWNER_RESULT_REGISTRY
OWNER_STATUS_TEXT = _core.OWNER_STATUS_TEXT
OWNER_ACTION_TEXT = _core.OWNER_ACTION_TEXT
reason_registry_entries = _core.reason_registry_entries
reason_registry_by_code = _core.reason_registry_by_code

_MINIMAL = "minimal"
_STRICT = "strict"
_CANDIDATE_STATUS_BY_TECHNICAL_STATUS = {
    _core.STATUS_GREEN: "GREEN",
    _core.STATUS_YELLOW: "YELLOW",
    _core.STATUS_RED: "RED",
}
_CANDIDATE_REASON_BY_CANONICAL = {
    "RSN-REVIEW-NOT-CURRENT": "stale_technical_review_identity",
    "RSN-REQUIRED-CHECK-FAILED": "required_technical_check_failed",
    "RSN-CRITICAL-SUPPORTED-FINDING": "critical_supported_finding",
    "RSN-HIGH-REPRODUCED-FINDING": "high_reproduced_finding",
    "RSN-BLOCKING-MEDIUM-SUPPORTED": "blocking_medium_finding",
    "RSN-COVERAGE-INCOMPLETE": "incomplete_technical_scope",
    "RSN-REQUIRED-CHECK-UNRESOLVED": "bot_collection_incomplete",
    "RSN-HIGH-CODE-SUPPORTED-FINDING": "unresolved_valid_bot_finding",
}
_GOVERNANCE_REASON_STATUS = {
    "repository_settings_not_verified": "NOT_VERIFIABLE",
    "branch_protection_unavailable": "GAP_FOUND",
    "bypass_actors_unknown": "GAP_FOUND",
    "merge_authorization_unverified": "GAP_FOUND",
    "merge_queue_unavailable": "GAP_FOUND",
    "required_checks_not_verified": "GAP_FOUND",
    "required_review_enforcement_absent": "GAP_FOUND",
    "rulesets_unavailable": "GAP_FOUND",
    "sequence_enforcement_missing": "GAP_FOUND",
}
_GOVERNANCE_STATUSES = {
    "NOT_REQUESTED",
    "VERIFIED",
    "NOT_VERIFIABLE",
    "GAP_FOUND",
}


def _profile_reason_instances(assessment: SecurityProfileAssessment) -> list[dict[str, Any]]:
    return [
        {"reason_code": code, "subjects": [assessment.profile_name]}
        for code in assessment.reason_codes
    ]


def _canonical_reason_instances(
    pkg: dict[str, Any], assessment: SecurityProfileAssessment
) -> list[dict[str, Any]]:
    instances = list(_core.collect_reason_instances(pkg))
    instances.extend(_profile_reason_instances(assessment))
    order = {
        item["reason_code"]: index
        for index, item in enumerate(reason_registry_entries())
    }
    return sorted(instances, key=lambda item: order[item["reason_code"]])


def _resolved_evidence(
    governance_evidence: VerifiedGovernanceEvidence | None,
    sequence_enforcement: VerifiedSequenceEnforcement | None,
) -> tuple[
    VerifiedGovernanceEvidence | None,
    VerifiedSequenceEnforcement | None,
]:
    current_governance, current_sequence = current_evidence()
    if governance_evidence is None and isinstance(
        current_governance, VerifiedGovernanceEvidence
    ):
        governance_evidence = current_governance
    if sequence_enforcement is None and isinstance(
        current_sequence, VerifiedSequenceEnforcement
    ):
        sequence_enforcement = current_sequence
    return governance_evidence, sequence_enforcement


def _inspection_profile(pkg: dict[str, Any]) -> str:
    profile = pkg.get("inspection_profile", _MINIMAL)
    if profile not in {_MINIMAL, _STRICT}:
        raise ProjectionError("inspection_profile must be minimal or strict")
    return profile


def _candidate_technical_reasons(canonical_codes: list[str]) -> list[str]:
    return list(
        dict.fromkeys(
            _CANDIDATE_REASON_BY_CANONICAL[code]
            for code in canonical_codes
            if code in _CANDIDATE_REASON_BY_CANONICAL
        )
    )


def _governance_decision(
    profile: str,
    pkg: dict[str, Any],
    governance_evidence: VerifiedGovernanceEvidence | None,
) -> dict[str, Any]:
    if profile == _MINIMAL:
        return {"status": "NOT_REQUESTED", "reason_codes": []}

    identity = pkg.get("review_identity")
    if (
        not isinstance(identity, dict)
        or not is_verified_governance_evidence(governance_evidence)
        or governance_evidence.repository != identity.get("target_repository")
        or governance_evidence.pull_request_number != identity.get("pr_number")
        or governance_evidence.exact_head_sha != identity.get("reviewed_head_sha")
    ):
        return {
            "status": "NOT_VERIFIABLE",
            "reason_codes": ["repository_settings_not_verified"],
        }

    if governance_evidence.merge_authorized:
        return {"status": "VERIFIED", "reason_codes": []}
    return {
        "status": "GAP_FOUND",
        "reason_codes": ["merge_authorization_unverified"],
    }


def _governance_follow_up(governance_decision: dict[str, Any]) -> dict[str, Any]:
    status = governance_decision["status"]
    if status in {"NOT_REQUESTED", "VERIFIED"}:
        kind = "none"
    elif status == "NOT_VERIFIABLE":
        kind = "access_limitation"
    else:
        kind = "informational_gap"
    return {"kind": kind, "may_modify_code": False, "prompt_required": False}


def project_decision(
    pkg: dict[str, Any],
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> dict[str, Any]:
    """Produce the sole official active decision projection."""

    governance_evidence, sequence_enforcement = _resolved_evidence(
        governance_evidence,
        sequence_enforcement,
    )
    assessment = assess_security_profile(
        pkg,
        governance_evidence,
        sequence_enforcement,
    )
    reason_instances = _canonical_reason_instances(pkg, assessment)
    all_codes = [item["reason_code"] for item in reason_instances]
    technical_status, technical_codes = _core._technical_status(all_codes)
    action_kind, action_codes = _core._choose_action(pkg, technical_status, all_codes)
    route = ACTION_ROUTING[action_kind]
    color = _core._owner_color(technical_status, action_kind)
    message_key = _core._owner_message_key(color, action_kind)

    inspection_profile = _inspection_profile(pkg)
    technical_decision = {
        "status": _CANDIDATE_STATUS_BY_TECHNICAL_STATUS[technical_status],
        "reason_codes": _candidate_technical_reasons(all_codes),
    }
    governance_decision = _governance_decision(
        inspection_profile,
        pkg,
        governance_evidence,
    )
    overall_recommendation = {
        "technical_ready": technical_decision["status"] == "GREEN",
        "merge_governance_verified": governance_decision["status"] == "VERIFIED",
    }
    governance_follow_up = _governance_follow_up(governance_decision)

    projection = {
        "schema_version": 1,
        "protocol_version": _core.CURRENT_VERSION,
        "inspection_profile": inspection_profile,
        "technical_decision": technical_decision,
        "governance_decision": governance_decision,
        "overall_recommendation": overall_recommendation,
        "governance_follow_up": governance_follow_up,
        "technical_status": technical_status,
        "technical_status_reason_codes": technical_codes,
        "approval_requirement": pkg["decision"]["approval_requirement"],
        "security_profile": assessment.projection(),
        "owner_readiness": {
            "color": color,
            "action_kind": action_kind,
            "message_key": message_key,
            "reason_codes": list(dict.fromkeys(technical_codes + action_codes)),
        },
        "next_action": {
            "kind": action_kind,
            "recipient": route["recipient"],
            "may_modify_code": route["may_modify_code"],
            "prompt_required": route["prompt_required"],
            "prompt_kind": route["prompt_kind"],
            "reason_codes": action_codes,
        },
        "review_identity": {
            "validity": pkg["review_identity"]["review_validity"],
            "reviewed_head_sha": pkg["review_identity"]["reviewed_head_sha"],
        },
        "reason_details": reason_instances,
        "required_actions": list(pkg.get("required_actions", [])),
    }
    validate_projection_invariants(projection)
    return projection


def validate_projection_invariants(projection: dict[str, Any]) -> None:
    _core.validate_projection_invariants(projection)
    profile = projection.get("security_profile")
    if not isinstance(profile, dict):
        raise ProjectionError("canonical security profile is missing")
    profile_codes = profile.get("reason_codes")
    if not isinstance(profile_codes, list):
        raise ProjectionError("security-profile reason codes are invalid")
    detail_codes = {item["reason_code"] for item in projection["reason_details"]}
    if any(code not in detail_codes for code in profile_codes):
        raise ProjectionError(
            "security-profile reasons are missing from canonical reason details"
        )
    if profile["blocks_green_merge_recommendation"]:
        if (
            projection["technical_status"] == _core.STATUS_GREEN
            or projection["next_action"]["kind"] == "merge_now"
        ):
            raise ProjectionError(
                "blocking security profile cannot produce technical Green or merge_now"
            )
    if (
        profile["repository_settings_enforced"] == "verified"
        and profile["governance_evidence_status"] != "verified"
    ):
        raise ProjectionError(
            "verified repository settings require verified governance evidence"
        )
    if (
        profile["merge_authorized"] == "verified"
        and profile["governance_evidence_status"] != "verified"
    ):
        raise ProjectionError(
            "verified merge authorization requires verified governance evidence"
        )

    inspection_profile = projection.get("inspection_profile")
    if inspection_profile not in {_MINIMAL, _STRICT}:
        raise ProjectionError("canonical inspection profile is invalid")
    expected_candidate_status = _CANDIDATE_STATUS_BY_TENICAL_STATUS.get(
        projection.get("technical_status")
    )
    technical_decision = projection.get("technical_decision")
    if (
        not isinstance(technical_decision, dict)
        or technical_decision.get("status") != expected_candidate_status
    ):
        raise ProjectionError("technical_decision contradicts canonical technical status")
    technical_reasons = technical_decision.get("reason_codes")
    if not isinstance(technical_reasons, list) or any(
        reason not in _CANDIDATE_REASON_BY_CANONICAL.values()
        for reason in technical_reasons
    ):
        raise ProjectionError("technical_decision reason codes are invalid")

    governance_decision = projection.get("governance_decision")
    if not isinstance(governance_decision, dict):
        raise ProjectionError("canonical governance decision is missing")
    governance_status = governance_decision.get("status")
    if governance_status not in _GOVERNANCE_STATUSES:
        raise ProjectionError("canonical governance status is invalid")
    governance_reasons = governance_decision.get("reason_codes")
    if not isinstance(governance_reasons, list):
        raise ProjectionError("governance reason codes are invalid")
    if governance_status in {"NOT_REQUESTED", "VERIFIED"} and governance_reasons:
        raise ProjectionError("governance decision has reasons for a non-gap status")
    if governance_status in {"NOT_VERIFIABLE", "GAP_FOUND"}:
        if not governance_reasons or any(
            _GOVERNANCE_REASON_STATUS.get(reason) != governance_status
            for reason in governance_reasons
        ):
            raise ProjectionError("governance reasons contradict governance status")
    if inspection_profile == _MINIMAL and governance_status != "NOT_REQUESTED":
        raise ProjectionError("minimal profile must not request governance evaluation")

    overall = projection.get("overall_recommendation")
    if not isinstance(overall, dict):
        raise ProjectionError("overall recommendation is missing")
    if overall.get("technical_ready") != (expected_candidate_status == "GREEN"):
        raise ProjectionError("technical_ready contradicts technical status")
    if overall.get("merge_governance_verified") != (
        governance_status == "VERIFIED"
    ):
        raise ProjectionError(
            "merge_governance_verified contradicts governance status"
        )
    if projection.get("governance_follow_up") != _governance_follow_up(
        governance_decision
    ):
        raise ProjectionError("governance follow-up contradicts governance decision")


def projection_json(projection: dict[str, Any]) -> str:
    validate_projection_invariants(projection)
    return (
        json.dumps(
            projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    )


def owner_result_text(projection: dict[str, Any]) -> str:
    validate_projection_invariants(projection)
    return OWNER_RESULT_REGISTRY[projection["owner_readiness"]["message_key"]]


def owner_status_text(projection: dict[str, Any]) -> str:
    validate_projection_invariants(projection)
    return OWNER_STATUS_TEXT[projection["owner_readiness"]["color"]]


def owner_action_text(projection: dict[str, Any]) -> str:
    validate_projection_invariants(projection)
    return OWNER_ACTION_TEXT[projection["owner_readiness"]["action_kind"]]


def expected_technical_status(
    pkg: dict[str, Any],
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> tuple[str, list[str]]:
    projection = project_decision(
        pkg,
        governance_evidence,
        sequence_enforcement,
    )
    return (
        projection["technical_status"],
        projection["technical_status_reason_codes"],
    )
