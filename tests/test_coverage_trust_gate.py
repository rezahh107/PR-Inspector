from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gate = load(
    "coverage_trust_gate",
    ROOT / "scripts/verify_coverage_trust_gate.py",
)
ISSUER = "a" * 40
BASE = "b" * 40
HEAD_43 = "c" * 40
HEAD_44 = "d" * 40


def claims(head: str, number: int = 43) -> dict:
    return {
        "iss": gate.OIDC_ISSUER,
        "aud": gate.OIDC_AUDIENCE,
        "repository": gate.TARGET_REPOSITORY,
        "repository_id": str(gate.TARGET_REPOSITORY_ID),
        "event_name": "pull_request",
        "workflow_ref": (
            f"{gate.TARGET_REPOSITORY}/{gate.CALLER_WORKFLOW_PATH}"
            f"@refs/pull/{number}/merge"
        ),
        "workflow_sha": head,
        "job_workflow_ref": (
            f"{gate.ISSUER_REPOSITORY}/{gate.ISSUER_WORKFLOW_PATH}"
            f"@{ISSUER}"
        ),
        "job_workflow_sha": ISSUER,
        "run_id": "1",
        "run_attempt": "1",
        "check_run_id": "2",
    }


def independent_claims(caller_sha: str) -> dict:
    return {
        "iss": gate.OIDC_ISSUER,
        "aud": gate.OIDC_AUDIENCE,
        "repository": gate.ISSUER_REPOSITORY,
        "repository_id": str(gate.ISSUER_REPOSITORY_ID),
        "event_name": "workflow_dispatch",
        "workflow_ref": (
            f"{gate.ISSUER_REPOSITORY}/{gate.INDEPENDENT_WORKFLOW_PATH}"
            "@refs/heads/test"
        ),
        "workflow_sha": caller_sha,
        "job_workflow_ref": (
            f"{gate.ISSUER_REPOSITORY}/{gate.ISSUER_WORKFLOW_PATH}"
            f"@{ISSUER}"
        ),
        "job_workflow_sha": ISSUER,
        "run_id": "1",
        "run_attempt": "1",
        "check_run_id": "2",
    }


def event(number: int, base: str, head: str) -> dict:
    return {
        "number": number,
        "repository": {
            "id": gate.TARGET_REPOSITORY_ID,
            "full_name": gate.TARGET_REPOSITORY,
        },
        "pull_request": {
            "number": number,
            "base": {"sha": base},
            "head": {"sha": head},
        },
    }


def api(number: int, base: str, head: str) -> dict:
    return {
        "number": number,
        "base": {
            "sha": base,
            "repo": {
                "id": gate.TARGET_REPOSITORY_ID,
                "full_name": gate.TARGET_REPOSITORY,
            },
        },
        "head": {"sha": head},
    }


def derive(number: int, head: str, **overrides):
    data = {
        "event": event(number, BASE, head),
        "api_pr": api(number, BASE, head),
        "oidc_claims": claims(head, number),
        "environment": {
            "GITHUB_RUN_ID": "1",
            "GITHUB_RUN_ATTEMPT": "1",
        },
    }
    data.update(overrides)
    return gate.derive_authoritative_identity(**data)


def workflow(
    issuer: str = ISSUER,
    *,
    dead: bool = False,
    needs: bool = True,
    ref: str = "${{ needs.external-coverage-trust.outputs.verified_head_sha }}",
) -> str:
    condition = "    if: ${{ false }}\n" if dead else ""
    dependency = "    needs: external-coverage-trust\n" if needs else ""
    return f"""name: Validate MVK
on:
  pull_request:
permissions:
  contents: read
jobs:
  external-coverage-trust:
{condition}    uses: rezahh107/PR-Inspector/.github/workflows/coverage-trust-gate.yml@{issuer}
    permissions:
      contents: read
      pull-requests: read
      id-token: write
  validate-mvk:
{dependency}    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          ref: {ref}
      - run: npm run validate:coverage
        env:
          COVERAGE_REPOSITORY: ${{{{ needs.external-coverage-trust.outputs.verified_repository }}}}
          COVERAGE_PR_NUMBER: ${{{{ needs.external-coverage-trust.outputs.verified_pr_number }}}}
          COVERAGE_BASE_SHA: ${{{{ needs.external-coverage-trust.outputs.verified_base_sha }}}}
          COVERAGE_HEAD_SHA: ${{{{ needs.external-coverage-trust.outputs.verified_head_sha }}}}
"""


class IdentityTests(unittest.TestCase):
    def test_pr_43_and_second_pr_resolve_dynamically(self):
        for number, head in ((43, HEAD_43), (44, HEAD_44)):
            identity, diagnostics = derive(number, head)
            self.assertEqual([], diagnostics)
            assert identity is not None
            self.assertEqual(number, identity.pull_request_number)
            self.assertEqual(head, identity.target_head_sha)
            self.assertEqual(ISSUER, identity.issuer_workflow_sha)

    def test_event_api_pr_number_mismatch_fails(self):
        identity, diagnostics = derive(
            43,
            HEAD_43,
            api_pr=api(44, BASE, HEAD_43),
        )
        self.assertIsNone(identity)
        self.assertIn(
            "COV_EXTERNAL_EVENT_PR_MISMATCH",
            {item.code for item in diagnostics},
        )

    def test_event_api_head_mismatch_fails(self):
        identity, diagnostics = derive(
            43,
            HEAD_43,
            api_pr=api(43, BASE, HEAD_44),
        )
        self.assertIsNone(identity)
        self.assertIn(
            "COV_EXTERNAL_EVENT_HEAD_MISMATCH",
            {item.code for item in diagnostics},
        )

    def test_target_caller_cannot_select_independent_policy(self):
        identity, diagnostics = gate.derive_authoritative_identity(
            event=event(43, BASE, HEAD_43),
            api_pr=api(43, BASE, HEAD_43),
            oidc_claims=claims(HEAD_43),
            environment={
                "GITHUB_RUN_ID": "1",
                "GITHUB_RUN_ATTEMPT": "1",
            },
            independent_policy_pr_number=43,
        )
        self.assertIsNone(identity)
        self.assertIn(
            "COV_EXTERNAL_TARGET_POLICY_INPUT_FORBIDDEN",
            {item.code for item in diagnostics},
        )


    def test_missing_and_invalid_run_identity_fails(self):
        for bad_claims, bad_env in (
            ({**claims(HEAD_43), "run_id": ""}, {"GITHUB_RUN_ID": "1", "GITHUB_RUN_ATTEMPT": "1"}),
            ({**claims(HEAD_43), "run_attempt": "0"}, {"GITHUB_RUN_ID": "1", "GITHUB_RUN_ATTEMPT": "1"}),
            (claims(HEAD_43), {"GITHUB_RUN_ID": "", "GITHUB_RUN_ATTEMPT": "1"}),
            (claims(HEAD_43), {"GITHUB_RUN_ID": "1", "GITHUB_RUN_ATTEMPT": "nope"}),
        ):
            identity, diagnostics = gate.derive_authoritative_identity(
                event=event(43, BASE, HEAD_43),
                api_pr=api(43, BASE, HEAD_43),
                oidc_claims=bad_claims,
                environment=bad_env,
            )
            self.assertIsNone(identity)
            self.assertIn(
                "COV_EXTERNAL_OIDC_RUN_IDENTITY_MISMATCH",
                {item.code for item in diagnostics},
            )

    def test_one_off_pr43_policy_is_separate_but_issuer_is_reusable(self):
        identity, diagnostics = gate.derive_authoritative_identity(
            event={},
            api_pr=api(43, BASE, HEAD_43),
            oidc_claims=independent_claims("e" * 40),
            environment={
                "GITHUB_RUN_ID": "1",
                "GITHUB_RUN_ATTEMPT": "1",
            },
            independent_policy_pr_number=43,
        )
        self.assertEqual([], diagnostics)
        assert identity is not None
        self.assertEqual(
            "independent_explicit_policy_api",
            identity.verification_mode,
        )
        self.assertEqual(ISSUER, identity.issuer_workflow_sha)
        self.assertEqual(
            gate.ISSUER_WORKFLOW_PATH,
            identity.issuer_workflow_path,
        )

    def test_no_repository_wide_target_pr_constant(self):
        self.assertFalse(hasattr(gate, "TARGET_PR_NUMBER"))


class TopologyTests(unittest.TestCase):
    def test_dead_and_non_required_jobs_fail(self):
        dead_codes = {
            item.code
            for item in gate.workflow_diagnostics(
                workflow(dead=True), ISSUER
            )
        }
        detached_codes = {
            item.code
            for item in gate.workflow_diagnostics(
                workflow(needs=False), ISSUER
            )
        }
        self.assertIn("COV_EXTERNAL_REQUIRED_JOB_DEAD", dead_codes)
        self.assertIn(
            "COV_EXTERNAL_VALIDATION_NEEDS_MISSING",
            detached_codes,
        )

    def test_validation_checkout_drift_fails(self):
        diagnostics = gate.workflow_diagnostics(
            workflow(ref="${{ github.sha }}"),
            ISSUER,
        )
        self.assertIn(
            "COV_EXTERNAL_VALIDATION_CHECKOUT_MISMATCH",
            {item.code for item in diagnostics},
        )


    def test_empty_comment_only_and_malformed_yaml_fail_closed(self):
        cases = (
            "",
            "# uses: rezahh107/PR-Inspector/.github/workflows/coverage-trust-gate.yml@" + ISSUER + "\n",
            "jobs: [",
            "- just\n- a\n- list\n",
        )
        for text in cases:
            diagnostics = gate.workflow_diagnostics(text, ISSUER)
            self.assertTrue(diagnostics, text)

    def test_non_mapping_jobs_job_steps_and_env_fail_closed(self):
        cases = (
            "jobs: []\n",
            workflow().replace("external-coverage-trust:\n", "external-coverage-trust: []\n", 1),
            workflow().replace("steps:\n", "steps: {}\n", 1),
            workflow().replace("env:\n", "env: []\n", 1),
        )
        for text in cases:
            diagnostics = gate.workflow_diagnostics(text, ISSUER)
            self.assertTrue(diagnostics, text)

    def test_comments_and_wrong_step_bindings_do_not_satisfy_gate(self):
        comment_only = workflow().replace(
            "          COVERAGE_REPOSITORY: ${{ needs.external-coverage-trust.outputs.verified_repository }}",
            "          # COVERAGE_REPOSITORY: ${{ needs.external-coverage-trust.outputs.verified_repository }}",
        )
        wrong_step = workflow().replace(
            "        env:\n          COVERAGE_REPOSITORY:",
            "      - run: echo misplaced\n        env:\n          COVERAGE_REPOSITORY:",
        )
        for text in (comment_only, wrong_step):
            diagnostics = gate.workflow_diagnostics(text, ISSUER)
            self.assertIn(
                "COV_EXTERNAL_VALIDATION_IDENTITY_BINDING_MISSING",
                {item.code for item in diagnostics},
            )

    def test_stale_and_mismatched_issuer_pins_fail(self):
        diagnostics = gate.workflow_diagnostics(workflow(issuer="e" * 40), ISSUER)
        self.assertIn(
            "COV_EXTERNAL_TRUST_ROOT_PIN_TOPOLOGY_INVALID",
            {item.code for item in diagnostics},
        )
        diagnostics = gate.workflow_diagnostics(
            workflow().replace(gate.ISSUER_WORKFLOW_PATH, ".github/workflows/other.yml"),
            ISSUER,
        )
        self.assertIn(
            "COV_EXTERNAL_TRUST_ROOT_PIN_TOPOLOGY_INVALID",
            {item.code for item in diagnostics},
        )

    def test_yaml_anchors_are_rejected(self):
        diagnostics = gate.workflow_diagnostics(
            workflow().replace("contents: read", "contents: &read read", 1),
            ISSUER,
        )
        self.assertIn(
            "COV_EXTERNAL_WORKFLOW_YAML_UNSUPPORTED",
            {item.code for item in diagnostics},
        )

    def test_valid_bootstrap_keeps_proof_credit_false(self):
        identity, diagnostics = derive(43, HEAD_43)
        self.assertEqual([], diagnostics)
        assert identity is not None
        value = gate.issue_bootstrap_attestation(
            identity,
            event(43, BASE, HEAD_43),
            api(43, BASE, HEAD_43),
            claims(HEAD_43),
            "2026-07-13T15:00:00Z",
        )
        self.assertEqual([], gate.verify_attestation(value, identity))
        self.assertFalse(value["proof_credit_authorized"])


class PlanningCoverageTests(unittest.TestCase):
    def test_malformed_invalid_utf8_and_unreadable_json_fail_closed(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "planning" / "coverage"
            folder.mkdir(parents=True)
            (folder / "malformed.json").write_text("{", encoding="utf-8")
            (folder / "invalid-utf8.json").write_bytes(b"\xff")
            (folder / "missing.json").symlink_to(folder / "does-not-exist.json")
            diagnostics = gate.planning_coverage_diagnostics(root)
        codes = {item.code for item in diagnostics}
        self.assertIn("COV_EXTERNAL_PLANNING_JSON_INVALID", codes)
        self.assertIn("COV_EXTERNAL_PLANNING_JSON_UNREADABLE", codes)
        self.assertTrue(all(item.path and item.path.startswith("planning/coverage") for item in diagnostics))

    def test_planning_proof_request_blocks_bootstrap(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "planning" / "coverage"
            folder.mkdir(parents=True)
            (folder / "proof.json").write_text(
                '{"artifact_role":"coverage_credit"}\n',
                encoding="utf-8",
            )
            diagnostics = gate.planning_coverage_diagnostics(root)
        self.assertEqual(
            ["COV_EXTERNAL_TRUST_BOOTSTRAP_PROOF_CREDIT_FORBIDDEN"],
            [item.code for item in diagnostics],
        )


class NegativeIdentityTests(unittest.TestCase):
    def test_event_api_repository_mismatch_fails(self):
        bad_event = event(43, BASE, HEAD_43)
        bad_event["repository"] = {"id": 1, "full_name": "evil/repo"}
        identity, diagnostics = derive(43, HEAD_43, event=bad_event)
        self.assertIsNone(identity)
        self.assertIn(
            "COV_EXTERNAL_EVENT_REPOSITORY_ID_MISMATCH",
            {item.code for item in diagnostics},
        )

    def test_event_api_base_mismatch_fails(self):
        identity, diagnostics = derive(
            43,
            HEAD_43,
            api_pr=api(43, "e" * 40, HEAD_43),
        )
        self.assertIsNone(identity)
        self.assertIn(
            "COV_EXTERNAL_EVENT_BASE_MISMATCH",
            {item.code for item in diagnostics},
        )

    def test_wrong_issuer_sha_fails(self):
        bad_claims = claims(HEAD_43)
        bad_claims["job_workflow_sha"] = "f" * 40
        identity, diagnostics = derive(43, HEAD_43, oidc_claims=bad_claims)
        self.assertIsNone(identity)
        self.assertIn(
            "COV_EXTERNAL_OIDC_WORKFLOW_IDENTITY_MISMATCH",
            {item.code for item in diagnostics},
        )

    def test_missing_api_evidence_fails(self):
        identity, diagnostics = derive(43, HEAD_43, api_pr={})
        self.assertIsNone(identity)
        codes = {item.code for item in diagnostics}
        self.assertIn("COV_EXTERNAL_API_REPOSITORY_ID_MISMATCH", codes)
        self.assertIn("COV_EXTERNAL_API_PR_IDENTITY_INVALID", codes)

    def test_stale_head_fails_exact_head_checkout(self):
        identity, diagnostics = derive(43, HEAD_43)
        self.assertEqual([], diagnostics)
        assert identity is not None
        # Use a temporary git repository instead of mocking so this covers the
        # exact-head checkout gate as executed by evaluate_target.
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.check_call(["git", "init", "-q"], cwd=root)
            subprocess.check_call(
                ["git", "config", "user.email", "t@example.com"],
                cwd=root,
            )
            subprocess.check_call(
                ["git", "config", "user.name", "Test"],
                cwd=root,
            )
            (root / "file.txt").write_text("x\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "file.txt"], cwd=root)
            subprocess.check_call(
                ["git", "commit", "-q", "-m", "init"],
                cwd=root,
            )
            stale_codes = {
                item.code
                for item in gate.evaluate_target(
                    target_root=root,
                    identity=identity,
                )
            }
        self.assertIn("COV_EXTERNAL_TRUST_HEAD_MISMATCH", stale_codes)

    def test_invalid_attestation_identity_fails(self):
        identity, diagnostics = derive(43, HEAD_43)
        self.assertEqual([], diagnostics)
        assert identity is not None
        value = gate.issue_bootstrap_attestation(
            identity,
            event(43, BASE, HEAD_43),
            api(43, BASE, HEAD_43),
            claims(HEAD_43),
            "2026-07-13T15:00:00Z",
        )
        value["target"]["evidence_head_sha"] = HEAD_44
        self.assertIn(
            "COV_EXTERNAL_ATTESTATION_CAPABILITY_INVALID",
            {item.code for item in gate.verify_attestation(value, identity)},
        )


if __name__ == "__main__":
    unittest.main()
