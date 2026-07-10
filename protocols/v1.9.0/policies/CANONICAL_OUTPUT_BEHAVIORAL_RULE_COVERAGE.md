# Behavioral Rule Coverage — Canonical Output Completion

Version: `v1.9.0`  
Scope: official package-to-output orchestration, live target-head identity, verified completion, atomic publication, quarantine-first rollback, and fail-closed user-facing output.  
Decision: `PASS` only while both focused adversarial suites and full repository validation pass on the exact candidate head.

This matrix applies Behavioral Rule Coverage v0.4.1. It does not make low-level renderers a security sandbox and does not claim external downstream enforcement. The supported official output boundary is `pr_inspector.official_review.complete_review` supplied with a verifier-created `GitHubPullRequestHeadSource`; lower-level projection and rendering functions remain compositional primitives and cannot prove completed official output.

| rule_id | concept | risk | prose_source | carrier | validator_rule | valid_fixture | invalid_fixture | CI_step | downstream_contract | session_scope | recovery_action | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `PRR-CANONICAL-PACKAGE-001` | Official completion requires a schema-valid and semantically valid canonical package bound to the live GitHub repository, PR, and current head. | Critical | this policy, official boundary | package bytes plus verified live-head receipt | `complete_review`, `validate_package`, `PRI-COMPLETE-007`; reject invalid semantics or identity mismatch before publication | `fixtures/golden-green/review-package.json` | `manual_package_status_injection` | python -m pytest -q tests/test_canonical_output_enforcement.py | supported CLI uses only `complete_review` | per_artifact | block | ci_enforced |
| `PRR-CANONICAL-PROJECTION-001` | Status, approval, owner readiness, recipient, authority, and action routing come only from the deterministic projection. | Critical | `PR_REVIEW_CONTRACT.md#decide-once` | `DECISION_PROJECTION.json` | `project_decision`, `validate_directory`, and official accessors reject projection or manual action drift | golden Green fixture | `caller_projection_action_injection` | python -m pytest -q tests/test_canonical_output_enforcement.py | official accessors require verified completion | per_artifact | block | ci_enforced |
| `PRR-ARTIFACT-COMPLETENESS-001` | Every required artifact exists and the conditional prompt exists exactly when required. | Critical | `PR_REVIEW_CONTRACT.md#output-artifacts` | required and conditional artifact set | `validate_directory` and `_validate_completed_bundle` reject missing or forbidden artifacts | repair fixture | `partial_or_conditional_artifact_set` | python -m pytest -q tests/test_canonical_output_enforcement.py | only a completed bundle exposes output | per_artifact | block | ci_enforced |
| `PRR-MANIFEST-INTEGRITY-001` | Canonical package hashes, final-file hashes, deterministic bytes, and prompt routing match the manifest. | Critical | `PR_REVIEW_CONTRACT.md#artifact-integrity` | manifest plus final bytes | manifest diagnostics and bundle verification reject canonical hash, file hash, byte, or routing drift | rendered repair fixture | `manifest_or_final_byte_drift` | python -m pytest -q tests/test_canonical_output_enforcement.py | accessors revalidate before returning content | per_artifact | block | ci_enforced |
| `PRR-VERIFIED-COMPLETION-001` | Official outputs require verifier-created completion bound to live GitHub identity and artifact hashes. | Critical | this policy, completion proof | `VerifiedReviewCompletion` | marker check, live-head recheck, and bundle revalidation reject booleans, mappings, low-level renderer returns, and mutation | result from `complete_review` | `caller_completion_flag_or_low_level_renderer` | python -m pytest -q tests/test_canonical_output_enforcement.py | accidental alternate paths cannot claim official completion | per_artifact | block | ci_enforced |
| `PRR-FAIL-CLOSED-OUTPUT-001` | Rendering, validation, publication, rollback, or cleanup failure emits bounded incomplete output; the official path contains the restored prior bundle or no authoritative bundle. | Critical | candidate pipeline required sequence | sibling staging, backup, quarantine, manifest invalidation fallback, `IncompleteReview` | `complete_review`, `publish`, and `restore` quarantine failed publication before backup restoration, reject ignored deletion as proof, and retain explicit diagnostics/evidence on restoration or cleanup failure | successful atomic completion | `interrupted_render_or_validation_failure` | python -m pytest -q tests/test_canonical_output_atomicity.py | CLI/API never expose an unverified completion on rollback failure | per_artifact | rollback | ci_enforced |
| `PRR-FINAL-HEAD-RECHECK-001` | Official completion is tied to actual GitHub PR payloads and fails closed if the head changes before or after publication. | Critical | candidate pipeline final SHA recheck | opaque live source plus canonical PR API payload receipts | initial, prepublication, final, and accessor-time live head reads; `PRI-COMPLETE-008`; rollback on final drift | stable exact-head API payload | `live_head_changes_during_completion` | python -m pytest -q tests/test_canonical_output_enforcement.py | external consumers must use the official boundary; arbitrary chat prose remains unenforceable | cross_turn | rollback | sequence_ci_enforced |

## Official boundary

```text
canonical package
→ fresh official GitHub PR payload
→ schema and semantic validation
→ deterministic projection/rendering in sibling staging
→ complete artifact and manifest validation
→ fresh prepublication PR-head recheck
→ atomic publication
→ post-publication bundle validation
→ fresh final PR-head recheck
→ verifier-created completion
→ live-rechecking official accessors
```

Missing endpoints, partial/non-canonical payloads, stale heads, network failure, artifact drift, or validation failure return `IncompleteReview`, which has diagnostics and bounded failure messages but no technical status, approval, owner readiness, next action, or prompt.

## Claim boundary

`VerifiedReviewCompletion` is an in-process misuse-prevention capability, not a cryptographic signature, sandbox, OS harness, repository setting, or hostile same-process boundary. The repository can enforce its supported CLI and package APIs. It cannot stop an unrelated external language model from manually typing authoritative-looking prose outside those paths.

## Rollback invariant

Post-publication recovery is quarantine-first:

```text
failed published directory
→ atomic rename to unique quarantine
→ restore previous backup to official path
→ clean quarantine only after restoration
```

If quarantine rename fails, the manifest is atomically removed from the failed directory before explicit deletion is attempted. Deletion, restoration, and cleanup are verified from filesystem state; `ignore_errors=True` and absence of an exception are not rollback evidence. Failed restoration retains the backup and quarantine with diagnostics while the official path remains absent or non-authoritative.

The dedicated command is `python -m pytest -q tests/test_canonical_output_atomicity.py`.
