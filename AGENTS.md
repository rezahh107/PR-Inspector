# Repository Operating Instructions

## Active protocol
`v1.13.0` is selected by `CURRENT_VERSION`. The model-facing and runtime coordination SSOT is `protocols/v1.13.0/functional-runtime-contract.json`.

## Review startup
Read only `runtime_bootstrap_inputs` from `protocol-manifest.yaml`. Per-review startup must perform zero Inspector self-verification network calls and must not run `validate_repository` or scan release locks.

## Maintenance
Released protocol directories and release locks are immutable. Create a successor version for protocol changes. Full repository/release validation remains CI/maintenance-only.

Before publishing changes run:

```bash
python scripts/validate_runtime_contract.py
python scripts/validate_planning_governance.py --check-static
python scripts/validate_repository_v2.py
python -m pytest
```

Preserve exact target identity, complete evidence enumeration, fail-closed unknowns, `project_decision`, canonical bytes, atomic publication, live-Head rechecks, `VerifiedReviewCompletion`, and `official_owner_delivery`.
