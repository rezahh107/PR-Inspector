# Repository Operating Instructions

## Active protocol
Resolve the active protocol from `CURRENT_VERSION`. The model-facing and runtime coordination SSOT is `protocols/<CURRENT_VERSION>/functional-runtime-contract.json`. A literal version in `AGENTS.md` must never be treated as an independent active-version authority.

## Review startup
Follow `BOOTSTRAP.md` as the per-review startup authority. Connector startup is retrieval-only and must not read `protocol-manifest.yaml`, run `validate_repository`, scan release locks, or perform Inspector self-verification.

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
