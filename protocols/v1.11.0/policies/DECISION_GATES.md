# Deterministic Decision Gates

## One authoritative projection

`pr_inspector.decision_projection.project_decision` is the only active v1.9 implementation that converts structured package fields into technical status, owner readiness, reason codes, recipient, authority, and prompt routing. `semantic_v2`, renderers, validators, and scripts consume it. No component may parse free text to derive status or action.

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

Explicit `unverified_areas`, structured `required_actions`, and approval requirements affect owner readiness and next action without rewriting the technical status. This preserves the distinction between technical readiness and practical merge readiness.

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

The projection action `merge_now` means only that package-level technical conditions have no remaining canonical action. It is not `merge_authorized`. Final authorization is a later lifecycle gate requiring authoritative exact-head checks, independent approvals, applicable specialist evidence, and verified repository settings.

## Candidate v1.11.0 decision-domain gates

Reason codes are domain-scoped. Technical reason codes may affect only `technical_decision.status`; governance reason codes may affect only `governance_decision.status` and `governance_follow_up`.

Critical candidate gates:

- `PRI-111-PROFILE-001`: absent explicit profile with a PR URL selects `inspection_profile: minimal`.
- `PRI-111-GOV-001`: governance reason codes must not alter technical status.
- `PRI-111-BOT-001`: incomplete bot-review collection prevents complete technical Green.
- `PRI-111-BOT-002`: accepted bot suggestions without an independently valid linked Finding do not authorize repair.
- `PRI-111-REUSE-001`: strict reuse must verify target identity, Inspector identity, artifact hashes, and exact head; head drift triggers minimal refresh before strict.
