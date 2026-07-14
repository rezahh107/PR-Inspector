# Personal Minimum-Security Governance Profile

## Scope

The active structured profile is `personal_ai_operated_strong_governance_minimum_security`. It is evaluated only by the canonical `project_decision` path from the versioned `review-package.json` carrier. Free text, helper output, manually edited projections, and caller-supplied dictionaries cannot upgrade an official decision.

## Default minimum

For a personal AI-operated repository, the minimum merge-control invariant is:

```text
sequence_ci_enforced OR verified_repository_hosted_enforcement
```

A dedicated GitHub App, App private key, exact App-ID check producer, branch protection, Rulesets, merge queue, CODEOWNERS approval, and repository-hosted exact-source enforcement are optional hardening by default. They become required when an explicit repository requirement, security activation trigger, external requirement, or stronger governance claim is present.

## Evidence boundary

`repository_settings_enforced` and `merge_authorized` are separate claims. They remain `not_claimed` or `rejected` unless a verifier-created opaque `VerifiedGovernanceEvidence` capability is exact-bound to the target repository, pull request, reviewed head, and the package `governance_evidence_id`.

Serialized JSON, booleans, PR prose, workflow output, and a matching-looking evidence identifier are not verified governance evidence.

## Fail-closed reasons

The canonical reason registry owns:

- `RSN-MERGE-ENFORCEMENT-MINIMUM-MISSING`;
- `RSN-REPOSITORY-HOSTED-ENFORCEMENT-REQUIRED`;
- `RSN-REPOSITORY-SETTINGS-CLAIM-UNVERIFIED`;
- `RSN-MERGE-AUTHORIZATION-CLAIM-UNVERIFIED`.

Each reason blocks Green and routes to non-modifying verification. The same profile projection is consumed by semantic validation, owner readiness, next-action routing, Technical Handoff, Owner Result, and the conditional action artifact.
