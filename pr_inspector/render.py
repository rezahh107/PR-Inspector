from __future__ import annotations

import hashlib
import json
from typing import Any

from .constants import SPECIALIST_APPROVALS


CANONICAL_ACTION_TEXT: dict[str, str] = {
    "merge_now": (
        "No technical blocker, pending structured action, or additional technical "
        "approval remains for the reviewed head; the project owner may merge it."
    ),
    "owner_confirmation": (
        "Obtain explicit project-owner confirmation for the reviewed head before merge."
    ),
    "human_technical_review": (
        "Obtain the required human technical review on the reviewed head before merge."
    ),
    "specialist_review": (
        "Obtain the required security or domain-specialist review on the reviewed head "
        "before merge."
    ),
    "repair": (
        "Apply only the bounded repairs identified by the canonical reason codes, then "
        "run exact-head validation and a fresh PR Inspector review."
    ),
    "verify": (
        "Collect the missing evidence identified by the canonical reason codes without "
        "modifying the repository, then run a fresh PR Inspector review."
    ),
    "repair_and_verify": (
        "Complete the bounded repairs and the separate evidence obligations, then run "
        "exact-head validation and a fresh PR Inspector review."
    ),
    "rerun_review": (
        "Run a fresh PR Inspector review on the current head; this non-current package "
        "grants no repair, approval, or merge authority."
    ),
    "blocked_internal_error": (
        "Resolve the internal projection or artifact error and regenerate validated "
        "review artifacts before taking any repository action."
    ),
}


def canonical_json_bytes(pkg: dict[str, Any]) -> bytes:
    return (json.dumps(pkg, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def package_sha256(pkg: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(pkg)).hexdigest()


def _projection(pkg: dict[str, Any], projection: dict[str, Any] | None = None) -> dict[str, Any]:
    if projection is not None:
        return projection
    from .decision_projection import project_decision
    return project_decision(pkg)


def owner_status(pkg: dict[str, Any], projection: dict[str, Any] | None = None) -> str:
    from .decision_projection import owner_status_text
    return owner_status_text(_projection(pkg, projection))


def owner_action(pkg: dict[str, Any], projection: dict[str, Any] | None = None) -> str:
    from .decision_projection import owner_action_text
    return owner_action_text(_projection(pkg, projection))


def canonical_action_text(projection: dict[str, Any]) -> str:
    """Render the sole authoritative technical action from the canonical projection."""

    from .decision_projection import validate_projection_invariants

    validate_projection_invariants(projection)
    action_kind = projection["next_action"]["kind"]
    try:
        return CANONICAL_ACTION_TEXT[action_kind]
    except KeyError as exc:
        raise ValueError(f"no canonical technical action text for {action_kind}") from exc


def render_owner(pkg: dict[str, Any], projection: dict[str, Any] | None = None) -> str:
    projection = _projection(pkg, projection)
    card = pkg["owner_card"]
    specialist = pkg["decision"]["approval_requirement"] in SPECIALIST_APPROVALS
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "نتیجهٔ بررسی PR", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "",
        f"وضعیت: {owner_status(pkg, projection)}", "", "این تغییر چه کاری می‌کند؟", card["summary"], "",
    ]
    if card["mental_model"]:
        lines += ["تصویر ذهنی:", card["mental_model"], ""]
    lines += [
        "چه چیزی ممکن است خراب شود؟", card["risk"], "",
        "چه چیزی بررسی شده؟", card["checked"], "",
        "چه چیزی هنوز مشخص نیست؟", card["unknown"], "",
        "الان چه کار کنیم؟", owner_action(pkg, projection), "",
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


def _extend_bullet_list(out: list[str], items: list[str]) -> None:
    out.extend(f"- {item}" for item in items) if items else out.append("- none")


def _extend_numbered_list(out: list[str], items: list[str]) -> None:
    out.extend(f"{index}. {item}" for index, item in enumerate(items, 1)) if items else out.append("1. none")


def _markdown_table_cell(value: Any) -> str:
    return " ".join(str(value).replace("\r", " ").replace("\n", " ").split()).replace("|", "\\|")


def _accepted_external_suggestions(pkg: dict[str, Any]) -> list[dict[str, Any]]:
    intake = pkg.get("external_review_intake") or {}
    return [item for item in intake.get("suggestions", []) if item.get("triage_decision") == "accepted" and item.get("repair_handoff")]


def _render_external_review_intake(out: list[str], pkg: dict[str, Any]) -> None:
    out.extend(["## 10. External Review Suggestions Considered", ""])
    intake = pkg.get("external_review_intake")
    if not intake or not intake.get("suggestions"):
        out.extend(["None.", ""])
        return
    out.extend(["| id | source | decision | linked finding | reason |", "|---|---|---|---|---|"])
    for item in intake["suggestions"]:
        linked = ", ".join(item["linked_finding_ids"]) or "None"
        out.append(f"| {_markdown_table_cell(item['external_suggestion_id'])} | {_markdown_table_cell(item['author'])} | {_markdown_table_cell(item['triage_decision'])} | {_markdown_table_cell(linked)} | {_markdown_table_cell(item['triage_reason'])} |")
    out.append("")


def _render_repair_handoff(out: list[str], pkg: dict[str, Any]) -> None:
    handoff = pkg.get("repair_handoff")
    accepted_external = _accepted_external_suggestions(pkg)
    out.extend(["## 11. Repair Handoff for Implementer Model", ""])
    if (not handoff or not handoff.get("affected_findings")) and not accepted_external:
        out.extend(["None.", ""])
        return
    if handoff and handoff.get("affected_findings"):
        out.extend([f"Intended recipient: {handoff['intended_recipient']}  ", f"Repair scope: {handoff['repair_scope']}", ""])
        for item in handoff["affected_findings"]:
            out.extend([f"### {item['finding_id']}", "", "Affected rules:"])
            _extend_bullet_list(out, item["affected_rule_ids"])
            out.extend(["", f"Repair objective: {item['repair_objective']}", "", "Smallest safe repair:"])
            _extend_numbered_list(out, item["smallest_safe_repair"])
            out.extend(["", "Do not change:"])
            _extend_bullet_list(out, item["do_not_change"])
            out.extend(["", "Required validation:"])
            _extend_bullet_list(out, item["required_validation"])
            out.extend(["", "Overclaim guards:"])
            _extend_bullet_list(out, item["overclaim_guards"])
            out.append("")
    if accepted_external:
        out.extend(["### Accepted External Suggestions", ""])
        for item in accepted_external:
            repair = item["repair_handoff"]
            linked = ", ".join(item["linked_finding_ids"]) or "None"
            out.extend([f"#### {item['external_suggestion_id']} → {linked}", "", "Source:", item["author"], "", "Verified issue:", item["claim_summary"], "", "Smallest safe repair:"])
            _extend_numbered_list(out, repair["smallest_safe_repair"])
            out.extend(["", "Do not change:"])
            _extend_bullet_list(out, repair["do_not_change"])
            out.extend(["", "Required validation:"])
            _extend_bullet_list(out, repair["required_validation"])
            out.extend(["", "Overclaim guards:"])
            _extend_bullet_list(out, repair["overclaim_guards"])
            out.append("")


def render_handoff(pkg: dict[str, Any], projection: dict[str, Any] | None = None) -> str:
    projection = _projection(pkg, projection)
    identity = pkg["review_identity"]
    decision = pkg["decision"]
    scope = pkg["scope"]
    canonical_action = canonical_action_text(projection)
    out = ["# Technical Handoff Package", "", "## 1. Review Identity", "", "```yaml"]
    identity_fields = ["inspector_repository", "inspector_commit_sha", "protocol_version", "target_repository", "pr_number", "base_branch", "base_sha", "head_branch", "reviewed_head_sha", "merge_base_sha", "review_started", "review_completed", "review_validity", "execution_mode", "review_mode"]
    merged = {**identity, "protocol_version": pkg["protocol_version"]}
    for key in identity_fields:
        out.append(f"{key}: {_yaml_scalar(merged[key])}")
    out += ["```", "", "> This review is valid only for the reviewed head SHA above.", "", "## 2. Decision Header", "", "```yaml"]
    for key in ["technical_status", "risk_classification", "approval_requirement", "blocking_findings_count"]:
        out.append(f"{key}: {_yaml_scalar(decision[key])}")
    out.extend([
        f"canonical_next_action_kind: {projection['next_action']['kind']}",
        f"canonical_next_action_recipient: {projection['next_action']['recipient']}",
        f"canonical_next_action_may_modify_code: {_yaml_scalar(projection['next_action']['may_modify_code'])}",
        f"canonical_next_action_prompt_kind: {_yaml_scalar(projection['next_action']['prompt_kind'])}",
        f"canonical_next_action_text: {canonical_action}",
    ])
    out += [
        "```",
        "",
        (
            "> `decision.next_required_action` remains in `review-package.json` only "
            "for legacy package compatibility. It is non-authoritative, is not rendered "
            "as an instruction, and cannot override `DECISION_PROJECTION.json`."
        ),
        "",
        f"Sensitive domains: {', '.join(decision['sensitive_domains']) or 'none'}",
        "",
        "## 3. Capability Manifest",
        "",
    ]
    for key, value in pkg["capabilities"].items():
        out.append(f"- `{key}`: `{value}`")
    out += ["", "## 4. Scope and Coverage", "", "```yaml"]
    for key in ["total_changed_files", "total_changed_lines", "coverage_complete", "scope_limit_reason"]:
        out.append(f"{key}: {_yaml_scalar(scope[key])}")
    out += ["```", ""]
    for key in ["files_fully_reviewed", "files_partially_reviewed", "files_not_reviewed", "files_reviewed_outside_diff", "high_risk_areas_reviewed", "high_risk_areas_not_reviewed", "excluded_generated_or_vendor_files"]:
        out.append(f"- **{key}:** {', '.join(scope[key]) or 'none'}")
    summary = pkg["change_summary"]
    out += ["", "## 5. Change Summary", "", f"- **Previous behavior:** {summary['previous_behavior']}", f"- **Intended behavior:** {summary['intended_behavior']}", f"- **Actual implementation:** {summary['actual_implementation']}", f"- **Mismatch:** {summary['mismatch'] or 'none'}", ""]
    intent = pkg.get("intent_fit")
    out += ["## 6. Intent Fit Evidence", ""]
    if intent is None:
        out.append("None.")
    else:
        out += ["```yaml", f"intent_source: {intent['intent_source']}", f"intent_fit_result: {intent['intent_fit_result']}", "```", "", f"- **Stated intent:** {intent['stated_intent'] or 'none'}", f"- **Unsupported claims:** {', '.join(intent['unsupported_claims']) or 'none'}", ""]
        if not intent["implementation_evidence"]:
            out.append("No implementation evidence recorded.")
        for item in intent["implementation_evidence"]:
            out += [f"- `{item['evidence_label']}` {item['file']} ({item['lines_or_symbol']}): {item['evidence_summary']}", f"  - Evidence refs: {', '.join(item['evidence_refs'])}"]
    out += ["", "## 7. Evidence Records", ""]
    if not pkg["evidence_records"]:
        out.append("None.")
    for item in pkg["evidence_records"]:
        out += [f"### {item['evidence_id']}", "", f"- Type: `{item['evidence_type']}`", f"- Source: {item['source']}", f"- Head SHA: `{item['reviewed_head_sha']}`", f"- Result: `{item['result']}`", f"- Excerpt: {item['excerpt'] or 'none'}", f"- Reference: {item['reference'] or 'none'}", f"- SHA-256: {item['sha256'] or 'none'}", f"- Redactions: {', '.join(item['redactions']) or 'none'}", f"- Limitations: {', '.join(item['limitations']) or 'none'}", ""]
    blocking = [item for item in pkg["findings"] if item["blocking"]]
    non_blocking = [item for item in pkg["findings"] if not item["blocking"]]

    def findings_section(title: str, items: list[dict[str, Any]]) -> None:
        out.extend([title, ""])
        if not items:
            out.extend(["None.", ""])
            return
        for item in items:
            out.extend([f"### {item['finding_id']} — {item['severity']} / {item['evidence_label']}", "", f"- Location: `{item['file_location']}`", f"- Symbol: `{item['symbol'] or 'n/a'}`", f"- Issue: {item['issue']}", f"- Failure scenario: {item['failure_scenario']}", f"- Recommended fix: {item['recommended_fix']}", f"- Recommended test: {item['recommended_test']}", f"- Evidence: {', '.join(item['evidence_refs'])}", f"- Rules: {', '.join(item['rule_ids'])}", ""])

    findings_section("## 8. Merge-Blocking Findings", blocking)
    findings_section("## 9. Non-Blocking Findings", non_blocking)
    _render_external_review_intake(out, pkg)
    _render_repair_handoff(out, pkg)
    out += ["## 12. Files Reviewed Outside the Diff", "", *(f"- {item}" for item in scope["files_reviewed_outside_diff"])]
    if not scope["files_reviewed_outside_diff"]:
        out.append("None.")
    out += ["", "## 13. Unverified Areas", "", *(f"- {item}" for item in pkg["unverified_areas"])]
    if not pkg["unverified_areas"]:
        out.append("None.")
    out += ["", "## 14. Required Actions Before Merge", "", *(f"{index}. {item}" for index, item in enumerate(pkg["required_actions"], 1))]
    if not pkg["required_actions"]:
        out.append("None.")
    out += ["", "## 15. Out-of-Scope Observations", "", *(f"- {item}" for item in pkg["out_of_scope_observations"])]
    if not pkg["out_of_scope_observations"]:
        out.append("None.")
    out += ["", "## 16. Owner-Card Consistency Map", "", "| Technical field | Owner-facing value |", "|---|---|", f"| Status / validity | {owner_status(pkg, projection)} |", f"| Next owner action | {owner_action(pkg, projection)} |", f"| Projected recipient | {projection['next_action']['recipient']} |", f"| Specialist required | {'yes' if decision['approval_requirement'] in SPECIALIST_APPROVALS else 'no'} |", "", "## 17. Validation Metadata", "", f"- Canonical package SHA-256: `{package_sha256(pkg)}`", "- Canonicalization: sorted-key compact UTF-8 JSON with LF terminator, version 1", "- Schema: JSON Schema Draft 2020-12", "", "## 18. Final Technical Decision", "", f"- Status: `{decision['technical_status']}`", f"- Risk: `{decision['risk_classification']}`", f"- Approval: `{decision['approval_requirement']}`", f"- Validity: `{identity['review_validity']}`", f"- Canonical next action kind: `{projection['next_action']['kind']}`", f"- Canonical next action: {canonical_action}", "- Legacy `decision.next_required_action`: non-authoritative package context; intentionally omitted from action instructions.", ""]
    return "\n".join(out)
