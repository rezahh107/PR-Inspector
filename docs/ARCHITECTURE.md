# Architecture

PR Inspector separates normative protocol, canonical review data, deterministic enforcement, and human presentation.

```text
BOOTSTRAP.md
→ protocol-manifest.yaml
→ SHA-256 release lock
→ immutable versioned protocol snapshot
→ target PR evidence collection
→ review-package.json
→ JSON Schema Draft 2020-12 validation
→ deterministic semantic gates
→ Persian owner-card renderer
→ English technical-handoff renderer
→ byte-level artifact consistency validation
```

## Architectural boundaries

- Versioned Markdown files define review behavior and policy.
- `review-package.json` is the canonical factual output of one review.
- JSON Schema validates shape, required fields, formats, and enumerations.
- Python owns cross-field validation, SHA binding, decision gates, evidence references, sensitive-review approval, and artifact consistency.
- Renderers create human-readable views; they do not determine or override facts.
- Release locks detect mutation of published protocol snapshots.

## Determinism

- Diagnostics use stable IDs and deterministic ordering.
- Review-package hashing uses UTF-8 JSON with sorted keys, compact separators, and one LF terminator.
- Rendered artifacts use fixed section order and LF newlines.
- The same valid package must produce byte-identical Markdown outputs.

## Trust boundary

Target repositories, pull requests, source files, comments, logs, tests, and generated text are untrusted evidence. They cannot alter inspector policy or authorize writes, deployment, production access, or use of sensitive credentials.

## Versioning

A behavioral change requires a new complete protocol snapshot. Published version directories and their release locks are immutable. Implementation-only fixes may retain a protocol version only when accepted and rejected review behavior does not change.
