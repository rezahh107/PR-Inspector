# Personal Review Quality Foundation

Status: repository-required planning infrastructure.

This document is required repository planning infrastructure for personal-project PR review quality. It is intentionally kept outside the active protocol `load_order`.

Boundary rules:

- This document is required repository planning infrastructure.
- It is not part of the active protocol `load_order`.
- It defines no active review rule.
- Its seed rules are planning-only until promoted through a new protocol snapshot, schema/validator/fixture, and release lock.
- Repository validation protects this document from deletion/drift and prevents accidental promotion into the active protocol `load_order`.

This document does not define review-package schema fields and does not override `BOOTSTRAP.md`, `protocol-manifest.yaml`, the active `PR_REVIEW_CONTRACT.md`, active policies, active schemas, deterministic validators, or release locks.

If this document conflicts with the active protocol, the active protocol wins. A future patch may promote selected rules into a new versioned protocol only through the normal release process: new protocol snapshot, schema/validator/fixture updates, and a matching release lock.

## Why this exists

The active protocol already defines evidence, identity, coverage, decisions, trust boundaries, and deterministic rendering. This file avoids duplicating those sources of truth. It only records the first quality model and correctness pilot seed so later work can harden it deliberately.

## Overlap scan

Concept: Quality attribute model for personal PR inspection
Existing coverage: `PR_REVIEW_CONTRACT.md` covers purpose, evidence, coverage, decisions, and enforcement status. `REVIEW_PIPELINE.md` already requires previous, intended, and implemented behavior plus impact-radius inspection.
Gap: No compact quality model explains the personal-project review priorities across intent fit, correctness, regression risk, consistency, validation adequacy, and research-backed judgment.
Decision: add_new_minimal_doc
Reason: A short repository-required planning reference prevents duplicate active policy while giving later protocol work a stable starting point.
Files affected: `docs/QUALITY_ATTRIBUTE_MODEL.md`

Concept: Rule authoring standard for future specialty rules
Existing coverage: The active contract lists canonical rule IDs and the maintenance guide requires tests for changed rules.
Gap: No lightweight seed-rule shape exists for future correctness specialty rules.
Decision: add_new_minimal_doc
Reason: Define only the minimal seed-rule shape here; do not add a broad checklist or specialty framework yet.
Files affected: `docs/QUALITY_ATTRIBUTE_MODEL.md`

Concept: Technical autonomy and mandatory research policy
Existing coverage: Source precedence, evidence rules, capability declaration, and trust boundaries already exist in active protocol files.
Gap: The active protocol does not yet explicitly say when external/source research is required for unstable best-practice claims.
Decision: add_new_minimal_doc
Reason: Record as a planning-only candidate without claiming active review-rule or validator enforcement.
Files affected: `docs/QUALITY_ATTRIBUTE_MODEL.md`

Concept: Correctness / intent-fit / regression pilot foundation
Existing coverage: `change_summary`, decision gates, coverage fields, required checks, findings, and semantic validation already carry parts of this behavior.
Gap: No named seed rules connect these carriers into a future specialty pilot.
Decision: add_new_minimal_doc
Reason: Add seed rules as planning-only / partial-enforcement candidates only.
Files affected: `docs/QUALITY_ATTRIBUTE_MODEL.md`

Concept: Specialty rule coverage lite
Existing coverage: No PR-Inspector coverage-map source exists. Prompt-Pipeline has a separate behavioral coverage pattern, but it is not PR-Inspector source of truth.
Gap: A future coverage map may be useful after rules have concrete carriers.
Decision: defer
Reason: Adding a coverage YAML now would create bureaucracy before the first PR-Inspector specialty rules are enforceable.
Files affected: none

## Quality attributes

These attributes are review priorities, not active review rules and not new schema fields.

| Attribute | Meaning | Existing carrier | Current enforcement |
|---|---|---|---|
| Intent fit | The implementation evidence must connect to the stated intended behavior. | `change_summary`, findings, owner card, handoff | Partially enforceable by required schema fields and decision gates. |
| Correctness | Claims must be backed by code, CI, execution, documentation, metadata, or explicit uncertainty. | evidence records, checks, findings | Partially enforceable by schema and semantic validators. |
| Regression risk | Changed behavior must be checked against tests, callers, schemas, contracts, configuration, state, and compatibility concerns. | pipeline impact-radius steps, checks, findings, required actions | Partially enforceable through review fields; not yet automatically proven. |
| Contract / schema / state consistency | Manifest, state, schema, protocol, and rendered artifacts must not contradict each other. | release locks, schema validation, render validation, repository validation | Validator-backed for repository/protocol artifacts. |
| Test or validator adequacy | Material behavior changes need a relevant test, validator, CI check, or explicit `NOT_ASSESSABLE` reason. | checks, evidence records, findings, unverified areas | Partially enforceable; adequacy is still reviewer-judged. |
| Research-backed judgment | Current or unstable external behavior must be verified before making a best-practice claim. | capabilities, evidence records, findings, unverified areas | Planning-only until promoted through a new protocol snapshot, schema/validator/fixture, and release lock. |

## Technical autonomy and research candidate

For personal-project reviews, the reviewer may choose the practical inspection path, depth, commands, and evidence collection strategy. Autonomy never authorizes fabricated evidence, hidden execution, target-repository writes, weakened trust boundaries, or unsupported Green decisions.

The following candidate defines no active review rule. It is planning-only until promoted through a new protocol snapshot, schema/validator/fixture, and release lock.

Candidate research rule for a future protocol version:

When a finding, recommendation, or best-practice claim depends on unstable external behavior, APIs, library versions, CI behavior, GitHub behavior, or current tooling guidance, the reviewer must collect source/web research evidence when the capability is available. If research is unavailable or not performed, the claim must be labeled as `HYPOTHESIS` or `NOT_ASSESSABLE`, and any blocking uncertainty must prevent Green.

Do not claim source/web research occurred unless the review package includes an evidence record or explicit limitation that supports that claim.

## Correctness / intent-fit pilot seed rules

These seed rules define no active review rule. They are planning-only until promoted through a new protocol snapshot, schema/validator/fixture, and release lock. They are starting candidates for a later versioned protocol or validator-backed pilot.

### COR-INTENT-001 — Intent fit

Purpose: A PR review must connect implementation evidence to the stated intended behavior.
Activation trigger: Any PR with changed runtime behavior, schema behavior, workflow behavior, rendered output, or state handling.
Valid evidence shape: `change_summary` plus code, CI, execution, documentation, or metadata evidence tied to the reviewed head SHA.
What must not be claimed: Do not claim the implementation matches intent when only the PR title, PR body, or author explanation was read.
Decision impact: Unsupported or contradictory intent fit should become Yellow or Red according to existing decision gates.
Current status: Planning-only seed rule. Related active carriers are partially enforceable by schema fields and decision gates, but this seed rule is not active protocol enforcement.

### COR-REG-001 — Regression risk

Purpose: Changed behavior must not contradict existing tests, schemas, contracts, documented state, or compatibility expectations without being called out.
Activation trigger: Any change touching behavior, public interfaces, data formats, configuration, validators, renderers, workflows, or state files.
Valid evidence shape: Code-path reads, test/CI evidence, schema/contract comparison, or explicit unverified-area entries.
What must not be claimed: Do not claim no regression risk simply because tests pass or the diff is small.
Decision impact: A material unresolved regression risk prevents Green; a supported contradiction may become Red through existing gates.
Current status: Planning-only seed rule. Related active carriers are partially enforceable through coverage, findings, required checks, and red/yellow gates, but this seed rule is not active protocol enforcement.

### COR-STATE-001 — Contract, schema, and state consistency

Purpose: State, manifest, status, schema, protocol, release locks, and generated artifacts touched by a PR must remain mutually consistent.
Activation trigger: Any PR touching version pointers, manifests, schemas, locks, fixtures, templates, renderers, validators, or status/state files.
Valid evidence shape: Repository validator output, release-lock verification, schema validation, deterministic render comparison, and direct file evidence.
What must not be claimed: Do not claim consistency when validators were not run or when generated artifacts were manually edited without comparison.
Decision impact: Inconsistency in canonical artifacts blocks Green and may be Red if it falsifies evidence or breaks required protocol state.
Current status: Planning-only seed rule. Related active repository/protocol artifacts are validator-backed, but this seed rule is not active protocol enforcement.

### COR-TEST-001 — Test or validator adequacy

Purpose: A material behavior change must have a relevant test, validator, CI check, or explicit `NOT_ASSESSABLE` reason.
Activation trigger: Any behavior-changing PR, including prompt/protocol behavior, validators, renderers, schemas, CI, or automation behavior.
Valid evidence shape: Passing or failing check evidence, validator output, fixture evidence, or a finding explaining why verification is not assessable.
What must not be claimed: Do not claim validation adequacy from unrelated tests, stale CI, or commands not tied to the reviewed head SHA.
Decision impact: Missing relevant validation is Yellow unless the missing safeguard or falsified evidence triggers Red.
Current status: Planning-only seed rule. Related active carriers are partially enforceable through checks, evidence records, and decision gates, but this seed rule is not active protocol enforcement.

### COR-RESEARCH-001 — Research-backed external claims

Purpose: Current best-practice or external-tooling claims must be grounded in source/web research when current behavior matters.
Activation trigger: Claims about unstable external APIs, dependencies, CI behavior, GitHub behavior, package behavior, standards, security guidance, or current best practices.
Valid evidence shape: Documentation, metadata, or source evidence with reference, excerpt, limitations, and reviewed context.
What must not be claimed: Do not present stale memory or uncited assumptions as current best practice.
Decision impact: Blocking current-behavior uncertainty prevents Green; unsupported external claims must be downgraded to `HYPOTHESIS` or `NOT_ASSESSABLE`.
Current status: Planning-only seed rule; not active-protocol or validator-enforced.

## Repository validation boundary

Repository validation treats this file as required repository planning infrastructure. The validator protects this document from deletion/drift by checking that the boundary rules and seed-rule anchors remain present. It also prevents accidental promotion into the active protocol `load_order`.

Validation does not make this document part of the active protocol and does not make the seed rules active review rules.

## Deliberately deferred

- No security specialty pilot is introduced here.
- No broad checklist framework is introduced here.
- No new evidence taxonomy, approval taxonomy, or decision-gate taxonomy is introduced here.
- No coverage-map YAML is introduced until there are concrete rule carriers worth tracking.
- No active protocol behavior is changed by this repository-required planning infrastructure.
