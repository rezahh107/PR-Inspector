from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .constants import STATUS_GREEN, STATUS_RED, STATUS_YELLOW

ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
REGISTRY_PATH = ROOT / f"protocols/{CURRENT_VERSION}/registries/DECISION_REASON_REGISTRY.yaml"

TECHNICAL_EFFECTS = {"NONE", "YELLOW", "RED"}
ACTION_KINDS = {
    "merge_now",
    "owner_confirmation",
    "human_technical_review",
    "specialist_review",
    "repair",
    "verify",
    "repair_and_verify",
    "rerun_review",
    "blocked_internal_error",
}
RECIPIENTS = {
    "none",
    "project_owner",
    "implementer_model",
    "reviewer_model",
    "human_technical_reviewer",
    "security_or_domain_specialist",
}
PROMPT_KINDS = {
    None,
    "implementer_repair_prompt",
    "verification_prompt",
    "fresh_review_prompt",
    "human_review_handoff",
    "specialist_review_handoff",
}

ACTION_ROUTING: dict[str, dict[str, Any]] = {
    "merge_now": {
        "recipient": "none",
        "may_modify_code": False,
        "prompt_required": False,
        "prompt_kind": None,
    },
    "owner_confirmation": {
        "recipient": "project_owner",
        "may_modify_code": False,
        "prompt_required": False,
        "prompt_kind": None,
    },
    "human_technical_review": {
        "recipient": "human_technical_reviewer",
        "may_modify_code": False,
        "prompt_required": True,
        "prompt_kind": "human_review_handoff",
    },
    "specialist_review": {
        "recipient": "security_or_domain_specialist",
        "may_modify_code": False,
        "prompt_required": True,
        "prompt_kind": "specialist_review_handoff",
    },
    "repair": {
        "recipient": "implementer_model",
        "may_modify_code": True,
        "prompt_required": True,
        "prompt_kind": "implementer_repair_prompt",
    },
    "verify": {
        "recipient": "reviewer_model",
        "may_modify_code": False,
        "prompt_required": True,
        "prompt_kind": "verification_prompt",
    },
    "repair_and_verify": {
        "recipient": "implementer_model",
        "may_modify_code": True,
        "prompt_required": True,
        "prompt_kind": "implementer_repair_prompt",
    },
    "rerun_review": {
        "recipient": "reviewer_model",
        "may_modify_code": False,
        "prompt_required": True,
        "prompt_kind": "fresh_review_prompt",
    },
    "blocked_internal_error": {
        "recipient": "none",
        "may_modify_code": False,
        "prompt_required": False,
        "prompt_kind": None,
    },
}

OWNER_RESULT_REGISTRY: dict[str, str] = {
    "green_merge_now": (
        "🟢 وضعیت: از نظر فنی آماده\n"
        "آمادگی فنی تأیید شده؛ حفاظت ادغام در GitHub جداگانه بررسی شود.\n"
    ),
    "yellow_owner_confirmation": (
        "🟡 وضعیت: تأیید شما لازم است\n"
        "تغییر را بررسی و تأیید کنید.\n"
    ),
    "yellow_human_technical_review": (
        "🟡 وضعیت: بازبینی فنی لازم است\n"
        "پیش از ادغام، بازبینی فنی انجام شود.\n"
    ),
    "yellow_specialist_review": (
        "🟡 وضعیت: بازبینی متخصص لازم است\n"
        "پیش از ادغام، نظر متخصص گرفته شود.\n"
    ),
    "yellow_verify": (
        "🟡 وضعیت: مدرک بیشتری لازم است\n"
        "پرامپت بررسی آماده است.\n"
    ),
    "yellow_repair": (
        "🟡 وضعیت: هنوز آماده نیست\n"
        "بخشی از کار باید اصلاح شود؛ پرامپت اصلاح آماده است.\n"
    ),
    "yellow_repair_and_verify": (
        "🟡 وضعیت: اصلاح و بررسی لازم است\n"
        "پرامپت اقدام آماده است.\n"
    ),
    "yellow_rerun_review": (
        "🟡 وضعیت: گزارش قدیمی شده است\n"
        "پرامپت بررسی دوباره آماده است.\n"
    ),
    "red_repair": (
        "🔴 وضعیت: ادغام نشود\n"
        "مشکل باید اصلاح شود؛ پرامپت اصلاح آماده است.\n"
    ),
    "red_repair_and_verify": (
        "🔴 وضعیت: ادغام نشود\n"
        "اصلاح و مدرک تازه لازم است؛ پرامپت اقدام آماده است.\n"
    ),
    "blocked_internal_error": (
        "⚪ وضعیت: بررسی کامل نشد\n"
        "خطای داخلی باید برطرف شود.\n"
    ),
}

OWNER_STATUS_TEXT = {
    "GREEN": "🟢 سبز — از نظر فنی آماده",
    "YELLOW": "🟡 زرد — هنوز آماده نیست",
    "RED": "🔴 قرمز — ادغام نشود",
    "BLOCKED": "⚪ مسدود — بررسی کامل نشد",
}

OWNER_ACTION_TEXT = {
    "merge_now": "آمادگی فنی برقرار است؛ مجوز و حفاظت واقعی ادغام باید از شواهد GitHub تأیید شود.",
    "owner_confirmation": "تأیید مالک پروژه لازم است.",
    "human_technical_review": "پیش از ادغام، بازبینی فنی انسانی لازم است.",
    "specialist_review": "پیش از ادغام، بازبینی متخصص امنیت یا حوزه لازم است.",
    "repair": "ابتدا اصلاح مشخص‌شده انجام شود.",
    "verify": "ابتدا شواهد یا بررسی مشخص‌شده تکمیل شود.",
    "repair_and_verify": "ابتدا اصلاح و سپس شواهد لازم تکمیل شود.",
    "rerun_review": "گزارش معتبر نیست؛ بررسی تازه روی head فعلی لازم است.",
    "blocked_internal_error": "خروجی تصمیم معتبر تولید نشد؛ خطای داخلی باید رفع شود.",
}

REQUIRED_REGISTRY_FIELDS = {
    "reason_code",
    "concept",
    "trigger",
    "predicate",
    "technical_status_effect",
    "action_effect",
    "recipient",
    "may_modify_code",
    "prompt_kind",
    "recovery_action",
}


class ProjectionError(ValueError):
    """Raised when the canonical decision projection cannot be produced safely."""


@lru_cache(maxsize=1)
def reason_registry_entries() -> tuple[dict[str, Any], ...]:
    try:
        raw = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ProjectionError(f"cannot load decision reason registry: {exc}") from exc

    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ProjectionError("decision reason registry schema_version must be 1")
    if raw.get("registry_version") != CURRENT_VERSION:
        raise ProjectionError("decision reason registry version does not match CURRENT_VERSION")
    reasons = raw.get("reasons")
    if not isinstance(reasons, list) or not reasons:
        raise ProjectionError("decision reason registry must contain a non-empty reasons list")

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(reasons):
        if not isinstance(item, dict):
            raise ProjectionError(f"registry reason {index} is not an object")
        missing = REQUIRED_REGISTRY_FIELDS - set(item)
        if missing:
            raise ProjectionError(
                f"registry reason {index} is missing fields: {', '.join(sorted(missing))}"
            )
        code = item["reason_code"]
        if not isinstance(code, str) or not code.startswith("RSN-"):
            raise ProjectionError(f"registry reason {index} has invalid reason_code")
        if code in seen:
            raise ProjectionError(f"duplicate reason_code {code}")
        seen.add(code)
        if item["technical_status_effect"] not in TECHNICAL_EFFECTS:
            raise ProjectionError(f"{code} has invalid technical_status_effect")
        if item["action_effect"] not in ACTION_KINDS:
            raise ProjectionError(f"{code} has invalid action_effect")
        if item["recipient"] not in RECIPIENTS:
            raise ProjectionError(f"{code} has invalid recipient")
        if item["prompt_kind"] not in PROMPT_KINDS:
            raise ProjectionError(f"{code} has invalid prompt_kind")
        route = ACTION_ROUTING[item["action_effect"]]
        if item["recipient"] != route["recipient"]:
            raise ProjectionError(f"{code} recipient diverges from canonical action routing")
        if item["may_modify_code"] != route["may_modify_code"]:
            raise ProjectionError(f"{code} may_modify_code diverges from canonical action routing")
        if item["prompt_kind"] != route["prompt_kind"]:
            raise ProjectionError(f"{code} prompt_kind diverges from canonical action routing")
        out.append(dict(item))
    return tuple(out)


@lru_cache(maxsize=1)
def reason_registry_by_code() -> dict[str, dict[str, Any]]:
    return {item["reason_code"]: item for item in reason_registry_entries()}


def _accepted_external_suggestions(pkg: dict[str, Any]) -> list[dict[str, Any]]:
    intake = pkg.get("external_review_intake") or {}
    return [
        item
        for item in intake.get("suggestions", [])
        if item.get("triage_decision") == "accepted" and item.get("repair_handoff")
    ]


def _append_reason(
    out: list[dict[str, Any]],
    code: str,
    subjects: list[str] | tuple[str, ...],
) -> None:
    registry = reason_registry_by_code()
    if code not in registry:
        raise ProjectionError(f"unregistered reason code emitted: {code}")
    clean_subjects = [str(value) for value in subjects if str(value)]
    if not clean_subjects:
        return
    existing = next((item for item in out if item["reason_code"] == code), None)
    if existing is None:
        out.append({"reason_code": code, "subjects": clean_subjects})
        return
    for value in clean_subjects:
        if value not in existing["subjects"]:
            existing["subjects"].append(value)


def collect_reason_instances(pkg: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect all structured reasons once, without parsing free text."""

    reasons: list[dict[str, Any]] = []
    identity = pkg["review_identity"]
    decision = pkg["decision"]
    checks = pkg["checks"]
    findings = pkg["findings"]
    scope = pkg["scope"]
    intent = pkg.get("intent_fit")

    if identity["review_validity"] != "CURRENT":
        _append_reason(
            reasons,
            "RSN-REVIEW-NOT-CURRENT",
            [identity["review_validity"]],
        )

    _append_reason(
        reasons,
        "RSN-RED-GATE-FLAG",
        list(pkg.get("red_gate_flags", [])),
    )

    _append_reason(
        reasons,
        "RSN-REQUIRED-CHECK-FAILED",
        [
            f"{check['check_id']}:{check['name']}"
            for check in checks
            if check["required"] and check["result"] == "FAIL"
        ],
    )
    _append_reason(
        reasons,
        "RSN-CRITICAL-SUPPORTED-FINDING",
        [
            finding["finding_id"]
            for finding in findings
            if finding["severity"] == "CRITICAL"
            and finding["evidence_label"] in {"REPRODUCED", "CODE_SUPPORTED"}
        ],
    )
    _append_reason(
        reasons,
        "RSN-HIGH-REPRODUCED-FINDING",
        [
            finding["finding_id"]
            for finding in findings
            if finding["severity"] == "HIGH"
            and finding["evidence_label"] == "REPRODUCED"
        ],
    )

    _append_reason(
        reasons,
        "RSN-REQUIRED-CHECK-UNRESOLVED",
        [
            f"{check['check_id']}:{check['name']}"
            for check in checks
            if check["required"] and check["result"] in {"UNKNOWN", "NOT_RUN"}
        ],
    )
    _append_reason(
        reasons,
        "RSN-HIGH-CODE-SUPPORTED-FINDING",
        [
            finding["finding_id"]
            for finding in findings
            if finding["severity"] == "HIGH"
            and finding["evidence_label"] == "CODE_SUPPORTED"
        ],
    )
    _append_reason(
        reasons,
        "RSN-HIGH-HYPOTHESIS-FINDING",
        [
            finding["finding_id"]
            for finding in findings
            if finding["severity"] == "HIGH"
            and finding["evidence_label"] == "HYPOTHESIS"
        ],
    )
    _append_reason(
        reasons,
        "RSN-BLOCKING-MEDIUM-SUPPORTED",
        [
            finding["finding_id"]
            for finding in findings
            if finding["severity"] == "MEDIUM"
            and finding["blocking"]
            and finding["evidence_label"] in {"REPRODUCED", "CODE_SUPPORTED"}
        ],
    )
    _append_reason(
        reasons,
        "RSN-BLOCKING-MEDIUM-UNVERIFIED",
        [
            finding["finding_id"]
            for finding in findings
            if finding["severity"] == "MEDIUM"
            and finding["blocking"]
            and finding["evidence_label"] in {"HYPOTHESIS", "NOT_ASSESSABLE"}
        ],
    )
    _append_reason(
        reasons,
        "RSN-BLOCKING-HYPOTHESIS",
        [
            finding["finding_id"]
            for finding in findings
            if finding["blocking"] and finding["evidence_label"] == "HYPOTHESIS"
        ],
    )
    _append_reason(
        reasons,
        "RSN-NOT-ASSESSABLE-FINDING",
        [
            finding["finding_id"]
            for finding in findings
            if finding["evidence_label"] == "NOT_ASSESSABLE"
        ],
    )

    if identity["review_mode"] == "PARTIAL":
        _append_reason(reasons, "RSN-PARTIAL-REVIEW", ["PARTIAL"])
    _append_reason(
        reasons,
        "RSN-HIGH-RISK-AREA-UNREVIEWED",
        list(scope["high_risk_areas_not_reviewed"]),
    )
    if not scope["coverage_complete"]:
        _append_reason(reasons, "RSN-COVERAGE-INCOMPLETE", ["coverage_complete=false"])
    _append_reason(reasons, "RSN-UNVERIFIED-AREA", list(pkg["unverified_areas"]))

    if intent is None:
        _append_reason(reasons, "RSN-INTENT-MISSING", ["intent_fit"])
    else:
        if intent["intent_fit_result"] != "satisfied":
            _append_reason(
                reasons,
                "RSN-INTENT-UNSATISFIED",
                [intent["intent_fit_result"]],
            )
        _append_reason(
            reasons,
            "RSN-INTENT-UNSUPPORTED-CLAIM",
            list(intent["unsupported_claims"]),
        )

    handoff = pkg.get("repair_handoff") or {}
    _append_reason(
        reasons,
        "RSN-REPAIR-HANDOFF-PRESENT",
        [
            item["finding_id"]
            for item in handoff.get("affected_findings", [])
        ],
    )
    _append_reason(
        reasons,
        "RSN-EXTERNAL-REPAIR-ACCEPTED",
        [
            item["external_suggestion_id"]
            for item in _accepted_external_suggestions(pkg)
        ],
    )
    _append_reason(
        reasons,
        "RSN-REQUIRED-ACTION-PENDING",
        list(pkg.get("required_actions", [])),
    )

    approval = decision["approval_requirement"]
    if approval == "PROJECT_OWNER_CONFIRMATION":
        _append_reason(
            reasons,
            "RSN-OWNER-CONFIRMATION-REQUIRED",
            [approval],
        )
    elif approval == "HUMAN_TECHNICAL_REVIEW_REQUIRED":
        _append_reason(
            reasons,
            "RSN-HUMAN-TECHNICAL-REVIEW-REQUIRED",
            [approval],
        )
    elif approval == "SECURITY_OR_DOMAIN_SPECIALIST_REQUIRED":
        _append_reason(
            reasons,
            "RSN-SPECIALIST-REVIEW-REQUIRED",
            [approval],
        )

    registry_order = {
        item["reason_code"]: index
        for index, item in enumerate(reason_registry_entries())
    }
    return sorted(reasons, key=lambda item: registry_order[item["reason_code"]])


def _technical_status(reason_codes: list[str]) -> tuple[str, list[str]]:
    registry = reason_registry_by_code()
    red = [
        code
        for code in reason_codes
        if registry[code]["technical_status_effect"] == "RED"
    ]
    if red:
        return STATUS_RED, red
    yellow = [
        code
        for code in reason_codes
        if registry[code]["technical_status_effect"] == "YELLOW"
    ]
    if yellow:
        return STATUS_YELLOW, yellow
    return STATUS_GREEN, []


def _approval_action(approval_requirement: str) -> str:
    mapping = {
        "NO_ADDITIONAL_TECHNICAL_APPROVAL": "merge_now",
        "PROJECT_OWNER_CONFIRMATION": "owner_confirmation",
        "HUMAN_TECHNICAL_REVIEW_REQUIRED": "human_technical_review",
        "SECURITY_OR_DOMAIN_SPECIALIST_REQUIRED": "specialist_review",
    }
    try:
        return mapping[approval_requirement]
    except KeyError as exc:
        raise ProjectionError(
            f"unsupported approval requirement: {approval_requirement}"
        ) from exc


def _choose_action(
    pkg: dict[str, Any],
    technical_status: str,
    reason_codes: list[str],
) -> tuple[str, list[str]]:
    registry = reason_registry_by_code()
    if pkg["review_identity"]["review_validity"] != "CURRENT":
        return "rerun_review", ["RSN-REVIEW-NOT-CURRENT"]

    if technical_status != STATUS_GREEN:
        repair_codes = [
            code
            for code in reason_codes
            if registry[code]["action_effect"] == "repair"
        ]
        verify_codes = [
            code
            for code in reason_codes
            if registry[code]["action_effect"] == "verify"
        ]
        if repair_codes and verify_codes:
            return "repair_and_verify", repair_codes + verify_codes
        if repair_codes:
            return "repair", repair_codes
        if verify_codes:
            return "verify", verify_codes
        raise ProjectionError(
            "non-Green technical status has no registered repair or verification reason"
        )

    pending_verify_codes = [
        code
        for code in reason_codes
        if registry[code]["action_effect"] == "verify"
    ]
    if pending_verify_codes:
        return "verify", pending_verify_codes

    action = _approval_action(pkg["decision"]["approval_requirement"])
    approval_codes = [
        code
        for code in reason_codes
        if registry[code]["action_effect"] == action
    ]
    return action, approval_codes


def _owner_color(technical_status: str, action_kind: str) -> str:
    if action_kind == "blocked_internal_error":
        return "BLOCKED"
    if action_kind == "rerun_review":
        return "YELLOW"
    if technical_status == STATUS_RED:
        return "RED"
    if action_kind == "merge_now":
        return "GREEN"
    return "YELLOW"


def _owner_message_key(color: str, action_kind: str) -> str:
    key = f"{color.lower()}_{action_kind}"
    if key not in OWNER_RESULT_REGISTRY:
        raise ProjectionError(
            f"no owner-result registry entry for color={color}, action={action_kind}"
        )
    return key


def project_decision(pkg: dict[str, Any]) -> dict[str, Any]:
    """Produce the single canonical structured decision projection."""

    reason_instances = collect_reason_instances(pkg)
    all_codes = [item["reason_code"] for item in reason_instances]
    technical_status, technical_codes = _technical_status(all_codes)
    action_kind, action_codes = _choose_action(pkg, technical_status, all_codes)
    route = ACTION_ROUTING[action_kind]
    color = _owner_color(technical_status, action_kind)
    message_key = _owner_message_key(color, action_kind)

    projection = {
        "schema_version": 1,
        "protocol_version": CURRENT_VERSION,
        "technical_status": technical_status,
        "technical_status_reason_codes": technical_codes,
        "approval_requirement": pkg["decision"]["approval_requirement"],
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
    """Fail closed when a derived field contradicts canonical routing."""

    action = projection["next_action"]["kind"]
    route = ACTION_ROUTING.get(action)
    if route is None:
        raise ProjectionError(f"unregistered action kind: {action}")
    for field in ("recipient", "may_modify_code", "prompt_required", "prompt_kind"):
        if projection["next_action"][field] != route[field]:
            raise ProjectionError(
                f"projection {field} diverges from canonical action routing"
            )

    owner = projection["owner_readiness"]
    expected_key = _owner_message_key(owner["color"], owner["action_kind"])
    if owner["message_key"] != expected_key:
        raise ProjectionError("owner message key diverges from owner readiness")

    if action == "merge_now":
        if projection["technical_status"] != STATUS_GREEN:
            raise ProjectionError("merge_now requires technical Green")
        if projection["approval_requirement"] != "NO_ADDITIONAL_TECHNICAL_APPROVAL":
            raise ProjectionError("merge_now requires no additional approval")
        if projection["review_identity"]["validity"] != "CURRENT":
            raise ProjectionError("merge_now requires CURRENT review validity")
        if projection["next_action"]["prompt_required"]:
            raise ProjectionError("merge_now must not generate a prompt")

    if action in {"verify", "rerun_review", "human_technical_review", "specialist_review"}:
        if projection["next_action"]["may_modify_code"]:
            raise ProjectionError(f"{action} must not authorize code modification")

    registry = reason_registry_by_code()
    for field in (
        projection["technical_status_reason_codes"],
        projection["owner_readiness"]["reason_codes"],
        projection["next_action"]["reason_codes"],
    ):
        unknown = [code for code in field if code not in registry]
        if unknown:
            raise ProjectionError(
                f"projection contains unregistered reason codes: {', '.join(unknown)}"
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


def expected_technical_status(pkg: dict[str, Any]) -> tuple[str, list[str]]:
    projection = project_decision(pkg)
    return (
        projection["technical_status"],
        projection["technical_status_reason_codes"],
    )
