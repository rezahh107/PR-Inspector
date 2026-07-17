# Canonical Artifact and Official-Output Boundary

Status: v1.11.1 corrected activation completion is implemented on this pull-request head and pending independent review; activation remains determined by live `main`.

```yaml
active_protocol: v1.11.1
implementation_state: v1.11.1_output_authority_consolidation_pending_independent_review
canonical_output_boundary: implemented
publication_commit_point: implemented
verified_byte_snapshot_accessors: implemented
governance_code_boundary: implemented
candidate_pre_package_compatibility: implemented
candidate_independent_output_authority: removed
prompt_semantic_completeness: implemented
repository_settings_enforcement: insufficient_evidence
confirmed_merged_implementation_findings_at_audit_start: none
closure_pr_review_state: pending_independent_review
live_review_thread_state: not_asserted_by_static_document
bot_commented_feedback: not_approval
closure_status: profile_implementation_complete_pending_independent_review
```

GitHub repository settings remain a separate administrative evidence boundary. This branch does not claim it is independently reviewed, approved, merge-authorized, or merged. No additional runtime implementation defect was confirmed outside the bounded activation/output-authority scope.

## Supported path

`complete_review` or `verify_completed_review` produces `VerifiedReviewCompletion`. Owner-facing prompt-required output is returned only by `official_owner_delivery`; profile commands are returned separately by `official_owner_profile_commands`.

`pr_inspector.candidate_v1_11` is pre-package compatibility only. Legacy Candidate projection, rendering, artifact generation, artifact verification, and unverified owner composition raise deterministic migration errors. A compatibility owner-delivery call delegates only from a genuine verified completion.

## Semantic boundary

Artifact hashes and deterministic bytes remain mandatory. In addition, `validate_prompt_semantics` rejects non-actionable prompt-required output, including the PR #22 placeholder, generic prose, missing identity, missing action routing, missing reason codes/findings/tests, missing rereview, modification authority leaks, governance-only repair authority, and embedded profile commands.

## External integration obligation

External integrations must use `VerifiedReviewCompletion` and `official_owner_delivery`. Manual concatenation, Candidate output accessors, reconstructed prompts, summaries, truncation, and later-delivery promises are unsupported. Repository tests enforce the adapter contract; actual external orchestration execution remains separately verifiable evidence.
