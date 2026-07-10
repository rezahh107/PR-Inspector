# PR Inspector

PR Inspector is a versioned, evidence-based pull-request review protocol for non-technical project owners, technical reviewers, and downstream AI agents.

## Start here

Ask the reviewing model to read [`BOOTSTRAP.md`](BOOTSTRAP.md). The bootstrap verifies the active immutable protocol and requests a target repository plus pull-request number.

## Authoritative output model

Every completed review validates one canonical package and computes one canonical structured decision projection:

1. `review-package.json` — canonical review source of truth;
2. `DECISION_PROJECTION.json` — registered technical reasons, owner readiness, next action, recipient, authority, prompt routing, validity, and reviewed head;
3. `OWNER_DECISION_CARD.fa.md` — complete Persian owner decision interface;
4. `TECHNICAL_HANDOFF.en.md` — complete English technical evidence handoff;
5. `OWNER_RESULT.fa.txt` — exact two-line Persian owner-readiness result from a finite registry;
6. `NEXT_ACTION_PROMPT.en.md` — generated only when the projection requires a recipient-specific action artifact;
7. `artifact-manifest.json` — canonical and actual-file hashes plus projection-backed routing metadata.

Technical status, approval state, owner readiness, prompt recipient, and modification authority are not re-derived by individual renderers. Schema, semantic, projection, byte, manifest, release-lock, or exact-head failure blocks a completed owner decision.

## Behavioral enforcement

The active v1.8 protocol includes a versioned decision-reason registry and a focused Behavioral Rule Coverage matrix. Critical per-artifact rules are mutation-tested in CI; mandatory post-repair PR Inspector re-review is sequence-tested.

## Validation

```bash
python -m pip install ".[dev]"
python scripts/validate_repository_v2.py
python -m pytest -q tests/test_behavioral_rule_coverage.py
python -m pytest
python scripts/validate_review_v2.py fixtures/golden-green --package-only
```

Pull-request CI explicitly checks out the triggering PR head, asserts the tested SHA, records tested-object identity, and distinguishes exact-head evidence from synthetic merge evidence.

## Active protocol candidate

`v1.8.0`

The unmerged protocol snapshot is under [`protocols/v1.8.0/`](protocols/v1.8.0/) and protected by [`release-locks/v1.8.0.sha256`](release-locks/v1.8.0.sha256). The default branch remains authoritative for the released protocol until this pull request is independently re-reviewed and merged.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
