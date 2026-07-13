#!/usr/bin/env python3
"""Externally pinned Coverage trust-root verifier."""
from __future__ import annotations

import argparse
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
ISSUER_WORKFLOW_PATH = ".github/workflows/coverage-trust-gate.yml"
CALLER_WORKFLOW_PATH = ".github/workflows/validate-mvk.yml"
SENSITIVE_GATE_PATHS = (
    CALLER_WORKFLOW_PATH,
    "kernel/validator/validate-coverage-guarantee.mjs",
    "kernel/validator/validate-coverage-guarantee-legacy.mjs",
)
SELF_ISSUED_ENV_NAMES = (
    "COVERAGE_VALIDATED_AT",
    "COVERAGE_VALIDATION_SOURCE",
    "COVERAGE_TRUSTED_INGESTION_ATTESTATIONS",
)
PROOF_ROLES = {"runtime_proof", "consumer_proof", "coverage_credit"}
SHA40 = re.compile(r"^[0-9a-f]{40}$")
RFC3339_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


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


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


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


def _caller_pin(workflow: str) -> str | None:
    pattern = re.compile(
        r"uses:\s*"
        + re.escape(f"{ISSUER_REPOSITORY}/{ISSUER_WORKFLOW_PATH}@")
        + r"([0-9a-f]{40})"
    )
    match = pattern.search(workflow)
    return match.group(1) if match else None


def evaluate_target(
    *,
    target_root: Path,
    target_repository: str,
    target_head_sha: str,
    target_base_sha: str,
    issuer_workflow_sha: str,
    proof_credit_mode: str,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if target_repository != "rezahh107/EV4-Decision-Kernel":
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_TARGET_REPOSITORY_MISMATCH",
            "The external gate is bound to rezahh107/EV4-Decision-Kernel.",
        ))
    if not SHA40.fullmatch(target_head_sha):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_HEAD_INVALID",
            "The evidence head must be an exact 40-hex commit SHA.",
        ))
    if not SHA40.fullmatch(target_base_sha):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_BASE_INVALID",
            "The base must be an exact 40-hex commit SHA.",
        ))
    if not SHA40.fullmatch(issuer_workflow_sha):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_ROOT_INVALID",
            "The issuer workflow must be pinned by immutable 40-hex commit SHA.",
        ))
    try:
        checked_out_head = _run_git(target_root, "rev-parse", "HEAD")
    except subprocess.CalledProcessError:
        checked_out_head = ""
    if checked_out_head != target_head_sha:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_HEAD_MISMATCH",
            "The externally verified checkout does not match the declared evidence head.",
        ))
    try:
        _run_git(target_root, "merge-base", "--is-ancestor", target_base_sha, target_head_sha)
    except subprocess.CalledProcessError:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_BASE_NOT_ANCESTOR",
            "The declared base is not an ancestor of the evidence head.",
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
    if _caller_pin(workflow) != issuer_workflow_sha:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_ROOT_UNPINNED",
            "The caller must invoke the external trust workflow at the exact approved immutable SHA.",
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
    proof_requested = _proof_credit_requested(target_root)
    if proof_credit_mode != "bootstrap_deny":
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_MODE_INVALID",
            "PRF-011 bootstrap permits only bootstrap_deny mode.",
        ))
    if proof_requested:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_BOOTSTRAP_PROOF_CREDIT_FORBIDDEN",
            "This bootstrap gate authorizes no runtime, consumer, or coverage-credit proof.",
            "planning/coverage",
        ))
        for relative_path in SENSITIVE_GATE_PATHS:
            try:
                current = _read_text(target_root, relative_path)
            except OSError:
                current = None
            base = _base_text(target_root, target_base_sha, relative_path)
            if current is None or base is None or current != base:
                diagnostics.append(Diagnostic(
                    "COV_EXTERNAL_TRUST_GATE_IDENTITY_MISMATCH",
                    "Proof credit requires gate-sensitive code to match the approved base identity.",
                    relative_path,
                ))
    return diagnostics


def issue_bootstrap_attestation(
    *,
    issuer_workflow_sha: str,
    target_repository: str,
    target_base_sha: str,
    target_head_sha: str,
    pull_request_number: int,
    run_id: str,
    run_attempt: int,
    validated_at: str,
) -> dict[str, Any]:
    if not SHA40.fullmatch(issuer_workflow_sha):
        raise ValueError("issuer_workflow_sha must be 40 lowercase hex")
    if not SHA40.fullmatch(target_base_sha) or not SHA40.fullmatch(target_head_sha):
        raise ValueError("base/head must be 40 lowercase hex")
    if not RFC3339_UTC.fullmatch(validated_at):
        raise ValueError("validated_at must be second-precision UTC RFC3339")
    datetime.strptime(validated_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "attestation_kind": "coverage_trust_bootstrap_no_proof",
        "issuer": {
            "identity": ISSUER_REPOSITORY,
            "workflow_path": ISSUER_WORKFLOW_PATH,
            "workflow_sha": issuer_workflow_sha,
        },
        "target": {
            "repository": target_repository,
            "base_sha": target_base_sha,
            "evidence_head_sha": target_head_sha,
            "pull_request_number": pull_request_number,
        },
        "github": {"run_id": str(run_id), "run_attempt": run_attempt},
        "trusted_validation_at": validated_at,
        "trusted_ingestion_at": None,
        "proof_credit_authorized": False,
    }
    capability_input = b"ev4.coverage.external-trust.v1\0" + _canonical_bytes(payload)
    payload["verifier_created_capability"] = hashlib.sha256(capability_input).hexdigest()
    return payload


def verify_bootstrap_attestation(
    attestation: dict[str, Any],
    *,
    issuer_workflow_sha: str,
    target_repository: str,
    target_head_sha: str,
    run_id: str,
    run_attempt: int,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    expected_capability = attestation.get("verifier_created_capability")
    unsigned = dict(attestation)
    unsigned.pop("verifier_created_capability", None)
    actual_capability = hashlib.sha256(
        b"ev4.coverage.external-trust.v1\0" + _canonical_bytes(unsigned)
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
        or issuer.get("workflow_path") != ISSUER_WORKFLOW_PATH
        or issuer.get("workflow_sha") != issuer_workflow_sha
    ):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_TRUST_ROOT_IDENTITY_MISMATCH",
            "Attestation issuer identity or immutable workflow SHA does not match.",
        ))
    if (
        target.get("repository") != target_repository
        or target.get("evidence_head_sha") != target_head_sha
    ):
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_ATTESTATION_TARGET_MISMATCH",
            "Attestation target repository or evidence head does not match.",
        ))
    if str(github.get("run_id")) != str(run_id) or github.get("run_attempt") != run_attempt:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_ATTESTATION_RUN_MISMATCH",
            "Attestation GitHub run identity does not match.",
        ))
    if attestation.get("proof_credit_authorized") is not False:
        diagnostics.append(Diagnostic(
            "COV_EXTERNAL_ATTESTATION_BOOTSTRAP_SCOPE_INVALID",
            "Bootstrap attestation must explicitly deny proof credit.",
        ))
    return diagnostics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--target-repository", required=True)
    parser.add_argument("--target-head-sha", required=True)
    parser.add_argument("--target-base-sha", required=True)
    parser.add_argument("--pull-request-number", type=int, required=True)
    parser.add_argument("--issuer-workflow-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    parser.add_argument("--validated-at", required=True)
    parser.add_argument("--proof-credit-mode", default="bootstrap_deny")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    diagnostics = evaluate_target(
        target_root=args.target_root,
        target_repository=args.target_repository,
        target_head_sha=args.target_head_sha,
        target_base_sha=args.target_base_sha,
        issuer_workflow_sha=args.issuer_workflow_sha,
        proof_credit_mode=args.proof_credit_mode,
    )
    if diagnostics:
        print("External Coverage Trust Gate diagnostics:", file=sys.stderr)
        for item in diagnostics:
            location = f" [{item.path}]" if item.path else ""
            print(f"  {item.code}{location}: {item.message}", file=sys.stderr)
        return 1
    attestation = issue_bootstrap_attestation(
        issuer_workflow_sha=args.issuer_workflow_sha,
        target_repository=args.target_repository,
        target_base_sha=args.target_base_sha,
        target_head_sha=args.target_head_sha,
        pull_request_number=args.pull_request_number,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        validated_at=args.validated_at,
    )
    verify_diagnostics = verify_bootstrap_attestation(
        attestation,
        issuer_workflow_sha=args.issuer_workflow_sha,
        target_repository=args.target_repository,
        target_head_sha=args.target_head_sha,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
    )
    if verify_diagnostics:
        for item in verify_diagnostics:
            print(f"{item.code}: {item.message}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(attestation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": "PASS",
        "issuer": ISSUER_REPOSITORY,
        "issuer_workflow_sha": args.issuer_workflow_sha,
        "target_repository": args.target_repository,
        "evidence_head_sha": args.target_head_sha,
        "proof_credit_authorized": False,
        "attestation_path": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
