# PR Inspector

PR Inspector is a versioned, evidence-based pull-request review protocol for non-technical project owners, technical reviewers, and downstream AI agents.

## Start here

Ask the reviewing model to read [`BOOTSTRAP.md`](BOOTSTRAP.md). The bootstrap verifies the active immutable protocol and requests a target repository plus pull-request number.

## Authoritative output model

Every completed review produces three synchronized artifacts:

1. `review-package.json` — canonical machine-readable source of truth;
2. `OWNER_DECISION_CARD.fa.md` — concise Persian owner decision interface;
3. `TECHNICAL_HANDOFF.en.md` — complete English technical handoff.

The Markdown artifacts must be deterministically rendered from the JSON package. A mismatch invalidates the review.

## Validation

```bash
python -m pip install ".[dev]"
python scripts/validate_repository_v2.py
python -m pytest
python scripts/validate_review_v2.py fixtures/golden-green --package-only
```

## Active protocol

`v1.4.0`

The complete protocol snapshot is under [`protocols/v1.4.0/`](protocols/v1.4.0/) and protected by [`release-locks/v1.4.0.sha256`](release-locks/v1.4.0.sha256).

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
