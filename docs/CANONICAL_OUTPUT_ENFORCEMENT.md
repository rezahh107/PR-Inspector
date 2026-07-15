# Canonical Artifact and Official-Output Boundary

Status: v1.10.1 forward profile integration preserves the canonical-output implementation merged on live `main` for v1.9.0. PR #14 was integrated into PR #13, and PR #13 was then merged to `main`; those pull requests are historical provenance rather than pending activation or repair gates.

## Current closure status

```yaml
active_protocol: v1.10.1
implementation_state: v1.10.1_forward_profile_integration_pending_independent_review
live_main_head_at_audit_start: 35e3b398d8e8d6823007540f0a156ff2a3feece6
source_prs:
  - 13
  - 14
canonical_output_boundary: implemented
publication_commit_point: implemented
verified_byte_snapshot_accessors: implemented
atomic_owner_delivery: implemented_pending_independent_review
governance_code_boundary: implemented
repository_settings_enforcement: insufficient_evidence
merged_implementation_exact_head_ci:
  tested_head: 815d7f5fccb51a256ae853930deb77a605495f1f
  run_id: 29148064601
  conclusion: success
historical_v1_8_immutable: true
confirmed_merged_implementation_findings_at_audit_start: none
closure_pr_review_state: pending_independent_review
live_review_thread_state: not_asserted_by_static_document
bot_commented_feedback: not_approval
remaining_operational_actions:
  - independent review of the closure-polish pull request on its exact final head
  - authoritative verification or application of GitHub repository settings under separate authorization
closure_status: profile_implementation_complete_pending_independent_review
```

The status above records the merged v1.9 implementation and the evidence available at the start of this closure audit. No additional runtime implementation defect was confirmed in the already merged boundary during that audit. It does not assert the live review-thread state of PR #15, and it does not claim that this closure-polish branch is independently reviewed, approved, merge-authorized, or merged. Bot feedback with review state `COMMENTED` is not approval. GitHub repository settings remain a separate administrative evidence boundary.

## Personal minimum-security profile boundary

The v1.10.1 carrier is implemented in the canonical package, projection, reason registry, semantic validation, owner/action routing, renderers, fixtures, and CI. Repository-settings enforcement and merge authorization remain separate evidence claims and are not asserted by this document. Independent review of the final exact PR head remains pending.

## Boundary classification

```yaml
repository_execution_bug: true
repository_protocol_gap: true
supported_cli_bypass: true
external_interface_noncompliance: true
project_integration_gap: true
mixed_boundary_defect: true
```

The repository defect was real but bounded: the supported render CLI validated only the package, wrote directly into the destination, and printed success without independently validating the completed directory or re-reading the live GitHub PR head. Separately, arbitrary ChatGPT or connector orchestration can ignore repository code and type authoritative-looking prose directly; Python code in this repository cannot prevent that external behavior.

## Supported-path map

| path | classification | boundary |
|---|---|---|
| `scripts/render_review_v2.py` | official supported entry point | Must construct a live GitHub PR-head source, call `complete_review`, and emit the complete verified owner delivery to stdout. Technical success or diagnostics go to stderr. |
| `pr_inspector.official_review.complete_review` | official high-level package API | Performs live identity reads, validation, staging, atomic publication, pre-commit rollback, publication commit, and bounded obsolete-backup cleanup. |
| `pr_inspector.official_review.verify_completed_review` | official existing-bundle verifier | Requires a verifier-created live head source, captures exact artifact bytes, validates that snapshot, and reads GitHub before and after bundle validation. |
| `official_owner_delivery` | canonical owner-facing delivery accessor | Accepts only `VerifiedReviewCompletion`; returns the compact owner result and, when required, the complete canonical prompt from one reverified byte snapshot. |
| `official_owner_result` | compact owner-result accessor | Allowed only when the canonical projection does not require a prompt. Prompt-required decisions fail closed and must use `official_owner_delivery`. |
| `official_technical_handoff`, `official_next_action_prompt` | specialized official accessors | Accept only `VerifiedReviewCompletion`; recheck the live head, fully validate captured artifact bytes, and return only those verified bytes. |
| `decision_projection.project_decision` | internal composition API | Canonical decision derivation only; not completion evidence. |
| `derived_outputs.build_review_artifacts` | internal composition API | In-memory deterministic construction; not completion evidence. |
| `derived_outputs.write_review_artifacts` | internal composition API | Low-level writer; never an official completion signal. |
| `derived_outputs.render_next_action_prompt` | internal composition API | Deterministic renderer; direct text is not an official prompt-ready claim. |
| `scripts/validate_review_v2.py` | official validation-only entry point | Read-only directory validation; does not announce a completed live review. |
| fixtures/tests | test-only helper | Never live review evidence. |
| templates/policies | documentation-only path | Never generated completion evidence. |
| arbitrary chat/model prose | external interface outside repository control | Must be governed by project integration; repository code cannot technically block it. |

## Official completion sequence

```text
canonical package bytes
→ fresh canonical GitHub PR API payload
→ package schema + semantic validation
→ live repository/PR/head identity match
→ canonical projection
→ deterministic artifacts in sibling staging
→ manifest from final staged bytes
→ complete staged-directory validation
→ fresh prepublication head recheck
→ atomic directory publication
→ post-publication captured-byte bundle validation
→ fresh final head recheck
→ publication commit point
→ bounded obsolete-backup cleanup
→ verifier-created completion receipt
→ accessor-time live-head recheck
→ full validation of a captured byte snapshot
→ atomic owner-delivery composition from that same snapshot
→ return only captured verified owner and prompt bytes
```

A changed head before publication prevents publication. A changed head or failed endpoint after publication but before the commit point restores the prior directory. Partial payloads, non-canonical identity, network failure, invalid artifacts, or any other failed pre-commit gate return `IncompleteReview` with diagnostics only.

## Publication commit and cleanup invariant

The new official bundle becomes committed only after all four conditions succeed:

1. staged bundle validation;
2. atomic publication;
3. post-publication bundle validation;
4. final live GitHub-head verification.

Before that point, recovery is quarantine-first: the failed published directory is atomically renamed to a unique quarantine path, the previous backup is restored, and quarantine cleanup occurs only after restoration succeeds. If quarantine rename fails, the manifest is removed first so leftover files cannot remain an authoritative bundle; explicit deletion is then attempted and verified.

After the commit point, the prior backup is obsolete cleanup material. Recursive deletion may partially mutate it before raising. Therefore cleanup failure must never pass that backup to rollback. The new official bundle remains intact and authoritative; `PRI-COMPLETE-009` is retained in `VerifiedReviewCompletion.cleanup_diagnostics`, and any partial backup residue remains available for bounded diagnosis.

## Verified-byte accessor invariant

Bundle verification captures the exact bytes and relevant path types for every official artifact before validation. It validates a temporary snapshot constructed from those bytes with the complete existing pipeline: package schema and semantics, deterministic projection, rendered-byte equality, prompt routing, manifest structure, and final-byte hashes.

The verified `_Bundle` carries those immutable bytes. Official accessors perform the live-head recheck and full snapshot verification, compare the resulting identities and hashes to the completion receipt, and then parse or decode `bundle.artifact_bytes`. They never reopen the source artifact after verification, eliminating the validation-to-read TOCTOU window.

## Atomic owner-delivery invariant

A prompt-required owner result is not a complete delivery by itself. `official_owner_delivery` reads `OWNER_RESULT.fa.txt`, `DECISION_PROJECTION.json`, and the conditional `NEXT_ACTION_PROMPT.en.md` from one fully reverified in-memory byte snapshot. When `prompt_required` is true, the returned text contains the complete prompt after the Persian `## پرامپت اقدام` heading. It never returns a path, readiness claim, summary, reconstructed prompt, or later-delivery promise as a substitute for the exact verified prompt bytes.

`official_owner_result` is intentionally fail-closed for prompt-required decisions. This preserves the two-line compact artifact while preventing supported integrations from displaying wording such as “پرامپت اصلاح آماده است” without the prompt body. The supported CLI emits `official_owner_delivery` by default and places only technical completion information on stderr.

## Completion and output claims

`VerifiedReviewCompletion` binds the repository, PR, reviewed head, canonical package hash, package file hash, projection hash, manifest hash, all official artifact hashes, and a canonical GitHub PR-payload receipt hash. It may also carry explicit non-authoritative cleanup diagnostics after successful publication.

The opaque markers prevent accidental use of booleans, dictionaries, or low-level renderer results as completion. They are not cryptographic signatures or hostile same-process security boundaries.

## External integration obligation

An external ChatGPT/project/connector integration that wants to present an **official PR Inspector result** must:

1. invoke the supported official CLI or package boundary;
2. require a successful process result and verifier-created completion;
3. use `official_owner_delivery` for owner-facing output;
4. never use the compact owner result alone when `prompt_required` is true;
5. never synthesize, summarize, truncate, postpone, or independently reconstruct the action prompt;
6. display technical or prompt content only through official accessors or from the validated published bundle;
7. never synthesize status, next action, or prompt-ready wording directly;
8. preserve failure output as incomplete/blocked rather than converting it into Green/Yellow/Red prose;
9. surface `cleanup_diagnostics` without treating cleanup residue as publication rollback.

The repository cannot enforce these rules against unrelated free-form chat output. That remaining obligation belongs to the external orchestration layer.

## TOCTOU limitation

GitHub head identity is exact at each observed API receipt. No client can eliminate the final network-to-display race entirely. The implementation narrows it through initial, prepublication, post-publication, and accessor-time reads and fails closed on every observed drift. Artifact content has the stronger invariant: bytes returned by an accessor are exactly the bytes captured and fully validated by that accessor invocation.
