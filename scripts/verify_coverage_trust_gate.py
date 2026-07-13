#!/usr/bin/env python3
"""PRF-013 authoritative external Coverage trust verifier."""
from __future__ import annotations

import argparse, base64, hashlib, json, os, re, subprocess, sys
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
    "target_repository", "target_repository_id", "target_head_sha",
    "target_base_sha", "pull_request_number", "issuer_workflow_sha",
)
FORBIDDEN_TRUST = (
    "COVERAGE_VALIDATED_AT", "COVERAGE_VALIDATION_SOURCE",
    "COVERAGE_TRUSTED_INGESTION_ATTESTATIONS", "/bin/date",
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
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def int_or_none(value: Any) -> int | None:
    try: return int(value)
    except (TypeError, ValueError): return None

def decode_oidc_claims(token: str) -> dict[str, Any]:
    parts = token.strip().split(".")
    if len(parts) != 3: raise ValueError("OIDC token must be a three-part JWT")
    raw = parts[1] + "=" * (-len(parts[1]) % 4)
    value = json.loads(base64.urlsafe_b64decode(raw.encode()))
    if not isinstance(value, dict): raise ValueError("OIDC payload must be an object")
    return value

def audience_ok(value: Any) -> bool:
    return value == OIDC_AUDIENCE or isinstance(value, list) and OIDC_AUDIENCE in value

def event_pr(event: dict[str, Any]) -> tuple[int | None, str | None, str | None]:
    pr = event.get("pull_request") or {}
    return (
        int_or_none(pr.get("number") or event.get("number")),
        (pr.get("base") or {}).get("sha"),
        (pr.get("head") or {}).get("sha"),
    )

def proof_requested(root: Path) -> bool:
    folder = root / "planning" / "coverage"
    if not folder.exists(): return False
    stack: list[Any] = []
    for path in folder.rglob("*.json"):
        try: stack.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError): continue
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            if value.get("artifact_role") in PROOF_ROLES or value.get("coverage_granted") is True:
                return True
            stack.extend(value.values())
        elif isinstance(value, list): stack.extend(value)
    return False

def derive_authoritative_identity(
    *, event: dict[str, Any], api_pr: dict[str, Any],
    oidc_claims: dict[str, Any], environment: dict[str, str],
    independent_policy_pr_number: int | None = None,
) -> tuple[VerifiedIdentity | None, list[Diagnostic]]:
    d: list[Diagnostic] = []
    repo = str(oidc_claims.get("repository") or "")
    repo_id = int_or_none(oidc_claims.get("repository_id"))
    event_name = str(oidc_claims.get("event_name") or "")
    workflow_ref = str(oidc_claims.get("workflow_ref") or "")
    workflow_sha = str(oidc_claims.get("workflow_sha") or "")
    job_ref = str(oidc_claims.get("job_workflow_ref") or "")
    job_sha = str(oidc_claims.get("job_workflow_sha") or "")
    run_id = str(oidc_claims.get("run_id") or "")
    run_attempt = int_or_none(oidc_claims.get("run_attempt"))
    check_run_id = str(oidc_claims.get("check_run_id") or "")
    if oidc_claims.get("iss") != OIDC_ISSUER or not audience_ok(oidc_claims.get("aud")):
        d.append(Diagnostic("COV_EXTERNAL_OIDC_AUTHORITY_INVALID", "OIDC issuer or audience is invalid."))
    if run_id != str(environment.get("GITHUB_RUN_ID") or "") or run_attempt != int_or_none(environment.get("GITHUB_RUN_ATTEMPT")):
        d.append(Diagnostic("COV_EXTERNAL_OIDC_RUN_IDENTITY_MISMATCH", "OIDC run identity mismatch."))

    number: int | None; event_base: str | None; event_head: str | None
    issuer_sha = ""; issuer_path = ""; mode = "invalid"
    if repo_id == TARGET_REPOSITORY_ID:
        if independent_policy_pr_number not in (None, 0):
            d.append(Diagnostic("COV_EXTERNAL_TARGET_POLICY_INPUT_FORBIDDEN", "Target callers may not select PR identity."))
        paths = {
            "pull_request": CALLER_WORKFLOW_PATH,
            "pull_request_target": REQUIRED_GUARD_WORKFLOW_PATH,
        }
        expected = paths.get(event_name)
        if repo != TARGET_REPOSITORY or expected is None or not workflow_ref.startswith(f"{TARGET_REPOSITORY}/{expected}@"):
            d.append(Diagnostic("COV_EXTERNAL_EVENT_CALLER_IDENTITY_MISMATCH", "Target caller identity mismatch."))
        mode = "target_pull_request_event_api" if event_name == "pull_request" else "target_pull_request_target_event_api"
        expected_ref = f"{ISSUER_REPOSITORY}/{ISSUER_WORKFLOW_PATH}@{job_sha}"
        if not SHA40.fullmatch(job_sha) or job_ref != expected_ref:
            d.append(Diagnostic("COV_EXTERNAL_OIDC_WORKFLOW_IDENTITY_MISMATCH", "Reusable issuer identity mismatch."))
        issuer_sha, issuer_path = job_sha, ISSUER_WORKFLOW_PATH
        er = event.get("repository") or {}
        if int_or_none(er.get("id")) != TARGET_REPOSITORY_ID or er.get("full_name") != TARGET_REPOSITORY:
            d.append(Diagnostic("COV_EXTERNAL_EVENT_REPOSITORY_ID_MISMATCH", "Event repository mismatch."))
        number, event_base, event_head = event_pr(event)
        if number is None or number < 1:
            d.append(Diagnostic("COV_EXTERNAL_EVENT_PR_INVALID", "Target event has no valid PR number."))
    elif repo_id == ISSUER_REPOSITORY_ID:
        if repo != ISSUER_REPOSITORY or not workflow_ref.startswith(f"{ISSUER_REPOSITORY}/{INDEPENDENT_WORKFLOW_PATH}@") or event_name not in {"push", "pull_request", "workflow_dispatch"}:
            d.append(Diagnostic("COV_EXTERNAL_INDEPENDENT_CALLER_IDENTITY_MISMATCH", "Independent caller identity mismatch."))
        number = independent_policy_pr_number
        if number is None or number < 1:
            d.append(Diagnostic("COV_EXTERNAL_INDEPENDENT_POLICY_PR_INVALID", "Independent policy PR is invalid."))
        event_base = (api_pr.get("base") or {}).get("sha")
        event_head = (api_pr.get("head") or {}).get("sha")
        issuer_sha, issuer_path = workflow_sha, INDEPENDENT_WORKFLOW_PATH
        mode = "independent_explicit_policy_api"
        if not SHA40.fullmatch(issuer_sha):
            d.append(Diagnostic("COV_EXTERNAL_INDEPENDENT_WORKFLOW_SHA_INVALID", "Independent workflow SHA is invalid."))
    else:
        number = None; event_base = None; event_head = None
        d.append(Diagnostic("COV_EXTERNAL_OIDC_CALLER_REPOSITORY_INVALID", "OIDC caller repository is not approved."))

    api_number = int_or_none(api_pr.get("number"))
    api_base = (api_pr.get("base") or {}).get("sha")
    api_head = (api_pr.get("head") or {}).get("sha")
    api_repo = (api_pr.get("base") or {}).get("repo") or {}
    if int_or_none(api_repo.get("id")) != TARGET_REPOSITORY_ID or api_repo.get("full_name") != TARGET_REPOSITORY:
        d.append(Diagnostic("COV_EXTERNAL_API_REPOSITORY_ID_MISMATCH", "API repository mismatch."))
    if number != api_number: d.append(Diagnostic("COV_EXTERNAL_EVENT_PR_MISMATCH", "Event/policy PR does not match API PR."))
    if event_base != api_base: d.append(Diagnostic("COV_EXTERNAL_EVENT_BASE_MISMATCH", "Event base does not match API base."))
    if event_head != api_head: d.append(Diagnostic("COV_EXTERNAL_EVENT_HEAD_MISMATCH", "Event head does not match API head."))
    if not SHA40.fullmatch(str(api_base or "")) or not SHA40.fullmatch(str(api_head or "")):
        d.append(Diagnostic("COV_EXTERNAL_API_PR_IDENTITY_INVALID", "API base/head is invalid."))
    if d: return None, d
    assert repo_id is not None and run_attempt is not None and api_number is not None
    return VerifiedIdentity(mode, TARGET_REPOSITORY, TARGET_REPOSITORY_ID, api_number,
        str(api_base), str(api_head), issuer_sha, issuer_path, repo, repo_id,
        workflow_ref, workflow_sha, event_name, run_id, run_attempt, check_run_id), []

def workflow_diagnostics(text: str, issuer_sha: str) -> list[Diagnostic]:
    d: list[Diagnostic] = []
    expected = f"uses: {ISSUER_REPOSITORY}/{ISSUER_WORKFLOW_PATH}@{issuer_sha}"
    if text.count(expected) != 1:
        d.append(Diagnostic("COV_EXTERNAL_TRUST_ROOT_PIN_TOPOLOGY_INVALID", "Issuer pin must appear once in the active job.", CALLER_WORKFLOW_PATH))
    if not re.search(r"(?ms)^  external-coverage-trust:\n(?:(?!^  \S).)*?" + re.escape(expected), text):
        d.append(Diagnostic("COV_EXTERNAL_REQUIRED_JOB_MISSING", "Active external job is missing.", CALLER_WORKFLOW_PATH))
    if re.search(r"(?ms)^  external-coverage-trust:\n(?:(?!^  \S).)*?^    if:", text):
        d.append(Diagnostic("COV_EXTERNAL_REQUIRED_JOB_DEAD", "External job may not be disabled.", CALLER_WORKFLOW_PATH))
    external = re.search(r"(?ms)^  external-coverage-trust:\n(?P<body>(?:(?!^  \S).)*)", text)
    if external and any(re.search(rf"(?m)^\s+{re.escape(key)}\s*:", external.group("body")) for key in FORBIDDEN_INPUTS):
        d.append(Diagnostic("COV_EXTERNAL_CALLER_IDENTITY_INPUT_FORBIDDEN", "Caller identity inputs are forbidden.", CALLER_WORKFLOW_PATH))
    validation = re.search(r"(?ms)^  validate-mvk:\n(?P<body>(?:(?!^  \S).)*)", text)
    if not validation:
        d.append(Diagnostic("COV_EXTERNAL_VALIDATION_JOB_MISSING", "Validation job is missing.", CALLER_WORKFLOW_PATH))
    else:
        body = validation.group("body")
        if "needs: external-coverage-trust" not in body:
            d.append(Diagnostic("COV_EXTERNAL_VALIDATION_NEEDS_MISSING", "Validation dependency is missing.", CALLER_WORKFLOW_PATH))
        refs = re.findall(r"(?m)^\s+ref:\s*(.*?)\s*$", body)
        if refs != ["${{ needs.external-coverage-trust.outputs.verified_head_sha }}"]:
            d.append(Diagnostic("COV_EXTERNAL_VALIDATION_CHECKOUT_MISMATCH", "Validation checkout is not externally bound.", CALLER_WORKFLOW_PATH))
        for binding in (
            "COVERAGE_REPOSITORY: ${{ needs.external-coverage-trust.outputs.verified_repository }}",
            "COVERAGE_PR_NUMBER: ${{ needs.external-coverage-trust.outputs.verified_pr_number }}",
            "COVERAGE_BASE_SHA: ${{ needs.external-coverage-trust.outputs.verified_base_sha }}",
            "COVERAGE_HEAD_SHA: ${{ needs.external-coverage-trust.outputs.verified_head_sha }}",
        ):
            if binding not in body:
                d.append(Diagnostic("COV_EXTERNAL_VALIDATION_IDENTITY_BINDING_MISSING", "Validation identity binding is missing.", CALLER_WORKFLOW_PATH)); break
    if any(token in text for token in FORBIDDEN_TRUST):
        d.append(Diagnostic("COV_EXTERNAL_TRUST_ROOT_TARGET_MINT_FORBIDDEN", "Target may not mint trust evidence.", CALLER_WORKFLOW_PATH))
    return d

def evaluate_target(*, target_root: Path, identity: VerifiedIdentity) -> list[Diagnostic]:
    d: list[Diagnostic] = []
    try: head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=target_root, text=True).strip()
    except subprocess.CalledProcessError: head = ""
    if head != identity.target_head_sha:
        d.append(Diagnostic("COV_EXTERNAL_TRUST_HEAD_MISMATCH", "Checkout does not match API head."))
    try: subprocess.check_call(["git", "merge-base", "--is-ancestor", identity.target_base_sha, identity.target_head_sha], cwd=target_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        d.append(Diagnostic("COV_EXTERNAL_TRUST_BASE_NOT_ANCESTOR", "API base is not an ancestor."))
    if identity.event_name == "pull_request":
        try: d.extend(workflow_diagnostics((target_root / CALLER_WORKFLOW_PATH).read_text(), identity.issuer_workflow_sha))
        except OSError: d.append(Diagnostic("COV_EXTERNAL_TRUST_CALLER_WORKFLOW_MISSING", "Caller workflow missing.", CALLER_WORKFLOW_PATH))
    if proof_requested(target_root):
        d.append(Diagnostic("COV_EXTERNAL_TRUST_BOOTSTRAP_PROOF_CREDIT_FORBIDDEN", "Proof credit remains disabled.", "planning/coverage"))
    return d

def issue_bootstrap_attestation(identity: VerifiedIdentity, event: dict[str, Any], api_pr: dict[str, Any], claims: dict[str, Any], validated_at: str) -> dict[str, Any]:
    if not RFC3339.fullmatch(validated_at): raise ValueError("validated_at is invalid")
    datetime.strptime(validated_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    value: dict[str, Any] = {
        "schema_version": 3,
        "attestation_kind": "coverage_trust_bootstrap_no_proof",
        "issuer": {"identity": ISSUER_REPOSITORY, "repository_id": ISSUER_REPOSITORY_ID, "workflow_path": identity.issuer_workflow_path, "workflow_sha": identity.issuer_workflow_sha},
        "target": {"repository": identity.target_repository, "repository_id": identity.target_repository_id, "pull_request_number": identity.pull_request_number, "base_sha": identity.target_base_sha, "evidence_head_sha": identity.target_head_sha},
        "github": {"verification_mode": identity.verification_mode, "caller_repository": identity.caller_repository, "caller_repository_id": identity.caller_repository_id, "caller_workflow_ref": identity.caller_workflow_ref, "caller_workflow_sha": identity.caller_workflow_sha, "event_name": identity.event_name, "run_id": identity.run_id, "run_attempt": identity.run_attempt, "check_run_id": identity.check_run_id},
        "authority_evidence": {"event_sha256": hashlib.sha256(canonical(event)).hexdigest(), "api_pr_sha256": hashlib.sha256(canonical(api_pr)).hexdigest(), "oidc_claims_sha256": hashlib.sha256(canonical(claims)).hexdigest()},
        "trusted_validation_at": validated_at, "trusted_ingestion_at": None, "proof_credit_authorized": False,
    }
    value["verifier_created_capability"] = hashlib.sha256(b"ev4.coverage.external-trust.prf013\0" + canonical(value)).hexdigest()
    return value

def verify_attestation(value: dict[str, Any], identity: VerifiedIdentity) -> list[Diagnostic]:
    unsigned = dict(value); capability = unsigned.pop("verifier_created_capability", None)
    expected = hashlib.sha256(b"ev4.coverage.external-trust.prf013\0" + canonical(unsigned)).hexdigest()
    d: list[Diagnostic] = []
    if capability != expected: d.append(Diagnostic("COV_EXTERNAL_ATTESTATION_CAPABILITY_INVALID", "Capability mismatch."))
    target = value.get("target") or {}; issuer = value.get("issuer") or {}
    if target != {"repository": identity.target_repository, "repository_id": identity.target_repository_id, "pull_request_number": identity.pull_request_number, "base_sha": identity.target_base_sha, "evidence_head_sha": identity.target_head_sha}:
        d.append(Diagnostic("COV_EXTERNAL_ATTESTATION_TARGET_MISMATCH", "Target mismatch."))
    if issuer.get("workflow_sha") != identity.issuer_workflow_sha or issuer.get("workflow_path") != identity.issuer_workflow_path:
        d.append(Diagnostic("COV_EXTERNAL_TRUST_ROOT_IDENTITY_MISMATCH", "Issuer mismatch."))
    if value.get("proof_credit_authorized") is not False:
        d.append(Diagnostic("COV_EXTERNAL_ATTESTATION_BOOTSTRAP_SCOPE_INVALID", "Proof credit must be false."))
    return d

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--target-root", type=Path, required=True); p.add_argument("--event-path", type=Path, required=True)
    p.add_argument("--api-pr-file", type=Path, required=True); p.add_argument("--oidc-token-file", type=Path, required=True)
    p.add_argument("--independent-policy-pr-number", type=int); p.add_argument("--validated-at", required=True)
    p.add_argument("--output", type=Path, required=True); p.add_argument("--github-output", type=Path, required=True)
    a = p.parse_args()
    try:
        event = json.loads(a.event_path.read_text()); api_pr = json.loads(a.api_pr_file.read_text())
        claims = decode_oidc_claims(a.oidc_token_file.read_text())
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"COV_EXTERNAL_AUTHORITY_EVIDENCE_INVALID: {exc}", file=sys.stderr); return 1
    identity, d = derive_authoritative_identity(event=event, api_pr=api_pr, oidc_claims=claims,
        environment={"GITHUB_RUN_ID": os.environ.get("GITHUB_RUN_ID", ""), "GITHUB_RUN_ATTEMPT": os.environ.get("GITHUB_RUN_ATTEMPT", "")},
        independent_policy_pr_number=a.independent_policy_pr_number)
    if identity: d.extend(evaluate_target(target_root=a.target_root, identity=identity))
    if d:
        for item in d: print(f"{item.code}: {item.message}", file=sys.stderr)
        return 1
    assert identity
    value = issue_bootstrap_attestation(identity, event, api_pr, claims, a.validated_at)
    if verify_attestation(value, identity): return 1
    a.output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    digest = hashlib.sha256(a.output.read_bytes()).hexdigest()
    outputs = {"verified_repository": identity.target_repository, "verified_repository_id": str(identity.target_repository_id), "verified_pr_number": str(identity.pull_request_number), "verified_base_sha": identity.target_base_sha, "verified_head_sha": identity.target_head_sha, "verified_issuer_sha": identity.issuer_workflow_sha, "verification_mode": identity.verification_mode, "attestation_digest": digest, "proof_credit_authorized": "false"}
    with a.github_output.open("a") as handle:
        for key, val in outputs.items(): handle.write(f"{key}={val}\n")
    print(json.dumps({**outputs, "result": "PASS"}, sort_keys=True)); return 0

if __name__ == "__main__": raise SystemExit(main())
