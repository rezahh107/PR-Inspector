# Deterministic Decision Gates

## One authoritative projection

`pr_inspector.decision_projection.project_decision` is the only active v1.9.1 implementation that converts structured package fields into technical status, owner readiness, reason codes, recipient, authority, and prompt routing. `semantic_v2`, renderers, validators, and scripts consume it. No component may parse free text to derive status or action.

The personal minimum-security assessment is a separate deterministic projection. It may classify repository-hosted controls as optional hardening without rewriting technical evidence, and it may block only the bounded merge recommendation or a stronger unsupported claim.

## Registered reason evaluation

Evaluate predicates in the versioned order of `registries/DECISION_REASON_REGISTRY.yaml`.

### Red technical effects

- explicit red-gate flag;
- failed required check;
- supported Critical finding;
- reproduced High finding.

### Yellow technical effects

- unresolved required check;
- High code-supported or hypothesis finding;
- blocking Medium finding;
- blocking hypothesis;
- not-assessable finding;
- partial review;
- non-current review;
- unreviewed high-risk area;
- incomplete coverage;
- missing, unsatisfied, or unsupported intent evidence;
- validated repair handoff;
- accepted external repair suggestion.

### Action-only reasons

Explicit `unverified_areas`, structured `required_actions`, approval requirements, and security-profile enforcement reasons affect owner readiness and next action without rewriting technical status. This preserves the distinction between technical readiness, bounded merge recommendation, and stronger repository claims.

The following profile reasons are action-only:

- `RSN-MERGE-ENFORCEMENT-MINIMUM-MISSING`;
- `RSN-REPOSITORY-HOSTED-ENFORCEMENT-REQUIRED`;
- `RSN-REPOSITORY-SETTINGS-CLAIM-UNVERIFIED`;
- `RSN-MERGE-AUTHORIZATION-CLAIM-UNVERIFIED`.

## Status precedence

1. Any registered Red effect → `RED_DO_NOT_MERGE`.
2. Otherwise any registered Yellow effect → `YELLOW_CHANGES_OR_VERIFICATION_REQUIRED`.
3. Otherwise → `GREEN_TECHNICALLY_READY`.

The package's `decision.technical_status` must equal this projection or `PRI-STATUS-001` is emitted.

## Action precedence

1. Non-current validity → `rerun_review`.
2. Non-Green with repair and verify reasons → `repair_and_verify`.
3. Non-Green with repair reasons → `repair`.
4. Non-Green with verification reasons → `verify`.
5. Technically Green with structured verification/pending-action reason → `verify`.
6. Otherwise route the independent approval requirement to `owner_confirmation`, `human_technical_review`, or `specialist_review`.
7. Only current Green with no pending action and no additional approval → `merge_now`.

A non-Green state without a registered repair or verification reason is a projection error and fails closed.

## AIGOV-MERGE-001 profile projection

For the default profile, the bounded recommendation requires:

```text
sequence_ci_enforced OR repository-hosted enforcement
```

Valid sequence enforcement satisfies the minimum. Repository-hosted enforcement and a dedicated GitHub App remain optional hardening unless an explicit requirement, activated trigger, external obligation, or stronger claim makes them required.

## Authority invariants

- `merge_now`: no prompt and no code authority.
- `owner_confirmation`: no model prompt.
- `human_technical_review` and `specialist_review`: human handoff only; models cannot satisfy approval.
- `verify`: reviewer model; no patch, commit, refactor, or behavior change.
- `repair`: implementer model; bounded same-PR repair.
- `repair_and_verify`: bounded repair plus separate evidence obligations.
- `rerun_review`: reviewer model; previous findings are non-authorizing.

Any route divergence is rejected before artifact acceptance.

## Merge-readiness terminology

The projection action `merge_now` and the profile result `GREEN_MERGE_RECOMMENDED` mean only that bounded technical conditions have no remaining canonical action for the exact reviewed head and scope. Neither proves `repository_settings_enforced`, `merge_authorized`, or `merged`.

Final stronger claims continue to require their authoritative lifecycle and GitHub evidence.
