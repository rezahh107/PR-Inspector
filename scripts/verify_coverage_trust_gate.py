#!/usr/bin/env python3
"""PRF-013 authoritative external Coverage trust verifier."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys

import yaml
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ISSUER_REPOSITORY = "rezahh107/PR-Inspector"
ISSUER_REPOSITORY_ID = 1288323264
ISSUER_WORKFLOW_PATH = ".github/workflows/coverage-trust-gate.yml"
INDEPENDENT_WORKFLOW_PATH = ".github/workflows/verify-ev4-decision-kernel-pr43.yml"
TARGET_REPOSITORY = "rezahh107/EV4-Decision-Kernel"
TARGET_REPOSITORY_ID = 1292378784
CALLER_WORKFLOW_PATH = ".github/workflows/validate-mvk.yml"
REQUIRED_GUARD_WORKFLOW_PATH = ".github/workflows/coverage-trust-required.yml"
OIDC_ISSUER = "https://token.actions.githubusercontent.com"
OIDC_AUDIENCE = "ev4-coverage-trust-gate-prf013"
PROOF_ROLES = {"runtime_proof", "consumer_proof", "coverage_credit"}
SHA40 = re.compile(r"^[0-9a-f]{40}$")
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
FORBIDDEN_INPUTS = (
    "target_repository",
    "target_repository_id",
    "target_head_sha",
    "target_base_sha",
    "pull_request_number",
    "issuer_workflow_sha",
)
FORBIDDEN_TRUST = (
    "COVERAGE_VALIDATED_AT",
    "COVERAGE_VALIDATION_SOURCE",
    "COVERAGE_TRUSTED_INGESTION_ATTESTATIONS",
    "/bin/date",
)


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    path: str | None = None


@dataclass(frozen=True)
class VerifiedIdentity:
    verification_mode: str
    target_repository: str
    target_repository_id: int
    pull_request_number: int
    target_base_sha: str
    target_head_sha: str
    issuer_workflow_sha: str
    issuer_workflow_path: str
    caller_repository: str
    caller_repository_id: int
    caller_workflow_ref: str
    caller_workflow_sha: str
    event_name: str
    run_id: str
    run_attempt: int
    check_run_id: str


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def decode_oidc_claims(token: str) -> dict[str, Any]:
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError("OIDC token must be a three-part JWT")
    raw = parts[1] + "=" * (-len(parts[1]) % 4)
    value = json.loads(base64.urlsafe_b64decode(raw.encode("ascii")))
    if not isinstance(value, dict):
        raise ValueError("OIDC payload must be an object")
    return value


def audience_ok(value: Any) -> bool:
    return value == OIDC_AUDIENCE or (
        isinstance(value, list) and OIDC_AUDIENCE in value
    )


def event_pr(
    event: dict[str, Any],
) -> tuple[int | None, str | None, str | None]:
    pr = event.get("pull_request") or {}
    return (
        int_or_none(pr.get("number") or event.get("number")),
        (pr.get("base") or {}).get("sha"),
        (pr.get("head") or {}).get("sha"),
    )


def bounded_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return path.name


def planning_coverage_diagnostics(root: Path) -> list[Diagnostic]:
    folder = root / "planning" / "coverage"
    if not folder.exists():
        return []
    diagnostics: list[Diagnostic] = []
    stack: list[Any] = []
    for path in sorted(folder.rglob("*.json")):
        rel = bounded_path(root, path)
        try:
            stack.append(json.loads(path.read_text(encoding="utf-8")))
        except UnicodeDecodeError as exc:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_PLANNING_JSON_INVALID",
                f"Planning coverage JSON is not valid UTF-8: {exc.reason}.",
                rel,
            ))
        except json.JSONDecodeError as exc:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_PLANNING_JSON_INVALID",
                f"Planning coverage JSON is malformed at line {exc.lineno} column {exc.colno}.",
                rel,
            ))
        except OSError as exc:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_PLANNING_JSON_UNREADABLE",
                f"Planning coverage JSON cannot be read: {exc.strerror or exc}.",
                rel,
            ))
    if diagnostics:
        return diagnostics
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            if (
                value.get("artifact_role") in PROOF_ROLES
                or value.get("coverage_granted") is True
            ):
                diagnostics.append(Diagnostic(
                    "COV_EXTERNAL_TRUST_BOOTSTRAP_PROOF_CREDIT_FORBIDDEN",
                    "Proof credit remains disabled.",
                    "planning/coverage",
                ))
                return diagnostics
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    return []


def derive_authoritative_identity(
    *,
    event: dict[str, Any],
    api_pr: dict[str, Any],
    oidc_claims: dict[str, Any],
    environment: dict[str, str],
    independent_policy_pr_number: int | None = None,
) -> tuple[VerifiedIdentity | None, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    repository = str(oidc_claims.get("repository") or "")
    repository_id = int_or_none(oidc_claims.get("repository_id"))
    event_name = str(oidc_claims.get("event_name") or "")
    workflow_ref = str(oidc_claims.get("workflow_ref") or "")
    workflow_sha = str(oidc_claims.get("workflow_sha") or "")
    job_workflow_ref = str(oidc_claims.get("job_workflow_ref") or "")
    job_workflow_sha = str(oidc_claims.get("job_workflow_sha") or "")
    run_id = str(oidc_claims.get("run_id") or "")
    run_attempt = int_or_none(oidc_claims.get("run_attempt"))
    check_run_id = str(oidc_claims.get("check_run_id") or "")

    if (
        oidc_claims.get("iss") != OIDC_ISSUER
        or not audience_ok(oidc_claims.get("aud"))
    ):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_OIDC_AUTHORITY_INVALID",
            "OIDC issuer or audience is invalid.",
        ))
    environment_run_id = str(environment.get("GITHUB_RUN_ID") or "")
    environment_run_attempt = int_or_none(
        environment.get("GITHUB_RUN_ATTEMPT")
    )
    if (
        not run_id.isdecimal()
        or int(run_id) < 1
        or run_attempt is None
        or run_attempt < 1
        or not environment_run_id.isdecimal()
        or int(environment_run_id) < 1
        or environment_run_attempt is None
        or environment_run_attempt < 1
        or run_id != environment_run_id
        or run_attempt != environment_run_attempt
    ):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_OIDC_RUN_IDENTITY_MISMATCH",
            "OIDC run identity mismatch.",
        ))

    number: int | None
    event_base: str | None
    event_head: str | None
    issuer_sha = ""
    issuer_path = ""
    mode = "invalid"

    expected_job_ref = (
        f"{ISSUER_REPOSITORY}/{ISSUER_WORKFLOW_PATH}@{job_workflow_sha}"
    )
    if (
        not SHA40.fullmatch(job_workflow_sha)
        or job_workflow_ref != expected_job_ref
    ):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_OIDC_WORKFLOW_IDENTITY_MISMATCH",
            "OIDC does not authenticate the immutable reusable issuer.",
        ))
    issuer_sha = job_workflow_sha
    issuer_path = ISSUER_WORKFLOW_PATH

    if repository_id == TARGET_REPOSITORY_ID:
        if independent_policy_pr_number not in (None, 0):
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_TARGET_POLICY_INPUT_FORBIDDEN",
                "Target callers may not select PR identity.",
            ))
        paths = {
            "pull_request": CALLER_WORKFLOW_PATH,
            "pull_request_target": REQUIRED_GUARD_WORKFLOW_PATH,
        }
        expected_path = paths.get(event_name)
        if (
            repository != TARGET_REPOSITORY
            or expected_path is None
            or not workflow_ref.startswith(
                f"{TARGET_REPOSITORY}/{expected_path}@"
            )
        ):
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_EVENT_CALLER_IDENTITY_MISMATCH",
                "Target caller identity mismatch.",
            ))
        mode = (
            "target_pull_request_event_api"
            if event_name == "pull_request"
            else "target_pull_request_target_event_api"
        )
        event_repository = event.get("repository") or {}
        if (
            int_or_none(event_repository.get("id"))
            != TARGET_REPOSITORY_ID
            or event_repository.get("full_name") != TARGET_REPOSITORY
        ):
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_EVENT_REPOSITORY_ID_MISMATCH",
                "Event repository mismatch.",
            ))
        number, event_base, event_head = event_pr(event)
        if number is None or number < 1:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_EVENT_PR_INVALID",
                "Target event has no valid PR number.",
            ))
    elif repository_id == ISSUER_REPOSITORY_ID:
        if (
            repository != ISSUER_REPOSITORY
            or not workflow_ref.startswith(
                f"{ISSUER_REPOSITORY}/{INDEPENDENT_WORKFLOW_PATH}@"
            )
            or event_name
            not in {"push", "pull_request", "workflow_dispatch"}
        ):
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_INDEPENDENT_CALLER_IDENTITY_MISMATCH",
                "Independent caller identity mismatch.",
            ))
        number = independent_policy_pr_number
        if number is None or number < 1:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_INDEPENDENT_POLICY_PR_INVALID",
                "Independent policy PR is invalid.",
            ))
        event_base = (api_pr.get("base") or {}).get("sha")
        event_head = (api_pr.get("head") or {}).get("sha")
        mode = "independent_explicit_policy_api"
    else:
        number = None
        event_base = None
        event_head = None
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_OIDC_CALLER_REPOSITORY_INVALID",
            "OIDC caller repository is not approved.",
        ))

    api_number = int_or_none(api_pr.get("number"))
    api_base = (api_pr.get("base") or {}).get("sha")
    api_head = (api_pr.get("head") or {}).get("sha")
    api_repository = (api_pr.get("base") or {}).get("repo") or {}
    if (
        int_or_none(api_repository.get("id")) != TARGET_REPOSITORY_ID
        or api_repository.get("full_name") != TARGET_REPOSITORY
    ):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_API_REPOSITORY_ID_MISMATCH",
            "API repository mismatch.",
        ))
    if number != api_number:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_EVENT_PR_MISMATCH",
            "Event or policy PR does not match API PR.",
        ))
    if event_base != api_base:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_EVENT_BASE_MISMATCH",
            "Event base does not match API base.",
        ))
    if event_head != api_head:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_EVENT_HEAD_MISMATCH",
            "Event head does not match API head.",
        ))
    if (
        not SHA40.fullmatch(str(api_base or ""))
        or not SHA40.fullmatch(str(api_head or ""))
    ):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_API_PR_IDENTITY_INVALID",
            "API base or head is invalid.",
        ))

    if diagnostics:
        return None, diagnostics
    if repository_id is None or run_attempt is None or api_number is None:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_AUTHORITY_IDENTITY_INCOMPLETE",
            "Authority identity is incomplete after validation.",
        ))
        return None, diagnostics
    return VerifiedIdentity(
        verification_mode=mode,
        target_repository=TARGET_REPOSITORY,
        target_repository_id=TARGET_REPOSITORY_ID,
        pull_request_number=api_number,
        target_base_sha=str(api_base),
        target_head_sha=str(api_head),
        issuer_workflow_sha=issuer_sha,
        issuer_workflow_path=issuer_path,
        caller_repository=repository,
        caller_repository_id=repository_id,
        caller_workflow_ref=workflow_ref,
        caller_workflow_sha=workflow_sha,
        event_name=event_name,
        run_id=run_id,
        run_attempt=run_attempt,
        check_run_id=check_run_id,
    ), []


def require_mapping(value: Any, code: str, message: str) -> tuple[dict[str, Any] | None, Diagnostic | None]:
    if not isinstance(value, dict):
        return None, Diagnostic(code, message, CALLER_WORKFLOW_PATH)
    return value, None


def workflow_diagnostics(
    text: str,
    issuer_sha: str,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if re.search(r"(?m)(^|[\s\[{,])([&*])[A-Za-z0-9_-]+", text):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_WORKFLOW_YAML_UNSUPPORTED",
            "YAML anchors and aliases are not allowed in trust topology.",
            CALLER_WORKFLOW_PATH,
        ))
        return diagnostics
    try:
        workflow = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        problem = getattr(exc, "problem", None) or exc.__class__.__name__
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_WORKFLOW_YAML_INVALID",
            f"Workflow YAML is malformed: {problem}.",
            CALLER_WORKFLOW_PATH,
        ))
        return diagnostics

    workflow, diagnostic = require_mapping(
        workflow,
        "COV_EXTERNAL_WORKFLOW_YAML_INVALID",
        "Workflow top-level YAML value must be a mapping.",
    )
    if diagnostic:
        return [diagnostic]
    assert workflow is not None
    jobs, diagnostic = require_mapping(
        workflow.get("jobs"),
        "COV_EXTERNAL_WORKFLOW_JOBS_INVALID",
        "Workflow jobs must be a mapping.",
    )
    if diagnostic:
        diagnostics.append(diagnostic)
        return diagnostics
    assert jobs is not None

    expected_uses = f"{ISSUER_REPOSITORY}/{ISSUER_WORKFLOW_PATH}@{issuer_sha}"
    external, diagnostic = require_mapping(
        jobs.get("external-coverage-trust"),
        "COV_EXTERNAL_REQUIRED_JOB_MISSING",
        "Active external job is missing or not a mapping.",
    )
    if diagnostic:
        diagnostics.append(diagnostic)
    else:
        assert external is not None
        if "if" in external:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_REQUIRED_JOB_DEAD",
                "External job may not be disabled.",
                CALLER_WORKFLOW_PATH,
            ))
        if external.get("uses") != expected_uses:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_TRUST_ROOT_PIN_TOPOLOGY_INVALID",
                "Issuer pin must be the exact reusable workflow on the active job.",
                CALLER_WORKFLOW_PATH,
            ))
        external_with = external.get("with") or {}
        if not isinstance(external_with, dict):
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_CALLER_IDENTITY_INPUT_FORBIDDEN",
                "External job inputs must be a mapping when present.",
                CALLER_WORKFLOW_PATH,
            ))
        elif any(key in external_with for key in FORBIDDEN_INPUTS):
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_CALLER_IDENTITY_INPUT_FORBIDDEN",
                "Caller identity inputs are forbidden.",
                CALLER_WORKFLOW_PATH,
            ))

    validation, diagnostic = require_mapping(
        jobs.get("validate-mvk"),
        "COV_EXTERNAL_VALIDATION_JOB_MISSING",
        "Validation job is missing or not a mapping.",
    )
    if diagnostic:
        diagnostics.append(diagnostic)
    else:
        assert validation is not None
        needs = validation.get("needs")
        needs_ok = needs == "external-coverage-trust" or (
            isinstance(needs, list) and needs == ["external-coverage-trust"]
        )
        if not needs_ok:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_VALIDATION_NEEDS_MISSING",
                "Validation dependency is missing.",
                CALLER_WORKFLOW_PATH,
            ))
        steps = validation.get("steps")
        if not isinstance(steps, list) or not steps:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_VALIDATION_STEPS_INVALID",
                "Validation steps must be a non-empty list.",
                CALLER_WORKFLOW_PATH,
            ))
        else:
            checkout_steps = []
            validation_steps = []
            for step in steps:
                if not isinstance(step, dict):
                    diagnostics.append(Diagnostic(
                        "COV_EXTERNAL_VALIDATION_STEPS_INVALID",
                        "Each validation step must be a mapping.",
                        CALLER_WORKFLOW_PATH,
                    ))
                    continue
                uses = str(step.get("uses") or "")
                if uses.startswith("actions/checkout@"):
                    checkout_steps.append(step)
                if step.get("run") == "npm run validate:coverage":
                    validation_steps.append(step)
            expected_ref = "${{ needs.external-coverage-trust.outputs.verified_head_sha }}"
            if len(checkout_steps) != 1:
                diagnostics.append(Diagnostic(
                    "COV_EXTERNAL_VALIDATION_CHECKOUT_MISMATCH",
                    "Validation must have exactly one checkout step.",
                    CALLER_WORKFLOW_PATH,
                ))
            else:
                checkout_with = checkout_steps[0].get("with")
                if (
                    not isinstance(checkout_with, dict)
                    or checkout_with.get("ref") != expected_ref
                ):
                    diagnostics.append(Diagnostic(
                        "COV_EXTERNAL_VALIDATION_CHECKOUT_MISMATCH",
                        "Validation checkout is not externally bound.",
                        CALLER_WORKFLOW_PATH,
                    ))
            expected_env = {
                "COVERAGE_REPOSITORY": "${{ needs.external-coverage-trust.outputs.verified_repository }}",
                "COVERAGE_PR_NUMBER": "${{ needs.external-coverage-trust.outputs.verified_pr_number }}",
                "COVERAGE_BASE_SHA": "${{ needs.external-coverage-trust.outputs.verified_base_sha }}",
                "COVERAGE_HEAD_SHA": "${{ needs.external-coverage-trust.outputs.verified_head_sha }}",
            }
            if len(validation_steps) != 1:
                diagnostics.append(Diagnostic(
                    "COV_EXTERNAL_VALIDATION_IDENTITY_BINDING_MISSING",
                    "Exactly one validation command step is required.",
                    CALLER_WORKFLOW_PATH,
                ))
            else:
                env = validation_steps[0].get("env")
                if not isinstance(env, dict) or any(
                    env.get(key) != expected for key, expected in expected_env.items()
                ):
                    diagnostics.append(Diagnostic(
                        "COV_EXTERNAL_VALIDATION_IDENTITY_BINDING_MISSING",
                        "Validation identity binding is missing from the validation step.",
                        CALLER_WORKFLOW_PATH,
                    ))

    def scan_forbidden(value: Any) -> bool:
        if isinstance(value, dict):
            return any(scan_forbidden(k) or scan_forbidden(v) for k, v in value.items())
        if isinstance(value, list):
            return any(scan_forbidden(item) for item in value)
        if isinstance(value, str):
            return any(token in value for token in FORBIDDEN_TRUST)
        return False

    if scan_forbidden(workflow):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_ROOT_TARGET_MINT_FORBIDDEN",
            "Target may not mint trust evidence.",
            CALLER_WORKFLOW_PATH,
        ))
    return diagnostics

def evaluate_target(
    *,
    target_root: Path,
    identity: VerifiedIdentity,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    try:
        checked_out_head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=target_root,
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        checked_out_head = ""
    if checked_out_head != identity.target_head_sha:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_HEAD_MISMATCH",
            "Checkout does not match API head.",
        ))
    try:
        subprocess.check_call(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                identity.target_base_sha,
                identity.target_head_sha,
            ],
            cwd=target_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_BASE_NOT_ANCESTOR",
            "API base is not an ancestor.",
        ))
    if identity.event_name == "pull_request":
        try:
            workflow = (
                target_root / CALLER_WORKFLOW_PATH
            ).read_text(encoding="utf-8")
        except OSError:
            diagnostics.append(Diagnostic(
                "COV_EXTERNAL_TRUST_CALLER_WORKFLOW_MISSING",
                "Caller workflow missing.",
                CALLER_WORKFLOW_PATH,
            ))
        else:
            diagnostics.extend(workflow_diagnostics(
                workflow,
                identity.issuer_workflow_sha,
            ))
    diagnostics.extend(planning_coverage_diagnostics(target_root))
    return diagnostics


def issue_bootstrap_attestation(
    identity: VerifiedIdentity,
    event: dict[str, Any],
    api_pr: dict[str, Any],
    claims: dict[str, Any],
    validated_at: str,
) -> dict[str, Any]:
    if not RFC3339.fullmatch(validated_at):
        raise ValueError("validated_at is invalid")
    datetime.strptime(validated_at, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    value: dict[str, Any] = {
        "schema_version": 3,
        "attestation_kind": "coverage_trust_bootstrap_no_proof",
        "issuer": {
            "identity": ISSUER_REPOSITORY,
            "repository_id": ISSUER_REPOSITORY_ID,
            "workflow_path": identity.issuer_workflow_path,
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
            "event_name": identity.event_name,
            "run_id": identity.run_id,
            "run_attempt": identity.run_attempt,
            "check_run_id": identity.check_run_id,
        },
        "authority_evidence": {
            "event_sha256": hashlib.sha256(canonical(event)).hexdigest(),
            "api_pr_sha256": hashlib.sha256(canonical(api_pr)).hexdigest(),
            "oidc_claims_sha256": hashlib.sha256(
                canonical(claims)
            ).hexdigest(),
        },
        "trusted_validation_at": validated_at,
        "trusted_ingestion_at": None,
        "proof_credit_authorized": False,
    }
    value["verifier_created_capability"] = hashlib.sha256(
        b"ev4.coverage.external-trust.prf013\0" + canonical(value)
    ).hexdigest()
    return value


def verify_attestation(
    value: dict[str, Any],
    identity: VerifiedIdentity,
) -> list[Diagnostic]:
    unsigned = dict(value)
    capability = unsigned.pop("verifier_created_capability", None)
    expected = hashlib.sha256(
        b"ev4.coverage.external-trust.prf013\0" + canonical(unsigned)
    ).hexdigest()
    diagnostics: list[Diagnostic] = []
    if capability != expected:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_ATTESTATION_CAPABILITY_INVALID",
            "Capability mismatch.",
        ))
    target = value.get("target") or {}
    expected_target = {
        "repository": identity.target_repository,
        "repository_id": identity.target_repository_id,
        "pull_request_number": identity.pull_request_number,
        "base_sha": identity.target_base_sha,
        "evidence_head_sha": identity.target_head_sha,
    }
    if target != expected_target:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_ATTESTATION_TARGET_MISMATCH",
            "Target mismatch.",
        ))
    issuer = value.get("issuer") or {}
    if (
        issuer.get("workflow_sha") != identity.issuer_workflow_sha
        or issuer.get("workflow_path") != identity.issuer_workflow_path
    ):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_ROOT_IDENTITY_MISMATCH",
            "Issuer mismatch.",
        ))
    if value.get("proof_credit_authorized") is not False:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_ATTESTATION_BOOTSTRAP_SCOPE_INVALID",
            "Proof credit must be false.",
        ))
    return diagnostics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--event-path", type=Path, required=True)
    parser.add_argument("--api-pr-file", type=Path, required=True)
    parser.add_argument("--oidc-token-file", type=Path, required=True)
    parser.add_argument("--independent-policy-pr-number", type=int)
    parser.add_argument("--validated-at", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--github-output", type=Path, required=True)
    args = parser.parse_args()

    try:
        event = json.loads(args.event_path.read_text(encoding="utf-8"))
        api_pr = json.loads(args.api_pr_file.read_text(encoding="utf-8"))
        claims = decode_oidc_claims(
            args.oidc_token_file.read_text(encoding="utf-8").strip()
        )
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
            "GITHUB_RUN_ID": os.environ.get("GITHUB_RUN_ID", ""),
            "GITHUB_RUN_ATTEMPT": os.environ.get(
                "GITHUB_RUN_ATTEMPT", ""
            ),
        },
        independent_policy_pr_number=args.independent_policy_pr_number,
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
            print(
                f"  {item.code}{location}: {item.message}",
                file=sys.stderr,
            )
        return 1
    assert identity is not None

    value = issue_bootstrap_attestation(
        identity,
        event,
        api_pr,
        claims,
        args.validated_at,
    )
    verification = verify_attestation(value, identity)
    if verification:
        for item in verification:
            print(f"{item.code}: {item.message}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    outputs = {
        "verified_repository": identity.target_repository,
        "verified_repository_id": str(identity.target_repository_id),
        "verified_pr_number": str(identity.pull_request_number),
        "verified_base_sha": identity.target_base_sha,
        "verified_head_sha": identity.target_head_sha,
        "verified_issuer_sha": identity.issuer_workflow_sha,
        "verification_mode": identity.verification_mode,
        "attestation_digest": digest,
        "proof_credit_authorized": "false",
    }
    with args.github_output.open("a", encoding="utf-8") as handle:
        for key, output_value in outputs.items():
            handle.write(f"{key}={output_value}\n")
    print(json.dumps({**outputs, "result": "PASS"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
