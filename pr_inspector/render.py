from __future__ import annotations
import hashlib
import json
from typing import Any

from .constants import OWNER_STATUS, OWNER_INVALID, OWNER_ACTION, OWNER_INVALID_ACTION, SPECIALIST_APPROVALS


def canonical_json_bytes(pkg: dict[str, Any]) -> bytes:
    return (json.dumps(pkg, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def package_sha256(pkg: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(pkg)).hexdigest()


def owner_status(pkg: dict[str, Any]) -> str:
    if pkg["review_identity"]["review_validity"] != "CURRENT":
        return OWNER_INVALID
    return OWNER_STATUS[pkg["decision"]["technical_status"]]


def owner_action(pkg: dict[str, Any]) -> str:
    if pkg["review_identity"]["review_validity"] != "CURRENT":
        return OWNER_INVALID_ACTION
    return OWNER_ACTION[pkg["decision"]["technical_status"]]


def render_owner(pkg: dict[str, Any]) -> str:
    card = pkg["owner_card"]
    specialist = pkg["decision"]["approval_requirement"] in SPECIALIST_APPROVALS
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "نتیجهٔ بررسی PR", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "",
        f"وضعیت: {owner_status(pkg)}", "",
        "این تغییر چه کاری می‌کند؟", card["summary"], "",
    ]
    if card["mental_model"]:
        lines += ["تصویر ذهنی:", card["mental_model"], ""]
    lines += [
        "چه چیزی ممکن است خراب شود؟", card["risk"], "",
        "چه چیزی بررسی شده؟", card["checked"], "",
        "چه چیزی هنوز مشخص نیست؟", card["unknown"], "",
        "الان چه کار کنیم؟", owner_action(pkg), "",
        "آیا متخصص لازم است؟", "بله" if specialist else "خیر", card["specialist_reason"],
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "",
    ]
    return "\n".join(lines)


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def render_handoff(pkg: dict[str, Any]) -> str:
    identity = pkg["review_identity"]
    decision = pkg["decision"]
    scope = pkg["scope"]
    out = ["# Technical Handoff Package", "", "## 1. Review Identity", "", "```yaml"]
    identity_fields = [
        "inspector_repository", "inspector_commit_sha", "protocol_version", "target_repository",
        "pr_number", "base_branch", "base_sha", "head_branch", "reviewed_head_sha",
        "merge_base_sha", "review_started", "review_completed", "review_validity",
        "execution_mode", "review_mode",
    ]
    merged = {**identity, "protocol_version": pkg["protocol_version"]}
    for key in identity_fields:
        out.append(f"{key}: {_yaml_scalar(merged[key])}")
    out += ["```", "", "> This review is valid only for the reviewed head SHA above.", "", "## 2. Decision Header", "", "```yaml"]
    for key in ["technical_status", "risk_classification", "approval_requirement", "blocking_findings_count", "next_required_action"]:
        out.append(f"{key}: {_yaml_scalar(decision[key])}")
    out += ["```", "", f"Sensitive domains: {', '.join(decision['sensitive_domains']) or 'none'}", "", "## 3. Capability Manifest", ""]
    for key, value in pkg["capabilities"].items():
        out.append(f"- `{key}`: `{value}`")
    out += ["", "## 4. Scope and Coverage", "", "```yaml"]
    for key in ["total_changed_files", "total_changed_lines", "coverage_complete", "scope_limit_reason"]:
        out.append(f"{key}: {_yaml_scalar(scope[key])}")
    out += ["```", ""]
    for key in [
        "files_fully_reviewed", "files_partially_reviewed", "files_not_reviewed",
        "files_reviewed_outside_diff", "high_risk_areas_reviewed",
        "high_risk_areas_not_reviewed", "excluded_generated_or_vendor_files",
    ]:
        out.append(f"- **{key}:** {', '.join(scope[key]) or 'none'}")
    summary = pkg["change_summary"]
    out += [
        "", "## 5. Change Summary", "",
        f"- **Previous behavior:** {summary['previous_behavior']}",
        f"- **Intended behavior:** {summary['intended_behavior']}",
        f"- **Actual implementation:** {summary['actual_implementation']}",
        f"- **Mismatch:** {summary['mismatch'] or 'none'}", "", "## 6. Evidence Records", "",
    ]
    if not pkg["evidence_records"]:
        out.append("None.")
    for item in pkg["evidence_records"]:
        out += [
            f"### {item['evidence_id']}", "",
            f"- Type: `{item['evidence_type']}`", f"- Source: {item['source']}",
            f"- Head SHA: `{item['reviewed_head_sha']}`", f"- Result: `{item['result']}`",
            f"- Excerpt: {item['excerpt'] or 'none'}", f"- Reference: {item['reference'] or 'none'}",
            f"- SHA-256: {item['sha256'] or 'none'}", f"- Redactions: {', '.join(item['redactions']) or 'none'}",
            f"- Limitations: {', '.join(item['limitations']) or 'none'}", "",
        ]
    blocking = [item for item in pkg["findings"] if item["blocking"]]
    non_blocking = [item for item in pkg["findings"] if not item["blocking"]]

    def findings_section(title: str, items: list[dict[str, Any]]) -> None:
        out.extend([title, ""])
        if not items:
            out.extend(["None.", ""])
            return
        for item in items:
            out.extend([
                f"### {item['finding_id']} — {item['severity']} / {item['evidence_label']}", "",
                f"- Location: `{item['file_location']}`", f"- Symbol: `{item['symbol'] or 'n/a'}`",
                f"- Issue: {item['issue']}", f"- Failure scenario: {item['failure_scenario']}",
                f"- Recommended fix: {item['recommended_fix']}", f"- Recommended test: {item['recommended_test']}",
                f"- Evidence: {', '.join(item['evidence_refs'])}", f"- Rules: {', '.join(item['rule_ids'])}", "",
            ])

    findings_section("## 7. Merge-Blocking Findings", blocking)
    findings_section("## 8. Non-Blocking Findings", non_blocking)
    out += ["## 9. Files Reviewed Outside the Diff", "", *(f"- {item}" for item in scope["files_reviewed_outside_diff"])]
    if not scope["files_reviewed_outside_diff"]:
        out.append("None.")
    out += ["", "## 10. Unverified Areas", "", *(f"- {item}" for item in pkg["unverified_areas"])]
    if not pkg["unverified_areas"]:
        out.append("None.")
    out += ["", "## 11. Required Actions Before Merge", "", *(f"{index}. {item}" for index, item in enumerate(pkg["required_actions"], 1))]
    if not pkg["required_actions"]:
        out.append("None.")
    out += ["", "## 12. Out-of-Scope Observations", "", *(f"- {item}" for item in pkg["out_of_scope_observations"])]
    if not pkg["out_of_scope_observations"]:
        out.append("None.")
    out += [
        "", "## 13. Owner-Card Consistency Map", "",
        "| Technical field | Owner-facing value |", "|---|---|",
        f"| Status / validity | {owner_status(pkg)} |",
        f"| Next owner action | {owner_action(pkg)} |",
        f"| Specialist required | {'yes' if decision['approval_requirement'] in SPECIALIST_APPROVALS else 'no'} |",
        "", "## 14. Validation Metadata", "",
        f"- Canonical package SHA-256: `{package_sha256(pkg)}`",
        "- Canonicalization: sorted-key compact UTF-8 JSON with LF terminator, version 1",
        "- Schema: JSON Schema Draft 2020-12", "", "## 15. Final Technical Decision", "",
        f"- Status: `{decision['technical_status']}`", f"- Risk: `{decision['risk_classification']}`",
        f"- Approval: `{decision['approval_requirement']}`", f"- Validity: `{identity['review_validity']}`",
        f"- Exact next action: {decision['next_required_action']}", "",
    ]
    return "\n".join(out)
