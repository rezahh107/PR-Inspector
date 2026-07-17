"""Independent semantic validation for canonical next-action artifacts.

Hash and byte equality prove integrity, not operational completeness. These
checks bind a prompt-required artifact to structured package and projection
facts without treating package prose as authority.
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from .diagnostics import Diagnostic

CODE = "PRI-PROMPT-SEMANTICS-001"
PATH = "/NEXT_ACTION_PROMPT.en.md"
HISTORICAL_PLACEHOLDER = (
    "Repair independently validated technical findings before rereview."
)
PROFILE_COMMAND_FRAGMENTS = (
    "برای بررسی حفاظت‌های Merge",
    "برای بررسی حداقلی بنویس",
)
MODEL_REQUIRED_SECTIONS = (
    "[ROLE AND AUTHORITY]",
    "[AUTHORITATIVE REVIEW IDENTITY]",
    "## Canonical decision projection",
    "[FINDINGS AND EVIDENCE]",
    "[SCOPE CONTROL]",
    "[VALIDATION AND EVIDENCE]",
    "[MANDATORY PR INSPECTOR RE-REVIEW]",
)
HUMAN_HANDOFF_SECTIONS = (
    "## Authoritative identity",
    "## Boundary",
    "## Review material",
)
REPAIR_ACTIONS = {"repair", "repair_and_verify"}
NON_MODIFYING_ACTIONS = {"verify", "rerun_review", "fresh_review"}


def _diag(message: str) -> Diagnostic:
    return Diagnostic(CODE, PATH, message)


def _json_token(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _contains_token(prompt: str, value: Any) -> bool:
    token = _json_token(value)
    if token in prompt:
        return True
    return isinstance(value, (str, int)) and f"`{value}`" in prompt


def _finding_ids(package: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    findings = package.get("findings")
    if isinstance(findings, Sequence) and not isinstance(
        findings, (str, bytes)
    ):
        for finding in findings:
            if (
                isinstance(finding, Mapping)
                and isinstance(finding.get("finding_id"), str)
            ):
                values.append(finding["finding_id"])
    return values


def _required_evidence_and_tests(
    package: Mapping[str, Any], action: str
) -> tuple[list[str], list[str]]:
    evidence: list[str] = []
    tests: list[str] = []
    findings = package.get("findings")
    if not isinstance(findings, Sequence) or isinstance(
        findings, (str, bytes)
    ):
        return evidence, tests
    for finding in findings:
        if not isinstance(finding, Mapping):
            continue
        blocking = finding.get("blocking") is True
        supported = finding.get("evidence_label") in {
            "REPRODUCED",
            "CODE_SUPPORTED",
        }
        if action in REPAIR_ACTIONS and not (blocking or supported):
            continue
        refs = finding.get("evidence_refs")
        if isinstance(refs, Sequence) and not isinstance(refs, (str, bytes)):
            evidence.extend(
                str(ref) for ref in refs if isinstance(ref, str)
            )
        test = finding.get("recommended_test")
        if isinstance(test, str) and test:
            tests.append(test)
    return sorted(set(evidence)), sorted(set(tests))


def validate_prompt_semantics(
    package: Mapping[str, Any],
    projection: Mapping[str, Any],
    prompt: str | None,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    action = projection.get("next_action")
    if not isinstance(action, Mapping):
        return [_diag("canonical projection has no structured next_action")]

    prompt_required = action.get("prompt_required") is True
    if not prompt_required:
        if prompt is not None:
            diagnostics.append(
                _diag("projection forbids a next-action prompt")
            )
        return diagnostics

    if prompt is None or not prompt.strip():
        return [_diag("projection requires a non-empty actionable prompt")]

    text = prompt.strip()
    if text == HISTORICAL_PLACEHOLDER:
        diagnostics.append(
            _diag("historical PR #22 placeholder is forbidden")
        )

    prompt_kind = action.get("prompt_kind")
    is_human_handoff = prompt_kind in {
        "human_review_handoff",
        "specialist_review_handoff",
    }
    minimum_lines = 14 if is_human_handoff else 20
    if len(text.splitlines()) < minimum_lines:
        diagnostics.append(
            _diag("prompt is non-empty but operationally incomplete")
        )

    required_sections = (
        HUMAN_HANDOFF_SECTIONS
        if is_human_handoff
        else MODEL_REQUIRED_SECTIONS
    )
    for section in required_sections:
        if section not in prompt:
            diagnostics.append(_diag(f"missing required section {section}"))

    if any(fragment in prompt for fragment in PROFILE_COMMAND_FRAGMENTS):
        diagnostics.append(
            _diag(
                "profile-selection commands must remain a separate "
                "verified artifact"
            )
        )

    identity = package.get("review_identity")
    if not isinstance(identity, Mapping):
        diagnostics.append(
            _diag("canonical package has no structured review identity")
        )
        return sorted(set(diagnostics))

    required_identity = {
        "target_repository": identity.get("target_repository"),
        "pr_number": identity.get("pr_number"),
        "reviewed_head_sha": identity.get("reviewed_head_sha"),
        "base_sha": identity.get("base_sha"),
    }
    for name, value in required_identity.items():
        if value in {None, ""}:
            diagnostics.append(
                _diag(f"structured identity field {name} is missing")
            )
        elif not _contains_token(prompt, value):
            diagnostics.append(_diag(f"prompt does not bind {name}"))

    protocol = package.get("protocol_version")
    if not isinstance(protocol, str) or not protocol:
        diagnostics.append(_diag("structured protocol_version is missing"))
    elif not is_human_handoff and not _contains_token(prompt, protocol):
        diagnostics.append(_diag("prompt does not bind protocol_version"))

    kind = action.get("kind")
    recipient = action.get("recipient")
    may_modify = action.get("may_modify_code")
    reason_codes = action.get("reason_codes")
    routing_values = {"recipient": recipient}
    if not is_human_handoff:
        routing_values.update(
            {
                "action kind": kind,
                "may_modify_code": str(bool(may_modify)).lower(),
                "prompt_kind": prompt_kind,
            }
        )
    for name, value in routing_values.items():
        if value in {None, ""} or not _contains_token(prompt, value):
            diagnostics.append(_diag(f"prompt does not bind {name}"))

    if not isinstance(reason_codes, list) or not reason_codes:
        diagnostics.append(
            _diag(
                "prompt-required action must carry canonical reason codes"
            )
        )
    elif not is_human_handoff and _json_token(reason_codes) not in prompt:
        diagnostics.append(
            _diag("prompt does not bind canonical reason codes")
        )
    elif is_human_handoff and not all(
        code in prompt for code in reason_codes
    ):
        diagnostics.append(
            _diag("human handoff does not bind canonical reason codes")
        )

    if kind in REPAIR_ACTIONS:
        if may_modify is not True:
            diagnostics.append(
                _diag(
                    "repair action must carry bounded modification authority"
                )
            )
        if "Modify only files materially necessary" not in prompt:
            diagnostics.append(
                _diag("repair prompt lacks bounded scope authority")
            )

    if kind in NON_MODIFYING_ACTIONS:
        if may_modify is not False:
            diagnostics.append(
                _diag(
                    "verification or fresh-review action must not "
                    "authorize modification"
                )
            )
        prohibition = (
            "No code, file, commit, workflow, schema, test, "
            "documentation, or behavior modification is authorized."
        )
        if prohibition not in prompt:
            diagnostics.append(
                _diag(
                    "non-modifying action lacks an explicit "
                    "modification prohibition"
                )
            )

    if kind == "rerun_review":
        if "run a fresh PR Inspector review" not in prompt:
            diagnostics.append(
                _diag("rerun_review must request a fresh review")
            )
        if (
            "Repair every confirmed defect" in prompt
            or "bounded repair lead" in prompt
        ):
            diagnostics.append(
                _diag("rerun_review must not authorize repair")
            )

    if kind == "verify" and (
        "Repair every confirmed defect" in prompt
        or "bounded repair lead" in prompt
    ):
        diagnostics.append(_diag("verify must not authorize repair"))

    governance = projection.get("governance_decision")
    technical_reasons = projection.get("technical_status_reason_codes")
    if (
        kind in REPAIR_ACTIONS
        and isinstance(governance, Mapping)
        and governance.get("status") in {"GAP_FOUND", "NOT_VERIFIABLE"}
        and isinstance(technical_reasons, list)
        and not technical_reasons
    ):
        diagnostics.append(
            _diag(
                "governance-only gaps cannot create technical "
                "repair authority"
            )
        )

    finding_ids = _finding_ids(package)
    evidence_refs, required_tests = _required_evidence_and_tests(
        package, str(kind)
    )
    reason_details = projection.get("reason_details")
    if (
        kind in REPAIR_ACTIONS
        and not finding_ids
        and not package.get("required_actions")
        and (
            not isinstance(reason_details, list)
            or not reason_details
        )
    ):
        diagnostics.append(
            _diag(
                "repair prompt has no affected finding, structured "
                "required action, or canonical reason subject"
            )
        )

    for finding_id in finding_ids:
        if finding_id not in prompt:
            diagnostics.append(
                _diag(f"prompt omits affected finding {finding_id}")
            )
    for ref in evidence_refs:
        if ref not in prompt:
            diagnostics.append(
                _diag(f"prompt omits evidence reference {ref}")
            )
    for test in required_tests:
        if _json_token(test) not in prompt:
            diagnostics.append(
                _diag("prompt omits a finding-required test")
            )

    if is_human_handoff:
        if "No merge or approval is performed by PR Inspector." not in prompt:
            diagnostics.append(
                _diag("human handoff omits merge/approval prohibition")
            )
        boundary = (
            "A model response, prompt execution, or generated summary "
            "cannot satisfy or claim this approval."
        )
        if boundary not in prompt:
            diagnostics.append(
                _diag(
                    "human handoff does not preserve the "
                    "human-approval boundary"
                )
            )
    else:
        mandatory_prohibitions = (
            "Do not merge or approve the PR",
            "write the default branch",
            "deploy",
            "access secrets or production",
        )
        for prohibition in mandatory_prohibitions:
            if prohibition not in prompt:
                diagnostics.append(
                    _diag(
                        f"prompt omits prohibition: {prohibition}"
                    )
                )
        if "independently reviewed again" not in prompt:
            diagnostics.append(
                _diag(
                    "prompt omits mandatory fresh PR Inspector re-review"
                )
            )

    return sorted(set(diagnostics))


def require_prompt_semantics(
    package: Mapping[str, Any],
    projection: Mapping[str, Any],
    prompt: str | None,
) -> None:
    diagnostics = validate_prompt_semantics(package, projection, prompt)
    if diagnostics:
        details = "; ".join(item.message for item in diagnostics)
        raise ValueError(f"{CODE}: {details}")


__all__ = [
    "CODE",
    "HISTORICAL_PLACEHOLDER",
    "PATH",
    "require_prompt_semantics",
    "validate_prompt_semantics",
]
