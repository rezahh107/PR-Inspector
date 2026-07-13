# Canonical Artifact and Official-Output Boundary

Status: `v1.9.1` is a candidate protocol revision on a Draft PR branch. Live `main` at the inspected base remains `v1.9.0`.

## Current candidate status

```yaml
selected_protocol: v1.9.1
live_main_protocol_at_base: v1.9.0
live_main_base_sha: 65e6b1b46c3e8da7c782c666cd3562947f2b7923
implementation_state: candidate_on_draft_pr
ssot_version: v1.0.2
security_profile: personal_ai_operated_strong_governance_minimum_security
sequence_ci_enforced: required_for_default_minimum
repository_hosted_enforcement: optional_hardening
github_app_exact_source_enforcement: optional_hardening
repository_settings_enforced: not_claimed
merge_authorized: not_claimed
merged: false
independent_review_state: pending_fresh_exact_head_review
```

The candidate preserves exact-head identity, stale-on-change invalidation, independent review, evidence provenance, Scope Gate, Progress Gate, sequence validation, post-merge verification, secret boundaries, and destructive-action boundaries.

`GREEN_MERGE_RECOMMENDED` is a bounded technical recommendation. It does not prove repository settings enforcement. It does not prove merge authorization. It does not prove that merge occurred.

No GitHub App, private key, branch protection, repository ruleset, merge queue, CODEOWNERS rule, check publisher, secret, or repository setting is created by this revision.

## Existing canonical-output guarantees

The v1.9 canonical-output boundary, atomic publication commit point, quarantine-first rollback, verified-byte snapshot accessors, and governance evidence capability remain unchanged. The candidate adds only the smallest profile and claim-classification layer required by AI Authority Deterministic Governance v1.0.2.

## Activation boundary

The Draft PR is not an activation receipt. A fresh independent review must inspect the exact final head. Merge, if later authorized and performed, must be verified on live `main` before `v1.9.1` is reported active.
