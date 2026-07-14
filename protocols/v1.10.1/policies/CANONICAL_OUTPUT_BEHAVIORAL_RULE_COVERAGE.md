# Behavioral Rule Coverage — Canonical Output Completion

Version: `v1.10.1`  
Scope: official package-to-output orchestration, live target-head identity, verified completion, atomic publication, publication commit point, quarantine-first rollback, verified-byte access, and fail-closed user-facing output.  
Decision: `PASS` only while both focused adversarial suites and full repository validation pass on the exact active head.

This matrix applies Behavioral Rule Coverage v0.4.1. It does not make low-level renderers a security sandbox and does not claim external downstream enforcement. The supported official output boundary is `pr_inspector.official_review.complete_review` supplied with a verifier-created `GitHubPullRequestHeadSource`; lower-level projection and rendering functions remain compositional primitives and cannot prove completed official output.

| rule_id | concept | risk | prose_source | carrier | validator_rule | valid_fixture | invalid_fixture | CI_step | downstream_contract | session_scope | recovery_action | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `PRR-CANONICAL-PACKAGE-001` | Official completion requires a schema-valid and semantically valid canonical package bound to the live GitHub repository, PR, and current head. | Critical | this policy, official boundary | package bytes plus verified live-head receipt | `complete_review`, `validate_package`, `PRI-COMPLETE-007`; reject invalid semantics or identity mismatch before publication | `fixtures/golden-green/review-package.json` | `manual_package_status_injection` | python -m pytest -q tests/test_canonical_output_enforcement.py | supported CLI uses only `complete_review` | per_artifact | block | ci_enforced |
| `PRR-CANONICAL-PROJECTION-001` | Status, approval, owner readiness, recipient, authority, and action routing come only from the deterministic projection. | Critical | `PR_REVIEW_CONTRACT.md#decide-once` | `DECISION_PROJECTION.json` | `project_decision`, `validate_directory`, and official accessors reject projection or manual action drift | golden Green fixture | `caller_projection_action_injection` | python -m pytest -q tests/test_canonical_output_enforcement.py | official accessors require verified completion | per_artifact | block | ci_enforced |
| `PRR-ARTIFACT-COMPLETENESS-001` | Every required artifact exists and the conditional prompt exists exactly when required. | Critical | `PR_REVIEW_CONTRACT.md#output-artifacts` | required and conditional artifact set | `validate_directory` and `validate_bundle` reject missing or forbidden artifacts | repair fixture | `partial_or_conditional_artifact_set` | python -m pytest -q tests/test_canonical_output_enforcement.py | only a completed bundle exposes output | per_artifact | block | ci_enforced |
| `PRR-MANIFEST-INTEGRITY-001` | Canonical package hashes, final-file hashes, deterministic bytes, and prompt routing match the manifest. | Critical | `PR_REVIEW_CONTRACT.md#artifact-integrity` | manifest plus final bytes | manifest diagnostics and bundle verification reject canonical hash, file hash, byte, or routing drift | rendered repair fixture | `manifest_or_final_byte_drift` | python -m pytest -q tests/test_canonical_output_enforcement.py | accessors fully validate captured bytes before returning content | per_artifact | block | ci_enforced |
| `PRR-VERIFIED-COMPLETION-001` | Official outputs require verifier-created completion bound to live GitHub identity and artifact hashes. | Critical | this policy, completion proof | `VerifiedReviewCompletion` | marker check, live-head recheck, and bundle revalidation reject booleans, mappings, low-level renderer returns, and mutation | result from `complete_review` | `caller_completion_flag_or_low_level_renderer` | python -m pytest -q tests/test_canonical_output_enforcement.py | accidental alternate paths cannot claim official completion | per_artifact | block | ci_enforced |
| `PRR-FAIL-CLOSED-OUTPUT-001` | Rendering, validation, publication, or pre-commit rollback failure emits bounded incomplete output; the official path contains the restored prior bundle or no authoritative bundle. | Critical | official pipeline required sequence | sibling staging, backup, quarantine, manifest invalidation fallback, `IncompleteReview` | `complete_review`, `publish`, and `restore` quarantine failed publication before backup restoration, reject ignored deletion as proof, and retain explicit diagnostics/evidence on restoration failure | successful atomic completion | `interrupted_render_or_validation_failure` | python -m pytest -q tests/test_canonical_output_atomicity.py | CLI/API never expose an unverified completion on rollback failure | per_artifact | rollback | ci_enforced |
| `PRR-FINAL-HEAD-RECHECK-001` | Official completion is tied to actual GitHub PR payloads and fails closed if the head changes before or after publication. | Critical | official pipeline final SHA recheck | opaque live source plus canonical PR API payload receipts | initial, prepublication, final, and accessor-time live head reads; `PRI-COMPLETE-008`; rollback on final drift before commit point | stable exact-head API payload | `live_head_changes_during_completion` | python -m pytest -q tests/test_canonical_output_enforcement.py | external consumers must use the official boundary; arbitrary chat prose remains unenforceable | cross_turn | rollback | sequence_ci_enforced |
| `PRR-PUBLICATION-COMMIT-POINT-001` | After staged validation, atomic publication, post-publication validation, and the final live-head check succeed, the new official bundle is committed and obsolete-backup cleanup cannot trigger rollback. | Critical | this policy, official completion sequence | verified official directory plus cleanup diagnostics | `complete_review` records `PRI-COMPLETE-009` on failed or partial backup cleanup, retains residue, and returns the verified completion without mutating the official path | second valid publication over an existing valid bundle | `partial_obsolete_backup_cleanup_after_publication_commit` | python -m pytest -q tests/test_canonical_output_atomicity.py | consumers receive the newly verified bundle plus explicit cleanup diagnostics | per_artifact | retain_residue_and_diagnose | ci_enforced |
| `PRR-VERIFIED-BYTE-SNAPSHOT-001` | Every official accessor returns, decodes, or parses the exact bytes captured by the same full verification that validated schema, semantics, projection, manifest, prompt routing, and final-byte hashes. | Critical | this policy, official accessor boundary | immutable in-memory artifact-byte snapshot in `_Bundle` | `validate_bundle` validates a captured snapshot; accessors consume `bundle.artifact_bytes` and never reopen the artifact after verification | fully verified official bundle | `accessor_validation_to_read_toctou` | python -m pytest -q tests/test_canonical_output_enforcement.py | returned bytes are the verified bytes even if disk changes after verification returns | per_access | block_future_access_on_drift | ci_enforced |

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
→ publication commit point
→ best-effort obsolete-backup cleanup with explicit diagnostics
→ verifier-created completion
→ live-head recheck plus full verification of a captured byte snapshot
→ accessors return only the captured verified bytes
```

Missing endpoints, partial/non-canonical payloads, stale heads, network failure, artifact drift, or validation failure before the publication commit point return `IncompleteReview`, which has diagnostics and bounded failure messages but no technical status, approval, owner readiness, next action, or prompt. Failure to clean an obsolete backup after the commit point is cleanup degradation, not publication failure: it is recorded on `VerifiedReviewCompletion.cleanup_diagnostics`, residue may remain, and the new verified official bundle stays authoritative.

## Claim boundary

`VerifiedReviewCompletion` is an in-process misuse-prevention capability, not a cryptographic signature, sandbox, OS harness, repository setting, or hostile same-process boundary. The repository can enforce its supported CLI and package APIs. It cannot stop an unrelated external language model from manually typing authoritative-looking prose outside those paths.

## Rollback and commit invariant

Before the publication commit point, post-publication recovery is quarantine-first:

```text
failed published directory
→ atomic rename to unique quarantine
→ restore previous backup to official path
→ clean quarantine only after restoration
```

If quarantine rename fails, the manifest is atomically removed from the failed directory before explicit deletion is attempted. Deletion, restoration, and cleanup are verified from filesystem state; `ignore_errors=True` and absence of an exception are not rollback evidence. Failed restoration retains the backup and quarantine with diagnostics while the official path remains absent or non-authoritative.

After post-publication bundle validation and the final live-head verification succeed, publication is committed. The old backup is obsolete cleanup material. A cleanup routine may partially mutate that backup before failing, so it must never be passed to rollback after the commit point. The dedicated command is `python -m pytest -q tests/test_canonical_output_atomicity.py`.

## Verified-byte accessor invariant

`validate_bundle` first captures the exact bytes and relevant path types of every official artifact, validates a temporary snapshot built from those bytes with the full schema/semantic/deterministic/manifest pipeline, and returns those same bytes in the verified bundle. Accessors recheck the live GitHub head, perform that full snapshot verification, compare all expected identities and hashes, and then parse or decode the captured bytes. They do not reopen the source path after verification. The dedicated command is `python -m pytest -q tests/test_canonical_output_enforcement.py`.
