---
title: PR Inspector Review Receipt Publication Contract
title_fa: قرارداد انتشار رسید بازبینی PR Inspector
version: 1.2.0
status: active_companion
parent_standard: AI Authority Deterministic Governance v2.5.0
document_role: bounded integration contract for publishing verified Review Receipt Cores
companion_lifecycle:
  activation_scope: separate_from_core
  integration_allowed_status: active_companion
  core_activation_effect: none
adoption_eligibility:
  production_integration: blocked_until_active
  non_blocking_experimental_trial: explicit_owner_authorization_required
---

# PR Inspector Review Receipt Publication Contract v1.2.0

## 1. Authority and boundary

`PR-Inspector` می‌تواند read-only Review engine باقی بماند. Publisher یک capability جداست و فقط exact verified Receipt Core را منتشر می‌کند. Candidate این Contract integration authority ایجاد نمی‌کند.

این bounded flow باید با `AIGOV-TOOL-EXECUTION-001` و Core-defined `tool_execution_attestation` conform باشد، اما این Contract generic Rule یا Carrier را redefine نمی‌کند.

```text
PR-Inspector read-only engine
→ verified review package
→ immutable Review Receipt Core
→ RFC 8785/JCS digest
→ bounded Publisher
→ structured PR Comment
→ read-back validation
```

## 2. Review Receipt Core

```yaml
review_receipt_core:
  receipt_schema_version: "1.0"
  review_id: "<stable-id>"
  sequence_number: 1
  supersedes_review_id: null
  supersession_reason: null
  repository_full_name: "<owner/repo>"
  repository_id: "<id>"
  pr_number: 0
  reviewed_head_sha: "<sha>"
  scope_digest: "sha256:<digest>"
  protocol_version: "<active PR-Inspector protocol>"
  inspector_repository: "rezahh107/PR-Inspector"
  inspector_repository_id: "<id>"
  inspector_commit_sha: "<sha>"
  inspection_profile: minimal | standard | strict
  evidence_profile: compact | full | high_assurance
  execution_urgency: normal | expedited
  technical_status: GREEN_TECHNICALLY_READY | YELLOW_CHANGES_OR_VERIFICATION_REQUIRED | RED_DO_NOT_MERGE
  canonical_package_digest: "sha256:<digest>"
  decision_projection_digest: "sha256:<digest>"
  performed_at: "<UTC>"
```

Publisher identity، Comment ID، timestamp و current validity داخل Core نیستند.

## 3. Canonicalization

```text
Core object
→ RFC 8785 JSON Canonicalization Scheme
→ UTF-8 without BOM
→ SHA-256
→ receipt_core_digest
```

YAML فقط rendering انسانی است. Hash روی YAML، whitespace یا key order آزاد ممنوع است.

## 4. Publication attempt

```yaml
publication_attempt:
  publication_attempt_id: "<id>"
  review_id: "<same-id>"
  receipt_core_digest: "sha256:<digest>"
  publication_status: not_attempted | publishing | published_verified | publication_failed
  publisher_identity:
    actor_login: "<login>"
    actor_id: "<id>"
    actor_type: User | Bot | App
    github_app_id: null
    installation_id: null
  target_repository_full_name: "<owner/repo>"
  target_repository_id: "<id>"
  pr_number: 0
  head_observed_at_publish: "<sha>"
  comment_id: null
  published_at: null
  readback_verified_at: null
  published_body_sha256: null
  failure_reason: null
```

## 5. Comment format

Comment body before publication:

````markdown
<!-- PR-INSPECTOR-REVIEW-RECEIPT:v1 -->

## PR Inspector Review Receipt

```yaml
publication_attempt_id: "<pre-generated-id>"
review_receipt_core: <rendered exact Core>
receipt_core_digest: "sha256:<JCS digest>"
```

This receipt records technical Review only. It is not Approval, Merge authorization, deployment authorization, or Repository-settings proof.
````

`publisher_identity`، `comment_id`، `created_at`، `updated_at`، `readback_verified_at` و `published_body_sha256` از authoritative GitHub response مشتق و در publication attempt record خارج از body ثبت می‌شوند. این جداسازی از self-referential body hash و نیاز به edit بعد از publication جلوگیری می‌کند.

## 6. Publisher capability

```yaml
publisher_capability:
  allowed_action:
    - publish_exact_verified_review_receipt
  exact_target_binding:
    repository: "<exact>"
    repository_id: "<id>"
    pr_number: 0
    reviewed_head_sha: "<sha>"
  forbidden_actions:
    - alter_receipt_core
    - modify_repository_content
    - approve_pull_request
    - merge_pull_request
    - modify_labels
    - modify_settings
    - modify_rulesets
    - access_secrets
    - deploy
```

## 7. Publication sequence

1. receive verified Core bytes/object and expected JCS digest؛
2. recompute digest independently؛
3. re-fetch exact PR and current Head؛
4. reject Head mismatch؛
5. publish one append-only Comment؛
6. re-fetch Comment؛
7. verify marker، platform Publisher identity، target، publication_attempt_id، rendered Core semantics، Core digest و exact body digest؛
8. return `published_verified` only after read-back PASS.

## 8. Retry and idempotency

Retry همان Review Core را تغییر نمی‌دهد. `review_id` و `receipt_core_digest` ثابت می‌مانند؛ `publication_attempt_id`، Comment ID و timestamps تغییر می‌کنند.

```text
Head unchanged + Core digest unchanged
→ republish same Core

Head changed
→ Review STALE
→ fresh Review required
```

Idempotency key:

```text
review_id + repository_id + pr_number + reviewed_head_sha + receipt_core_digest
```

## 9. Append-only, supersession and conflict

Publisher prior Comments را edit/delete نمی‌کند. Rereview Core جدید و optional supersession chain می‌سازد. Retry publication supersession نیست. چند Core متعارض بدون chain معتبر → `RECEIPT_CONFLICT`.

## 10. Acceptance tests

1. valid Core canonicalizes deterministically؛
2. key order یا YAML whitespace digest Core را تغییر نمی‌دهد؛
3. changed semantic field digest را تغییر می‌دهد؛
4. Publisher metadata Core digest را تغییر نمی‌دهد؛
5. valid exact-head attempt publishes and reads back؛
6. Head drift rejects؛
7. unauthorized Publisher rejects؛
8. body mutation rejects؛
9. retry preserves Core identity؛
10. rereview creates new Core and valid supersession؛
11. conflicting Cores block؛
12. Comment edit invalidates unless full revalidation passes.

## 11. Activation

این Contract فقط با receipt جدا فعال می‌شود. `PATH A` با fresh independent companion audit stronger و preferred است. `PATH B` فقط در single-maintainer/personal AI-operated deployment، با `audit_independence: NOT_INDEPENDENT`، deterministic integrity، zero blocking findings و explicit reduced-independence acceptance مجاز است. Core activation آن را فعال نمی‌کند.
