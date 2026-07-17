# PRF-002 — Inspector Commit Provenance

Status: `implemented_pending_rereview`

The Inspector repository and commit verifier accepts only registry-backed `GitHubApiResponse` capabilities produced by the operational GitHub HTTPS adapter. It verifies canonical request and response URLs, successful status codes, locked repository identity, exact commit identity, and canonical API and HTML URLs.

Plain mappings, copied JSON, manually reconstructed response objects, response subclasses, copied capability fields, and reconstructed `VerifiedInspectorCommit` objects cannot mint reusable Minimal-review authority.

The bounded repair preserves the existing `VerifiedMinimalReviewReference` seal, source-artifact revalidation, same-Head Minimal reuse, mandatory genuine refresh after Head drift, and fail-closed Candidate output tombstones.

This document does not claim independent review, approval, merge authorization, repository-hosted enforcement, or merge readiness. A fresh independent PR Inspector review and separate exact-bound enforcement evidence remain required.
