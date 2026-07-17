from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from .decision_projection import ProjectionError, project_decision
from .diagnostics import Diagnostic
from .render import package_sha256

PROMPT_CONTRACT_HEADING = "[CANONICAL ACTION CONTRACT]"
PROMPT_CONTRACT_OPEN = "```json"
PROMPT_CONTRACT_CLOSE = "```"
PROFILE_COMMAND_FRAGMENTS = (
    "برای بررسی حفاظت‌های Merge",
    "برای بررسی حداقلی بنویس",
)
HISTORICAL_PLACEHOLDER = "Repair independently validated technical findings before rereview."
PROHIBITED_ACTIONS = (
    "merge_pull_request",
    "approve_pull_request",
    "write_default_branch",
    "deploy",
    "access_secrets",
    "access_production",
    "destructive_operation",
    "modify_unrelated_repository",
)
_ACTION_RULES: dict[str, tuple[str, bool, str]] = {
    "repair": ("implementer_model", True, "implementer_repair_prompt"),
    "repair_and_verify": ("implementer_model", True, "implementer_repair_prompt"),
    "verify": ("reviewer_model", False, "verification_prompt"),
    "rerun_review": ("reviewer_model", False, "fresh_review_prompt"),
    "human_technical_review": ("human_technical_reviewer", False, "human_review_handoff"),
    "specialist_review": ("security_or_domain_specialist", False, "specialist_review_handoff"),
}
_CONTRACT_PATTERN = re.compile(
    rf"{re.escape(PROMPT_CONTRACT_HEADING)}\n\n{re.escape(PROMPT_CONTRACT_OPEN)}\n(?P<json>.*?)\n{re.escape(PROMPT_CONTRACT_CLOSE)}",
    re.DOTALL,
)


class PromptSemanticError(ValueError):
    pass


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _reason_subjects(projection: Mapping[str, Any]) -> dict[str, list[str]]:
    selected = set(projection["next_action"]["reason_codes"])
    return {
        item["reason_code"]: list(item["subjects"])
        for item in projection.get("reason_details", [])
        if item.get("reason_code") in selected
    }


def build_prompt_contract(package: Mapping[str, Any], projection: Mapping[str, Any]) -> dict[str, Any]:
    action = projection["next_action"]
    kind = action["kind"]
    if kind not in _ACTION_RULES:
        raise PromptSemanticError(f"action kind {kind!r} does not have a prompt semantic contract")
    identity = package["review_identity"]
    findings = package.get("findings") or []
    finding_ids = [item["finding_id"] for item in findings]
    evidence_refs = _unique([ref for item in findings for ref in item.get("evidence_refs", [])])
    required_tests = _unique([item.get("recommended_test", "") for item in findings])
    recipient, may_modify_code, prompt_kind = _ACTION_RULES[kind]
    return {
        "schema_version": 1,
        "protocol_version": projection["protocol_version"],
        "target_repository": identity["target_repository"],
        "pull_request": identity["pr_number"],
        "reviewed_head_sha": identity["reviewed_head_sha"],
        "review_validity": identity["review_validity"],
        "canonical_review_package_sha256": package_sha256(dict(package)),
        "inspection_profile": projection.get("inspection_profile", "minimal"),
        "action_kind": kind,
        "recipient": recipient,
        "may_modify_code": may_modify_code,
        "prompt_kind": prompt_kind,
        "reason_codes": list(action["reason_codes"]),
        "reason_subjects": _reason_subjects(projection),
        "finding_ids": finding_ids,
        "evidence_references": evidence_refs,
        "required_actions": list(projection.get("required_actions", [])),
        "required_tests": required_tests,
        "fresh_rereview_required": True,
        "profile_commands_separate": True,
        "prohibited_actions": list(PROHIBITED_ACTIONS),
    }


def render_prompt_contract_block(package: Mapping[str, Any], projection: Mapping[str, Any]) -> list[str]:
    serialized = json.dumps(build_prompt_contract(package, projection), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return [PROMPT_CONTRACT_HEADING, "", PROMPT_CONTRACT_OPEN, serialized, PROMPT_CONTRACT_CLOSE, ""]


def extract_prompt_contract(prompt: str) -> dict[str, Any]:
    matches = list(_CONTRACT_PATTERN.finditer(prompt))
    if len(matches) != 1:
        raise PromptSemanticError("prompt must contain exactly one canonical action contract")
    try:
        value = json.loads(matches[0].group("json"))
    except json.JSONDecodeError as exc:
        raise PromptSemanticError(f"canonical action contract is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise PromptSemanticError("canonical action contract must be a JSON object")
    return value


def _validate_action_rules(contract: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    kind = contract.get("action_kind")
    rule = _ACTION_RULES.get(kind)
    if rule is None:
        return ["unsupported prompt action kind"]
    recipient, may_modify, prompt_kind = rule
    if contract.get("recipient") != recipient: errors.append("recipient disagrees with action kind")
    if contract.get("may_modify_code") is not may_modify: errors.append("code-modification authority disagrees with action kind")
    if contract.get("prompt_kind") != prompt_kind: errors.append("prompt kind disagrees with action kind")
    if kind in {"verify", "rerun_review", "human_technical_review", "specialist_review"} and contract.get("may_modify_code") is not False:
        errors.append("non-repair action authorizes code modification")
    if kind == "rerun_review" and contract.get("review_validity") == "CURRENT":
        errors.append("fresh-review prompt requires non-current review identity")
    if kind in {"repair", "repair_and_verify"} and not (contract.get("finding_ids") or contract.get("required_actions") or contract.get("reason_subjects")):
        errors.append("repair prompt has no bounded operational subject")
    return errors


def validate_prompt_semantics(package: Mapping[str, Any], projection: Mapping[str, Any], prompt: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    path = "/NEXT_ACTION_PROMPT.en.md"
    if prompt.strip() == HISTORICAL_PLACEHOLDER:
        diagnostics.append(Diagnostic("PRI-PROMPT-SEM-001", path, "historical generic Candidate placeholder is forbidden"))
    if len(prompt.strip()) < 200:
        diagnostics.append(Diagnostic("PRI-PROMPT-SEM-001", path, "prompt-required artifact is not operationally complete"))
    if any(fragment in prompt for fragment in PROFILE_COMMAND_FRAGMENTS):
        diagnostics.append(Diagnostic("PRI-PROMPT-SEM-002", path, "profile-selection commands must remain a separate verified artifact"))
    try:
        actual = extract_prompt_contract(prompt)
        expected = build_prompt_contract(package, projection)
    except (PromptSemanticError, KeyError, TypeError) as exc:
        diagnostics.append(Diagnostic("PRI-PROMPT-SEM-001", path, str(exc)))
        return sorted(set(diagnostics))
    if actual != expected:
        diagnostics.append(Diagnostic("PRI-PROMPT-SEM-003", path, "canonical action contract does not match structured review data"))
    required = {"protocol_version", "target_repository", "pull_request", "reviewed_head_sha", "action_kind", "recipient", "may_modify_code", "prompt_kind", "reason_codes", "reason_subjects", "finding_ids", "evidence_references", "required_actions", "required_tests", "fresh_rereview_required", "profile_commands_separate", "prohibited_actions"}
    missing = sorted(required - set(actual))
    if missing:
        diagnostics.append(Diagnostic("PRI-PROMPT-SEM-004", path, "canonical action contract is missing: " + ", ".join(missing)))
    if actual.get("fresh_rereview_required") is not True:
        diagnostics.append(Diagnostic("PRI-PROMPT-SEM-005", path, "prompt must require a fresh independent PR Inspector review"))
    if actual.get("profile_commands_separate") is not True:
        diagnostics.append(Diagnostic("PRI-PROMPT-SEM-002", path, "prompt contract must preserve profile-command separation"))
    if actual.get("prohibited_actions") != list(PROHIBITED_ACTIONS):
        diagnostics.append(Diagnostic("PRI-PROMPT-SEM-006", path, "prompt prohibited-action boundary is incomplete"))
    for message in _validate_action_rules(actual):
        diagnostics.append(Diagnostic("PRI-PROMPT-SEM-007", path, message))
    if not projection.get("technical_status_reason_codes", []) and projection.get("governance_decision", {}).get("status") in {"GAP_FOUND", "NOT_VERIFIABLE"} and actual.get("action_kind") in {"repair", "repair_and_verify"}:
        diagnostics.append(Diagnostic("PRI-PROMPT-SEM-008", path, "governance-only gaps cannot create technical repair authority"))
    return sorted(set(diagnostics))


def require_prompt_semantics(package: Mapping[str, Any], projection: Mapping[str, Any], prompt: str) -> None:
    diagnostics = validate_prompt_semantics(package, projection, prompt)
    if diagnostics:
        raise PromptSemanticError("; ".join(item.line() for item in diagnostics))


def validate_prompt_directory(path: Path) -> list[Diagnostic]:
    path = Path(path)
    package_path, projection_path = path / "review-package.json", path / "DECISION_PROJECTION.json"
    prompt_path = path / "NEXT_ACTION_PROMPT.en.md"
    if not package_path.is_file() or not projection_path.is_file():
        return []
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
        actual_projection = json.loads(projection_path.read_text(encoding="utf-8"))
        expected_projection = project_decision(package)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ProjectionError, KeyError, TypeError):
        return []
    if not expected_projection["next_action"]["prompt_required"]:
        return []
    if not prompt_path.is_file():
        return [Diagnostic("PRI-PROMPT-SEM-001", "/NEXT_ACTION_PROMPT.en.md", "prompt-required artifact is missing")]
    try:
        prompt = prompt_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [Diagnostic("PRI-PROMPT-SEM-001", "/NEXT_ACTION_PROMPT.en.md", str(exc))]
    diagnostics = validate_prompt_semantics(package, expected_projection, prompt)
    return diagnostics
