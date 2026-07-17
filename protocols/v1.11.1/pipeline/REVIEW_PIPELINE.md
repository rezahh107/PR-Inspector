# Review Pipeline — v1.11.1

1. Parse requested `minimal` or `strict` profile.
2. Bind repository, PR, exact Head, Inspector identity, review surfaces, and evidence through sealed sources.
3. Produce one canonical `review-package.json`.
4. Derive one official decision projection.
5. Build one official artifact set.
6. Validate schema, semantics, prompt completeness, deterministic bytes, manifest hashes, and exact identity.
7. Mint `VerifiedReviewCompletion` only after complete validation.
8. Publish owner output only through `official_owner_delivery`.
9. Retrieve profile commands separately through `official_owner_profile_commands`.
10. Require fresh independent PR Inspector review after any repair.

Candidate compatibility ends before step 3 except for verified-completion delegation. Any Candidate-owned projection, rendering, verification, or composition fails closed.
