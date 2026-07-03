# Contributing

1. Read `BOOTSTRAP.md`, `AGENTS.md`, and the active maintenance rules.
2. Classify the change as editorial, implementation-only, or protocol-behavioral.
3. Never edit a released `protocols/vX.Y.Z/` directory or its release lock.
4. Behavioral changes require a new versioned protocol snapshot plus manifest and version-pointer updates.
5. Add or update schemas, diagnostics, fixtures, and tests for every changed rule.
6. Run:

```bash
python -m pip install ".[dev]"
python scripts/validate_repository_v2.py
python -m pytest
```

Contributions are accepted under Apache-2.0 unless explicitly marked otherwise.
