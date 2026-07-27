# PR Review Contract v1.13.1

Status: generated, non-authoritative view. The authority is `functional-runtime-contract.json`.

v1.13.1 preserves one canonical projection authority, `project_decision`, process-local
`VerifiedReviewCompletion`, atomic publication, and `official_owner_delivery`. Owner profile commands remain a separate verified artifact; manual concatenation is not an authority boundary.
The v1.12 pre-package compatibility boundary remains available for historical callers.
Per-review startup loads the local functional contract and does not attest the Inspector
repository, origin, remote commit, release lock, or historical releases.

## Historical provenance

PR #12 is historical provenance. Its visible reviewer state `COMMENTED` did not prove completion or establish that all required approvals were received.
