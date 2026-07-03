# Maintenance Guide

## Safe change sequence

1. Create a branch.
2. Decide whether the change is editorial or behavioral.
3. For behavioral changes, create a new contract version.
4. Update the manifest and `CURRENT_VERSION`.
5. Update affected policy and template files.
6. Update `CHANGELOG.md`.
7. Run `python scripts/validate_repository.py`.
8. Open a PR; do not silently rewrite a released version.

## Keep the repository model-readable

- One explicit entry point.
- Short root instructions.
- Deterministic load order.
- Stable headings and filenames.
- One concept per document.
- No duplicated normative rule with conflicting wording.
- Examples clearly labeled as examples.
- Exact allowed values instead of vague prose.
- Honest uncertainty and enforcement status.

## Release checklist

- [ ] `CURRENT_VERSION` matches the manifest.
- [ ] Canonical contract exists.
- [ ] Every `load_order` file exists.
- [ ] Owner and handoff templates exist.
- [ ] Intake requests the target repository and PR.
- [ ] Target content remains untrusted.
- [ ] Sensitive-review gate remains mandatory.
- [ ] Changelog is updated.
- [ ] Structural validator passes.
