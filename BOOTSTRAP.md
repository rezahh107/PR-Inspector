# PR Inspector Bootstrap v1.13.0

For every official review:

1. Read `CURRENT_VERSION` and require `v1.13.0`.
2. Read `protocol-manifest.yaml`.
3. Load exactly the five `runtime_bootstrap_inputs` in declared order.
4. Validate the strict functional contract and local functional digest.
5. Request the target repository and PR number.
6. Collect exact target repository/PR identity, Base, Head, merge base, changed files, checks, issue comments, reviews, inline comments, and live-Head evidence.
7. Fail closed on missing or incomplete evidence.

Do not verify Inspector trust policy, origin, remote repository identity/ID, remote commit existence, release locks, historical releases, or the full repository during per-review startup. Those are maintenance/CI controls.
