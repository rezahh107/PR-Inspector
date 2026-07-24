# PR Inspector Review Contract v1.12.0

Status: active corrected-activation patch.

## Purpose

v1.12.0 completes the intended v1.11 dual-profile activation without changing the technical/governance domain split. It closes the historical PR #22 Candidate output defect, the PR #26 activation gap, and the PR #28 residual parallel-authority gap.

## Canonical boundary

The caller supplies only `ReviewRequest` and bounded `ReviewAssessment`. The official runtime collects `ReviewFacts`, loads `ProtocolContext`, and invokes the sole `assemble_review_package` function. `review-package.json` is therefore an official output, not an authoritative input.

```text
ReviewRequest + ReviewAssessment
→ internal OfficialReviewRuntime factory
→ verified ProtocolContext + complete paginated GitHub collection
→ ReviewFacts + explicit external-review reconciliation
→ assemble_review_package()
→ CanonicalReviewPackage
→ project_decision
→ build_review_artifacts
→ validate_directory
→ VerifiedReviewCompletion
→ official_owner_delivery
```

There is one package assembler, one canonical projection authority, one artifact builder, one bundle validator, and one owner-delivery authority. Public `complete_review` accepts no evidence source, facts, live-Head object, or protocol context. A private `_complete_review_with_runtime` seam exists only for deterministic internal tests.

All check runs, issue comments, review submissions, and inline review comments are enumerated through bounded pagination. Missing configured required checks are represented as required `UNKNOWN` checks; incomplete enumeration fails assembly. Every collected external review source must receive an explicit bounded disposition before reconciliation is `COMPLETE`; otherwise technical Green is blocked.

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

`protocols/v1.11.1/*` and `release-locks/v1.11.1.sha256` are immutable historical artifacts. `v1.12.0` introduces evidence-bound package issuance and does not retroactively reinterpret historical packages or receipts.


## Review-package authority boundary

The v1.12 runtime uses ordinary typed immutable values and one internally constructed runtime. Machine facts, reviewer assessment, deterministic derivations, and protocol metadata are explicitly classified by `FIELD_AUTHORITY`. A raw file, path, mapping, arbitrary JSON object, or prebuilt package cannot enter official completion. The old signature returns `PRI-PACKAGE-AUTHORITY-001`.
