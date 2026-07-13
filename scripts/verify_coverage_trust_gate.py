#!/usr/bin/env python3
"""Authoritative external Coverage trust verifier for PRF-012 bootstrap."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ISSUER_REPOSITORY = "rezahh107/PR-Inspector"
ISSUER_REPOSITORY_ID = 1288323264
ISSUER_WORKFLOW_PATH = ".github/workflows/coverage-trust-gate.yml"
INDEPENDENT_WORKFLOW_PATH = ".github/workflows/verify-ev4-decision-kernel-pr43.yml"
TARGET_REPOSITORY = "rezahh107/EV4-Decision-Kernel"
TARGET_REPOSITORY_ID = 1292378784
TARGET_PR_NUMBER = 43
CALLER_WORKFLOW_PATH = ".github/workflows/validate-mvk.yml"
REQUIRED_GUARD_WORKFLOW_PATH = ".github/workflows/coverage-trust-required.yml"
OIDC_ISSUER = "https://token.actions.githubusercontent.com"
OIDC_AUDIENCE = "ev4-coverage-trust-gate-prf012"
EXPECTED_EXTERNAL_JOB = "external-coverage-trust"
EXPECTED_VALIDATION_JOB = "validate-mvk"
EXPECTED_GUARD_EXTERNAL_JOB = "authoritative-coverage-trust"
EXPECTED_GUARD_VALIDATION_JOB = "authoritative-target-validation"
REQUIRED_EXTERNAL_CHECK_NAME = "PRF-012 Authoritative Coverage Trust"
REQUIRED_VALIDATION_CHECK_NAME = "PRF-012 Authoritative Target Validation"
SENSITIVE_GATE_PATHS = (
    CALLER_WORKFLOW_PATH,
    REQUIRED_GUARD_WORKFLOW_PATH,
    "kernel/validator/validate-coverage-guarantee.mjs",
    "kernel/validator/validate-coverage-guarantee-prf010.mjs",
    "kernel/validator/validate-coverage-guarantee-legacy.mjs",
)
SELF_ISSUED_ENV_NAMES = (
    "COVERAGE_VALIDATED_AT",
    "COVERAGE_VALIDATION_SOURCE",
    "COVERAGE_TRUSTED_INGESTION_ATTESTATIONS",
)
FORBIDDEN_CALLER_IDENTITY_KEYS = (
    "target_repository",
    "target_repository_id",
    "target_head_sha",
    "target_base_sha",
    "pull_request_number",
    "issuer_workflow_sha",
)
PROOF_ROLES = {"runtime_proof", "consumer_proof", "coverage_credit"}
SHA40 = re.compile(r"^[0-9a-f]{40}$")
RFC3339_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
JOB_KEY = re.compile(r"^  ([A-Za-z0-9_-]+):(?:\s+#.*)?$")


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    path: str | None = None

    def as_dict(self) -> dict[str, str]:
        result = {"code": self.code, "message": self.message}
        if self.path:
            result["path"] = self.path
        return result


@dataclass(frozen=True)
class VerifiedIdentity:
    verification_mode: str
    target_repository: str
    target_repository_id: int
    pull_request_number: int
    target_base_sha: str
    target_head_sha: str
    issuer_workflow_sha: str
    caller_repository: str
    caller_repository_id: int
    caller_workflow_ref: str
    caller_workflow_sha: str
    run_id: str
    run_attempt: int
    check_run_id: str


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _run_git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL
    ).strip()


def _read_text(root: Path, relative_path: str) -> str:
    return (root / relative_path).read_text(encoding="utf-8")


def _base_text(root: Path, base_sha: str, relative_path: str) -> str | None:
    try:
        return _run_git(root, "show", f"{base_sha}:{relative_path}")
    except subprocess.CalledProcessError:
        return None


def _walk_json(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _proof_credit_requested(root: Path) -> bool:
    coverage_root = root / "planning" / "coverage"
    if not coverage_root.exists():
        return False
    for path in coverage_root.rglob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for node in _walk_json(value):
            if not isinstance(node, dict):
                continue
            if node.get("artifact_role") in PROOF_ROLES:
                return True
            if node.get("coverage_granted") is True:
                return True
    return False


def decode_oidc_claims(token: str) -> dict[str, Any]:
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError("OIDC token must be a three-part JWT")
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    value = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
    if not isinstance(value, dict):
        raise ValueError("OIDC JWT payload must be an object")
    return value


def _audience_matches(value: Any) -> bool:
    if isinstance(value, str):
        return value == OIDC_AUDIENCE
    if isinstance(value, list):
        return OIDC_AUDIENCE in value
    return False


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _job_blocks(workflow: str) -> tuple[dict[str, str], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    if "\t" in workflow or re.search(r"(?m)^\s*[^#\n]*[&*][A-Za-z0-9_-]+", workflow):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_CALLER_WORKFLOW_NONCANONICAL",
            "The protected caller workflow may not use tabs, YAML anchors, or aliases.",
            CALLER_WORKFLOW_PATH,
        ))
    lines = workflow.splitlines()
    try:
        jobs_index = next(i for i, line in enumerate(lines) if line == "jobs:")
    except StopIteration:
        return {}, diagnostics + [Diagnostic(
            "COV_EXTERNAL_REQUIRED_JOB_GRAPH_MISSING",
            "The caller workflow has no canonical jobs mapping.",
            CALLER_WORKFLOW_PATH,
        )]
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines[jobs_index + 1:]:
        if line and not line.startswith(" "):
            break
        match = JOB_KEY.match(line)
        if match:
            current = match.group(1)
            if current in blocks:
                diagnostics.append(Diagnostic(
                    "COV_EXTERNAL_CALLER_WORKFLOW_DUPLICATE_JOB",
                    f"Duplicate workflow job id: {current}.",
                    CALLER_WORKFLOW_PATH,
                ))
            blocks.setdefault(current, []).append(line)
        elif current is not None:
            blocks[current].append(line)
    return {key: "\n".join(value) for key, value in blocks.items()}, diagnostics


def _job_level_value(block: str, key: str) -> str | None:
    match = re.search(rf"(?m)^    {re.escape(key)}:\s*(.*?)\s*$", block)
    return match.group(1) if match else None


def _workflow_topology_diagnostics(workflow: str, issuer_sha: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    blocks, parse_diagnostics = _job_blocks(workflow)
    diagnostics.extend(parse_diagnostics)
    external = blocks.get(EXPECTED_EXTERNAL_JOB)
    validation = blocks.get(EXPECTED_VALIDATION_JOB)
    expected_uses = (
        f"{ISSUER_REPOSITORY}/{ISSUER_WORKFLOW_PATH}@{issuer_sha}"
    )
    pin_pattern = re.compile(
        r"uses:\s*"
        + re.escape(f"{ISSUER_REPOSITORY}/{ISSUER_WORKFLOW_PATH}@")
        + r"([0-9a-f]{40})"
    )
    all_pins = pin_pattern.findall(workflow)

    if external is None:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_REQUIRED_JOB_MISSING",
            f"The required {EXPECTED_EXTERNAL_JOB} job is missing.",
            CALLER_WORKFLOW_PATH,
        ))
    else:
        if _job_level_value(external, "uses") != expected_uses:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_OIDC_ISSUER_SHA_MISMATCH",
                "The active external job must use the immutable reusable-workflow SHA authenticated by OIDC.",
                CALLER_WORKFLOW_PATH,
            ))
        if _job_level_value(external, "if") is not None:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_REQUIRED_JOB_DEAD",
                "The required external job may not be conditionally disabled.",
                CALLER_WORKFLOW_PATH,
            ))
        if any(re.search(rf"(?m)^\s+{re.escape(key)}\s*:", external)
               for key in FORBIDDEN_CALLER_IDENTITY_KEYS):
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_CALLER_IDENTITY_INPUT_FORBIDDEN",
                "Repository, PR, base, head, and issuer identity must be derived inside external enforcement.",
                CALLER_WORKFLOW_PATH,
            ))
        if "id-token: write" not in external or "pull-requests: read" not in external:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_REQUIRED_JOB_PERMISSIONS_INVALID",
                "The external job must grant only the read and OIDC permissions required for authoritative verification.",
                CALLER_WORKFLOW_PATH,
            ))

    if all_pins != [issuer_sha]:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_ROOT_PIN_TOPOLOGY_INVALID",
            "The immutable external workflow pin must appear exactly once in the active required job.",
            CALLER_WORKFLOW_PATH,
        ))

    if validation is None:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_VALIDATION_JOB_MISSING",
            f"The required {EXPECTED_VALIDATION_JOB} job is missing.",
            CALLER_WORKFLOW_PATH,
        ))
    else:
        if _job_level_value(validation, "needs") != EXPECTED_EXTERNAL_JOB:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_VALIDATION_NEEDS_MISSING",
                "Target validation must require successful authoritative external verification.",
                CALLER_WORKFLOW_PATH,
            ))
        if _job_level_value(validation, "if") is not None:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_VALIDATION_CONDITION_INVALID",
                "Target validation may not bypass or neutralize its external dependency.",
                CALLER_WORKFLOW_PATH,
            ))
        expected_ref = (
            "ref: ${{ needs.external-coverage-trust.outputs.verified_head_sha }}"
        )
        checkout_refs = re.findall(r"(?m)^\s+ref:\s*(.*?)\s*$", validation)
        if expected_ref not in validation or checkout_refs != [
            "${{ needs.external-coverage-trust.outputs.verified_head_sha }}"
        ]:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_VALIDATION_CHECKOUT_MISMATCH",
                "Validation checkout must be bound only to the externally verified exact PR head.",
                CALLER_WORKFLOW_PATH,
            ))
        expected_bindings = (
            "COVERAGE_REPOSITORY: ${{ needs.external-coverage-trust.outputs.verified_repository }}",
            "COVERAGE_PR_NUMBER: ${{ needs.external-coverage-trust.outputs.verified_pr_number }}",
            "COVERAGE_BASE_SHA: ${{ needs.external-coverage-trust.outputs.verified_base_sha }}",
            "COVERAGE_HEAD_SHA: ${{ needs.external-coverage-trust.outputs.verified_head_sha }}",
        )
        if any(binding not in validation for binding in expected_bindings):
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_VALIDATION_IDENTITY_BINDING_MISSING",
                "Coverage validation inputs must use only authoritative external identity outputs.",
                CALLER_WORKFLOW_PATH,
            ))

    if any(name in workflow for name in SELF_ISSUED_ENV_NAMES) or "/bin/date" in workflow:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_ROOT_TARGET_MINT_FORBIDDEN",
            "A target-controlled workflow may not mint validation time or trust-source values.",
            CALLER_WORKFLOW_PATH,
        ))
    if "COVERAGE_TRUSTED_INGESTION_ATTESTATIONS" in workflow:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_ATTESTATION_UNSIGNED_ENV_FORBIDDEN",
            "Plain target-controlled environment JSON is not a verified ingestion attestation.",
            CALLER_WORKFLOW_PATH,
        ))
    return diagnostics


def _required_guard_diagnostics(
    target_root: Path, issuer_sha: str
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    try:
        workflow = _read_text(target_root, REQUIRED_GUARD_WORKFLOW_PATH)
    except OSError:
        return [Diagnostic(
            "COV_EXTERNAL_REQUIRED_GUARD_MISSING",
            "The protected pull_request_target enforcement workflow is missing.",
            REQUIRED_GUARD_WORKFLOW_PATH,
        )]
    if "pull_request_target:" not in workflow:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_REQUIRED_GUARD_TRIGGER_INVALID",
            "The enforcement workflow must run from the protected default-branch pull_request_target definition.",
            REQUIRED_GUARD_WORKFLOW_PATH,
        ))
    blocks, parse_diagnostics = _job_blocks(workflow)
    diagnostics.extend(
        Diagnostic(item.code, item.message, REQUIRED_GUARD_WORKFLOW_PATH)
        for item in parse_diagnostics
    )
    external = blocks.get(EXPECTED_GUARD_EXTERNAL_JOB)
    validation = blocks.get(EXPECTED_GUARD_VALIDATION_JOB)
    expected_uses = f"{ISSUER_REPOSITORY}/{ISSUER_WORKFLOW_PATH}@{issuer_sha}"
    pin_pattern = re.compile(
        r"uses:\s*"
        + re.escape(f"{ISSUER_REPOSITORY}/{ISSUER_WORKFLOW_PATH}@")
        + r"([0-9a-f]{40})"
    )
    if external is None:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_REQUIRED_GUARD_JOB_MISSING",
            "The protected authoritative external trust job is missing.",
            REQUIRED_GUARD_WORKFLOW_PATH,
        ))
    else:
        if _job_level_value(external, "uses") != expected_uses:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_REQUIRED_GUARD_ISSUER_MISMATCH",
                "The protected guard must call the OIDC-authenticated immutable issuer SHA.",
                REQUIRED_GUARD_WORKFLOW_PATH,
            ))
        if _job_level_value(external, "if") is not None:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_REQUIRED_GUARD_JOB_DEAD",
                "The protected external trust job may not be conditionally disabled.",
                REQUIRED_GUARD_WORKFLOW_PATH,
            ))
        if any(re.search(rf"(?m)^\s+{re.escape(key)}\s*:", external)
               for key in FORBIDDEN_CALLER_IDENTITY_KEYS):
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_REQUIRED_GUARD_CALLER_INPUT_FORBIDDEN",
                "The protected guard may not supply target or issuer identity.",
                REQUIRED_GUARD_WORKFLOW_PATH,
            ))
        if REQUIRED_EXTERNAL_CHECK_NAME not in external:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_REQUIRED_CHECK_NAME_MISMATCH",
                "The protected external check has the wrong immutable check name.",
                REQUIRED_GUARD_WORKFLOW_PATH,
            ))
    if pin_pattern.findall(workflow) != [issuer_sha]:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_REQUIRED_GUARD_PIN_TOPOLOGY_INVALID",
            "The guard issuer pin must appear exactly once in the active protected job.",
            REQUIRED_GUARD_WORKFLOW_PATH,
        ))
    if validation is None:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_REQUIRED_GUARD_VALIDATION_MISSING",
            "The protected exact-head validation job is missing.",
            REQUIRED_GUARD_WORKFLOW_PATH,
        ))
    else:
        if _job_level_value(validation, "needs") != EXPECTED_GUARD_EXTERNAL_JOB:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_REQUIRED_GUARD_NEEDS_MISSING",
                "Protected validation must depend on authoritative external trust.",
                REQUIRED_GUARD_WORKFLOW_PATH,
            ))
        if _job_level_value(validation, "if") is not None:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_REQUIRED_GUARD_CONDITION_INVALID",
                "Protected validation may not bypass its external dependency.",
                REQUIRED_GUARD_WORKFLOW_PATH,
            ))
        expected_ref = (
            "ref: ${{ needs.authoritative-coverage-trust.outputs.verified_head_sha }}"
        )
        if expected_ref not in validation:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_REQUIRED_GUARD_CHECKOUT_MISMATCH",
                "Protected validation checkout must use the externally verified exact head.",
                REQUIRED_GUARD_WORKFLOW_PATH,
            ))
        if REQUIRED_VALIDATION_CHECK_NAME not in validation:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_REQUIRED_VALIDATION_CHECK_NAME_MISMATCH",
                "The protected validation check has the wrong immutable check name.",
                REQUIRED_GUARD_WORKFLOW_PATH,
            ))
    workflow_root = target_root / ".github" / "workflows"
    if workflow_root.exists():
        for path in workflow_root.glob("*.y*ml"):
            relative = path.relative_to(target_root).as_posix()
            if relative == REQUIRED_GUARD_WORKFLOW_PATH:
                continue
            try:
                other = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if (
                REQUIRED_EXTERNAL_CHECK_NAME in other
                or REQUIRED_VALIDATION_CHECK_NAME in other
            ):
                diagnostics.append(Diagnostic(
                    "COV_EXTERNAL_REQUIRED_CHECK_NAME_SPOOFED",
                    "Reserved protected check names may not appear in another target workflow.",
                    relative,
                ))
    return diagnostics


def derive_authoritative_identity(
    *,
    event: dict[str, Any],
    api_pr: dict[str, Any],
    oidc_claims: dict[str, Any],
    environment: dict[str, str],
) -> tuple[VerifiedIdentity | None, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    caller_repository = str(oidc_claims.get("repository") or "")
    caller_repository_id = _int(oidc_claims.get("repository_id"))
    event_name = str(oidc_claims.get("event_name") or "")
    workflow_ref = str(oidc_claims.get("workflow_ref") or "")
    workflow_sha = str(oidc_claims.get("workflow_sha") or "")
    job_workflow_ref = str(oidc_claims.get("job_workflow_ref") or "")
    issuer_sha = str(oidc_claims.get("job_workflow_sha") or "")
    run_id = str(oidc_claims.get("run_id") or "")
    run_attempt = _int(oidc_claims.get("run_attempt"))
    check_run_id = str(oidc_claims.get("check_run_id") or "")

    if oidc_claims.get("iss") != OIDC_ISSUER or not _audience_matches(oidc_claims.get("aud")):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_OIDC_AUTHORITY_INVALID",
            "OIDC issuer or audience does not match the external Coverage trust policy.",
        ))
    if not SHA40.fullmatch(issuer_sha):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_OIDC_ISSUER_SHA_INVALID",
            "OIDC must authenticate the immutable reusable-workflow commit SHA.",
        ))
    expected_job_prefix = f"{ISSUER_REPOSITORY}/{ISSUER_WORKFLOW_PATH}@"
    if not job_workflow_ref.startswith(expected_job_prefix):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_OIDC_WORKFLOW_IDENTITY_MISMATCH",
            "OIDC job_workflow_ref does not identify the approved reusable workflow.",
        ))
    env_run_id = str(environment.get("GITHUB_RUN_ID") or "")
    env_run_attempt = _int(environment.get("GITHUB_RUN_ATTEMPT"))
    if run_id != env_run_id or run_attempt != env_run_attempt:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_OIDC_RUN_IDENTITY_MISMATCH",
            "OIDC run ID or attempt does not match the executing GitHub job.",
        ))

    mode: str
    if caller_repository_id == TARGET_REPOSITORY_ID:
        mode = "target_pull_request_event_api"
        expected_workflow_prefix = f"{TARGET_REPOSITORY}/{CALLER_WORKFLOW_PATH}@"
        if (
            caller_repository != TARGET_REPOSITORY
            or event_name != "pull_request"
            or not workflow_ref.startswith(expected_workflow_prefix)
        ):
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_EVENT_CALLER_IDENTITY_MISMATCH",
                "The target caller must be the canonical pull_request workflow in the expected repository.",
            ))
        repository = event.get("repository") or {}
        pr = event.get("pull_request") or {}
        event_number = _int(pr.get("number") or event.get("number"))
        event_base = ((pr.get("base") or {}).get("sha"))
        event_head = ((pr.get("head") or {}).get("sha"))
        event_repo_id = _int(repository.get("id"))
        event_repo_name = repository.get("full_name")
        if event_repo_id != TARGET_REPOSITORY_ID or event_repo_name != TARGET_REPOSITORY:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_EVENT_REPOSITORY_ID_MISMATCH",
                "GitHub event repository identity does not match the protected target.",
            ))
    elif caller_repository_id == ISSUER_REPOSITORY_ID:
        mode = "independent_policy_api"
        expected_workflow_prefix = f"{ISSUER_REPOSITORY}/{INDEPENDENT_WORKFLOW_PATH}@"
        if (
            caller_repository != ISSUER_REPOSITORY
            or not workflow_ref.startswith(expected_workflow_prefix)
            or event_name not in {"push", "workflow_dispatch", "pull_request"}
        ):
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_INDEPENDENT_CALLER_IDENTITY_MISMATCH",
                "Independent verification must originate from the fixed PR-Inspector workflow.",
            ))
        event_number = TARGET_PR_NUMBER
        event_base = ((api_pr.get("base") or {}).get("sha"))
        event_head = ((api_pr.get("head") or {}).get("sha"))
        event_repo_id = TARGET_REPOSITORY_ID
        event_repo_name = TARGET_REPOSITORY
    else:
        mode = "invalid"
        event_number = None
        event_base = None
        event_head = None
        event_repo_id = None
        event_repo_name = None
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_OIDC_CALLER_REPOSITORY_INVALID",
            "OIDC caller repository is neither the protected target nor the fixed independent verifier.",
        ))

    api_number = _int(api_pr.get("number"))
    api_base = (api_pr.get("base") or {}).get("sha")
    api_head = (api_pr.get("head") or {}).get("sha")
    api_base_repo = (api_pr.get("base") or {}).get("repo") or {}
    api_repo_id = _int(api_base_repo.get("id"))
    api_repo_name = api_base_repo.get("full_name")

    if api_repo_id != TARGET_REPOSITORY_ID or api_repo_name != TARGET_REPOSITORY:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_API_REPOSITORY_ID_MISMATCH",
            "Authoritative GitHub API repository identity does not match the protected target.",
        ))
    if api_number != TARGET_PR_NUMBER or event_number != api_number:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_EVENT_PR_MISMATCH",
            "GitHub event/policy PR number does not match the authoritative API PR number.",
        ))
    if event_base != api_base:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_EVENT_BASE_MISMATCH",
            "GitHub event base SHA does not match the authoritative API base SHA.",
        ))
    if event_head != api_head:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_EVENT_HEAD_MISMATCH",
            "GitHub event head SHA does not match the authoritative API PR head.",
        ))
    if not SHA40.fullmatch(str(api_base or "")) or not SHA40.fullmatch(str(api_head or "")):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_API_PR_IDENTITY_INVALID",
            "Authoritative API base and head must be immutable 40-hex commit SHAs.",
        ))

    if diagnostics:
        return None, diagnostics
    assert caller_repository_id is not None
    assert run_attempt is not None
    return VerifiedIdentity(
        verification_mode=mode,
        target_repository=TARGET_REPOSITORY,
        target_repository_id=TARGET_REPOSITORY_ID,
        pull_request_number=api_number,
        target_base_sha=api_base,
        target_head_sha=api_head,
        issuer_workflow_sha=issuer_sha,
        caller_repository=caller_repository,
        caller_repository_id=caller_repository_id,
        caller_workflow_ref=workflow_ref,
        caller_workflow_sha=workflow_sha,
        run_id=run_id,
        run_attempt=run_attempt,
        check_run_id=check_run_id,
    ), diagnostics


def evaluate_target(
    *,
    target_root: Path,
    identity: VerifiedIdentity,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    try:
        checked_out_head = _run_git(target_root, "rev-parse", "HEAD")
    except subprocess.CalledProcessError:
        checked_out_head = ""
    if checked_out_head != identity.target_head_sha:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_HEAD_MISMATCH",
            "The externally verified checkout does not match the authoritative API PR head.",
        ))
    try:
        _run_git(
            target_root,
            "merge-base",
            "--is-ancestor",
            identity.target_base_sha,
            identity.target_head_sha,
        )
    except subprocess.CalledProcessError:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_BASE_NOT_ANCESTOR",
            "The authoritative API base is not an ancestor of the PR head.",
        ))
    try:
        workflow = _read_text(target_root, CALLER_WORKFLOW_PATH)
    except OSError:
        workflow = ""
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_CALLER_WORKFLOW_MISSING",
            "The target caller workflow is missing.",
            CALLER_WORKFLOW_PATH,
        ))
    diagnostics.extend(_workflow_topology_diagnostics(
        workflow, identity.issuer_workflow_sha
    ))
    diagnostics.extend(_required_guard_diagnostics(
        target_root, identity.issuer_workflow_sha
    ))
    proof_requested = _proof_credit_requested(target_root)
    if proof_requested:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_BOOTSTRAP_PROOF_CREDIT_FORBIDDEN",
            "PRF-012 bootstrap authorizes no runtime, consumer, or coverage-credit proof.",
            "planning/coverage",
        ))
        for relative_path in SENSITIVE_GATE_PATHS:
            try:
                current = _read_text(target_root, relative_path)
            except OSError:
                current = None
            base = _base_text(target_root, identity.target_base_sha, relative_path)
            if current is None or base is None or current != base:
                diagnostics.append(Diagnostic(
                    "COV_EXTERNAL_TRUST_GATE_IDENTITY_MISMATCH",
                    "Proof credit requires gate-sensitive code to match a separately approved identity.",
                    relative_path,
                ))
    return diagnostics


def issue_bootstrap_attestation(
    *,
    identity: VerifiedIdentity,
    event: dict[str, Any],
    api_pr: dict[str, Any],
    oidc_claims: dict[str, Any],
    validated_at: str,
) -> dict[str, Any]:
    if not RFC3339_UTC.fullmatch(validated_at):
        raise ValueError("validated_at must be second-precision UTC RFC3339")
    datetime.strptime(validated_at, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    payload: dict[str, Any] = {
        "schema_version": 2,
        "attestation_kind": "coverage_trust_bootstrap_no_proof",
        "issuer": {
            "identity": ISSUER_REPOSITORY,
            "repository_id": ISSUER_REPOSITORY_ID,
            "workflow_path": ISSUER_WORKFLOW_PATH,
            "workflow_sha": identity.issuer_workflow_sha,
        },
        "target": {
            "repository": identity.target_repository,
            "repository_id": identity.target_repository_id,
            "pull_request_number": identity.pull_request_number,
            "base_sha": identity.target_base_sha,
            "evidence_head_sha": identity.target_head_sha,
        },
        "github": {
            "verification_mode": identity.verification_mode,
            "caller_repository": identity.caller_repository,
            "caller_repository_id": identity.caller_repository_id,
            "caller_workflow_ref": identity.caller_workflow_ref,
            "caller_workflow_sha": identity.caller_workflow_sha,
            "run_id": identity.run_id,
            "run_attempt": identity.run_attempt,
            "check_run_id": identity.check_run_id,
        },
        "authority_evidence": {
            "event_sha256": _sha256_json(event),
            "api_pr_sha256": _sha256_json(api_pr),
            "oidc_claims_sha256": _sha256_json(oidc_claims),
        },
        "trusted_validation_at": validated_at,
        "trusted_ingestion_at": None,
        "proof_credit_authorized": False,
    }
    capability_input = b"ev4.coverage.external-trust.prf012\0" + _canonical_bytes(payload)
    payload["verifier_created_capability"] = hashlib.sha256(
        capability_input
    ).hexdigest()
    return payload


def verify_bootstrap_attestation(
    attestation: dict[str, Any],
    *,
    identity: VerifiedIdentity,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    expected_capability = attestation.get("verifier_created_capability")
    unsigned = dict(attestation)
    unsigned.pop("verifier_created_capability", None)
    actual_capability = hashlib.sha256(
        b"ev4.coverage.external-trust.prf012\0" + _canonical_bytes(unsigned)
    ).hexdigest()
    if expected_capability != actual_capability:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_ATTESTATION_CAPABILITY_INVALID",
            "The verifier-created capability does not bind the attestation bytes.",
        ))
    issuer = attestation.get("issuer") or {}
    target = attestation.get("target") or {}
    github = attestation.get("github") or {}
    if (
        issuer.get("identity") != ISSUER_REPOSITORY
        or issuer.get("repository_id") != ISSUER_REPOSITORY_ID
        or issuer.get("workflow_path") != ISSUER_WORKFLOW_PATH
        or issuer.get("workflow_sha") != identity.issuer_workflow_sha
    ):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_ROOT_IDENTITY_MISMATCH",
            "Attestation issuer identity or immutable OIDC workflow SHA does not match.",
        ))
    if (
        target.get("repository") != identity.target_repository
        or target.get("repository_id") != identity.target_repository_id
        or target.get("pull_request_number") != identity.pull_request_number
        or target.get("base_sha") != identity.target_base_sha
        or target.get("evidence_head_sha") != identity.target_head_sha
    ):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_ATTESTATION_TARGET_MISMATCH",
            "Attestation target repository ID, PR, base, or head does not match.",
        ))
    if (
        str(github.get("run_id")) != identity.run_id
        or github.get("run_attempt") != identity.run_attempt
        or github.get("check_run_id") != identity.check_run_id
    ):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_ATTESTATION_RUN_MISMATCH",
            "Attestation GitHub run/check identity does not match.",
        ))
    if attestation.get("proof_credit_authorized") is not False:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_ATTESTATION_BOOTSTRAP_SCOPE_INVALID",
            "Bootstrap attestation must explicitly deny proof credit.",
        ))
    return diagnostics


def _write_outputs(path: Path, identity: VerifiedIdentity) -> None:
    values = {
        "verified_repository": identity.target_repository,
        "verified_repository_id": str(identity.target_repository_id),
        "verified_pr_number": str(identity.pull_request_number),
        "verified_base_sha": identity.target_base_sha,
        "verified_head_sha": identity.target_head_sha,
        "verified_issuer_sha": identity.issuer_workflow_sha,
        "verification_mode": identity.verification_mode,
        "proof_credit_authorized": "false",
    }
    with path.open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--event-path", type=Path, required=True)
    parser.add_argument("--api-pr-file", type=Path, required=True)
    parser.add_argument("--oidc-token-file", type=Path, required=True)
    parser.add_argument("--validated-at", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--github-output", type=Path, required=True)
    args = parser.parse_args()

    try:
        event = json.loads(args.event_path.read_text(encoding="utf-8"))
        api_pr = json.loads(args.api_pr_file.read_text(encoding="utf-8"))
        token = args.oidc_token_file.read_text(encoding="utf-8").strip()
        claims = decode_oidc_claims(token)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(
            f"COV_EXTERNAL_AUTHORITY_EVIDENCE_INVALID: {exc}",
            file=sys.stderr,
        )
        return 1

    identity, diagnostics = derive_authoritative_identity(
        event=event,
        api_pr=api_pr,
        oidc_claims=claims,
        environment={
            "GITHUB_RUN_ID": str(__import__("os").environ.get("GITHUB_RUN_ID", "")),
            "GITHUB_RUN_ATTEMPT": str(__import__("os").environ.get("GITHUB_RUN_ATTEMPT", "")),
        },
    )
    if identity is not None:
        diagnostics.extend(evaluate_target(
            target_root=args.target_root,
            identity=identity,
        ))
    if diagnostics:
        print("External Coverage Trust Gate diagnostics:", file=sys.stderr)
        for item in diagnostics:
            location = f" [{item.path}]" if item.path else ""
            print(f"  {item.code}{location}: {item.message}", file=sys.stderr)
        return 1
    assert identity is not None

    attestation = issue_bootstrap_attestation(
        identity=identity,
        event=event,
        api_pr=api_pr,
        oidc_claims=claims,
        validated_at=args.validated_at,
    )
    verify_diagnostics = verify_bootstrap_attestation(
        attestation, identity=identity
    )
    if verify_diagnostics:
        for item in verify_diagnostics:
            print(f"{item.code}: {item.message}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(attestation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_outputs(args.github_output, identity)
    print(json.dumps({
        "result": "PASS",
        "verification_mode": identity.verification_mode,
        "issuer_workflow_sha": identity.issuer_workflow_sha,
        "target_repository": identity.target_repository,
        "target_repository_id": identity.target_repository_id,
        "pull_request_number": identity.pull_request_number,
        "base_sha": identity.target_base_sha,
        "evidence_head_sha": identity.target_head_sha,
        "run_id": identity.run_id,
        "run_attempt": identity.run_attempt,
        "check_run_id": identity.check_run_id,
        "proof_credit_authorized": False,
        "attestation_path": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
