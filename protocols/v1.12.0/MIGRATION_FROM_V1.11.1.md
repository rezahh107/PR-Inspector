# Migration from v1.11.1 to v1.12.0

```yaml
historical_protocol: v1.11.1
new_protocol: v1.12.0
historical_files_modified: false
raw_package_official_completion_removed: true
review_package_is_official_output: true
preview_compatibility_available: true
automatic_reinterpretation_of_historical_artifacts: false
```

`protocols/v1.11.1/**` and `release-locks/v1.11.1.sha256` remain immutable.

The v1.11 public boundary accepted a caller-authored package path. In v1.12 the caller supplies only `ReviewRequest` and bounded `ReviewAssessment`. `ReviewEvidenceSource` collects `ReviewFacts`, and `assemble_review_package` creates the complete canonical package in memory.

Calls using the old path/package signature return the stable migration diagnostic `PRI-PACKAGE-AUTHORITY-001`. The legacy path cannot publish artifacts or mint `VerifiedReviewCompletion`. Preview output remains explicitly non-authoritative.
