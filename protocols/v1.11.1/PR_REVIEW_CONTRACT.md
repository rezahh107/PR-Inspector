# PR Review Contract

**Version:** 1.11.1  
**Status:** immutable corrected-activation patch snapshot  
**Default authority:** read-only review  
**Canonical source artifact:** `review-package.json`  
**Canonical decision projection:** `DECISION_PROJECTION.json`

## 1. Patch purpose

v1.11.1 completes the intended v1.11 activation. It preserves dual-profile intake, evidence collection, provenance, Head-drift handling, bot-review reconciliation, technical/governance separation, and all v1.11.0 security boundaries. It removes the remaining independent Candidate output authority introduced before activation.

Unchanged v1.11.0 policy, schema, registry, and template material incorporated byte-for-byte into this snapshot remains normative. This patch file and the modified v1.11.1 policy files control when they differ.

## 2. Decide once

`review-package.json` is the sole review source of truth. After active schema and semantic validation, `pr_inspector.decision_projection.project_decision` is the sole active projection authority.

After the canonical package boundary, all authoritative processing is exactly:

```text
review-package.json
→ official project_decision
→ official derived outputs
→ official artifact validation
→ VerifiedReviewCompletion
→ official_owner_delivery
```

No Candidate-compatible module may independently project, render, build, verify, compose, or publish owner-facing output.

## 3. Candidate compatibility boundary

`pr_inspector.candidate_v1_11` is compatibility-only. It may expose allowlisted pre-package helpers for intake, verified repository and live-Head identity, strict-after-minimal Head-drift orchestration, review-surface pagination and annotation provenance, bot-suggestion reconciliation, sealed governance-evidence adaptation, and binding a verified official minimal completion for same-Head reuse.

Candidate output symbols are unsupported. Direct calls fail closed with a deterministic migration error. They must not return bytes, projections, manifests, or partial owner text.

## 4. Dual-profile semantics

`inspection_profile` is independent from review mode. `minimal` is the default. Minimal records governance as `NOT_REQUESTED`; missing governance evidence cannot rewrite technical findings or create technical repair authority. `strict` is additive, fail-closed, and may reuse only a verifier-created same-repository, same-PR, same-Head official minimal completion.

## 5. Prompt semantic completeness

A prompt-required `NEXT_ACTION_PROMPT.en.md` must contain exactly one structured `[CANONICAL ACTION CONTRACT]` derived from the package and projection. Byte/hash parity is necessary but not sufficient.

The structured contract binds protocol version, repository, PR, exact Head, review validity, package hash, profile, action kind, recipient, modification authority, prompt kind, reasons, Findings, evidence, required actions/tests, mandatory re-review, profile-command separation, and prohibited actions.

`repair` and `repair_and_verify` require a bounded operational subject. `verify`, human/specialist review, and `rerun_review` cannot authorize modification. Governance-only gaps never create technical repair authority. Generic prose, the historical Candidate placeholder, heading-only content, missing fields, or profile commands inside the prompt fail closed even when hashes are correct.

## 6. Atomic owner delivery

`official_owner_delivery` is the sole prompt-required owner-facing accessor. It accepts only `VerifiedReviewCompletion`. `official_owner_result` fails when a prompt is required. Profile commands are retrieved separately through `official_owner_profile_commands` and are never appended to the action prompt or owner delivery.

## 7. Integration contract

External integrations presenting an official result must use `VerifiedReviewCompletion` and `official_owner_delivery`. Candidate output accessors, manual concatenation, reconstructed or summarized prompts, and later-delivery promises are unsupported.

## 8. Historical activation closure

PR #22 introduced the incomplete Candidate output path; PR #26 activated v1.11.0 without convergence; PR #28 completed only the official side. v1.11.1 preserves useful pre-package helpers and eliminates independent post-package Candidate output authority.
