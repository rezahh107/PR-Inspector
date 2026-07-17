# PR Inspector

PR Inspector is a versioned, evidence-based pull-request review protocol for non-technical project owners, technical reviewers, and downstream AI agents.

## Start here

Ask the reviewing model to read [`BOOTSTRAP.md`](BOOTSTRAP.md). The bootstrap verifies the active immutable protocol and requests a target repository plus pull-request number.

## Authoritative output model

Every completed review validates one canonical package and computes one canonical structured decision projection. Technical status, approval state, governance enforcement, and merge authorization are separate states.

Repository code validates artifacts, prompt semantics, provenance, identities, and lifecycle sequences. GitHub-hosted governance independently blocks merge when configured. Human or specialist reviewers supply judgment. PR Inspector records evidence but never approves or merges.

## Current v1.11.1 status

The `v1.11.1` corrected-activation patch completes the intended v1.11 output architecture. It preserves `minimal` / `strict` intake, evidence collection, Head-drift handling, pagination, annotation provenance, bot-review reconciliation, and technical/governance separation. It removes the remaining independent Candidate projection, prompt, artifact-verification, and owner-delivery authority.

Prompt-required artifacts now include an independently validated structured action contract. Hash-valid generic prose, the historical Candidate placeholder, profile commands embedded in prompts, and action-kind authority drift fail closed. Official owner-facing output requires `VerifiedReviewCompletion` and `official_owner_delivery`; profile commands remain a separate verified accessor.

Repository-settings enforcement remains `insufficient_evidence`. Successful CI does not prove branch protection, Rulesets, required reviews, CODEOWNERS enforcement, stale-approval dismissal, bypass restrictions, or merge-queue enforcement.

## Governance truth

A documented requirement is not machine evidence, and machine evidence is not GitHub-enforced protection. A Green technical result does not prove merge authorization. PR #12 remains historical provenance for the merged v1.8.0 release; historical comments are not rewritten as approvals.

## Validation

```bash
python -m pip install ".[dev]"
python scripts/validate_repository_v2.py
python -m pytest -q tests/test_v1_11_1_output_authority.py
python -m pytest -q tests/test_behavioral_rule_coverage.py
python -m pytest -q tests/test_governance_enforcement.py
python -m pytest -q tests/test_personal_minimum_security_profile.py
python -m pytest -q tests/test_repository_closure.py
python -m pytest -q tests/test_canonical_output_enforcement.py
python -m pytest -q tests/test_canonical_output_atomicity.py
python -m pytest
```

Pull-request CI checks out the triggering PR head, asserts the tested SHA, records object identity, and distinguishes exact-head evidence from synthetic merge evidence. CI success does not itself prove repository-settings enforcement.

## Active protocol

`v1.11.1`

`CURRENT_VERSION` selects the snapshot under [`protocols/v1.11.1/`](protocols/v1.11.1/) in this checkout, protected by [`release-locks/v1.11.1.sha256`](release-locks/v1.11.1.sha256). The immutable `v1.11.0` snapshot and lock remain historical and unchanged.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
