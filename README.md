# PR Inspector

PR Inspector is a versioned, evidence-based pull-request review protocol for non-technical project owners, technical reviewers, and downstream AI agents.

## Start here

Ask the reviewing model to read [`BOOTSTRAP.md`](BOOTSTRAP.md). The bootstrap verifies the active immutable protocol and requests a target repository plus pull-request number.

## Authoritative output model

Every completed review validates one canonical package and computes one canonical structured decision projection. Technical status, approval state, governance enforcement, and merge authorization are separate states.

Repository code validates artifacts, provenance, identities, and lifecycle sequences. GitHub-hosted governance independently blocks merge when configured. Human or specialist reviewers supply judgment. PR Inspector records evidence but never approves or merges.

## Current v1.10.1 status

The `v1.10.1` snapshot adds the structured personal minimum-security governance profile while preserving the v1.10.0 external Coverage trust gate security-boundary repair and the v1.9.0 canonical-output boundary, publication commit point, verified-byte snapshot accessors, and governance code boundary. PR #14 was integrated into PR #13, and PR #13 was then merged to `main`; those pull requests are historical provenance, not pending activation gates.

Repository-settings enforcement remains `insufficient_evidence`. Successful CI does not prove branch protection, Rulesets, required reviews, CODEOWNERS enforcement, stale-approval dismissal, bypass restrictions, or merge-queue enforcement.

## Governance truth

A documented requirement is not machine evidence, and machine evidence is not GitHub-enforced protection. A Green technical result does not prove required reviews, required status checks, CODEOWNERS enforcement, stale-approval dismissal, or bypass resistance. When repository settings cannot be observed, the result remains `insufficient_evidence`.

PR #12 is historical provenance for the merged v1.8.0 release; it is not a pending release boundary. Historical comments and timeline records are not rewritten as approvals.

## Validation

```bash
python -m pip install ".[dev]"
python scripts/validate_repository_v2.py
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

`v1.10.1`

`CURRENT_VERSION` selects the snapshot under [`protocols/v1.10.1/`](protocols/v1.10.1/) in this checkout, protected by [`release-locks/v1.10.1.sha256`](release-locks/v1.10.1.sha256). Repository authority is determined from live `main`; a feature branch or its own prose cannot independently prove activation or merge state. Earlier snapshots, including v1.8.0 and v1.9.0, remain immutable historical releases.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
