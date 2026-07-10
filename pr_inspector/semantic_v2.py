from __future__ import annotations

import copy
from datetime import datetime
from typing import Any

from .constants import DOMAIN_SPECIALIST_REQUIRED, SPECIALIST_APPROVALS, STATUS_GREEN
from .decision_projection import ProjectionError, expected_technical_status
from .diagnostics import Diagnostic
from .semantic import validate_external_review_intake, validate_intent_fit, validate_repair_handoff


def _diag(code: str, path: str, message: str) -> Diagnostic:
    return Diagnostic(code, path, message)


def validate_semantics(pkg: dict[str, Any]) -> list[Diagnostic]:
    """Active v1.8 semantic validation using one canonical decision projection."""
    normalized = copy.deepcopy(pkg)
    capabilities = normalized.get("capabilities", {})
    if "credential_access" in capabilities and "protected_credentials" not in capabilities:
        capabilities["protected_credentials"] = capabilities["credential_access"]

    diagnostics: list[Diagnostic] = []
    identity = normalized["review_identity"]
    decision = normalized["decision"]
    evidence = {item["evidence_id"]: item for item in normalized["evidence_records"]}
    checks = normalized["checks"]
    findings = normalized["findings"]

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

    evidence_ids = [item["evidence_id"] for item in normalized["evidence_records"]]
    if len(evidence_ids) != len(set(evidence_ids)):
        diagnostics.append(_diag("PRI-EVID-002", "/evidence_records", "evidence IDs must be unique"))
    check_ids = [item["check_id"] for item in checks]
    if len(check_ids) != len(set(check_ids)):
        diagnostics.append(_diag("PRI-CHECK-001", "/checks", "check IDs must be unique"))
    finding_ids = [item["finding_id"] for item in findings]
    if len(finding_ids) != len(set(finding_ids)):
        diagnostics.append(_diag("PRI-FIND-001", "/findings", "finding IDs must be unique"))

    for index, item in enumerate(normalized["evidence_records"]):
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
            reproduced = any(item["evidence_type"] in {"EXECUTION", "CI"} and item["reviewed_head_sha"] == identity["reviewed_head_sha"] and item["result"] == "FAIL" for item in refs)
            if not reproduced:
                diagnostics.append(_diag("PRI-EXEC-001", f"/findings/{index}/evidence_label", "REPRODUCED requires failing execution or CI evidence tied to the reviewed head SHA"))

    diagnostics.extend(validate_intent_fit(normalized, evidence))
    diagnostics.extend(validate_repair_handoff(normalized))
    diagnostics.extend(validate_external_review_intake(normalized, evidence, checks))

    try:
        expected, reason_codes = expected_technical_status(normalized)
    except ProjectionError as exc:
        diagnostics.append(_diag("PRI-PROJECTION-001", "/decision", str(exc)))
    else:
        if decision["technical_status"] != expected:
            diagnostics.append(_diag("PRI-STATUS-001", "/decision/technical_status", f"expected {expected}; canonical reason codes: {', '.join(reason_codes) or 'none'}"))

    try:
        started = datetime.fromisoformat(identity["review_started"].replace("Z", "+00:00"))
        completed = datetime.fromisoformat(identity["review_completed"].replace("Z", "+00:00"))
        if completed < started:
            diagnostics.append(_diag("PRI-TIME-001", "/review_identity/review_completed", "completion time precedes start time"))
    except ValueError:
        pass

    if normalized["capabilities"]["production"] == "AVAILABLE" or normalized["capabilities"]["credential_access"] == "AVAILABLE":
        diagnostics.append(_diag("PRI-SECRET-001", "/capabilities", "ordinary review cannot declare production or credential access as available"))
    return sorted(set(diagnostics))
