---
title: AI Authority Deterministic Governance v2.5.0 — Active Release Integrity
standard_version: "2.5.0"
document_status: "active_governing_standard"
validated_at: "2026-07-17T20:56:54+02:00"
same_context_release_validation_status: "PASS"
same_context_final_audit_status: "PASS"
independent_document_audit_status: "NOT_PERFORMED"
activation_assurance_level: MAINTAINER_CONTROLLED_DETERMINISTIC
activation_basis: SAME_CONTEXT_DETERMINISTIC_FINALIZATION
activation_status: "PASS"
---

# Active Release Integrity Report

## Validation boundary

این گزارش deterministic same-context integrity است و reviewer independence را ادعا نمی‌کند. Archive digest به‌علت منع circular dependency فقط در external `.sha256` sidecar و external archive integrity receipt exact-bound می‌شود.

## Artifact identities

```yaml
artifacts:
  AIGOV_BEHAVIORAL_RULE_COVERAGE_CONTRACT_v1.2.0.fa.md:
    sha256: "7bfe410a0e6e1db79f2d38719219ea119f0a13601c1ce7f462c8d55bdd3de361"
    bytes: 11277
    lines: 333
    line_count_method: utf8_logical_lines_splitlines
    newline_sequence: LF
    final_newline_present: true
  AIGOV_BEHAVIORAL_RULE_COVERAGE_CONTRACT_v1.2.0_ACTIVATION_RECEIPT.fa.md:
    sha256: "662d5917ddfd0667fc94e34e57e1e29aeab8e9cae3fc05afa30ecbf4320afc48"
    bytes: 980
    lines: 20
    line_count_method: utf8_logical_lines_splitlines
    newline_sequence: LF
    final_newline_present: true
  AIGOV_v2.5.0_ACTIVATION_RECEIPT.fa.md:
    sha256: "6ba682831d99cb0973e04a823dae813724c326f181d1be7f31e506c37171ca29"
    bytes: 1010
    lines: 20
    line_count_method: utf8_logical_lines_splitlines
    newline_sequence: LF
    final_newline_present: true
  AIGOV_v2.5.0_ACTIVATION_TRANSFORM_REPORT.fa.md:
    sha256: "b98b17ec334b78e0d432dbfc4773ac81da205aea5b87c8d4f50aa9ef6c73e295"
    bytes: 1973
    lines: 39
    line_count_method: utf8_logical_lines_splitlines
    newline_sequence: LF
    final_newline_present: true
  AIGOV_v2.5.0_IMPLEMENTATION_REPORT.fa.md:
    sha256: "044c16280bf0350ba07a8225ec2dbacb9c1b64f9abbb298acc386a1adc3e7ff6"
    bytes: 3407
    lines: 88
    line_count_method: utf8_logical_lines_splitlines
    newline_sequence: LF
    final_newline_present: true
  AIGOV_v2.5.0_INCIDENT_AND_MIGRATION_RECORD.fa.md:
    sha256: "1bde9b9e17bcd551e8712e3dc93e5cf3f13b7921e279b5c36c0e5b9809f79520"
    bytes: 2052
    lines: 46
    line_count_method: utf8_logical_lines_splitlines
    newline_sequence: LF
    final_newline_present: true
  AIGOV_v2.5.0_SAME_CONTEXT_FINAL_AUDIT.fa.md:
    sha256: "165f00cb11f9b31cf29ecfd1d4b36138ec5cb9e6fa6356c7ed122a6a84bb110b"
    bytes: 2285
    lines: 52
    line_count_method: utf8_logical_lines_splitlines
    newline_sequence: LF
    final_newline_present: true
  AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.fa.md:
    sha256: "a8310ca60ba5577256789b5fcc7c5620a3f24af0deafc3587e8a2a60310d4186"
    bytes: 129878
    lines: 2500
    line_count_method: utf8_logical_lines_splitlines
    newline_sequence: LF
    final_newline_present: true
  AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.projection-parity-matrix.json:
    sha256: "87c8c9dea5775283e8e2ae0f2410c8c4a669526f643a42233d70ab413046e160"
    bytes: 16598
    lines: 341
    line_count_method: utf8_logical_lines_splitlines
    newline_sequence: LF
    final_newline_present: true
  PERSONAL_AI_OPERATED_REPOSITORY_REVIEW_PROFILE_v1.2.0.fa.md:
    sha256: "9b7d8cd1f1c1b744b89edb0ada8c882d50cd2aa3d99001e85f88de8c541b44b5"
    bytes: 5554
    lines: 144
    line_count_method: utf8_logical_lines_splitlines
    newline_sequence: LF
    final_newline_present: true
  PERSONAL_AI_OPERATED_REPOSITORY_REVIEW_PROFILE_v1.2.0_ACTIVATION_RECEIPT.fa.md:
    sha256: "057e59646c0929b4c7f4ad70ab6ab5f2fcddfeb3743e15fe8604fca36cbb8436"
    bytes: 975
    lines: 20
    line_count_method: utf8_logical_lines_splitlines
    newline_sequence: LF
    final_newline_present: true
  PR_INSPECTOR_REVIEW_RECEIPT_PUBLICATION_CONTRACT_v1.2.0.fa.md:
    sha256: "a49c47cd2c4275c9134c70fbb3f3a15eaf3f7a0b2f6495fa64d076e2d57afd2a"
    bytes: 6819
    lines: 195
    line_count_method: utf8_logical_lines_splitlines
    newline_sequence: LF
    final_newline_present: true
  PR_INSPECTOR_REVIEW_RECEIPT_PUBLICATION_CONTRACT_v1.2.0_ACTIVATION_RECEIPT.fa.md:
    sha256: "580c80b00d9088b0d1eb31483b747759f3eb4c0f9adee98f616cf822c407f1c8"
    bytes: 989
    lines: 20
    line_count_method: utf8_logical_lines_splitlines
    newline_sequence: LF
    final_newline_present: true
```

## Canonical counts

```yaml
canonical_rule_count: 27
canonical_boundary_count: 18
adversarial_fixture_count: 63
companion_artifact_count: 4
```

## Deterministic text convention

```yaml
encoding: UTF-8
newline_sequence: LF
final_newline_required: true
line_count_method: utf8_logical_lines_splitlines
line_count_definition: decoded UTF-8 text split with splitlines; final newline does not create an extra logical line
raw_byte_hashing: SHA-256 over final exact bytes without pre-hash normalization
```

## Validation results

| Check | Result |
|---|---|
| exact Rule catalog | PASS — 27 unique IDs |
| exact Boundary registry | PASS — 18 unique IDs |
| fixture catalog | PASS — contiguous 1–63 |
| obligation authority semantics | PASS |
| deterministic consequential ordering | PASS |
| Tool Execution Rule and carrier | PASS |
| dual activation paths | PASS |
| PATH A stronger/preferred | PASS |
| PATH B narrow scope/non-independent disclosure | PASS |
| Rule-level projection parity | PASS |
| Core/Companion authority separation | PASS |
| JSON/Markdown/front-matter structure | PASS |
| Manifest consistency | PASS |

## Lifecycle truth

```yaml
same_context_release_integrity: PASS
same_context_final_audit_status: PASS
independent_document_audit_status: NOT_PERFORMED
activation_assurance_level: MAINTAINER_CONTROLLED_DETERMINISTIC
activation_basis: SAME_CONTEXT_DETERMINISTIC_FINALIZATION
activation_status: PASS
same_context_final_audit_ref: AIGOV_v2.5.0_SAME_CONTEXT_FINAL_AUDIT.fa.md
activation_transform_ref: AIGOV_v2.5.0_ACTIVATION_TRANSFORM_REPORT.fa.md
activation_receipt_ref: AIGOV_v2.5.0_ACTIVATION_RECEIPT.fa.md
observed_active_zip_sha256: EXTERNAL_SIDECAR_AND_ARCHIVE_RECEIPT
externally_trusted_active_zip_sha256: null
```
