# PR Inspector

Evidence-based pull-request review for non-technical project owners and downstream AI reviewers.

## Start here

Ask the model to read [`BOOTSTRAP.md`](BOOTSTRAP.md). It will load the active protocol and request the target repository plus pull-request number.

## Outputs

1. A short Persian Owner Decision Card.
2. A complete English Technical Handoff Package.

## Repository map

- [`AGENTS.md`](AGENTS.md): compact agent instructions
- [`protocol-manifest.yaml`](protocol-manifest.yaml): canonical load order
- [`contracts/v1.3.0/PR_REVIEW_CONTRACT.md`](contracts/v1.3.0/PR_REVIEW_CONTRACT.md): active contract
- [`pipeline/REVIEW_PIPELINE.md`](pipeline/REVIEW_PIPELINE.md): operational sequence
- [`templates/`](templates/): fixed report formats

## Validation

```bash
python scripts/validate_repository.py
```

Active protocol: `v1.3.0`
