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
publisher = load(
    "coverage_check_publisher",
    ROOT / "scripts/publish_coverage_check.py",
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


class PublisherTests(unittest.TestCase):
    def identity(self, head: str = HEAD_43, app_id: int = 24680):
        return publisher.PublicationIdentity(
            repository="rezahh107/EV4-Decision-Kernel",
            repository_id=1292378784,
            pull_request_number=43,
            base_sha=BASE,
            head_sha=head,
            issuer_workflow_sha=ISSUER,
            run_id="1",
            run_attempt=1,
            attestation_digest="e" * 64,
            expected_app_id=app_id,
        )

    def response(self, identity, app_id=None):
        return {
            "id": 9,
            **publisher.build_check_run_payload(identity),
            "app": {
                "id": (
                    identity.expected_app_id
                    if app_id is None
                    else app_id
                )
            },
        }

    def test_result_is_head_associated_not_base_associated(self):
        identity = self.identity()
        payload = publisher.build_check_run_payload(identity)
        self.assertEqual(identity.head_sha, payload["head_sha"])
        self.assertNotEqual(identity.base_sha, payload["head_sha"])
        publisher.validate_check_run_response(
            self.response(identity), identity
        )

    def test_new_head_makes_old_result_non_satisfying(self):
        with self.assertRaises(ValueError):
            publisher.validate_check_run_response(
                self.response(self.identity(HEAD_43)),
                self.identity(HEAD_44),
            )

    def test_same_name_wrong_app_source_fails(self):
        with self.assertRaisesRegex(
            ValueError,
            "source GitHub App mismatch",
        ):
            publisher.validate_check_run_response(
                self.response(self.identity(), 999),
                self.identity(),
            )

    def test_missing_result_fails(self):
        with self.assertRaises(ValueError):
            publisher.validate_check_run_response({}, self.identity())


if __name__ == "__main__":
    unittest.main()
