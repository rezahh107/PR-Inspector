---
title: AIGOV v2.5.0 Activation Transform Report
document_type: activation_transform_report
audited_candidate_identity: AIGOV_v2.5.0_release_candidate
audited_candidate_core_sha256: 4630d88515a87930412b4b438bfd19a4badc0807cf692413238b283fa1602c95
active_release_identity: AIGOV_v2.5.0_active
active_core_sha256: a8310ca60ba5577256789b5fcc7c5620a3f24af0deafc3587e8a2a60310d4186
activation_transform_status: PASS
---

# AIGOV v2.5.0 Activation Transform Report

## Allowed activation changes

```yaml
allowed_activation_changes:
  - lifecycle status fields
  - activation status, assurance and basis disclosures
  - activation timestamps and receipt references
  - active evidence artifacts, Manifest and derived hashes
  - archive filename and external checksum sidecar
```

## Normative artifact byte comparison

```yaml
observed_changed_files:
  AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.fa.md: [{"line": 5, "from": "status: release_candidate", "to": "status: active_governing_standard"}]
  PERSONAL_AI_OPERATED_REPOSITORY_REVIEW_PROFILE_v1.2.0.fa.md: [{"line": 5, "from": "status: release_candidate", "to": "status: active_companion"}]
  PR_INSPECTOR_REVIEW_RECEIPT_PUBLICATION_CONTRACT_v1.2.0.fa.md: [{"line": 5, "from": "status: release_candidate", "to": "status: active_companion"}]
  AIGOV_BEHAVIORAL_RULE_COVERAGE_CONTRACT_v1.2.0.fa.md: [{"line": 5, "from": "status: release_candidate", "to": "status: active_companion"}]
changed_fields:
  - Core front_matter.status: release_candidate -> active_governing_standard
  - Companion front_matter.status: release_candidate -> active_companion
unexpected_normative_changes: []
activation_transform_status: PASS
```

Implementation Report, parity status, README, Manifest, release-integrity and receipts are lifecycle/release-evidence surfaces regenerated after activation. No Rule, Boundary, carrier, predicate, prompt obligation, Acceptance Criterion, fixture or migration semantic changed after audit freeze.
