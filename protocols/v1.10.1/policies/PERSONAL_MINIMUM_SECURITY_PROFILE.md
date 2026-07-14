# Personal Minimum-Security Governance Profile

## Scope

The active structured profile is `personal_ai_operated_strong_governance_minimum_security`. It is evaluated only by the canonical `project_decision` path from the versioned `review-package.json` carrier. Free text, helper output, manually edited projections, caller-supplied dictionaries, and serialized capability lookalikes cannot upgrade an official decision.

## Default minimum

For a personal AI-operated repository, the minimum merge-control invariant is:

```text
verified_sequence_ci_enforcement OR verified_repository_hosted_enforcement
```

The package field `sequence_ci_enforced` is an untrusted claim. It contributes to the effective projection only when the official boundary receives a verifier-created opaque `VerifiedSequenceEnforcement` capability bound to the target repository, pull request, and exact reviewed head. The capability must be derived from the designated required check context `Validate rereview sequence enforcement`, bound to an exact App ID and verified successful on that exact head. A different required check and a bare `true` value both remain Yellow.

A dedicated GitHub App, App private key, exact App-ID check producer, branch protection, Rulesets, merge queue, CODEOWNERS approval, and repository-hosted exact-source enforcement are optional hardening by default. They become required when an explicit repository requirement, security activation trigger, external requirement, or stronger governance claim is present.

## Evidence boundary

`repository_settings_enforced` and `merge_authorized` are separate claims. They remain `not_claimed` or `rejected` unless a verifier-created opaque `VerifiedGovernanceEvidence` capability is exact-bound to the target repository, pull request, reviewed head, and the package `governance_evidence_id`.

The same opaque governance and sequence capabilities must be threaded through semantic status derivation, canonical projection generation, artifact rendering, directory validation, publication, final-byte bundle validation, and later completion re-verification. The capabilities are never serialized into `review-package.json` or generated artifacts.

Serialized JSON, booleans, PR prose, workflow output, matching-looking evidence identifiers, and caller-created dataclass lookalikes are not verified governance or sequence evidence.

## Fail-closed reasons

The canonical reason registry owns:

- `RSN-MERGE-ENFORCEMENT-MINIMUM-MISSING`;
- `RSN-REPOSITORY-HOSTED-ENFORCEMENT-REQUIRED`;
- `RSN-REPOSITORY-SETTINGS-CLAIM-UNVERIFIED`;
- `RSN-MERGE-AUTHORIZATION-CLAIM-UNVERIFIED`.

Each reason blocks Green and routes to non-modifying verification. The same profile projection is consumed by semantic validation, owner readiness, next-action routing, Technical Handoff, Owner Result, conditional action artifact, directory validation, and the official completion boundary.
