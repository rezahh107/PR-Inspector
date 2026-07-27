# PR Inspector

PR Inspector is a deterministic evidence-based pull-request review protocol.

## Active protocol

`v1.13.1`

- Protocol snapshot: [`protocols/v1.13.1/`](protocols/v1.13.1/)
- Startup manifest: [`protocol-manifest.yaml`](protocol-manifest.yaml)

The active model/runtime coordination source of truth is `protocols/v1.13.1/functional-runtime-contract.json`. Per-review startup is retrieval-only and reads only the active version, contract, and intake response through the repository connector; it performs no local validation or execution.

Target-side assurance remains strict: exact repository/PR/Base/Head/merge-base identity, complete paginated checks and review surfaces, missing-evidence fail-closed behavior, canonical `project_decision`, package/schema/semantic validation, canonical bytes and hashes, atomic publication, live-Head rechecks, process-local `VerifiedReviewCompletion`, `official_owner_delivery`, separately generated profile commands, and a prohibition on manual concatenation of owner artifacts.

## Validation

```bash
python -m pip install ".[dev]"
python scripts/validate_runtime_contract.py
python scripts/validate_planning_governance.py --check-static
python scripts/validate_repository_v2.py
python -m pytest
```

Repository authority is determined from live `main`; this branch is a candidate until merged and exact-main reconciliation completes.

Historical `protocols/v1.12.0/**` and `release-locks/v1.12.0.sha256` remain immutable.
