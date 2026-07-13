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


def init_target() -> tuple[tempfile.TemporaryDirectory, Path, str]:
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    git(root, "init", "-q")
    git(root, "config", "user.name", "Coverage Gate Test")
    git(root, "config", "user.email", "coverage-gate@example.invalid")
    write(root, ".github/workflows/validate-mvk.yml", "name: Validate MVK\n")
    write(root, "kernel/validator/validate-coverage-guarantee.mjs", "export {};\n")
    write(root, "kernel/validator/validate-coverage-guarantee-legacy.mjs", "export {};\n")
    write(root, "planning/coverage/coverage-baseline.v1.json", "{}\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    return temp, root, git(root, "rev-parse", "HEAD")


class CoverageTrustGateTests(unittest.TestCase):
    def test_rejects_target_minted_clock_and_forged_ingestion(self) -> None:
        temp, root, base = init_target()
        self.addCleanup(temp.cleanup)
        write(root, ".github/workflows/validate-mvk.yml", f"""name: Validate MVK
jobs:
  external:
    uses: rezahh107/PR-Inspector/.github/workflows/coverage-trust-gate.yml@{ISSUER_SHA}
  forged:
    runs-on: ubuntu-latest
    steps:
      - run: |
          echo COVERAGE_VALIDATED_AT=2024-01-02T00:00:00Z >> \"$GITHUB_ENV\"
          echo COVERAGE_VALIDATION_SOURCE=github_actions_runner_clock_v1 >> \"$GITHUB_ENV\"
          echo 'COVERAGE_TRUSTED_INGESTION_ATTESTATIONS={{}}' >> \"$GITHUB_ENV\"
""")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "forged trust")
        head = git(root, "rev-parse", "HEAD")
        codes = {item.code for item in gate.evaluate_target(
            target_root=root,
            target_repository="rezahh107/EV4-Decision-Kernel",
            target_head_sha=head,
            target_base_sha=base,
            issuer_workflow_sha=ISSUER_SHA,
            proof_credit_mode="bootstrap_deny",
        )}
        self.assertIn("COV_EXTERNAL_TRUST_ROOT_TARGET_MINT_FORBIDDEN", codes)
        self.assertIn("COV_EXTERNAL_ATTESTATION_UNSIGNED_ENV_FORBIDDEN", codes)

    def test_modified_wrapper_and_workflow_cannot_bypass_external_gate(self) -> None:
        temp, root, base = init_target()
        self.addCleanup(temp.cleanup)
        write(root, ".github/workflows/validate-mvk.yml", f"""name: Validate MVK
jobs:
  external:
    uses: rezahh107/PR-Inspector/.github/workflows/coverage-trust-gate.yml@{ISSUER_SHA}
  bypass:
    runs-on: ubuntu-latest
    steps:
      - run: echo COVERAGE_VALIDATED_AT=2024-01-02T00:00:00Z >> \"$GITHUB_ENV\"
""")
        write(root, "kernel/validator/validate-coverage-guarantee.mjs", "// bypass\n")
        write(root, "planning/coverage/proof.json", json.dumps({"artifact_role": "runtime_proof"}) + "\n")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "attempt bypass")
        head = git(root, "rev-parse", "HEAD")
        codes = {item.code for item in gate.evaluate_target(
            target_root=root,
            target_repository="rezahh107/EV4-Decision-Kernel",
            target_head_sha=head,
            target_base_sha=base,
            issuer_workflow_sha=ISSUER_SHA,
            proof_credit_mode="bootstrap_deny",
        )}
        self.assertIn("COV_EXTERNAL_TRUST_ROOT_TARGET_MINT_FORBIDDEN", codes)
        self.assertIn("COV_EXTERNAL_TRUST_BOOTSTRAP_PROOF_CREDIT_FORBIDDEN", codes)
        self.assertIn("COV_EXTERNAL_TRUST_GATE_IDENTITY_MISMATCH", codes)

    def test_valid_external_immutable_sha_attestation_path(self) -> None:
        temp, root, base = init_target()
        self.addCleanup(temp.cleanup)
        write(root, ".github/workflows/validate-mvk.yml", f"""name: Validate MVK
jobs:
  external:
    uses: rezahh107/PR-Inspector/.github/workflows/coverage-trust-gate.yml@{ISSUER_SHA}
""")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "external gate")
        head = git(root, "rev-parse", "HEAD")
        diagnostics = gate.evaluate_target(
            target_root=root,
            target_repository="rezahh107/EV4-Decision-Kernel",
            target_head_sha=head,
            target_base_sha=base,
            issuer_workflow_sha=ISSUER_SHA,
            proof_credit_mode="bootstrap_deny",
        )
        self.assertEqual([], diagnostics)
        attestation = gate.issue_bootstrap_attestation(
            issuer_workflow_sha=ISSUER_SHA,
            target_repository="rezahh107/EV4-Decision-Kernel",
            target_base_sha=base,
            target_head_sha=head,
            pull_request_number=43,
            run_id="123456",
            run_attempt=2,
            validated_at="2026-07-13T12:00:00Z",
        )
        self.assertEqual([], gate.verify_bootstrap_attestation(
            attestation,
            issuer_workflow_sha=ISSUER_SHA,
            target_repository="rezahh107/EV4-Decision-Kernel",
            target_head_sha=head,
            run_id="123456",
            run_attempt=2,
        ))
        self.assertFalse(attestation["proof_credit_authorized"])
        self.assertEqual(64, len(attestation["verifier_created_capability"]))


if __name__ == "__main__":
    unittest.main()
