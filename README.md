# PR Inspector

PR Inspector is a versioned, evidence-based pull-request review protocol for non-technical project owners, technical reviewers, and downstream AI agents.

## Start here

Ask the reviewing model to read [`BOOTSTRAP.md`](BOOTSTRAP.md). The bootstrap verifies the active immutable protocol and requests a target repository plus pull-request number.

## Authoritative output model

Every completed review preserves the canonical review artifacts and adds a deterministic derived output layer:

1. `review-package.json` — canonical machine-readable source of truth;
2. `OWNER_DECISION_CARD.fa.md` — existing Persian owner decision interface;
3. `TECHNICAL_HANDOFF.en.md` — existing complete English technical handoff;
4. `OWNER_RESULT.fa.txt` — exact two-line Persian default owner result;
5. `artifact-manifest.json` — paths, SHA-256 values, and conditional prompt metadata;
6. `NEXT_ACTION_PROMPT.en.md` — generated only for Yellow or Red and forbidden for Green.

All human-readable artifacts are deterministic projections of the validated JSON package. A mismatch, missing required artifact, forbidden Green prompt, or hash mismatch invalidates the review.

## Validation

```bash
python -m pip install ".[dev]"
python scripts/validate_repository_v2.py
python -m pytest
python scripts/validate_review_v2.py fixtures/golden-green --package-only
```

## Active protocol

`v1.8.0`

The complete protocol snapshot is under [`protocols/v1.8.0/`](protocols/v1.8.0/) and protected by [`release-locks/v1.8.0.sha256`](release-locks/v1.8.0.sha256).

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
