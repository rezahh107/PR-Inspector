---
title: Personal AI-Operated Repository Review Profile
title_fa: پروفایل بازبینی ریپوهای شخصی اداره‌شده با AI
version: 1.2.0
status: active_companion
parent_standard: AI Authority Deterministic Governance v2.5.0
document_role: Repository Profile template for explicitly adopting personal repositories
companion_lifecycle:
  activation_scope: separate_from_core
  adoption_allowed_status: active_companion
  core_activation_effect: none
adoption_eligibility:
  production_adoption: blocked_until_active
  non_blocking_experimental_trial: explicit_owner_authorization_required
---

# Personal AI-Operated Repository Review Profile v1.2.0

## 1. Authority

این Artifact قانون عمومی AIGOV نیست. فقط Repositoryای که exact active identity آن را adopt کند مشمول است.

این Profile حداقل semantics مربوط به `obligation_authority_binding` و `tool_execution_attestation` را از Core فعال می‌گیرد و آن‌ها را redefine یا تضعیف نمی‌کند.

## 2. Defaults

```yaml
repository_review_profile:
  requirement: required
  default_inspection_profile: minimal
  default_evidence_profile: compact
  default_merge_enforcement_profile: owner_controlled
  default_execution_urgency: normal
  structured_comment_publication: required
  comment_policy: append_only
  tamper_resistance: owner_controlled_not_immutable
  owner_only_merge: true
  behavioral_coverage_defaults:
    critical_minimum: fixture_tested
    high_minimum: validator_backed
    composite_critical_requires_minimum_semantic_children: true
```

`minimal` یک Review فنی واقعی است. نبود governance enrichment غیرلازم Technical Green را Yellow نمی‌کند.

## 3. Profile selection

### minimal

exact Repository/PR/Head، exact Scope، independent technical Review، targeted validation، reproduced-failure handling، Compact Receipt Core و structured Comment publication.

### standard

برای impact radius یا validation گسترده‌تر.

### strict

با Activation Conditionهای core، از جمله Secret/Credential، Production، destructive/irreversible، safety، legal/contractual، critical downstream trust یا capability expansion.

## 4. Urgency

`expedited` فقط enrichment غیرمتمایز را حذف می‌کند و exact identity، Head، Scope، Review، validation، Core canonicalization و Receipt publication را حفظ می‌کند.

## 5. Publication policy

```yaml
publication_carrier:
  type: structured_pr_comment
  marker: "PR-INSPECTOR-REVIEW-RECEIPT:v1"
  append_only: true
  exact_head_bound: true
  receipt_core_digest_algorithm: RFC8785-JCS-SHA256
  publisher_identity_required: true
  readback_required: true
```

Comment carrier رسمی discovery/publication است؛ canonical truth، verified package و immutable Receipt Core است.

## 6. Merge and post-Merge governance

```text
technical_status
!= merge_readiness_result
!= merge_governance_status
!= post_merge_closure_status
```

Owner-only Merge و current-main validation اجباری‌اند. `STATUS_DRIFT` closure و dependent work را block می‌کند؛ historical readiness را بازنویسی نمی‌کند.

## 7. Behavioral coverage

Repository باید active Behavioral Rule Coverage Contract را جداگانه adopt کند یا equivalent canonical contract داشته باشد. Critical composite Rule با Boolean تنها accepted نیست.

## 8. Migration safety

```text
publisher implementation
→ Receipt Core canonicalization/read-back/retry validation
→ behavioral coverage inventory
→ non-blocking trial
→ activate/adopt Companions
→ separate owner policy transition
→ required activation
→ post-Merge reconciliation
```

## 9. Repository adoption template

```yaml
repository_review_policy:
  schema_version: "1.1"
  repository_identity: "<owner/repo + repository_id>"
  policy_version: "<repo-policy-version>"
  policy_authority_ref: "<canonical-path>"
  policy_identity: "sha256:<digest>"
  adopted_profile:
    name: personal_ai_operated_repository_review_profile
    version: "1.2.0"
    identity: "sha256:<profile-digest>"
  default_requirement: required
  default_inspection_profile: minimal
  default_evidence_profile: compact
  default_merge_enforcement_profile: owner_controlled
  default_execution_urgency: normal
  publication_policy:
    required_when_review_required: true
    allowed_carriers: [structured_pr_comment]
```

## 10. Acceptance

- exact active Profile identity adopted؛
- Publication Contract active یا equivalent contract exact-adopted؛
- Behavioral Coverage Contract active یا equivalent contract exact-adopted؛
- Publisher محدود و operational؛
- JCS Core digest deterministic؛
- Head change Review را stale می‌کند؛
- Retry Core را تغییر نمی‌دهد؛
- Technical status از Merge governance و post-Merge closure جداست؛
- strict Activation Effects قابل bypass با urgency نیستند.

## 11. Companion activation lifecycle

این Profile مستقل از Core فعال می‌شود. `PATH A` با fresh independent companion audit مسیر stronger و preferred است. `PATH B` فقط برای single-maintainer/personal AI-operated deployment، با `audit_independence: NOT_INDEPENDENT`، deterministic integrity، zero blocking findings، explicit reduced-independence acceptance و receipt جدا مجاز است. Core activation هیچ اثر خودکاری بر status این Profile ندارد.
