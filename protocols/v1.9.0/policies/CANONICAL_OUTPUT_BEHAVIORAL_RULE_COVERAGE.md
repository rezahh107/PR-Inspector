# Behavioral Rule Coverage — Canonical Output Completion

Version: `v1.9.0`  
Scope: official package-to-output orchestration, verified completion, atomic publication, quarantine-first rollback, and fail-closed user-facing output.  
Decision: `PASS` only while the focused adversarial suites and full repository validation pass on the exact active head.

This matrix applies Behavioral Rule Coverage v0.4.1. It does not make low-level renderers a security sandbox and does not claim external downstream enforcement. The supported official output boundary is `pr_inspector.official_review.complete_review`; lower-level projection and rendering functions remain compositional primitives and cannot by themselves prove completed official output.

| rule_id | concept | risk | prose_source | carrier | validator_rule | valid_fixture | invalid_fixture | CI_step | downstream_contract | session_scope | recovery_action | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `PRR-CANONICAL-PACKAGE-001` | Official completion requires a schema-valid and semantically valid canonical `review-package.json` bound to the caller-observed repository, PR, and head. | Critical | `protocols/v1.9.0/policies/CANONICAL_OUTPUT_BEHAVIORAL_RULE_COVERAGE.md#official-boundary` | canonical package bytes plus expected identity arguments | `complete_review`, `validate_package`, and `PRI-COMPLETE-007`; reject invalid semantics or identity mismatch before staging publication | `fixtures/golden-green/review-package.json` | `fixtures/canonical-output-enforcement/mutation-cases.json#manual_package_status_injection` | python -m pytest -q tests/test_canonical_output_enforcement.py | supported CLI and package API must use `complete_review` | per_artifact | block | ci_enforced |
| `PRR-CANONICAL-PROJECTION-001` | Status, approval, owner readiness, recipient, authority, and action routing come only from the deterministic canonical projection. | Critical | `protocols/v1.9.0/PR_REVIEW_CONTRACT.md#decide-once` | `DECISION_PROJECTION.json` | `project_decision`, `validate_projection_invariants`, `validate_directory`, and `verify_completed_review`; reject caller projection drift or manual action injection | `fixtures/golden-green/review-package.json` | `fixtures/canonical-output-enforcement/mutation-cases.json#caller_projection_action_injection` | python -m pytest -q tests/test_canonical_output_enforcement.py | official accessors accept only `VerifiedReviewCompletion` | per_artifact | block | ci_enforced |
| `PRR-ARTIFACT-COMPLETENESS-001` | Every required artifact exists and the conditional prompt exists exactly when the projection requires it. | Critical | `protocols/v1.9.0/PR_REVIEW_CONTRACT.md#output-artifacts` | required and conditional artifact set | `validate_directory` and `verify_completed_review`; reject missing required files, forbidden prompts, and required prompts that are absent | `fixtures/repair-handoff-valid/review-package.json` | `fixtures/canonical-output-enforcement/mutation-cases.json#partial_or_conditional_artifact_set` | python -m pytest -q tests/test_canonical_output_enforcement.py | only a verified completed bundle exposes owner, technical, or prompt output | per_artifact | block | ci_enforced |
| `PRR-MANIFEST-INTEGRITY-001` | Canonical package hashes, final-file hashes, deterministic bytes, and prompt routing must match the validated manifest. | Critical | `protocols/v1.9.0/PR_REVIEW_CONTRACT.md#artifact-integrity` | `artifact-manifest.json` and final artifact bytes | `_manifest_diagnostics`, deterministic byte comparison, and `verify_completed_review`; reject canonical hash, file hash, byte, or routing drift | rendered `fixtures/repair-handoff-valid/review-package.json` | `fixtures/canonical-output-enforcement/mutation-cases.json#manifest_or_final_byte_drift` | python -m pytest -q tests/test_canonical_output_enforcement.py | accessors revalidate the bundle before returning official content | per_artifact | block | ci_enforced |
| `PRR-VERIFIED-COMPLETION-001` | Official outputs require a verifier-created completion proof; booleans, dictionaries, low-level renderer results, and caller markers do not qualify. | Critical | `protocols/v1.9.0/policies/CANONICAL_OUTPUT_BEHAVIORAL_RULE_COVERAGE.md#completion-proof` | opaque in-process `VerifiedReviewCompletion` bound to identity and artifact hashes | `is_verified_review_completion`, `official_owner_result`, `official_technical_handoff`, and `official_next_action_prompt`; reject non-verifier values and revalidate on access | valid result from `complete_review` | `fixtures/canonical-output-enforcement/mutation-cases.json#caller_completion_flag_or_low_level_renderer` | python -m pytest -q tests/test_canonical_output_enforcement.py | accidental alternate application paths cannot claim completion through the supported API | per_artifact | block | ci_enforced |
| `PRR-FAIL-CLOSED-OUTPUT-001` | Rendering, validation, publication, rollback, or cleanup failure emits only bounded incomplete-review output; the official path contains the restored prior output or no authoritative bundle. | Critical | `protocols/v1.9.0/pipeline/REVIEW_PIPELINE.md#required-sequence` | sibling staging and backup paths, quarantine-first rollback, manifest invalidation fallback, and `IncompleteReview` diagnostics | `complete_review`, `_swap_staged_directory`, and `_restore_previous_directory`; quarantine failed publication before restore, never use ignored deletion as recovery proof, retain failed backup/quarantine evidence, and report all restoration/cleanup failures | successful atomic completion from `fixtures/golden-green/review-package.json` | `fixtures/canonical-output-enforcement/mutation-cases.json#interrupted_render_or_rollback_failure` | python -m pytest -q tests/test_canonical_output_atomicity.py | `scripts/render_review_v2.py` converts handled and unexpected boundary failures into bounded failure output | per_artifact | rollback | ci_enforced |

## Official boundary

The supported completed-review path is:

```text
canonical package + caller-observed identity
→ schema and semantic validation
→ deterministic projection and rendering in sibling staging
→ complete artifact and manifest validation
→ verifier-created completion proof
→ atomic publication
→ post-publication revalidation
→ official accessors
```

A failure returns `IncompleteReview`. It contains diagnostics and bounded failure messages but no technical status, approval requirement, owner readiness, next action, or prompt.

## Rollback boundary

Post-publication recovery is quarantine-first:

```text
failed official directory
→ atomic rename to unique quarantine
→ restore previous backup
→ cleanup quarantine only after restoration
```

If quarantine rename fails, the manifest is removed or invalidated before explicit deletion is attempted. Deletion, restoration, and cleanup results are verified by filesystem state and represented by diagnostics. `ignore_errors=True`, a completion boolean, or absence of an exception is not rollback proof. When restoration fails, the backup and quarantine are retained as evidence and the official path is kept absent or non-authoritative.

## Completion proof

`VerifiedReviewCompletion` is an in-process misuse-prevention capability, not a sandbox or cryptographic signature. It is produced only after the complete bundle validates, is bound to repository/PR/head plus canonical and final-byte hashes, and is revalidated whenever official content is read.

## Enforcement interpretation

- The focused enforcement suite includes manual status/action injection, arbitrary prompt, schema-valid semantic failure, projection drift, required/conditional artifact failures, manifest/hash mutations, partial output, caller completion flags, renderer misuse, interrupted rendering, stale-head reuse, owner-result disagreement, and prompt-ready overclaim.
- The focused atomicity suite includes failed published-directory deletion, quarantine rename failure, backup restore failure, no-prior-output rollback, retained valid backup evidence, unexpected rollback exceptions, authoritative-path assertions, and cleanup failure diagnostics.
- The workflow runs both focused commands on Python 3.10 through 3.14 before the full suite.
- Historical `v1.8.0` files remain unchanged.
- No row claims `downstream_contract_enforced`, OS sandboxing, cryptographic signing, repository-settings enforcement, or hostile same-process isolation.
