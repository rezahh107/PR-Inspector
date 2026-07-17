# PRF-002 — Inspector Commit Provenance

Status: `implemented_pending_rereview`

The Inspector repository and commit verifier accepts only exact, registry-backed `GitHubApiResponse` capabilities produced by the operational GitHub HTTPS adapter. The registry and operational mint are enclosed inside the production fetch boundary; no module-level helper can register a response or select the `github_https` origin.

The compatibility `_mint_response` test factory creates a separate `TestGitHubApiResponse`, fixes its origin to `test_factory`, and never touches the operational registry. Governance fixture files now supply endpoint names and URLs only; their payloads and status fields are ignored while the adapter performs live fetches.

Plain mappings, copied JSON, manually reconstructed response objects, response subclasses, test-factory responses, copied capability fields, and reconstructed `VerifiedInspectorCommit` objects cannot mint reusable Minimal-review authority. Unsuccessful and redirected HTTPS observations remain sealed negative receipts but fail the canonical status and URL requirements.

The bounded repair preserves the existing `VerifiedMinimalReviewReference` seal, source-artifact revalidation, same-Head Minimal reuse, mandatory genuine refresh after Head drift, and fail-closed Candidate output tombstones.

This document does not claim independent review, approval, merge authorization, repository-hosted enforcement, or merge readiness. A fresh independent PR Inspector review and separate exact-bound enforcement evidence remain required.
