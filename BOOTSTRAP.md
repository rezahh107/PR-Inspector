# PR Inspector Bootstrap v1.13.1

Per-review startup is retrieval-only:

1. Read `CURRENT_VERSION` from the connector-selected repository ref.
2. Read `protocols/<CURRENT_VERSION>/functional-runtime-contract.json` from that same ref to load the active inspection instructions.
3. Read `protocols/<CURRENT_VERSION>/prompts/INTAKE_RESPONSE.fa.md` from that same ref and return the intake response.
4. Accept the target PR URL or inspection request and begin evidence collection.

Startup requires no local checkout or local execution. It runs no Git command, Python subprocess, recursive repository scan, functional digest or file hash, cleanliness check, AST/symbol check, schema validation, authority inventory or generated-view comparison, release-lock check, trust/provenance/attestation check, remote identity check, or Inspector self-verification network call. Basic retrieval of the three active inputs from one ref is the only startup reading boundary. Inspection validation of the target PR remains part of the review workflow after intake.
