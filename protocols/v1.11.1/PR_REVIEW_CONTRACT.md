# PR Inspector Review Contract v1.11.1

Status: active corrected-activation patch.

## Purpose

v1.11.1 completes the intended v1.11 dual-profile activation without changing the technical/governance domain split. It closes the historical PR #22 Candidate output defect, the PR #26 activation gap, and the PR #28 residual parallel-authority gap.

## Canonical boundary

Candidate-compatible helpers MAY parse `حداقلی` / `سخت گیرانه`, bind verified target identity, collect sealed review surfaces, preserve annotation provenance, and orchestrate one bounded Head-drift refresh only before a canonical `review-package.json` exists.

After the canonical package exists, the only authoritative chain is:

```text
review-package.json
→ pr_inspector.decision_projection.project_decision
→ pr_inspector.derived_outputs.build_review_artifacts
→ pr_inspector.validation_v2.validate_directory
→ VerifiedReviewCompletion
→ official_owner_delivery
```

There is one canonical projection authority, one prompt renderer, one artifact builder, one artifact verifier, and one prompt-required owner-delivery authority.

## Dual profiles

`inspection_profile` defaults to `minimal`. Minimal assesses technical quality and records governance as `NOT_REQUESTED`. Strict is an optional fail-closed governance extension. Governance evidence cannot rewrite technical findings, technical status, technical action authority, or repair scope.

## Candidate compatibility

`pr_inspector.candidate_v1_11` is a bounded pre-package compatibility module. Its allowlisted intake, target, live-Head, review-surface, provenance, and evidence helpers remain supported. Legacy Candidate projection, rendering, artifact generation, artifact verification, and owner-output functions MUST fail closed with a deterministic migration error. `candidate_owner_delivery_stdout` MAY delegate only from a genuine `VerifiedReviewCompletion` and MUST return exact `official_owner_delivery` bytes.

## Prompt completeness

A prompt-required `NEXT_ACTION_PROMPT.en.md` must be both byte-canonical and semantically actionable. Independent validation binds it to repository, PR, exact reviewed Head, protocol version, action kind, recipient, modification authority, reason codes, affected findings, evidence references, required tests, prohibitions, and mandatory fresh PR Inspector re-review. A non-empty generic prompt is invalid. The historical placeholder `Repair independently validated technical findings before rereview.` is forbidden.

`verify` and `rerun_review` never authorize modification. `rerun_review` requests a fresh review. Governance-only gaps never create a technical repair prompt.

## Owner delivery

`official_owner_delivery(VerifiedReviewCompletion)` is the sole prompt-required owner-facing accessor. `official_owner_result` fails closed whenever a prompt is required. Manual concatenation and reconstructed prompts are unsupported. `OWNER_PROFILE_COMMANDS.fa.txt` remains a separate verified artifact and is retrieved only through `official_owner_profile_commands`; it is never appended to the action prompt.

## Integration contract

External integrations MUST consume verified completion and official accessors. Candidate output accessors, direct artifact concatenation, manually reconstructed prompts, and model-authored substitutes are not supported. External execution evidence remains separate from repository-enforceable acceptance tests.

## Historical review provenance

PR #12 is historical provenance only. Its recorded review state `COMMENTED` did not prove completion, approval, or merge authorization. Historical comments cannot replace current exact-head validation or independent review.

## Version integrity

`protocols/v1.11.0/*` and `release-locks/v1.11.0.sha256` are immutable. Files in this snapshot that are byte-identical to v1.11.0 inherit unchanged normative behavior; v1.11.1 changes only activation/output authority, semantic prompt completeness, and compatibility boundaries.
