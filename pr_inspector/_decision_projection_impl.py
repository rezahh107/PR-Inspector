from __future__ import annotations

import json
from typing import Any

from . import decision_projection_core as _core
from .evidence_context import current_evidence
from .governance import VerifiedGovernanceEvidence
from .security_profile import SecurityProfileAssessment, assess_security_profile
from .sequence_enforcement import VerifiedSequenceEnforcement

ProjectionError = _core.ProjectionError
ACTION_ROUTING = _core.ACTION_ROUTING
OWNER_RESULT_REGISTRY = _core.OWNER_RESULT_REGISTRY
OWNER_STATUS_TEXT = _core.OWNER_STATUS_TEXT
OWNER_ACTION_TEXT = _core.OWNER_ACTION_TEXT
reason_registry_entries = _core.reason_registry_entries
reason_registry_by_code = _core.reason_registry_by_code


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

    inspection_profile = pkg.get("inspection_profile", "minimal")
    technical_decision = pkg.get("technical_decision") or {
        "status": "GREEN" if technical_status == _core.STATUS_GREEN else ("RED" if technical_status == _core.STATUS_RED else "YELLOW"),
        "reason_codes": [],
    }
    governance_decision = pkg.get("governance_decision") or {"status": "NOT_REQUESTED", "reason_codes": []}
    overall_recommendation = pkg.get("overall_recommendation") or {
        "technical_ready": technical_decision.get("status") == "GREEN",
        "merge_governance_verified": governance_decision.get("status") == "VERIFIED",
    }
    governance_follow_up = {
        "kind": "none" if governance_decision.get("status") in {"NOT_REQUESTED", "VERIFIED"} else "access_limitation",
        "may_modify_code": False,
        "prompt_required": False,
    }

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
