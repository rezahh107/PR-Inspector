# PR Inspector Bootstrap v1.13.1

For every official review:

1. Read `CURRENT_VERSION`.
2. Read `protocol-manifest.yaml`.
3. Read exactly the five `runtime_bootstrap_inputs` in declared order.
4. Emit the active intake response and request the target repository and PR number.
5. After target input, collect target PR evidence and execute the review pipeline.

Per-review startup is load-only. Do not run or emulate validation, hashing, digest calculation, schema validation, symbol checks, release-lock checks, repository scans, Git commands, Python, subprocesses, local checkout verification, or Inspector self-attestation.

A missing local checkout, Python runtime, Git executable, or Inspector-side validation capability must not block startup. Use `UNKNOWN` for Inspector commit identity when it is not directly available.

Target-repository identity and PR evidence are collected only after valid target input is supplied.
