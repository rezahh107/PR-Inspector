# Personal Review Quality Foundation

Status: repository-required planning infrastructure.

This document is required repository planning infrastructure for personal-project PR review quality. It is intentionally kept outside the active protocol `load_order`.

Boundary rules:

- This document is required repository planning infrastructure.
- It is not part of the active protocol `load_order`.
- It defines no active review rule.
- Its seed rules are planning-only until promoted through a new protocol snapshot, schema/validator/fixture, and release lock.
- Repository validation protects this document from deletion/drift and prevents accidental promotion into the active protocol `load_order`.

Repository validation keeps this document guarded and outside the active protocol `load_order`.

This document does not define review-package schema fields and does not override `BOOTSTRAP.md`, `protocol-manifest.yaml`, the active `PR_REVIEW_CONTRACT.md`, active policies, active schemas, deterministic validators, or release locks.

If this document conflicts with the active protocol, the active protocol wins.

## Existing coverage summary

The active protocol already owns evidence, identity, coverage, decisions, trust boundaries, deterministic rendering, schema validation, semantic validation, and release locks. This document must not duplicate those sources of truth.

## Quality attributes

These attributes are review priorities, not active review rules and not new schema fields.

- Intent fit: connect implementation evidence to intended behavior.
- Correctness: back claims with evidence or explicit uncertainty.
- Regression risk: compare changed behavior with tests, callers, contracts, schemas, configuration, and state.
- Contract / schema / state consistency: keep manifests, schemas, locks, protocol files, validators, fixtures, and rendered artifacts aligned.
- Test or validator adequacy: use relevant tests, validators, CI, or explicit `NOT_ASSESSABLE` reasoning for material behavior changes.
- Research-backed judgment: verify unstable external behavior before making current best-practice claims.

## Correctness / intent-fit pilot seed rules

These seed rules define no active review rule. They are planning-only until promoted through a new protocol snapshot, schema/validator/fixture, and release lock.

### COR-INTENT-001 — Intent fit

Purpose: A PR review must connect implementation evidence to the stated intended behavior.
Current status: Planning-only seed rule; not active protocol enforcement.

### COR-REG-001 — Regression risk

Purpose: Changed behavior must not contradict existing tests, schemas, contracts, documented state, or compatibility expectations without being called out.
Current status: Planning-only seed rule; not active protocol enforcement.

### COR-STATE-001 — Contract, schema, and state consistency

Purpose: State, manifest, status, schema, protocol, release locks, and generated artifacts touched by a PR must remain mutually consistent.
Current status: Planning-only seed rule; not active protocol enforcement.

### COR-TEST-001 — Test or validator adequacy

Purpose: A material behavior change must have a relevant test, validator, CI check, or explicit `NOT_ASSESSABLE` reason.
Current status: Planning-only seed rule; not active protocol enforcement.

### COR-RESEARCH-001 — Research-backed external claims

Purpose: Current best-practice or external-tooling claims must be grounded in source/web research when current behavior matters.
Current status: Planning-only seed rule; not active protocol enforcement.

## Repository validation boundary

Repository validation treats this file as required repository planning infrastructure. It checks that the boundary statements and seed-rule anchors remain present. It also prevents accidental promotion into the active protocol `load_order`.

Validation does not make this document part of the active protocol and does not make the seed rules active review rules.

## Deliberately deferred

- No security specialty pilot is introduced here.
- No broad checklist framework is introduced here.
- No new evidence taxonomy, approval taxonomy, or decision-gate taxonomy is introduced here.
- No coverage-map YAML is introduced until there are concrete rule carriers worth tracking.
- No active protocol behavior is changed by this repository-required planning infrastructure.
