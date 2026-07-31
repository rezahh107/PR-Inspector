## v1.13.1

- Activate v1.13.1 as the current PR Inspector protocol.
- Make per-review startup retrieval-only through `CURRENT_VERSION`, the active functional runtime contract, and the active intake response.
- Keep the three active startup inputs bounded to `CURRENT_VERSION`, `protocols/v1.13.1/functional-runtime-contract.json`, and `protocols/v1.13.1/prompts/INTAKE_RESPONSE.fa.md`.
- Update package and Runtime metadata to 1.13.1.
- Preserve v1.13.0 as a historical protocol snapshot.

## v1.13.0

- Replace per-review Inspector trust/repository/commit/release attestation with one strict local functional runtime contract.
- Separate compact runtime bootstrap from full release/repository validation.
- Derive Behavioral Rule Coverage from the functional contract instead of a hard-coded required-rule registry.
- Preserve public `complete_review`, exact target evidence, canonical decision, publication, completion, and owner-delivery semantics.
- Preserve v1.12.0 and its release lock byte-for-byte.

## v1.12.0

- Historical release; see `protocols/v1.12.0/` and `release-locks/v1.12.0.sha256`.
