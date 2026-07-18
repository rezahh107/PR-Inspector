---
title: AIGOV v2.5.0 Incident and Migration Record
version: 2.5.0
document_type: incident_and_migration_record
status: informative
language: fa
source_version: 2.4.0
successor_version: 2.5.0
recorded_at: "2026-07-17T20:56:54+02:00"
---

# AIGOV v2.5.0 Incident and Migration Record

## 1. Trigger

Release Candidate `v2.4.0` دو packaging defect داشت: README وجود Implementation Report را اعلام می‌کرد ولی فایل در archive نبود؛ و external ZIP checksum sidecar تحویل نشده بود. علاوه بر آن، lifecycle policy فقط independent document audit را برای activation معتبر می‌دانست، درحالی‌که maintainer این successor را برای narrow single-maintainer/personal AI-operated use با deterministic same-context finalization تصویب کرد.

## 2. Classification

```yaml
change_class: L3
boundaries:
  - AIGOV-BOUNDARY-GOVERNANCE-AUTHORITY
  - AIGOV-BOUNDARY-INDEPENDENT-REVIEW
  - AIGOV-BOUNDARY-SCOPE-LIFECYCLE
  - AIGOV-BOUNDARY-PROVENANCE
normative_change: true
version_decision: minor_successor_2.5.0
```

## 3. Implemented migration

- `PATH A — Independent Activation` preserved as stronger/preferred.
- `PATH B — Maintainer-Controlled Deterministic Activation` added with narrow eligibility and reduced-assurance disclosure.
- `same_context_final_audit != independent_document_audit` made explicit.
- Lifecycle-bearing Companions advanced to `v1.2.0` and remain separately activated.
- Rule count and Boundary registry preserved; fixtures expanded from 59 to 63.
- Missing Implementation Report and external archive checksum were repaired.

## 4. Compatibility

Repository adoption does not auto-migrate. Existing `v2.4.0` references remain historical. Systems requiring independent assurance should use PATH A; PATH B must not be represented as equivalent.

## 5. Recovery

Any post-audit normative change invalidates the audit binding and requires a fresh Candidate freeze, complete audit, regenerated Manifest, receipts and archive checksum.
