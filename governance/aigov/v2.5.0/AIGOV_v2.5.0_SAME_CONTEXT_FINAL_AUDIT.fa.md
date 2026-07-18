---
title: AIGOV v2.5.0 Same-Context Final Audit
document_type: same_context_final_audit
audit_independence: NOT_INDEPENDENT
audit_assurance_level: MAINTAINER_CONTROLLED_DETERMINISTIC
audited_package_identity: AIGOV_v2.5.0_release_candidate
audited_core_version: 2.5.0
audited_core_sha256: 4630d88515a87930412b4b438bfd19a4badc0807cf692413238b283fa1602c95
audited_manifest_sha256: dd8c071f12ad225c9f416b58f098af728fe14cd18930cdfe2ddeaba0ae36f2d0
audited_candidate_zip_sha256: 356de0be18b396628002b75669983faf0de58fc9a79fe67fbbdb639c60023f92
audit_timestamp: "2026-07-17T20:56:54+02:00"
same_context_final_audit_status: PASS
activation_eligibility: PASS
---

# AIGOV v2.5.0 Same-Context Final Audit

## Audit scope

Read-only audit of the exact frozen Candidate archive. This audit is explicitly not independent and does not claim assurance equivalence with PATH A.

## Audit checks

| Domain | Result | Evidence |
|---|---|---|
| exact Candidate identity | PASS | Core, Manifest and ZIP hashes above |
| required artifacts | PASS | Implementation Report present; no duplicate archive members |
| Rule count | PASS | 27 unique canonical Rule IDs |
| Boundary count | PASS | 18 unique canonical Boundary IDs |
| fixture count | PASS | contiguous 1–63 |
| dual activation lifecycle | PASS | PATH A preserved/preferred; PATH B narrow and non-equivalent |
| assurance disclosure | PASS | `NOT_INDEPENDENT` + `MAINTAINER_CONTROLLED_DETERMINISTIC` |
| obligation authority semantics | PASS | preserved |
| Tool Execution semantics | PASS | preserved |
| Core/Companion authority separation | PASS | separate activation required |
| projection parity | PASS | 27 semantic rows; release row strengthened |
| JSON and Markdown structure | PASS | parsed; fences balanced |
| line-count reproducibility | PASS | UTF-8/LF/final newline/splitlines |
| Manifest hashes and byte counts | PASS | recomputed from frozen bytes |
| candidate sidecar | PASS | exact external digest; not inside ZIP |

## Findings

```yaml
blocking_findings: []
nonblocking_findings: []
same_context_final_audit_status: PASS
activation_eligibility: PASS
selected_activation_path: PATH_B_MAINTAINER_CONTROLLED_DETERMINISTIC_ACTIVATION
independent_document_audit_status: NOT_PERFORMED
reduced_independence_accepted: true
```
