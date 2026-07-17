# Canonical Artifact and Official-Output Boundary

Status: v1.11.1 corrected activation implementation is complete on the implementation branch and pending exact-head CI plus independent review; activation remains determined by live `main`.

## Current closure status

```yaml
active_protocol: v1.11.1
implementation_state: v1.11.1_corrected_activation_pending_independent_review
baseline_main_head: f0f74bba89e4c85f4a4b10c706a2be2980d71c25
defect_lifecycle:
  introduced: PR_22
  activated: PR_26
  official_path_strengthened_but_candidate_preserved: PR_28
canonical_output_boundary: implemented
single_projection_authority: implemented
single_prompt_authority: implemented
single_verification_authority: implemented
single_owner_delivery_authority: implemented
semantic_prompt_completeness: implemented
candidate_pre_package_compatibility: implemented
candidate_output_authority: eliminated_fail_closed
profile_command_separation: implemented
publication_commit_point: implemented
verified_byte_snapshot_accessors: implemented
governance_code_boundary: implemented
repository_settings_enforcement: insufficient_evidence
closure_pr_review_state: pending_independent_review
live_review_thread_state: not_asserted_by_static_document
bot_commented_feedback: not_approval
external_chat_connector_acceptance: not_run
closure_status: implementation_complete_pending_exact_head_ci_and_independent_review
```

This document does not claim that the implementation branch is independently reviewed, approved, merge-authorized, or merged. GitHub repository settings remain a separate administrative evidence boundary.

## Defect closure

PR #22 introduced an isolated Candidate output stack with a generic placeholder prompt and independent owner-delivery composition. PR #26 activated v1.11.0 without consolidating that stack. PR #28 completed the official path but left Candidate output code importable.

v1.11.1 preserves only useful pre-package Candidate functionality: intake routing, verified target/live-Head identity, Head-drift handling, review-surface pagination, annotation provenance, bot reconciliation, sealed evidence adaptation, and binding of an official minimal completion for strict same-Head reuse.

Candidate projection, prompt rendering, artifact generation, artifact verification, manifest generation, owner-facing composition, and prompt-required stdout no longer operate independently. Legacy symbols raise a deterministic migration error and are excluded from the supported export list.

## Supported-path map

| path | classification | boundary |
|---|---|---|
| `scripts/render_review_v2.py` | official supported entry point | Produces only verified official owner delivery on stdout. |
| `pr_inspector.official_review.complete_review` | official completion API | Validates, renders, publishes, re-verifies, and binds live Head identity. |
| `pr_inspector.decision_projection.project_decision` | sole projection authority | Derives all status/action/profile/governance routing. |
| `pr_inspector.derived_outputs.build_review_artifacts` | sole active artifact builder | Builds official projection, owner result, profile commands, prompt, and manifest. |
| `pr_inspector.prompt_semantics` | independent semantic prompt validator | Recomputes the structured action contract and rejects generic or authority-divergent prompts. |
| `pr_inspector.validation_v2.validate_directory` | sole official artifact-validation boundary | Enforces package semantics, deterministic bytes, prompt semantics, and manifest integrity. |
| `VerifiedReviewCompletion` | completion capability | Binds immutable artifact identities and live Head re-verification. |
| `official_owner_delivery` | sole prompt-required owner accessor | Returns exact owner result plus exact verified prompt. |
| `official_owner_profile_commands` | separate profile-command accessor | Never participates in prompt or owner-delivery composition. |
| `pr_inspector.candidate_v1_11` allowlist | pre-package compatibility | Intake/evidence/reconciliation only. |
| Candidate legacy output symbols | unsupported migration tombstones | Fail closed without returning output. |
| arbitrary chat/model prose | external boundary | Must be exercised separately; repository tests cannot prove compliance. |

## Prompt semantic invariant

Every prompt-required artifact contains exactly one `[CANONICAL ACTION CONTRACT]` JSON block derived from structured package and projection data. It binds repository, PR, exact Head, review validity, canonical package hash, profile, action kind, recipient, modification authority, prompt kind, reason codes/subjects, Findings, evidence references, required actions/tests, mandatory fresh re-review, profile-command separation, and prohibited actions.

The validator rejects the exact PR #22 placeholder, generic non-empty prompts, heading-only prompts, missing identity or action fields, missing reasons/Findings/tests, profile commands inside the prompt, modification authority in `verify` or `rerun_review`, repair language in fresh-review routing, governance-only technical repair, and hash-valid semantic incompleteness.

## External integration obligation

An external ChatGPT/project/connector integration presenting an official result must use `VerifiedReviewCompletion` and `official_owner_delivery`. Candidate output calls, compact prompt-required access, manual concatenation, independently reconstructed prompts, summarization, truncation, or later-delivery promises are unsupported.

Repository tests enforce the producer and included adapter. Actual external orchestration execution remains `NOT_RUN` until separately exercised and its displayed bytes are compared with official delivery.
