# Canonical Output Behavioral Rule Coverage

Version: `v1.11.1`

| rule_id | invariant | enforcement | mutation coverage |
|---|---|---|---|
| `PRR-PROMPT-SEMANTIC-001` | Prompt-required artifacts are actionable and identity/action/finding/evidence/test-bound. | `prompt_semantics` plus `validation_v2` | PR #22 placeholder, generic prompt, missing identity/reasons/findings/tests/re-review, heading-only, hash-valid incomplete prompt |
| `PRR-CANDIDATE-OUTPUT-AUTHORITY-001` | No active Candidate projection, renderer, builder, verifier, owner delivery, or prompt stdout remains. | literal allowlist, migration errors, repository closure | direct imports, PR #27-style re-export, legacy four-segment output, Candidate/official divergence |
| `PRR-PROFILE-COMMAND-SEPARATION-001` | Profile commands remain a separate artifact/accessor. | prompt validator and owner-delivery contract | appended profile commands and manual concatenation |
| `PRR-OFFICIAL-COMPLETION-ONLY-001` | Prompt-ready owner output requires `VerifiedReviewCompletion` and `official_owner_delivery`. | official bundle and re-verification | compact bypass, unverified bundle, altered bytes |

Repository tests enforce producer and included-adapter behavior. External ChatGPT/project/connector execution remains `NOT_RUN` until separately exercised.
