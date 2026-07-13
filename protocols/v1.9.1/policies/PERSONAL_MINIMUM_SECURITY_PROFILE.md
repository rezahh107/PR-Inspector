# Personal AI-Operated Minimum-Security Profile

**Profile:** `personal_ai_operated_strong_governance_minimum_security`  
**SSOT alignment:** AI Authority Deterministic Governance v1.0.2  
**Security posture:** `minimum_security`

## Purpose

This profile preserves strong evidence, exact-head, scope, progress, stale-on-change,
independent-review, and post-merge controls without treating enterprise GitHub
administration as a prerequisite for a bounded technical recommendation.

## Decision vocabulary

The following states are separate and MUST NOT be collapsed:

1. `technical_green` — canonical review evidence supports
   `GREEN_TECHNICALLY_READY`.
2. `GREEN_MERGE_RECOMMENDED` — bounded technical recommendation for the exact
   reviewed head and reviewed scope.
3. `repository_settings_enforced` — authoritative GitHub settings evidence proves
   an independently blocking repository-hosted rule.
4. `merge_authorized` — every active stronger authorization predicate is
   authoritatively satisfied.
5. `merged` — GitHub authoritatively reports the merge event.

No earlier state proves a later state.

## Default classification

Unless a stronger requirement is activated, the following controls are
`optional_hardening` and their absence does not create a Critical or High blocker
for technical review or `GREEN_MERGE_RECOMMENDED`:

- dedicated GitHub App;
- GitHub App private key;
- Check Runs tied to an exact numeric `app_id`;
- branch protection;
- repository rulesets;
- merge queue;
- CODEOWNERS approval;
- repository-hosted exact-source enforcement.

The same controls may be recorded as `intentionally_out_of_scope` by a target
repository. Neither classification means `missing`, `failed`, or `security_gap`.

## AIGOV-MERGE-001

Minimum enforcement is:

```text
sequence_ci_enforced
OR
repository-hosted enforcement
```

For this default profile:

```text
preferred minimum: sequence_ci_enforced
repository-hosted enforcement: optional_hardening
```

A dedicated GitHub App is therefore not an independent prerequisite when valid
sequence enforcement exists.

## Activation triggers

Repository-hosted enforcement becomes `required` only when at least one of these
is present:

- an explicit repository requirement;
- an activated security-profile trigger;
- an external legal, contractual, organizational, or production requirement;
- a repository claim that repository-hosted enforcement is active;
- a claim of `repository_settings_enforced` or `merge_authorized`.

A missing required control remains blocking for the stronger recommendation or
claim. Activation does not weaken or replace any exact-head or evidence predicate.

## Claim boundary

`repository_settings_enforced` and `merge_authorized` can be `verified` only from
the existing opaque, verifier-created `VerifiedGovernanceEvidence` capability.
A boolean, mapping, prose statement, PR body, fixture, or caller-authored record is
rejected. An absent claim is `not_claimed`.

`merged` is never projected from review artifacts.

## Preserved guarantees

This profile does not weaken:

- exact reviewed-head identity;
- stale review invalidation;
- independent review;
- evidence classification and provenance;
- rejection of self-asserted truth;
- Scope Gate;
- Progress Gate;
- sequence validation;
- post-merge verification;
- secret handling;
- destructive-action boundaries.
