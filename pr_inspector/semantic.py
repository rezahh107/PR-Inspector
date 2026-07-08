from __future__ import annotations
from datetime import datetime
from typing import Any

from .constants import (
    STATUS_GREEN,
    STATUS_YELLOW,
    STATUS_RED,
    SPECIALIST_APPROVALS,
    DOMAIN_SPECIALIST_REQUIRED,
)
from .diagnostics import Diagnostic

SUPPORTED_INTENT_LABELS = {"REPRODUCED", "CODE_SUPPORTED"}
INTENT_CLAIM_PHRASES = (
    "satisfies its intent",
    "satisfies the stated intent",
    "intent is satisfied",
    "matches intended behavior",
    "implementation matches intended behavior",
    "هدف pr را برآورده",
    "هدف را برآورده",
    "مطابق هدف",
    "رفتار موردنظر را پیاده",
)


def _diag(code: str, path: str, message: str) -> Diagnostic:
    return Diagnostic(code, path, message)


def _text_claims_intent_satisfied(pkg: dict[str, Any]) -> bool:
    parts: list[str] = []
    for section in ("change_summary", "owner_card"):
        value = pkg.get(section, {})
        if isinstance(value, dict):
            parts.extend(str(item) for item in value.values() if item is not None)
    decision = pkg.get("decision", {})
    if isinstance(decision, dict):
        parts.append(str(decision.get("next_required_action", "")))
    text = "\n".join(parts).lower()
    return any(phrase in text for phrase in INTENT_CLAIM_PHRASES)


def _claims_intent_satisfied(pkg: dict[str, Any]) -> bool:
    decision = pkg.get("decision", {})
    return decision.get("technical_status") == STATUS_GREEN or _text_claims_intent_satisfied(pkg)


def _intent_item_supported(item: dict[str, Any], evidence: dict[str, dict[str, Any]], reviewed_head_sha: str) -> bool:
    label = item.get("evidence_label")
    if label not in SUPPORTED_INTENT_LABELS:
        return False
    refs = [evidence[ref] for ref in item.get("evidence_refs", []) if ref in evidence]
    if label == "CODE_SUPPORTED":
        return any(ref["evidence_type"] == "CODE" and ref["reviewed_head_sha"] == reviewed_head_sha for ref in refs)
    if label == "REPRODUCED":
        return any(ref["evidence_type"] in {"EXECUTION", "CI"} and ref["reviewed_head_sha"] == reviewed_head_sha and ref["result"] == "PASS" for ref in refs)
    return False


def _intent_fit_supported(pkg: dict[str, Any], evidence: dict[str, dict[str, Any]]) -> bool:
    identity = pkg["review_identity"]
    intent_fit = pkg.get("intent_fit") or {}
    return any(_intent_item_supported(item, evidence, identity["reviewed_head_sha"]) for item in intent_fit.get("implementation_evidence", []))


def expected_status(pkg: dict[str, Any]) -> tuple[str, list[str]]:
    red: list[str] = []
    yellow: list[str] = []
    identity = pkg["review_identity"]
    scope = pkg["scope"]
    findings = pkg["findings"]
    checks = pkg["checks"]
    intent_fit = pkg.get("intent_fit")

    if pkg.get("red_gate_flags"):
        red.append("explicit red-gate flag")
    if any(c["required"] and c["result"] == "FAIL" for c in checks):
        red.append("required check failed")
    if any(f["severity"] == "CRITICAL" and f["evidence_label"] in {"REPRODUCED", "CODE_SUPPORTED"} for f in findings):
        red.append("critical supported finding")
    if any(f["severity"] == "HIGH" and f["evidence_label"] == "REPRODUCED" for f in findings):
        red.append("high reproduced finding")
    if red:
        return STATUS_RED, red

    if any(c["required"] and c["result"] in {"UNKNOWN", "NOT_RUN"} for c in checks):
        yellow.append("required check missing or unknown")
    if any(f["blocking"] and f["evidence_label"] == "HYPOTHESIS" for f in findings):
        yellow.append("blocking hypothesis")
    if any(f["severity"] == "HIGH" and f["evidence_label"] in {"CODE_SUPPORTED", "HYPOTHESIS"} for f in findings):
        yellow.append("unresolved high finding")
    if any(f["severity"] == "MEDIUM" and f["blocking"] for f in findings):
        yellow.append("blocking medium finding")
    if any(f["evidence_label"] == "NOT_ASSESSABLE" for f in findings):
        yellow.append("not assessable finding")
    if identity["review_mode"] == "PARTIAL":
        yellow.append("partial review")
    if identity["review_validity"] != "CURRENT":
        yellow.append("review validity is not current")
    if scope["high_risk_areas_not_reviewed"]:
        yellow.append("high-risk area unreviewed")
    if not scope["coverage_complete"]:
        yellow.append("coverage incomplete")
    if intent_fit is None:
        yellow.append("intent fit missing")
    elif intent_fit["intent_fit_result"] != "satisfied":
        yellow.append("intent fit is not satisfied")
    elif intent_fit["unsupported_claims"]:
        yellow.append("unsupported intent claim remains")
    if yellow:
        return STATUS_YELLOW, yellow
    return STATUS_GREEN, []


def validate_intent_fit(pkg: dict[str, Any], evidence: dict[str, dict[str, Any]]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    intent_fit = pkg.get("intent_fit")
    if intent_fit is None:
        if _claims_intent_satisfied(pkg):
            diagnostics.append(_diag("PRI-INTENT-001", "/intent_fit", "claiming full intent satisfaction requires a structured intent_fit object"))
        return diagnostics

    implementation_evidence = intent_fit["implementation_evidence"]
    if intent_fit["intent_source"] == "missing_or_insufficient" and intent_fit["intent_fit_result"] == "satisfied":
        diagnostics.append(_diag("PRI-INTENT-003", "/intent_fit/intent_fit_result", "missing or insufficient intent cannot be marked satisfied"))

    missing_refs: list[str] = []
    for index, item in enumerate(implementation_evidence):
        for ref in item["evidence_refs"]:
            if ref not in evidence:
                missing_refs.append(ref)
                diagnostics.append(_diag("PRI-INTENT-004", f"/intent_fit/implementation_evidence/{index}/evidence_refs", f"unknown evidence reference {ref}"))

    if intent_fit["intent_fit_result"] == "satisfied":
        if not implementation_evidence:
            diagnostics.append(_diag("PRI-INTENT-002", "/intent_fit/implementation_evidence", "satisfied intent fit requires concrete implementation evidence"))
        elif not missing_refs and not _intent_fit_supported(pkg, evidence):
            diagnostics.append(_diag("PRI-INTENT-002", "/intent_fit/implementation_evidence", "HYPOTHESIS or NOT_ASSESSABLE evidence cannot support satisfied intent fit"))
        if intent_fit["unsupported_claims"]:
            diagnostics.append(_diag("PRI-INTENT-005", "/intent_fit/unsupported_claims", "satisfied intent fit cannot retain unsupported satisfaction claims"))

    if intent_fit["intent_source"] == "missing_or_insufficient" and _claims_intent_satisfied(pkg):
        diagnostics.append(_diag("PRI-INTENT-006", "/intent_fit/intent_source", "missing or insufficient intent must not be paired with a full satisfaction claim"))

    return diagnostics


def validate_repair_handoff(pkg: dict[str, Any]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    handoff = pkg.get("repair_handoff")
    if handoff is None:
        return diagnostics

    findings_by_id = {item["finding_id"]: item for item in pkg["findings"]}
    seen_finding_ids: set[str] = set()
    for index, item in enumerate(handoff["affected_findings"]):
        finding_id = item["finding_id"]
        if finding_id in seen_finding_ids:
            diagnostics.append(_diag("PRI-HANDOFF-003", f"/repair_handoff/affected_findings/{index}/finding_id", f"duplicate repair handoff finding reference {finding_id}"))
        seen_finding_ids.add(finding_id)

        finding = findings_by_id.get(finding_id)
        if finding is None:
            diagnostics.append(_diag("PRI-HANDOFF-001", f"/repair_handoff/affected_findings/{index}/finding_id", f"unknown finding reference {finding_id}"))
            continue

        finding_rule_ids = set(finding["rule_ids"])
        unknown_rule_ids = [rule_id for rule_id in item["affected_rule_ids"] if rule_id not in finding_rule_ids]
        if unknown_rule_ids:
            diagnostics.append(_diag("PRI-HANDOFF-002", f"/repair_handoff/affected_findings/{index}/affected_rule_ids", f"rule IDs not attached to referenced finding {finding_id}: {', '.join(unknown_rule_ids)}"))

    return diagnostics


def validate_semantics(pkg: dict[str, Any]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    identity = pkg["review_identity"]
    decision = pkg["decision"]
    evidence = {item["evidence_id"]: item for item in pkg["evidence_records"]}
    checks = pkg["checks"]
    findings = pkg["findings"]

    if identity["review_validity"] == "CURRENT" and identity["reviewed_head_sha"] == "UNKNOWN":
        diagnostics.append(_diag("PRI-SHA-001", "/review_identity/reviewed_head_sha", "CURRENT requires an exact reviewed head SHA"))
    if identity["review_validity"] != "CURRENT" and decision["technical_status"] == STATUS_GREEN:
        diagnostics.append(_diag("PRI-STALE-001", "/decision/technical_status", "STALE or UNKNOWN validity cannot be Green"))

    if decision["risk_classification"] == "SENSITIVE" and decision["approval_requirement"] not in SPECIALIST_APPROVALS:
        diagnostics.append(_diag("PRI-SENS-001", "/decision/approval_requirement", "Sensitive risk requires qualified human technical approval"))
    if set(decision["sensitive_domains"]) & DOMAIN_SPECIALIST_REQUIRED and decision["approval_requirement"] != "SECURITY_OR_DOMAIN_SPECIALIST_REQUIRED":
        diagnostics.append(_diag("PRI-SENS-002", "/decision/approval_requirement", "selected sensitive domain requires security or domain specialist approval"))

    blocking = sum(1 for finding in findings if finding["blocking"])
    if decision["blocking_findings_count"] != blocking:
        diagnostics.append(_diag("PRI-COUNT-001", "/decision/blocking_findings_count", f"expected {blocking} from findings"))

    evidence_ids = [item["evidence_id"] for item in pkg["evidence_records"]]
    if len(evidence_ids) != len(set(evidence_ids)):
        diagnostics.append(_diag("PRI-EVID-002", "/evidence_records", "evidence IDs must be unique"))
    check_ids = [item["check_id"] for item in checks]
    if len(check_ids) != len(set(check_ids)):
        diagnostics.append(_diag("PRI-CHECK-001", "/checks", "check IDs must be unique"))
    finding_ids = [item["finding_id"] for item in findings]
    if len(finding_ids) != len(set(finding_ids)):
        diagnostics.append(_diag("PRI-FIND-001", "/findings", "finding IDs must be unique"))

    for index, item in enumerate(pkg["evidence_records"]):
        if item["reviewed_head_sha"] not in {"UNKNOWN", identity["reviewed_head_sha"]}:
            diagnostics.append(_diag("PRI-EVID-SHA-001", f"/evidence_records/{index}/reviewed_head_sha", "evidence is tied to a different head SHA"))

    for index, check in enumerate(checks):
        ref = check["evidence_id"]
        if ref is not None and ref not in evidence:
            diagnostics.append(_diag("PRI-EVID-001", f"/checks/{index}/evidence_id", f"unknown evidence reference {ref}"))
        if check["state"] in {"EXECUTED", "CI_INSPECTED"} and ref is None:
            diagnostics.append(_diag("PRI-CHECK-EVID-001", f"/checks/{index}/evidence_id", "executed or CI-inspected check requires evidence"))
        if check["result"] in {"PASS", "FAIL"} and check["state"] not in {"EXECUTED", "CI_INSPECTED"}:
            diagnostics.append(_diag("PRI-CHECK-STATE-001", f"/checks/{index}/state", "PASS or FAIL requires execution or CI inspection"))

    for index, finding in enumerate(findings):
        missing = [ref for ref in finding["evidence_refs"] if ref not in evidence]
        if missing:
            diagnostics.append(_diag("PRI-EVID-001", f"/findings/{index}/evidence_refs", f"unknown evidence references: {', '.join(missing)}"))
        if finding["evidence_label"] == "REPRODUCED":
            refs = [evidence[ref] for ref in finding["evidence_refs"] if ref in evidence]
            if not any(item["evidence_type"] in {"EXECUTION", "CI"} and item["reviewed_head_sha"] == identity["reviewed_head_sha"] and item["result"] == "FAIL" for item in refs):
                diagnostics.append(_diag("PRI-EXEC-001", f"/findings/{index}/evidence_label", "REPRODUCED requires failing execution or CI evidence tied to the reviewed head SHA"))

    diagnostics.extend(validate_intent_fit(pkg, evidence))
    diagnostics.extend(validate_repair_handoff(pkg))

    expected, reasons = expected_status(pkg)
    if decision["technical_status"] != expected:
        diagnostics.append(_diag("PRI-STATUS-001", "/decision/technical_status", f"expected {expected}; reasons: {', '.join(reasons) or 'all Green gates satisfied'}"))

    try:
        started = datetime.fromisoformat(identity["review_started"].replace("Z", "+00:00"))
        completed = datetime.fromisoformat(identity["review_completed"].replace("Z", "+00:00"))
        if completed < started:
            diagnostics.append(_diag("PRI-TIME-001", "/review_identity/review_completed", "completion time precedes start time"))
    except ValueError:
        pass

    if pkg["capabilities"]["production"] == "AVAILABLE" or pkg["capabilities"]["credential_access"] == "AVAILABLE":
        diagnostics.append(_diag("PRI-SECRET-001", "/capabilities", "ordinary review cannot declare production or credential access as available"))

    return sorted(set(diagnostics))
