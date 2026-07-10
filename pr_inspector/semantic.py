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


def _has_accepted_external_suggestion(pkg: dict[str, Any]) -> bool:
    intake = pkg.get("external_review_intake") or {}
    return any(item.get("triage_decision") == "accepted" for item in intake.get("suggestions", []))


def expected_status(pkg: dict[str, Any]) -> tuple[str, list[str]]:
    """Compatibility wrapper around the single active decision projection."""
    from .decision_projection import expected_technical_status

    return expected_technical_status(pkg)


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


def validate_external_review_intake(
    pkg: dict[str, Any],
    evidence: dict[str, dict[str, Any]],
    checks: list[dict[str, Any]],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    intake = pkg.get("external_review_intake")
    if intake is None:
        return diagnostics

    source_ids = [source["source_id"] for source in intake["sources_inspected"]]
    sources_by_id = {source["source_id"]: source for source in intake["sources_inspected"]}
    source_id_set = set(source_ids)
    if len(source_ids) != len(source_id_set):
        diagnostics.append(_diag("PRI-EXT-008", "/external_review_intake/sources_inspected", "external review source IDs must be unique"))

    suggestion_ids = [item["external_suggestion_id"] for item in intake["suggestions"]]
    if len(suggestion_ids) != len(set(suggestion_ids)):
        diagnostics.append(_diag("PRI-EXT-009", "/external_review_intake/suggestions", "external suggestion IDs must be unique"))

    evidence_ids = set(evidence)
    check_ids = {item["check_id"] for item in checks}
    finding_ids = {item["finding_id"] for item in pkg["findings"]}

    inaccessible_sources = {source["source_id"] for source in intake["sources_inspected"] if not source["inspected"]}
    insufficient_sources = {item["source_id"] for item in intake["suggestions"] if item["triage_decision"] == "insufficient_evidence"}
    for source_id in sorted(inaccessible_sources - insufficient_sources):
        diagnostics.append(_diag("PRI-EXT-010", "/external_review_intake/sources_inspected", f"inaccessible external review source {source_id} must be represented by an insufficient_evidence suggestion"))

    for index, item in enumerate(intake["suggestions"]):
        path = f"/external_review_intake/suggestions/{index}"
        source_id = item["source_id"]
        source = sources_by_id.get(source_id)
        if source is None:
            diagnostics.append(_diag("PRI-EXT-007", f"{path}/source_id", f"unknown external review source {source_id}"))

        for ref in item["evidence_refs"]:
            if ref.startswith("EVD-") and ref not in evidence_ids:
                diagnostics.append(_diag("PRI-EXT-004", f"{path}/evidence_refs", f"unknown evidence reference {ref}"))
            elif ref.startswith("CHK-") and ref not in check_ids:
                diagnostics.append(_diag("PRI-EXT-004", f"{path}/evidence_refs", f"unknown check reference {ref}"))

        for finding_id in item["linked_finding_ids"]:
            if finding_id not in finding_ids:
                diagnostics.append(_diag("PRI-EXT-005", f"{path}/linked_finding_ids", f"unknown finding reference {finding_id}"))

        repair = item.get("repair_handoff")
        if item["triage_decision"] == "accepted":
            if source is not None and not source["inspected"]:
                diagnostics.append(_diag("PRI-EXT-011", f"{path}/source_id", "accepted external suggestion requires an inspected source"))
            evidence_refs = [ref for ref in item["evidence_refs"] if ref.startswith("EVD-")]
            if not evidence_refs:
                diagnostics.append(_diag("PRI-EXT-001", f"{path}/evidence_refs", "accepted external suggestion requires at least one evidence record reference"))
            if not item["linked_finding_ids"]:
                diagnostics.append(_diag("PRI-EXT-002", f"{path}/linked_finding_ids", "accepted external suggestion requires at least one linked finding"))
            if repair is None:
                diagnostics.append(_diag("PRI-EXT-003", f"{path}/repair_handoff", "accepted external suggestion requires repair handoff instructions"))
            elif not repair["smallest_safe_repair"]:
                diagnostics.append(_diag("PRI-EXT-003", f"{path}/repair_handoff/smallest_safe_repair", "accepted external suggestion requires non-empty smallest safe repair"))
        elif repair is not None:
            diagnostics.append(_diag("PRI-EXT-006", f"{path}/repair_handoff", "non-accepted external suggestions must not carry repair instructions"))

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
    diagnostics.extend(validate_external_review_intake(pkg, evidence, checks))

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
