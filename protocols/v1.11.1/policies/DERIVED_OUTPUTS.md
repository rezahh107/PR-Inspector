# Derived Outputs

Version: `v1.11.1`

All derived artifacts consume the single official projection. `derived_outputs.build_review_artifacts` is the sole active builder and `validation_v2.validate_directory` is the official validation boundary used by completion.

Every prompt-required artifact contains one deterministic `[CANONICAL ACTION CONTRACT]` JSON block derived from structured package/projection data. Validation independently recomputes identity, action authority, reasons, Findings, evidence, required actions/tests, re-review, profile-command separation, and prohibited actions. Exact-byte comparison and manifest hashes remain mandatory but cannot substitute for semantic completeness.

Candidate-era output entrypoints are migration tombstones. They raise `CandidateOutputMigrationError` and do not return bytes. Only allowlisted intake/evidence helpers remain supported.
