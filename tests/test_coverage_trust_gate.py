from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify_coverage_trust_gate.py"
SPEC = importlib.util.spec_from_file_location("coverage_trust_gate", MODULE_PATH)
gate = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = gate
SPEC.loader.exec_module(gate)

ISSUER_SHA = "a" * 40


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def write(root: Path, path: str, content: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def caller_workflow(
    issuer_sha: str = ISSUER_SHA,
    *,
    identity_inputs: bool = False,
    dead: bool = False,
    needs: bool = True,
    checkout_ref: str = "${{ needs.external-coverage-trust.outputs.verified_head_sha }}",
) -> str:
    injected = ""
    if identity_inputs:
        injected = """    with:
      target_head_sha: deadbeef
      target_base_sha: deadbeef
      pull_request_number: 43
      issuer_workflow_sha: deadbeef
"""
    condition = "    if: ${{ false }}\n" if dead else ""
    dependency = "    needs: external-coverage-trust\n" if needs else ""
    return f"""name: Validate MVK
on:
  pull_request:
permissions:
  contents: read
jobs:
  external-coverage-trust:
    name: External Coverage Trust Gate
{condition}    uses: rezahh107/PR-Inspector/.github/workflows/coverage-trust-gate.yml@{issuer_sha}
{injected}    permissions:
      contents: read
      pull-requests: read
      id-token: write
  validate-mvk:
    name: Validate MVK
{dependency}    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          persist-credentials: false
          fetch-depth: 0
          ref: {checkout_ref}
      - run: npm run validate:coverage
        env:
          COVERAGE_REPOSITORY: ${{{{ needs.external-coverage-trust.outputs.verified_repository }}}}
          COVERAGE_PR_NUMBER: ${{{{ needs.external-coverage-trust.outputs.verified_pr_number }}}}
          COVERAGE_BASE_SHA: ${{{{ needs.external-coverage-trust.outputs.verified_base_sha }}}}
          COVERAGE_HEAD_SHA: ${{{{ needs.external-coverage-trust.outputs.verified_head_sha }}}}
"""


def guard_workflow(issuer_sha: str = ISSUER_SHA) -> str:
    return f"""name: Required Authoritative Coverage Trust
on:
  pull_request_target:
permissions:
  contents: read
  pull-requests: read
  id-token: write
jobs:
  authoritative-coverage-trust:
    name: PRF-012 Authoritative Coverage Trust
    uses: rezahh107/PR-Inspector/.github/workflows/coverage-trust-gate.yml@{issuer_sha}
    permissions:
      contents: read
      pull-requests: read
      id-token: write
  authoritative-target-validation:
    name: PRF-012 Authoritative Target Validation
    needs: authoritative-coverage-trust
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          repository: ${{{{ needs.authoritative-coverage-trust.outputs.verified_repository }}}}
          ref: ${{{{ needs.authoritative-coverage-trust.outputs.verified_head_sha }}}}
          persist-credentials: false
          fetch-depth: 0
      - run: git diff --check
"""


def init_target(caller: str | None = None):
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    git(root, "init", "-q")
    git(root, "config", "user.name", "Coverage Gate Test")
    git(root, "config", "user.email", "coverage-gate@example.invalid")
    write(root, gate.CALLER_WORKFLOW_PATH, caller or caller_workflow())
    write(root, gate.REQUIRED_GUARD_WORKFLOW_PATH, guard_workflow())
    for name in (
        "validate-coverage-guarantee.mjs",
        "validate-coverage-guarantee-prf010.mjs",
        "validate-coverage-guarantee-legacy.mjs",
    ):
        write(root, f"kernel/validator/{name}", "export {};\n")
    write(root, "planning/coverage/coverage-baseline.v1.json", "{}\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")
    write(root, "README.md", "head\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "head")
    return temp, root, base, git(root, "rev-parse", "HEAD")


def claims(head: str) -> dict:
    return {
        "iss": gate.OIDC_ISSUER,
        "aud": gate.OIDC_AUDIENCE,
        "repository": gate.TARGET_REPOSITORY,
        "repository_id": str(gate.TARGET_REPOSITORY_ID),
        "event_name": "pull_request",
        "workflow_ref": f"{gate.TARGET_REPOSITORY}/{gate.CALLER_WORKFLOW_PATH}@refs/pull/43/merge",
        "workflow_sha": head,
        "job_workflow_ref": f"{gate.ISSUER_REPOSITORY}/{gate.ISSUER_WORKFLOW_PATH}@{ISSUER_SHA}",
        "job_workflow_sha": ISSUER_SHA,
        "run_id": "1234",
        "run_attempt": "1",
        "check_run_id": "9876",
    }


def event(base: str, head: str, number: int = 43) -> dict:
    return {
        "number": number,
        "repository": {"id": gate.TARGET_REPOSITORY_ID, "full_name": gate.TARGET_REPOSITORY},
        "pull_request": {
            "number": number,
            "base": {"sha": base},
            "head": {"sha": head},
        },
    }


def api(base: str, head: str, number: int = 43) -> dict:
    return {
        "number": number,
        "base": {
            "sha": base,
            "repo": {"id": gate.TARGET_REPOSITORY_ID, "full_name": gate.TARGET_REPOSITORY},
        },
        "head": {"sha": head},
    }


class CoverageTrustGateTests(unittest.TestCase):
    def derive(self, base: str, head: str, **overrides):
        data = {
            "event": event(base, head),
            "api_pr": api(base, head),
            "oidc_claims": claims(head),
            "environment": {"GITHUB_RUN_ID": "1234", "GITHUB_RUN_ATTEMPT": "1"},
        }
        data.update(overrides)
        return gate.derive_authoritative_identity(**data)

    def test_real_event_head_differs_from_caller_supplied_head(self):
        temp, root, base, head = init_target(caller_workflow(identity_inputs=True))
        self.addCleanup(temp.cleanup)
        identity, diagnostics = self.derive(
            base,
            head,
            event=event(base, "d" * 40),
        )
        self.assertIsNone(identity)
        self.assertIn("COV_EXTERNAL_EVENT_HEAD_MISMATCH", {x.code for x in diagnostics})
        topology = gate._workflow_topology_diagnostics(
            caller_workflow(identity_inputs=True), ISSUER_SHA
        )
        self.assertIn("COV_EXTERNAL_CALLER_IDENTITY_INPUT_FORBIDDEN", {x.code for x in topology})

    def test_wrong_base_or_pr_number(self):
        temp, root, base, head = init_target()
        self.addCleanup(temp.cleanup)
        identity, diagnostics = self.derive(
            base,
            head,
            event=event("d" * 40, head, 44),
        )
        codes = {x.code for x in diagnostics}
        self.assertIsNone(identity)
        self.assertIn("COV_EXTERNAL_EVENT_BASE_MISMATCH", codes)
        self.assertIn("COV_EXTERNAL_EVENT_PR_MISMATCH", codes)

    def test_alternate_issuer_sha_while_uses_remains_pinned(self):
        codes = {
            x.code for x in gate._workflow_topology_diagnostics(
                caller_workflow("d" * 40, identity_inputs=True), ISSUER_SHA
            )
        }
        self.assertIn("COV_EXTERNAL_OIDC_ISSUER_SHA_MISMATCH", codes)
        self.assertIn("COV_EXTERNAL_CALLER_IDENTITY_INPUT_FORBIDDEN", codes)

    def test_dead_or_non_required_external_job(self):
        dead = {x.code for x in gate._workflow_topology_diagnostics(
            caller_workflow(dead=True), ISSUER_SHA
        )}
        detached = {x.code for x in gate._workflow_topology_diagnostics(
            caller_workflow(needs=False), ISSUER_SHA
        )}
        self.assertIn("COV_EXTERNAL_REQUIRED_JOB_DEAD", dead)
        self.assertIn("COV_EXTERNAL_VALIDATION_NEEDS_MISSING", detached)

    def test_validation_checkout_differs_from_external_head(self):
        codes = {x.code for x in gate._workflow_topology_diagnostics(
            caller_workflow(checkout_ref="${{ github.event.pull_request.head.sha }}"),
            ISSUER_SHA,
        )}
        self.assertIn("COV_EXTERNAL_VALIDATION_CHECKOUT_MISMATCH", codes)

    def test_forged_time_and_ingestion_are_rejected(self):
        workflow = caller_workflow() + (
            "\n# COVERAGE_VALIDATED_AT\n# COVERAGE_VALIDATION_SOURCE\n"
            "# COVERAGE_TRUSTED_INGESTION_ATTESTATIONS\n"
        )
        codes = {x.code for x in gate._workflow_topology_diagnostics(workflow, ISSUER_SHA)}
        self.assertIn("COV_EXTERNAL_TRUST_ROOT_TARGET_MINT_FORBIDDEN", codes)
        self.assertIn("COV_EXTERNAL_ATTESTATION_UNSIGNED_ENV_FORBIDDEN", codes)

    def test_reserved_required_check_name_cannot_be_spoofed(self):
        temp, root, base, head = init_target()
        self.addCleanup(temp.cleanup)
        write(root, ".github/workflows/spoof.yml",
              "jobs:\n  x:\n    name: PRF-012 Authoritative Coverage Trust\n")
        codes = {x.code for x in gate._required_guard_diagnostics(root, ISSUER_SHA)}
        self.assertIn("COV_EXTERNAL_REQUIRED_CHECK_NAME_SPOOFED", codes)

    def test_valid_exact_head_bootstrap_denies_proof_credit(self):
        temp, root, base, head = init_target()
        self.addCleanup(temp.cleanup)
        verified, diagnostics = self.derive(base, head)
        self.assertEqual([], diagnostics)
        assert verified is not None
        self.assertEqual([], gate.evaluate_target(target_root=root, identity=verified))
        attestation = gate.issue_bootstrap_attestation(
            identity=verified,
            event=event(base, head),
            api_pr=api(base, head),
            oidc_claims=claims(head),
            validated_at="2026-07-13T14:00:00Z",
        )
        self.assertEqual([], gate.verify_bootstrap_attestation(attestation, identity=verified))
        self.assertFalse(attestation["proof_credit_authorized"])
        self.assertEqual(head, attestation["target"]["evidence_head_sha"])
        self.assertEqual(64, len(attestation["verifier_created_capability"]))

    def test_oidc_job_workflow_sha_is_only_issuer_authority(self):
        temp, root, base, head = init_target()
        self.addCleanup(temp.cleanup)
        invalid = claims(head)
        invalid["job_workflow_sha"] = "not-a-sha"
        identity, diagnostics = self.derive(base, head, oidc_claims=invalid)
        self.assertIsNone(identity)
        self.assertIn("COV_EXTERNAL_OIDC_ISSUER_SHA_INVALID", {x.code for x in diagnostics})


if __name__ == "__main__":
    unittest.main()
