# PR Inspector

PR Inspector is a versioned, evidence-based pull-request review protocol for non-technical project owners, technical reviewers, and downstream AI agents.

## Start here

Ask the reviewing model to read [`BOOTSTRAP.md`](BOOTSTRAP.md). The bootstrap verifies the active immutable protocol and requests a target repository plus pull-request number.

## Authoritative output model

Every completed review validates one canonical package and computes one canonical structured decision projection. Technical status, approval state, governance enforcement, and merge authorization are separate states.

Repository code validates artifacts, provenance, identities, and lifecycle sequences. GitHub-hosted governance independently blocks merge when configured. Human or specialist reviewers supply judgment. PR Inspector records evidence but never approves or merges.

## Governance truth

A documented requirement is not machine evidence, and machine evidence is not GitHub-enforced protection. A Green technical result does not prove required reviews, required status checks, CODEOWNERS enforcement, stale-approval dismissal, or bypass resistance. When repository settings cannot be observed, the result remains `insufficient_evidence`.

PR #12 is historical provenance for the merged v1.8.0 release; it is not a pending release boundary. Historical comments and timeline records are not rewritten as approvals.

## Validation

```bash
python -m pip install ".[dev]"
python scripts/validate_repository_v2.py
python -m pytest -q tests/test_behavioral_rule_coverage.py
python -m pytest -q tests/test_governance_enforcement.py
python -m pytest
```

Pull-request CI checks out the triggering PR head, asserts the tested SHA, records object identity, and distinguishes exact-head evidence from synthetic merge evidence. CI success does not itself prove repository-settings enforcement.

## Active protocol

`v1.9.0`

The snapshot under [`protocols/v1.9.0/`](protocols/v1.9.0/) is the active protocol selected by `CURRENT_VERSION` on authoritative `main` and is protected by [`release-locks/v1.9.0.sha256`](release-locks/v1.9.0.sha256). Earlier snapshots, including v1.8.0, remain immutable historical releases.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
