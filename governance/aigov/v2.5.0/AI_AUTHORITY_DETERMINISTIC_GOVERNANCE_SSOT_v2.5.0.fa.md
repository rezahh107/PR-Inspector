---
title: AI Authority Deterministic Governance — Source of Truth
title_fa: سند حقیقت حاکمیت دترمنستیک بر قضاوت‌های احتمالاتی هوش مصنوعی
version: 2.5.0
status: active_governing_standard
document_role: reusable governance source of truth for AI-operated repositories
language: Persian with English technical identifiers
normative_authority_model:
  identity_precedence: front_matter identity fields govern version, status, title, and document role
  policy_precedence: detailed normative clause > normative rule catalog > normative summary > operational projection > informative text
  embedded_orchestrator_prompt:
    projection_type: derived_and_parity_validated
    generated_projection: false
    normative_authority: false
    source_standard_version: 2.5.0
    parity_validation_required: true
    candidate_parity_validation_ref: AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.projection-parity-matrix.json
    active_parity_validation_ref: AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.active-release-integrity.md
  audit_prompt:
    projection_type: derived_and_parity_validated
    generated_projection: false
    normative_authority: false
    source_standard_version: 2.5.0
    parity_validation_required: true
    candidate_parity_validation_ref: AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.projection-parity-matrix.json
    active_parity_validation_ref: AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.active-release-integrity.md
intended_use:
  - repository bootstrap and migration
  - agent operating contract
  - proportional independent review
  - review receipt publication and discovery
  - PR review, conditional Merge readiness and post-Merge closure
  - prevention of silent scope reduction, false completion and false permanent blocking
  - method-aware Merge-result verification
  - control cost/effectiveness governance
  - behavioral-rule enforcement coverage and semantic-carrier integrity
  - authority-bound obligations and source-bound verifiable tool execution
standard_lifecycle:
  status_source: front_matter.status
  repository_adoption_is_separate: true
  release_evidence_location: external_exact_bound_artifacts
  preferred_activation_path: PATH_A_INDEPENDENT_ACTIVATION
  activation_paths:
    PATH_A_INDEPENDENT_ACTIVATION:
      assurance_level: INDEPENDENTLY_AUDITED
      requires: [fresh_independent_document_audit, exact_identity_binding, bounded_activation_transform]
    PATH_B_MAINTAINER_CONTROLLED_DETERMINISTIC_ACTIVATION:
      assurance_level: MAINTAINER_CONTROLLED_DETERMINISTIC
      intended_use: single-maintainer or personal AI-operated governance systems where isolated reviewer infrastructure is unavailable and reduced independence is explicitly accepted
      requires: [same_context_final_audit, deterministic_release_integrity, projection_parity, zero_blocking_findings, explicit_assurance_disclosure, bounded_activation_transform]
  declared_release_artifacts:
    candidate_release_integrity: AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.release-integrity.md
    same_context_final_audit: AIGOV_v2.5.0_SAME_CONTEXT_FINAL_AUDIT.fa.md
    independent_document_audit: optional_path_a_external_artifact
    activation_transform: AIGOV_v2.5.0_ACTIVATION_TRANSFORM_REPORT.fa.md
    activation_receipt: AIGOV_v2.5.0_ACTIVATION_RECEIPT.fa.md
    active_release_integrity: AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.active-release-integrity.md
    active_bundle_manifest: bundle-manifest.json
    candidate_projection_parity_matrix: AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.projection-parity-matrix.json
    active_bundle_archive_digest: AIGOV_v2.5.0_active_bundle.zip.sha256
  evidence_binding_rule: declared paths are not evidence; active status is valid only when the selected-path audit, activation receipt, transform report, active release-integrity, active manifest and external archive sidecar exact-bind the applicable identities
companion_artifacts:
  personal_repository_profile: PERSONAL_AI_OPERATED_REPOSITORY_REVIEW_PROFILE_v1.2.0.fa.md
  pr_inspector_publication_contract: PR_INSPECTOR_REVIEW_RECEIPT_PUBLICATION_CONTRACT_v1.2.0.fa.md
  incident_and_migration_record: AIGOV_v2.5.0_INCIDENT_AND_MIGRATION_RECORD.fa.md
  behavioral_rule_coverage_contract: AIGOV_BEHAVIORAL_RULE_COVERAGE_CONTRACT_v1.2.0.fa.md
companion_lifecycle:
  core_activation_does_not_activate_companions: true
  core_normative_dependency_on_active_companions: false
  personal_repository_profile: separate_activation_required_before_adoption
  pr_inspector_publication_contract: separate_activation_required_before_integration
  incident_and_migration_record: informative_no_activation_required
  behavioral_rule_coverage_contract: separate_activation_required_before_adoption
standard_status_vocabulary:
  - draft
  - release_candidate
  - active_governing_standard
  - superseded
  - withdrawn
activation_assurance_level_vocabulary:
  - INDEPENDENTLY_AUDITED
  - MAINTAINER_CONTROLLED_DETERMINISTIC
activation_basis_vocabulary:
  - INDEPENDENT_DOCUMENT_AUDIT_FINALIZATION
  - SAME_CONTEXT_DETERMINISTIC_FINALIZATION
repository_adoption_status_vocabulary:
  - not_adopted
  - partially_adopted
  - adopted
  - migration_required
  - blocked_open_enforcement_gaps
version_conformance_status_vocabulary:
  - valid_under_adopted_version
  - not_yet_conformant_with_target_version
  - conformant_with_target_version
repository_risk_profile_vocabulary:
  - downstream_trust_authority
  - internal_tool
  - personal_script
---

# AI Authority Deterministic Governance — Source of Truth

## 0.1 تغییرات نسخه 2.5.0

> Authority: INFORMATIVE — truth-constrained changelog

نسخهٔ `2.5.0` جانشین exact Release Candidate نسخهٔ `v2.4.0` است. تغییر activation prerequisite یک تغییر هنجاری در lifecycle policy است؛ بنابراین identity نسخهٔ `v2.4.0` بازنویسی نشده و successor minor version ایجاد شده است.

اصلاحات اصلی:

1. حفظ کامل 27 Rule، 18 Boundary و همهٔ controls نسخهٔ `v2.4.0`؛
2. تعریف دو activation path معتبر برای release استاندارد؛
3. حفظ `PATH A — Independent Activation` به‌عنوان مسیر stronger و preferred؛
4. افزودن `PATH B — Maintainer-Controlled Deterministic Activation` برای single-maintainer یا personal AI-operated governance systems با پذیرش صریح reduced independence guarantee؛
5. تعریف `activation_assurance_level` با مقادیر `INDEPENDENTLY_AUDITED` و `MAINTAINER_CONTROLLED_DETERMINISTIC`؛
6. الزام disclosure صریح `same_context_final_audit != independent_document_audit`؛
7. تقویت `AIGOV-STANDARD-RELEASE-001`، minimum-enforcement table، Coverage Matrix، Acceptance Criteria، Embedded Orchestrator Prompt و Audit Prompt؛
8. افزودن fixtures 60–63 برای lifecycle dual-path، mislabeling و scope restriction؛
9. ارتقای Companionهای lifecycle-bearing به `v1.2.0` و حفظ activation جداگانهٔ آن‌ها؛
10. افزودن Implementation Report، Same-Context Final Audit، Activation Transform Report و exact activation receipts؛
11. بازتولید projection-parity matrix، release-integrity، Manifest، hashes و archive checksum sidecar.

Version decision:

```text
v2.4.0 remains an immutable historical Release Candidate identity.
v2.5.0 is a minor successor because activation-policy semantics change without removing existing Rules.
Lifecycle-bearing Companions advance to v1.2.0.
Candidate publication begins with front_matter.status = release_candidate.
```

## 0.2 هویت، authority و release state

> Authority: NORMATIVE

### 0.2.1 Identity authority

فقط front matter برای `version`، `status`، `title` و `document_role` authoritative است. هر تعارض دیگر `DOCUMENT_INTEGRITY_DRIFT` است.

```text
release_candidate != active_governing_standard
active standard != repository adopted
repository adopted != every control enforced
technical Green != Merge authorization
Merge observed != post-Merge verified
```

### 0.2.2 Policy precedence

```text
detailed normative clause
  > normative rule catalog
  > normative summary
  > operational projection
  > informative example or incident rationale
```

### 0.2.3 Section authority registry

| Section | Authority |
|---|---|
| 0.1 | INFORMATIVE changelog |
| 0.2 | NORMATIVE identity and release truth |
| 0.3 | OPERATIONAL PROJECTION — NON-NORMATIVE |
| 1 | NORMATIVE purpose |
| 2 | MIXED: rationale informative; explicit invariants normative |
| 3–13 | NORMATIVE |
| 14 | NORMATIVE Rule Catalog |
| 15–18 | NORMATIVE |
| 19 | INFORMATIVE adoption sequence constrained by normative clauses |
| 20 | NORMATIVE Acceptance Criteria |
| 21–22 | OPERATIONAL PROJECTION — NON-NORMATIVE |
| 23–24 | NORMATIVE migration and release lifecycle |
| 25 | INFORMATIVE fixtures; expected outcomes are truth-constrained |
| 26 | NORMATIVE summary |

### 0.2.4 Canonical version

```yaml
canonical_document_version:
  source: front_matter.version
  value: "2.5.0"
```

هر active reference باید `2.5.0` باشد. references به `v2.1.0` یا `v2.2.0` فقط با برچسب historical مجازند.

### 0.2.5 Release status truth

این فایل complete standalone release artifact است و status آن فقط از `front_matter.status` خوانده می‌شود. خود فایل، چه در حالت Candidate و چه در حالت active، به‌تنهایی activation evidence نیست. `active_governing_standard` فقط وقتی معتبر است که یکی از دو path مجاز کامل شود: `PATH A` با fresh independent document audit، یا `PATH B` با same-context final audit، deterministic integrity، projection parity، zero blocking findings و disclosure صریح reduced independence. `same_context_final_audit != independent_document_audit`. هر دو path به exact bounded activation transform، activation receipt، active release-integrity، active Manifest و external ZIP sidecar نیاز دارند.

## 0.3 Embedded Orchestrator Prompt

> Authority: OPERATIONAL PROJECTION — NON-NORMATIVE

```yaml
embedded_prompt_metadata:
  name: AI Governance Adoption and Repository Work Orchestrator Prompt
  projection_version: "2.5.0"
  source_standard_version: "2.5.0"
  generated_projection: false
  normative_authority: false
  parity_validation_required: true
  candidate_parity_validation_ref: AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.projection-parity-matrix.json
  active_parity_validation_ref: AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.active-release-integrity.md
```

````text
# AI Governance Adoption and Repository Work Orchestrator Prompt v2.5.0

[AUTHORITY]
Canonical NORMATIVE clauses of AIGOV v2.5.0 govern every conflict. This prompt cannot create Rules, statuses, Boundaries or exceptions.

[START AND DETERMINISTIC PRECHECKS]
Resolve live Repository identity, canonical authorities, current status, target identity, exact Head, capabilities and current Repository Profile. Run every applicable required mechanically decidable precheck before setting `consequential_decision_authorized=true`. `PASS` and authority-bound `NOT_APPLICABLE_WITH_AUTHORITY` are non-blocking; `FAIL` and `BLOCKED_INSUFFICIENT_EVIDENCE` block consequential authorization. A blocked state does not prohibit failure explanation, Evidence analysis, root-cause diagnosis or bounded Recovery guidance. Never infer execution or enforcement from prose.

[AUTHORITY-BOUND OBLIGATIONS, APPLICABILITY AND TRIGGER]
Every mandatory, rejecting, blocking, scope-limiting, evidence-requiring or tool-constraining obligation must exact-bind to canonical authority through `obligation_authority_binding`. Resolve rule_applicability_status independently from rule_trigger_status. Invented applicability, trigger or profile exclusion cannot create authority. UNKNOWN or insufficient evidence cannot silently become NOT_TRIGGERED, NOT_APPLICABLE or optional.

[STATUS DOMAINS]
Keep separate: technical_status, review_execution_status, receipt_publication_status, receipt_validation_status, review_validity, merge_readiness_result, merge_governance_status, post_merge_closure_status, dependent_work_authorization, implementation_status, session_status, repository_adoption_status and version_conformance_status.

[CLASSIFICATION]
Resolve canonical AIGOV-BOUNDARY IDs and change_class L0-L4. change_class does not directly determine independent_review_required. Reclassify when new evidence crosses a Boundary.

[REPOSITORY RISK AND CLASSIFICATION DRIFT]
Resolve exact Repository risk profile. Do not generalize Repository-specific recovery tasks. Classification-drift metrics are advisory and never substitute for exact target classification or STATUS_DRIFT.

[SCOPE, PROGRESS AND EVIDENCE]
Persist exact Scope and every readiness-affecting Scope Change Disclosure. No exclusion, deferral or omission is valid without source-bound authority. Keep plan, implementation, Review, publication, Merge and post-Merge closure as separate states. Bind every factual, mandatory, rejecting, blocking, readiness or completion claim to exact Evidence and verified obligation authority; never fabricate historical Evidence. Use the smallest sufficient Evidence that closes the actual Failure Boundary.

[BEHAVIORAL RULE COVERAGE]
Treat prompt/protocol repositories as behavioral source code. Discover candidate gates through modal-language scanning, then classify normative intent and risk. Critical or High behavioral gates require an honest coverage record. Detect EFBG and Semantic Illusion. A caller-supplied boolean cannot prove a composite predicate. Require Minimum Semantic Children, cross-field constraints, validator evidence, invalid fixtures and downstream rejection proportional to risk.

[TOOL EXECUTION]
For every consequential tool action, verify capability authority, tool/schema identity, exact target, source-to-parameter bindings, declared transformations, invocation Evidence, result capture, required read-back and result-to-claim bindings. Schema-valid but source-detached parameters, wrong targets, claimed execution without invocation, unverified success, missing required read-back or result-detached claims are blocking.

[REVIEW POLICY]
Resolve exact versioned policy. Each activated condition returns minimum requirement, inspection profile, evidence profile, Merge enforcement profile and urgency restrictions. Missing, stale, invalid, conflicting or identity-unverified policy yields BLOCKED_POLICY_UNRESOLVED.

[REVIEW EXECUTION AND PUBLICATION]
Keep immutable review_receipt_core separate from publication_attempt. Canonicalize Receipt Core with RFC 8785/JCS over UTF-8 and hash with SHA-256. Publisher identity and timestamps belong only to publication_attempt. If Head and Core digest are unchanged, retry publication without rerunning Review. If Head changed, mark Review STALE.

[INDEPENDENCE]
Required Review must be independent, current, exact-head and exact-scope. Implementer self-GREEN is never independent acceptance. Optional advisory Review cannot authorize Merge or replace validation.

[MERGE READINESS]
Evaluate pre-Merge readiness only from current pre-Merge predicates. Do not rewrite historical merge_readiness_result after Merge.

[POST-MERGE CLOSURE]
After Merge, detect actual Merge method, verify resulting default-branch content, run current-main validation and reconcile status. STATUS_DRIFT blocks post_merge_closure_status and dependent_work_authorization, not the historical pre-Merge readiness result.

[POLICY TRANSITION]
Use the exact typed owner-policy transition record. The Gate being changed cannot deadlock transition solely by its own absence. Standard safety Activation Conditions remain applicable with their complete minimum effects.

[COST, EVIDENCE PROPORTIONALITY AND RECOVERY]
Every new or stronger Blocking Gate requires a distinct Failure Boundary, no cheaper equivalent, automatically persisted Evidence and bounded Recovery. Use the smallest sufficient Evidence; neither under-evidence nor duplicate evidence without marginal value is acceptable. Fail closed does not mean block forever.

[STANDARD RELEASE]
Verify Candidate and active digests, projection parity matrix, selected activation path, exact audit identity binding, assurance disclosure, bounded metadata-only transform, active release-integrity, activation Receipt, active bundle manifest and external ZIP digest. Prefer PATH A. Permit PATH B only for its narrow declared scope, with `audit_independence=NOT_INDEPENDENT`, `activation_assurance_level=MAINTAINER_CONTROLLED_DETERMINISTIC` and explicit acceptance of reduced independence. Core activation never activates Candidate companions.

[RULE COVERAGE]
Evaluate and report all canonical Rules exactly once: AIGOV-START-001, AIGOV-APPLICABILITY-001, AIGOV-SCOPE-001, AIGOV-SCOPE-DISCLOSURE-001, AIGOV-PROGRESS-001, AIGOV-EVIDENCE-001, AIGOV-INDEPENDENCE-001, AIGOV-REVIEW-PUBLICATION-001, AIGOV-STALE-001, AIGOV-MERGE-001, AIGOV-POLICY-TRANSITION-001, AIGOV-STATUS-RECONCILIATION-001, AIGOV-CHANGE-CLASS-001, AIGOV-CHANGE-ESCALATION-001, AIGOV-REPOSITORY-RISK-001, AIGOV-CLASSIFICATION-DRIFT-001, AIGOV-CONTROL-EFFECTIVENESS-001, AIGOV-DOCUMENT-INTEGRITY-001, AIGOV-STANDARD-RELEASE-001, AIGOV-EVIDENCE-PROPORTIONALITY-001, AIGOV-REPORTING-001, AIGOV-SECURITY-PROFILE-001, AIGOV-HUMAN-001, AIGOV-COACH-001, AIGOV-SEMANTIC-CARRIER-001, AIGOV-BEHAVIORAL-COVERAGE-001 and AIGOV-TOOL-EXECUTION-001.

[REPORTING, HUMAN AUTHORITY AND OWNER GUIDANCE]
Keep owner action separate from technical approval. Report the smallest complete truth, preserve blockers and uncertainty, and provide exactly one precise non-technical owner action without inventing authority.

[OUTPUT]
Report exact identities, obligation authority bindings, deterministic precheck states, consequential authorization state, applicability, trigger state, classification, Tool Execution attestation, Review profiles, technical status, Receipt Core identity, publication attempt, Merge governance, post-Merge closure, behavioral coverage gaps, historical gaps and exactly one next owner action.
````

## 1. هدف و دامنه

> Authority: NORMATIVE

این استاندارد برای Repositoryهایی است که AI تصمیم فنی، طراحی، implementation و review را با تکیه بر Evidence و deterministic Gates انجام می‌دهد و مالک ممکن است تنها اقدام اداری نهایی را انجام دهد.

اصول مرکزی:

```text
AI is the authority for technical decisions.
Evidence is the authority for factual reality.
Deterministic gates constrain probabilistic judgments.
Owner action is not technical approval.
Fail closed is not permission to block forever.
```

این استاندارد reusable است. تصمیم‌های خاص یک مجموعه Repository باید در Repository Profile versioned ثبت شوند، نه اینکه به‌عنوان قانون عمومی وارد core شوند.

## 2. مسئله و rationale طراحی

> Authority: MIXED

### 2.1 Plan، implementation، review و Merge یک حقیقت نیستند

```text
plan != implementation
implementation != reviewed
review performed != receipt published
technical Green != Merge authorization
Merge observed != post-Merge verified
```

### 2.2 Evidence publication gap

Review ممکن است انجام شود ولی Evidence آن در حافظهٔ قابل‌کشف Repository ثبت نشود. بنابراین execution، immutable Receipt Core و publication attempt باید جدا ثبت شوند.

### 2.3 False Permanent Blocking

Fail-closed بدون Recovery محدود می‌تواند به بن‌بست دائمی تبدیل شود. هر Gate blocking باید مسیر truthful و bounded برای evidence غیرقابل‌بازتولید یا transition policy داشته باشد.

### 2.4 Proportional review

Review requirement، inspection depth، evidence depth، Merge enforcement و urgency محورهای مستقل‌اند. `minimal` Review ضعیف نیست و `expedited` invariant فنی را حذف نمی‌کند.

### 2.5 Cost/benefit

هر کنترل blocking باید Failure Boundary مستقل، risk reduction متمایز، هزینه، burden و Recovery مشخص داشته باشد. کنترل بدون ارزش افزوده باید automate، simplify، narrow، conditionalize یا retire شود.

### 2.6 Incident rationale — informative

حادثه historical مربوط به `rezahh107/EV4-Decision-Kernel` در Companion Incident Record ثبت شده است. درس عمومی آن:

```text
Review performed != Receipt published
content truth != Git topology
Fail closed != block forever
```

### 2.7 Tool-native but contract-conformant

استاندارد shape و semantics حداقلی Carrier را تعیین می‌کند. ابزار می‌تواند خروجی طبیعی خود را استفاده کند فقط وقتی contract-conformant و independently verifiable باشد.

برای predicateهای mechanically decidable، ترتیب زیر هنجاری است:

```text
required deterministic eligibility and structural validation
before
consequential authorization by probabilistic judgment
```

این ordering فقط اثر مجازکنندهٔ judgment را محدود می‌کند. مدل در حالت `FAIL` یا `BLOCKED_INSUFFICIENT_EVIDENCE` همچنان می‌تواند failure را توضیح دهد، Evidence را تحلیل کند، root cause را تشخیص دهد و Recovery غیرمجازکننده پیشنهاد کند.

Tool execution consequential باید زنجیرهٔ زیر را exact-bound کند:

```text
capability authority
→ tool selection
→ tool schema identity
→ exact target identity
→ authoritative source inputs
→ source-to-parameter binding
→ validated transformation
→ actual invocation
→ execution result
→ required read-back
→ result-to-claim binding
```

Schema validity به‌تنهایی semantic parameter fidelity یا target correctness را اثبات نمی‌کند.

Minimum startup ordering carrier:

```yaml
startup_record:
  repository_identity: "<exact>"
  target_identity: "<exact-or-null>"
  head_identity: "<exact-or-null>"
  authority_refs: []
  capability_refs: []
  deterministic_prechecks:
    - check_id: "<stable-id>"
      authority_ref: "<exact-source>"
      status: PASS | NOT_APPLICABLE_WITH_AUTHORITY | FAIL | BLOCKED_INSUFFICIENT_EVIDENCE
      evidence_ref: "<exact-ref>"
      non_applicability_decision_ref: "<exact-ref-or-null>"
  consequential_decision_authorized: true | false
  non_authorizing_analysis_permitted: true
```

Cross-field constraints:

```text
consequential_decision_authorized == true
only if
all applicable required prechecks are PASS or NOT_APPLICABLE_WITH_AUTHORITY

NOT_APPLICABLE_WITH_AUTHORITY
requires
exact canonical authority + sufficient Evidence + typed non-applicability decision

FAIL or BLOCKED_INSUFFICIENT_EVIDENCE
requires
consequential_decision_authorized == false
```

### 2.8 Separation of artifacts

Core قواعد reusable را نگه می‌دارد. Personal defaults، PR-Inspector publication protocol، Behavioral Rule Coverage و Incident rationale در Artifactهای جدا هستند.

### 2.9 Semantic Illusion

وجود field یا Boolean به‌تنهایی اثبات نمی‌کند Agent مفهوم Rule را رعایت کرده است. اگر predicate مرکب باشد، carrier باید Minimum Semantic Children و cross-field constraints داشته باشد. Boolean فقط وقتی projection معتبر است که از Carrier ساختاریافته و validator result مشتق شده باشد.

```text
caller_supplied_boolean != semantic_evidence
validator_derived_projection + canonical_evidence_ref = acceptable_projection
```

### 2.10 Enforcement-Free Behavioral Gate

`EFBG` Rule رفتاری Critical یا High است که فقط در prose، prompt، example یا role guidance وجود دارد و schema، validator، failing fixture، CI یا downstream rejection متناظر ندارد. EFBG باید صریح ثبت و با کوچک‌ترین mechanism کافی بسته شود؛ modal-language scan فقط discovery heuristic است، نه verdict authoritative.

## 3. Authority، trust و status domains

> Authority: NORMATIVE

### 3.1 Authority separation

```text
execution authority
repository policy authority
technical decision authority
Evidence reality authority
review producer authority
receipt publisher authority
owner Merge authority
```

هیچ‌کدام بدون rule صریح جای دیگری را نمی‌گیرد.

#### 3.1.1 Authority-bound obligation invariant

```text
model-generated obligation != authoritative obligation
```

Obligation فقط وقتی می‌تواند mandatory، rejecting، blocking، scope-limiting، evidence-requiring یا tool-constraining شود که exact-bound به canonical authority باشد.

```yaml
obligation_authority_binding:
  carrier_id: obligation_authority_binding
  governed_rules:
    - AIGOV-APPLICABILITY-001
    - AIGOV-SCOPE-001
    - AIGOV-EVIDENCE-001
    - AIGOV-TOOL-EXECUTION-001
  obligation_id: "<stable-id>"
  obligation_type: rule | applicability_condition | trigger | required_field | rejection_criterion | evidence_requirement | scope_exclusion | deferred_work_condition | tool_parameter_constraint
  authority_ref: "<canonical-source>"
  authority_identity: "<digest/sha/versioned-id>"
  source_locator: "<section/rule/schema-path>"
  resolution_status: VERIFIED_SOURCE_BOUND | UNRESOLVED | REJECTED_NOT_AUTHORITATIVE
```

Cross-field invariant:

```text
mandatory | rejecting | blocking | scope-limiting | evidence-requiring | tool-constraining
requires
resolution_status == VERIFIED_SOURCE_BOUND
```

`UNRESOLVED` obligation authority جدید ایجاد نمی‌کند. `REJECTED_NOT_AUTHORITATIVE` باید از enforcement، rejection، Scope reduction و tool constraints حذف شود، ولی historical trace آن می‌تواند برای Audit باقی بماند.

### 3.2 Canonical status vocabularies

```yaml
rule_applicability_status:
  - APPLICABLE_NOW
  - APPLICABLE_AFTER_DEPENDENCY
  - OUT_OF_SCOPE_BY_ACTIVE_PROFILE
  - NOT_APPLICABLE_TO_THIS_REPOSITORY
  - UNKNOWN_NEEDS_EVIDENCE
rule_trigger_status:
  - TRIGGERED
  - NOT_TRIGGERED_FOR_THIS_TARGET
  - BLOCKED_INSUFFICIENT_EVIDENCE
review_execution_status:
  - not_started
  - in_progress
  - performed
  - failed
receipt_publication_status:
  - not_required
  - not_attempted
  - publishing
  - published_verified
  - publication_failed
receipt_validation_status:
  - not_checked
  - current_valid
  - stale
  - invalid
  - conflicting
review_validity:
  - CURRENT
  - STALE
  - UNKNOWN
review_requirement:
  - required
  - optional_advisory
review_requirement_status:
  - REQUIRED
  - OPTIONAL_ADVISORY
  - NOT_TRIGGERED_FOR_THIS_TARGET
  - BLOCKED_POLICY_UNRESOLVED
inspection_profile:
  - minimal
  - standard
  - strict
evidence_profile:
  - compact
  - full
  - high_assurance
merge_enforcement_profile:
  - owner_controlled
  - ci_enforced
  - repository_enforced
merge_governance_status:
  - enforcement_verified
  - enforcement_unverified
  - enforcement_not_required
  - enforcement_conflicting
execution_urgency:
  - normal
  - expedited
technical_status:
  - GREEN_TECHNICALLY_READY
  - YELLOW_CHANGES_OR_VERIFICATION_REQUIRED
  - RED_DO_NOT_MERGE
merge_readiness_result:
  - READY_FOR_USER_MERGE
  - NOT_READY
  - BLOCKED_POLICY_UNRESOLVED
  - BLOCKED_REQUIRED_REVIEW
  - BLOCKED_REQUIRED_PUBLICATION
post_merge_closure_status:
  - not_started
  - merge_result_verified
  - current_main_validated
  - blocked_status_drift
  - status_reconciled
  - closure_recorded
dependent_work_authorization:
  - allowed
  - blocked_post_merge_closure
  - blocked_status_drift
behavioral_enforcement_status:
  - prose_only
  - schema_backed
  - validator_backed
  - fixture_tested
  - ci_enforced
  - downstream_contract_enforced
semantic_enforcement_status:
  - not_assessed
  - shallow_carrier_detected
  - minimum_children_defined
  - validator_proven
  - downstream_proven
obligation_resolution_status:
  - VERIFIED_SOURCE_BOUND
  - UNRESOLVED
  - REJECTED_NOT_AUTHORITATIVE
deterministic_precheck_status:
  - PASS
  - NOT_APPLICABLE_WITH_AUTHORITY
  - FAIL
  - BLOCKED_INSUFFICIENT_EVIDENCE
tool_parameter_binding_status:
  - VERIFIED_SOURCE_BOUND
  - VERIFIED_TRANSFORMATION_BOUND
  - INVALID_SOURCE_DETACHED
  - INVALID_UNDECLARED_TRANSFORMATION
tool_execution_status:
  - not_attempted
  - invoked
  - success
  - failed
  - unverified
tool_readback_status:
  - VERIFIED
  - READBACK_NOT_REQUIRED
  - FAILED
  - NOT_PERFORMED
tool_claim_binding_status:
  - VERIFIED_RESULT_BOUND
  - VERIFIED_READBACK_BOUND
  - INVALID_RESULT_DETACHED
```

### 3.3 No cross-domain substitution

```text
review_execution_status=performed does not imply publication verified
publication verified does not imply current review
current technical Green does not imply Merge authorized
technical_status=GREEN_TECHNICALLY_READY is compatible with merge_governance_status=enforcement_unverified
Merge observed does not imply post_merge_closure_status=closure_recorded
STATUS_DRIFT does not rewrite historical merge_readiness_result
historical review missing does not mean historical review failed
```

## 4. Applicability، Repository Profile و review policy resolution

> Authority: NORMATIVE

### 4.1 Rule applicability and trigger

```yaml
rule_applicability:
  rule_id: "<AIGOV-rule-id>"
  status: APPLICABLE_NOW | APPLICABLE_AFTER_DEPENDENCY | OUT_OF_SCOPE_BY_ACTIVE_PROFILE | NOT_APPLICABLE_TO_THIS_REPOSITORY | UNKNOWN_NEEDS_EVIDENCE
  repository_identity: "<exact>"
  target_identity: "<exact-or-null>"
  evidence_refs: []
  dependency_ref: null
  reevaluation_trigger: null
  profile_exclusion: null

rule_trigger:
  rule_id: "<same-rule-id>"
  status: TRIGGERED | NOT_TRIGGERED_FOR_THIS_TARGET | BLOCKED_INSUFFICIENT_EVIDENCE
  target_identity: "<exact>"
  trigger_predicates_evaluated: []
  evidence_refs: []
  reevaluation_trigger: null
```

Applicability دامنهٔ Rule را تعیین می‌کند؛ Trigger وقوع predicate برای target جاری را. Rule ممکن است Repository-applicable ولی برای PR جاری `NOT_TRIGGERED_FOR_THIS_TARGET` باشد.

هر applicability condition، trigger یا profile exclusion که enforcement effect دارد باید به `obligation_authority_binding` با `resolution_status=VERIFIED_SOURCE_BOUND` ارجاع دهد. این reference فقط obligationهای همین domain را حمل می‌کند و `rule_applicability` registry عمومی required field، Evidence requirement، Scope exclusion یا tool parameter constraint نیست.

### 4.2 Canonical Repository Review Policy

```yaml
repository_review_policy:
  schema_version: "1.1"
  repository_identity: "<owner/repo + repository_id>"
  policy_version: "<version>"
  policy_authority_ref: "<canonical-versioned-policy>"
  policy_identity: "sha256:<digest>"
  default_requirement: required | optional_advisory
  default_inspection_profile: minimal | standard | strict
  default_evidence_profile: compact | full | high_assurance
  default_merge_enforcement_profile: owner_controlled | ci_enforced | repository_enforced
  default_execution_urgency: normal | expedited
  boundary_overrides: []
  target_overrides: []
  publication_policy:
    required_when_review_required: true | false
    allowed_carriers: []
  transition_record_ref: null
```

### 4.3 Policy resolution state

```yaml
review_policy_resolution:
  status: RESOLVED | MISSING | INVALID | STALE | IDENTITY_UNVERIFIED | CONFLICT
  effective_requirement: required | optional_advisory | null
  effective_inspection_profile: minimal | standard | strict | null
  effective_evidence_profile: compact | full | high_assurance | null
  effective_merge_enforcement_profile: owner_controlled | ci_enforced | repository_enforced | null
  effective_execution_urgency: normal | expedited | null
  matched_sources: []
  activated_conditions: []
  evidence_refs: []
```

هر status غیر از `RESOLVED` به `BLOCKED_POLICY_UNRESOLVED` می‌رسد. Missing policy هرگز optional را infer نمی‌کند.

### 4.4 Resolution precedence

```text
standard safety activation minima
+ exact target override
+ exact boundary override
+ Repository default
→ strongest applicable minimum per dimension
```

Profile قوی‌تر مجاز است؛ Profile ضعیف‌تر از minimum فعال مجاز نیست. ترتیب enforcement برای minimum comparison:

```text
owner_controlled < ci_enforced < repository_enforced
```

Availability فقط preferred level را تغییر می‌دهد و minimum ثابت را پایین نمی‌آورد. تعارض هم‌سطح بدون canonical conflict rule → `CONFLICT`.

### 4.5 Standard review activation conditions

هر Activation Condition با exact evidence فعال می‌شود و effect کامل دارد:

| condition_id | boundary_ids | minimum_requirement | minimum_inspection | minimum_evidence | minimum_enforcement | urgency rule |
|---|---|---|---|---|---|---|
| `AIGOV-REVIEW-ACT-DESTRUCTIVE-IRREVERSIBLE` | `AIGOV-BOUNDARY-DESTRUCTIVE-IRREVERSIBLE` | `required` | `strict` | `high_assurance` | `ci_enforced` | expedited فقط با حفظ همه predicates |
| `AIGOV-REVIEW-ACT-SECURITY-SECRET` | `AIGOV-BOUNDARY-SECURITY-SECRET` | `required` | `strict` | `high_assurance` | minimum `ci_enforced`; preferred `repository_enforced` when proven available | no safety reduction |
| `AIGOV-REVIEW-ACT-EXTERNAL-PRODUCTION` | `AIGOV-BOUNDARY-EXTERNAL-PRODUCTION` | `required` | `strict` | `high_assurance` | `ci_enforced` | no validation reduction |
| `AIGOV-REVIEW-ACT-REAL-WORLD-SAFETY` | `AIGOV-BOUNDARY-REAL-WORLD-SAFETY` | `required` | `strict` | `high_assurance` | minimum `ci_enforced`; preferred `repository_enforced` when proven available | no safety reduction |
| `AIGOV-REVIEW-ACT-LEGAL-CONTRACTUAL` | `AIGOV-BOUNDARY-LEGAL-CONTRACTUAL` | exact obligation value | exact obligation value | exact obligation value | exact obligation value | unresolved dimension → `BLOCKED_POLICY_UNRESOLVED` |
| `AIGOV-REVIEW-ACT-CRITICAL-DOWNSTREAM-TRUST` | `AIGOV-BOUNDARY-CROSS-REPOSITORY-CONTRACT`, `AIGOV-BOUNDARY-PROVENANCE` | `required` | `strict` | `high_assurance` | `ci_enforced` | no trust reduction |

`L3` یا `L4` به‌تنهایی Activation Condition نیست.

Canonical record:

```yaml
review_activation_condition:
  condition_id: "<id>"
  boundary_ids: []
  status: TRIGGERED | NOT_TRIGGERED_FOR_THIS_TARGET | BLOCKED_INSUFFICIENT_EVIDENCE
  evidence_refs: []
  effect:
    minimum_requirement: required
    minimum_inspection_profile: strict
    minimum_evidence_profile: high_assurance
    minimum_merge_enforcement_profile: ci_enforced | repository_enforced
    urgency_constraints: []
```

### 4.6 Typed owner-policy transition

```yaml
policy_transition_record:
  schema_version: "1.0"
  transition_id: "<stable-id>"
  repository_identity: "<owner/repo + repository_id>"
  current_policy_identity: "sha256:<digest>"
  target_policy_identity: "sha256:<digest>"
  transition_scope_digest: "sha256:<digest>"
  exact_head_sha: "<sha>"
  owner_authority_verified: true
  exact_head_ci: PASS
  scope_validation: PASS
  secret_or_credential_change: false
  unauthorized_permission_escalation: false
  ruleset_or_branch_protection_mutation: false
  external_repository_write: false
  destructive_or_irreversible_action: false
  unrelated_implementation_bundled: false
  activation_condition_records: []
  merge_method: merge_commit | squash_merge | rebase_merge
  merge_result_proof_ref: "<exact-ref>"
  current_main_validation: PASS
  post_merge_closure_status: status_reconciled | closure_recorded
  status_reconciliation_ref: "<exact-ref>"
  transition_receipt_ref: "<exact-ref>"
```

Gateای که transition حذف می‌کند فقط به‌دلیل نبود همان Gate transition را block نمی‌کند. هر safety predicate خلاف یا Activation Condition فعال، transition ساده را رد و مسیر minimum effect همان Condition را فعال می‌کند. Transition باید increment مستقل باشد.

## 5. Change classification و material boundaries

> Authority: NORMATIVE

### 5.1 Classes

```text
L0 = read-only observation
L1 = isolated routine reversible change
L2 = multi-file routine or bounded behavior change
L3 = material governance/trust/lifecycle/cross-boundary change
L4 = destructive, irreversible, Production, Secret or real-world safety change
```

### 5.2 Canonical Material Boundary Registry

| boundary_id | failure boundary | minimum class |
|---|---|---|
| `AIGOV-BOUNDARY-CI-TRUST` | اعتماد به CI و انطباق نتیجه با exact tested object | `L3` |
| `AIGOV-BOUNDARY-COMPLETION` | ادعای completion، closure یا activation | `L3` |
| `AIGOV-BOUNDARY-CROSS-REPOSITORY-CONTRACT` | تغییر قرارداد یا write authority میان Repositoryها | `L3` |
| `AIGOV-BOUNDARY-DESTRUCTIVE-IRREVERSIBLE` | اقدام مخرب یا برگشت‌ناپذیر | `L4` |
| `AIGOV-BOUNDARY-EVIDENCE-CLASSIFICATION` | تغییر در semantics یا trust طبقه‌بندی Evidence | `L3` |
| `AIGOV-BOUNDARY-EXTERNAL-PRODUCTION` | اثر مستقیم بر Production یا سامانه بیرونی | `L4` |
| `AIGOV-BOUNDARY-FALSE-COMPLETION` | امکان ادعای تکمیل بدون واقعیت متناظر | `L3` |
| `AIGOV-BOUNDARY-GOVERNANCE-AUTHORITY` | تغییر authority، precedence یا policy حاکم | `L3` |
| `AIGOV-BOUNDARY-LEGAL-CONTRACTUAL` | الزام قانونی یا قراردادی صریح که minimum control یا Evidence را تعیین می‌کند | `L3` یا `L4` مطابق اثر |
| `AIGOV-BOUNDARY-INDEPENDENT-REVIEW` | تغییر requirement، independence یا acceptance review | `L3` |
| `AIGOV-BOUNDARY-POLICY-TRANSITION` | تغییر typed policy و activation state آن | `L3` |
| `AIGOV-BOUNDARY-PROVENANCE` | تغییر identity، provenance، digest یا exact-object binding | `L3` |
| `AIGOV-BOUNDARY-REAL-WORLD-SAFETY` | اثر ایمنی واقعی بر انسان یا محیط | `L4` |
| `AIGOV-BOUNDARY-REVIEW-EVIDENCE-PUBLICATION` | انتشار Receipt یا Pointer بازبینی در Repository هدف | `L3` |
| `AIGOV-BOUNDARY-SCOPE-LIFECYCLE` | تغییر Scope، lifecycle، phase یا closure authority | `L3` |
| `AIGOV-BOUNDARY-SECURITY-SECRET` | Secret، Credential، permission یا trust-sensitive security change | `L4` |
| `AIGOV-BOUNDARY-SILENT-SCOPE-DELETION` | کاهش Scope بدون disclosure و disposition صریح | `L3` |
| `AIGOV-BOUNDARY-VALIDATOR-TRUST` | تغییر validator، schema enforcement یا trust root آن | `L3` |

### 5.3 Separation invariant

```text
change_class
!= affected_boundary
!= independent_review_required
!= inspection_profile
!= merge_readiness_result
```

### 5.4 Classification terminal state

```yaml
classification_terminal:
  classification_resolution_status: resolved | blocked_insufficient_evidence
  final_class: L1 | L2 | L3 | L4 | null
  classification_outcome: supported_routine | confirmed_material | unsupported_upward | indeterminate | blocked_insufficient_evidence
  boundary_ids: []
  evidence_refs: []
  recovery_condition: null
```

`resolved` نیازمند `final_class` غیر-null است. blocked نیازمند bounded signal، missing evidence و `final_class: null` است.

## 6. Workflow، inspection profile و urgency

> Authority: NORMATIVE

### 6.1 Workflow selection

```text
L0 -> READ_ONLY
L1/L2 without material boundary -> ROUTINE_CHANGE
L3/L4 or governance migration -> MODE_A_PLAN then MODE_B_IMPLEMENT
```

Review requirement جداگانه از Section 4 resolve می‌شود.

### 6.2 Inspection profiles

#### minimal

حداقل invariantها:

- exact Repository/PR/Head؛
- exact Scope یا diff identity؛
- بررسی فنی واقعی؛
- targeted validation؛
- بررسی reproduced failures و relevant existing findings؛
- technical status روشن؛
- Receipt مطابق evidence profile.

عدم وجود governance enrichment غیرلازم technical status را Yellow نمی‌کند.

#### standard

تمام minimal به‌علاوه impact analysis گسترده‌تر، validation کامل‌تر و evidence rationale بیشتر.

#### strict

تمام standard به‌علاوه specialist/security/governance controls فعال‌شده، provenance قوی‌تر و enforcement evidence متناسب.

### 6.3 Execution urgency

`expedited` برای کاهش delay است، نه کاهش کیفیت فنی. این موارد هرگز حذف نمی‌شوند:

```text
exact identity
exact Head
exact Scope
real technical review when required
targeted validation
reproduced-failure handling
clear technical status
owner-only Merge
```

Expedited می‌تواند فقط enrichment غیرضروری، duplicate receipt یا control فاقد failure boundary مستقل را حذف/تعویق دهد.

## 7. Scope Gate

> Authority: NORMATIVE

Scope Gate باید ثبت کند:

```yaml
scope_record:
  repository_identity: "<exact>"
  target_identity: "<exact>"
  base_sha: "<sha>"
  head_sha: "<sha>"
  included_paths: []
  excluded_paths: []
  deferred_items: []
  scope_authority_binding_refs: []
  governing_revision: "<identity>"
  scope_digest: "sha256:<digest>"
```

هر exclusion، deferral، omission یا out-of-scope classification باید به `obligation_authority_binding` معتبر متصل باشد. هر تغییر Scope که readiness یا completion را عوض کند Scope Change Disclosure می‌خواهد. Expedited از این Gate معاف نیست.

## 8. Evidence، Review execution و Receipt publication

> Authority: NORMATIVE

### 8.1 Review execution record

```yaml
review_execution:
  review_id: "<stable-id>"
  repository_full_name: "<owner/repo>"
  repository_id: "<id>"
  pr_number: 0
  reviewed_head_sha: "<sha>"
  scope_digest: "sha256:<digest>"
  protocol_version: "<version>"
  inspector_identity:
    repository: "<reviewer-repo>"
    repository_id: "<id>"
    commit_sha: "<sha>"
  inspection_profile: minimal | standard | strict
  evidence_profile: compact | full | high_assurance
  execution_urgency: normal | expedited
  execution_status: performed | failed
  technical_status: GREEN_TECHNICALLY_READY | YELLOW_CHANGES_OR_VERIFICATION_REQUIRED | RED_DO_NOT_MERGE | null
  canonical_package_digest: "sha256:<digest-or-null>"
  decision_projection_digest: "sha256:<digest-or-null>"
  performed_at: "<UTC>"
```

### 8.2 Immutable Review Receipt Core

`review_receipt_core` فقط semantics Review را حمل می‌کند و با Retry publication تغییر نمی‌کند:

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
  protocol_version: "<version>"
  inspector_repository: "<owner/repo>"
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

`publisher_identity`، `comment_id`، `published_at` و current `review_validity` جزو Core نیستند.

### 8.3 Canonicalization and digest

Canonical digest فقط با این pipeline معتبر است:

```text
review_receipt_core object
→ RFC 8785 JSON Canonicalization Scheme (JCS)
→ UTF-8 without BOM
→ SHA-256
→ receipt_core_digest
```

YAML نمایش Comment است و canonical hashing representation نیست. Serializer یا whitespace متفاوت نباید digest جدید تولید کند.

### 8.4 Publication attempt envelope

```yaml
publication_attempt:
  publication_attempt_id: "<stable-attempt-id>"
  review_id: "<same-review-id>"
  receipt_core_digest: "sha256:<digest>"
  publication_status: not_attempted | publishing | published_verified | publication_failed
  carrier: structured_pr_comment | github_check_run | immutable_ledger_pointer | repository_defined
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
  published_object_id: null
  published_at: null
  readback_verified_at: null
  published_body_sha256: null
  failure_reason: null
```

Review Core ثابت است؛ publication attempt قابل تکرار است.

### 8.5 Canonical source and carrier

```text
verified review package
→ immutable review_receipt_core
→ canonical JCS digest
→ publication_attempt envelope
→ structured carrier
→ read-back and validation
```

Carrier technical truth جدید تولید نمی‌کند و Approval یا Merge authority نیست.

### 8.6 Structured PR comment

Comment body فقط marker، rendered Core، `receipt_core_digest` و pre-generated `publication_attempt_id` را حمل می‌کند. `publisher_identity`، `comment_id`، platform timestamps، `readback_verified_at` و `published_body_sha256` از authoritative GitHub read-back در publication attempt record ثبت می‌شوند و داخل body self-referential نیستند.

Policy:

```text
append-only by policy
exact Head required
publisher verification from platform metadata required
created_at and updated_at checked
edited receipt invalid unless Core digest and exact body are fully revalidated
```

### 8.7 Supersession and conflicts

Rereview یک Core جدید می‌سازد. چند Core متعارض بدون chain معتبر → `RECEIPT_CONFLICT`. Retry publication همان Core supersession نیست.

### 8.8 Publication retry

اگر exact Head، package digest، projection digest و `receipt_core_digest` ثابت‌اند، همان Core با `publication_attempt_id` جدید republish می‌شود. اگر Head تغییر کرده، Review verdict `STALE` است و Core قدیمی current acceptance نیست.

### 8.9 Personal compact-carrier limitation

Repository شخصی می‌تواند structured Comment را publication carrier کافی برای current-head readiness بداند؛ این انتخاب cryptographic immutability یا third-party authority ادعا نمی‌کند.

## 9. Independent Review و staleness

> Authority: NORMATIVE

### 9.1 Required mode

Review required باید:

- separate review context داشته باشد؛
- exact Head و Scope را ثبت کند؛
- protocol و Inspector identity exact داشته باشد؛
- current verdict داشته باشد؛
- implementer self-acceptance نباشد؛
- اگر publication policy required است Receipt current داشته باشد.

### 9.2 Optional advisory mode

در optional mode:

```text
missing review is not blocking
stale advisory review is not blocking
review sequence/provenance absence is not blocking unless another exact policy requires it
advisory review cannot authorize Merge
advisory review cannot replace validation
```

اگر advisory finding به failure قابل‌بازتولید برسد، failure از Evidence بازتولیدشده authority می‌گیرد.

### 9.3 Layered staleness

```text
reviewed_head_sha != current_head_sha -> review_validity=STALE
```

اما supporting Evidence با identity جدا ممکن است reusable باشد. Verdict staleness همه Evidence را خودکار stale نمی‌کند.

## 10. Progress Gate، completion و historical gaps

> Authority: NORMATIVE

### 10.1 Qualified progress

```yaml
progress_state:
  implementation_status: not_started | in_progress | implemented_pending_review | implementation_complete
  review_execution_status: not_started | in_progress | performed | failed
  receipt_publication_status: not_required | not_attempted | publishing | published_verified | publication_failed
  merge_status: not_merged | merged_observed | merge_result_verified
  post_merge_status: not_started | current_main_validated | status_reconciled | closure_recorded
```

### 10.2 Historical evidence gap

```yaml
historical_evidence_gap:
  evidence_type: "<type>"
  originally_required: true | false
  recreatable_without_fabrication: true | false
  historical_truth: missing | unknown | failed
  current_relevance: blocking | non_blocking_under_current_policy
  alternate_deterministic_evidence_refs: []
  policy_transition_ref: null
  limitations: []
  closure_status: open | closed_under_superseding_policy_with_disclosed_historical_gap
```

Historical missing review به معنی failed review نیست. Policy جدید نمی‌تواند ادعا کند review قدیمی انجام شده است.

### 10.3 False permanent blocking prohibition

Closure با historical gap فقط وقتی مجاز است که:

- gap غیرقابل‌بازتولید بدون fabrication باشد؛
- current canonical policy آن را non-blocking کند؛
- alternate deterministic evidence implementation و Merge state را ثابت کند؛
- gap در closure receipt باقی بماند.

## 11. Conditional Merge readiness و method-aware proof

> Authority: NORMATIVE

### 11.1 Required-review formula

```text
resolved required policy
+ current exact-head independent GREEN
+ required Receipt publication verified
+ resolved classification
+ exact-head validation
+ exact Scope
+ all applicable deterministic pre-Merge Gates
+ owner-only Merge
= READY_FOR_USER_MERGE
```

### 11.2 Optional-advisory formula

```text
resolved optional_advisory policy
+ no triggered Activation Condition requiring Review
+ resolved classification
+ exact-head validation
+ exact Scope
+ all applicable deterministic pre-Merge Gates
+ owner-only Merge
= READY_FOR_USER_MERGE
```

Optional path Review Receipt، Review freshness یا Review provenance نمی‌خواهد مگر exact policy آن را required کند. Reproduced failure مستقل از Review label blocking است.

### 11.3 Merge methods

```text
merge_commit
squash_merge
rebase_merge
```

Squash/Rebase ممکن است ancestry را حفظ نکند. نتیجه باید با method-aware content/tree proof بررسی شود:

```text
content_equivalence_verified
history_topology_verified
history_topology_not_preserved_by_merge_method
content_loss_detected
insufficient_evidence
```

### 11.4 Technical status and Merge governance

```yaml
merge_readiness_record:
  technical_status: GREEN_TECHNICALLY_READY | YELLOW_CHANGES_OR_VERIFICATION_REQUIRED | RED_DO_NOT_MERGE
  merge_readiness_result: READY_FOR_USER_MERGE | NOT_READY | BLOCKED_POLICY_UNRESOLVED | BLOCKED_REQUIRED_REVIEW | BLOCKED_REQUIRED_PUBLICATION
  merge_enforcement_profile: owner_controlled | ci_enforced | repository_enforced
  merge_governance_status: enforcement_verified | enforcement_unverified | enforcement_not_required | enforcement_conflicting
```

`GREEN_TECHNICALLY_READY + enforcement_unverified` معتبر است؛ adopted policy ممکن است readiness را جدا block کند.

## 12. Post-Merge verification، closure و STATUS_DRIFT

> Authority: NORMATIVE

بعد از Merge:

```text
inspect live default branch
→ detect Merge method
→ verify resulting content
→ verify current policy identity
→ run current-main validation
→ reconcile canonical mutable status
→ persist closure receipt
```

Canonical closure record:

```yaml
post_merge_closure:
  merge_result_proof_ref: "<exact-ref>"
  current_main_validation: PASS | FAIL | NOT_RUN
  status_authority_ref: "<exact-ref>"
  post_merge_closure_status: not_started | merge_result_verified | current_main_validated | blocked_status_drift | status_reconciled | closure_recorded
  dependent_work_authorization: allowed | blocked_post_merge_closure | blocked_status_drift
  closure_receipt_ref: null
```

اگر live truth با status authority برابر نباشد:

```text
STATUS_DRIFT
post_merge_closure_status = blocked_status_drift
dependent_work_authorization = blocked_status_drift
```

`merge_readiness_result` تاریخی بازنویسی نمی‌شود. Classification drift Advisory است؛ STATUS_DRIFT blocking و recoverable است.

## 13. Security، owner و Publisher boundaries

> Authority: NORMATIVE

### 13.1 Mandatory safety floor

Secret، Credential، Production، destructive، irreversible، real-world safety، legal/contractual و critical downstream trust فقط requirement را تغییر نمی‌دهند؛ minimum effect کامل Section 4.5 را اعمال می‌کنند. Repository Profile یا urgency نمی‌تواند minimum inspection، Evidence یا enforcement فعال را تضعیف کند.

### 13.2 Bounded publisher

Publisher باید capability جدا داشته باشد:

```yaml
review_receipt_publisher_capability:
  allowed_action:
    - publish_exact_verified_review_receipt
  exact_target_binding:
    repository: "<exact>"
    pr_number: 0
    reviewed_head_sha: "<sha>"
  forbidden_actions:
    - alter_receipt_content
    - modify_repository_content
    - approve_pull_request
    - merge_pull_request
    - modify_labels
    - modify_settings
    - modify_rulesets
    - access_secrets
    - deploy
```

Reviewer engine می‌تواند read-only بماند. Publisher logical/permission boundary جدا است؛ الزاماً deployment جدا نیست، اما capability باید جدا verify شود.

## 14. Canonical Rule Catalog

> Authority: NORMATIVE

Canonical rules این نسخه:

- `AIGOV-START-001`
- `AIGOV-APPLICABILITY-001`
- `AIGOV-SCOPE-001`
- `AIGOV-SCOPE-DISCLOSURE-001`
- `AIGOV-PROGRESS-001`
- `AIGOV-EVIDENCE-001`
- `AIGOV-INDEPENDENCE-001`
- `AIGOV-REVIEW-PUBLICATION-001`
- `AIGOV-STALE-001`
- `AIGOV-MERGE-001`
- `AIGOV-POLICY-TRANSITION-001`
- `AIGOV-STATUS-RECONCILIATION-001`
- `AIGOV-CHANGE-CLASS-001`
- `AIGOV-CHANGE-ESCALATION-001`
- `AIGOV-REPOSITORY-RISK-001`
- `AIGOV-CLASSIFICATION-DRIFT-001`
- `AIGOV-CONTROL-EFFECTIVENESS-001`
- `AIGOV-DOCUMENT-INTEGRITY-001`
- `AIGOV-STANDARD-RELEASE-001`
- `AIGOV-EVIDENCE-PROPORTIONALITY-001`
- `AIGOV-REPORTING-001`
- `AIGOV-SECURITY-PROFILE-001`
- `AIGOV-HUMAN-001`
- `AIGOV-COACH-001`
- `AIGOV-SEMANTIC-CARRIER-001`
- `AIGOV-BEHAVIORAL-COVERAGE-001`
- `AIGOV-TOOL-EXECUTION-001`

### 14.1 `AIGOV-START-001` — Startup, deterministic precheck and live-authority gate

```yaml
rule_id: AIGOV-START-001
title: "Startup, deterministic precheck and live-authority gate"
risk: Critical
session_scope: per_session
profile_excludable: false
allowed_profile_exclusions: []
trigger: "شروع کار Repository-aware، ادامه کار قبلی یا هر consequential decision."
predicate: "هویت Repository، authorityهای canonical، status جاری، exact target/Head، capabilityهای واقعی و هر applicable required deterministic precheck resolve شده‌اند؛ consequential_decision_authorized فقط وقتی true است که همه precheckها PASS یا NOT_APPLICABLE_WITH_AUTHORITY معتبر باشند."
enforcement: "بدون Startup Gate هیچ action authorization، readiness decision، completion claim، technical acceptance claim، Merge/release authorization، factual execution claim، state-transition authorization یا production-impacting approval مجاز نیست؛ FAIL و BLOCKED_INSUFFICIENT_EVIDENCE با probabilistic judgment override نمی‌شوند."
recovery_action: "authorityها و live state را بخوان؛ precheck شکست‌خورده یا Evidence مفقود را resolve کن؛ در حالت blocked فقط non-authorizing analysis، failure explanation، root-cause diagnosis و Recovery guidance تولید کن."
minimum_enforcement: "validator_backed"
carrier_expectation: "startup_record"
stale_behavior: "هر identity، precheck یا Evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.2 `AIGOV-APPLICABILITY-001` — Typed, authority-bound applicability and trigger separation

```yaml
rule_id: AIGOV-APPLICABILITY-001
title: "Typed, authority-bound applicability and trigger separation"
risk: Critical
session_scope: per_target
profile_excludable: false
allowed_profile_exclusions: []
trigger: "هر Rule یا Gate که برای Repository یا target جاری ارزیابی می‌شود."
predicate: "applicability، trigger و profile exclusion در recordهای مستقل ثبت شده و هر obligation اثرگذار در این domain به canonical authority exact-bound است."
enforcement: "UNKNOWN یا blocked evidence نمی‌تواند ضمنی NOT_TRIGGERED، NOT_APPLICABLE یا optional شود؛ invented applicability condition، trigger یا profile exclusion authority ایجاد نمی‌کند."
recovery_action: "Evidence و obligation authority binding لازم را resolve کن؛ claim فاقد authority را UNRESOLVED یا REJECTED_NOT_AUTHORITATIVE ثبت و هر دو domain را دوباره ارزیابی کن."
minimum_enforcement: "validator_backed"
carrier_expectation: "rule_applicability + rule_trigger + obligation_authority_binding references"
stale_behavior: "هر identity، authority binding یا Evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.3 `AIGOV-SCOPE-001` — Authority-bound Scope and no silent reduction

```yaml
rule_id: AIGOV-SCOPE-001
title: "Authority-bound Scope and no silent reduction"
risk: Critical
session_scope: cross_turn
profile_excludable: false
allowed_profile_exclusions: []
trigger: "تعریف، تغییر یا اجرای Scope."
predicate: "Scope، exclusions، deferred work، omissions و out-of-scope classifications exact/versioned هستند و هر محدودسازی به obligation_authority_binding با VERIFIED_SOURCE_BOUND متصل است."
enforcement: "کاهش بی‌صدای Scope، اجرای خارج از Scope یا exclusion/deferral فاقد authority blocked است."
recovery_action: "authority binding را resolve، Scope Change Disclosure را ثبت و disposition همه موارد حذف/تعویق‌شده را exact-bound کن."
minimum_enforcement: "sequence_ci_enforced_or_equivalent"
carrier_expectation: "scope_record + obligation_authority_binding references"
stale_behavior: "هر identity، authority binding یا Evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.4 `AIGOV-SCOPE-DISCLOSURE-001` — Proportional scope-change disclosure

```yaml
rule_id: AIGOV-SCOPE-DISCLOSURE-001
title: "Proportional scope-change disclosure"
risk: Critical
session_scope: cross_turn
profile_excludable: false
allowed_profile_exclusions: []
trigger: "readiness یا completion به Scope، lifecycle، phase، adoption یا material boundary وابسته است."
predicate: "تفاوت Scope قبلی و جدید، rationale، authority و وضعیت اقلام حذف‌شده ثبت شده است."
enforcement: "بدون disclosure، readiness و completion وابسته blocked است."
recovery_action: "disclosure را روی exact Head تولید و validate کن."
minimum_enforcement: "sequence_ci_enforced"
carrier_expectation: "scope_change_disclosure"
stale_behavior: "هر identity یا evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.5 `AIGOV-PROGRESS-001` — Progress truth and completion separation

```yaml
rule_id: AIGOV-PROGRESS-001
title: "Progress truth and completion separation"
risk: Critical
session_scope: cross_turn
profile_excludable: false
allowed_profile_exclusions: []
trigger: "هر claim درباره implementation، review، publication، Merge، verification یا completion."
predicate: "هر status در domain خودش ثبت شده و هیچ مرحله‌ای از مرحله دیگر استنتاج نشده است."
enforcement: "plan!=implementation، review performed!=receipt published، merge!=post-merge verified و CI Green!=independent acceptance."
recovery_action: "statusهای qualified را از evidence واقعی بازسازی کن."
minimum_enforcement: "sequence_ci_enforced"
carrier_expectation: "progress_state"
stale_behavior: "هر identity یا evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.6 `AIGOV-EVIDENCE-001` — Evidence truth, obligation authority and historical-gap integrity

```yaml
rule_id: AIGOV-EVIDENCE-001
title: "Evidence truth, obligation authority and historical-gap integrity"
risk: Critical
session_scope: per_claim
profile_excludable: false
allowed_profile_exclusions: []
trigger: "هر factual، validation، mandatory، rejecting، blocking، readiness، review، Merge یا completion claim."
predicate: "claim به Evidence exact-bound و هر obligation مبنای آن به canonical authority VERIFIED_SOURCE_BOUND متصل است؛ missing historical evidence جعل نشده و gap صریح است."
enforcement: "caller text، self-authored marker، hash اعلامی یا model-generated/unresolved obligation authority ایجاد نمی‌کند و نمی‌تواند claim mandatory، rejecting، blocking، readiness، completion یا factual را پشتیبانی کند."
recovery_action: "current producible evidence و authority binding را تولید کن؛ obligation جعلی را حذف/رد و historical gap غیرقابل‌بازتولید را preserve کن."
minimum_enforcement: "ci_enforced_or_downstream_rejection"
carrier_expectation: "evidence_manifest_or_historical_evidence_gap + obligation_authority_binding references"
stale_behavior: "هر identity، authority binding یا Evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.7 `AIGOV-INDEPENDENCE-001` — Policy-driven independent review

```yaml
rule_id: AIGOV-INDEPENDENCE-001
title: "Policy-driven independent review"
risk: Critical_when_triggered
session_scope: cross_turn
profile_excludable: false
allowed_profile_exclusions: []
trigger: "canonical repository policy، exact target/boundary override یا standard activation condition review را برای target جاری required می‌کند."
predicate: "Review مستقل، exact-head، exact-scope، current و protocol-bound است؛ implementer self-review مستقل محسوب نمی‌شود."
enforcement: "required review مفقود یا stale readiness را block می‌کند؛ optional_advisory به‌تنهایی block نمی‌کند."
recovery_action: "Review جاری را اجرا یا policy/activation conflict را resolve کن؛ historical review جعل نکن."
minimum_enforcement: "sequence_ci_enforced_when_required; advisory_validation_when_optional"
carrier_expectation: "review_policy_resolution + verified_review_package"
stale_behavior: "هر identity یا evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.8 `AIGOV-REVIEW-PUBLICATION-001` — Immutable Review Receipt Core and bounded publication

```yaml
rule_id: AIGOV-REVIEW-PUBLICATION-001
title: "Immutable Review Receipt Core and bounded publication"
risk: High_or_Critical_by_policy
session_scope: cross_turn
profile_excludable: false
allowed_profile_exclusions: []
trigger: "Repository Profile انتشار Receipt را required می‌کند."
predicate: "immutable review_receipt_core با JCS canonicalization از publication_attempt جداست؛ publisher فقط exact Core را منتشر و read-back می‌کند."
enforcement: "publication failure Review execution را erase نمی‌کند؛ publisher metadata یا timestamp نمی‌تواند Receipt Core digest را تغییر دهد."
recovery_action: "اگر Head و Core digest ثابت‌اند attempt تازه منتشر کن؛ اگر Head تغییر کرده Review تازه لازم است."
minimum_enforcement: "validator_backed; sequence_ci_enforced_when_blocking"
carrier_expectation: "review_receipt_core + publication_attempt + structured carrier"
stale_behavior: "هر identity یا Evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.9 `AIGOV-STALE-001` — Exact-head and layered staleness

```yaml
rule_id: AIGOV-STALE-001
title: "Exact-head and layered staleness"
risk: Critical
session_scope: cross_turn
profile_excludable: false
allowed_profile_exclusions: []
trigger: "Head، Scope، policy identity، protocol identity یا material evidence تغییر می‌کند."
predicate: "review verdict، receipt، policy و supporting evidence هرکدام با semantics خود current/stale ارزیابی شده‌اند."
enforcement: "stale required review یا stale required non-review evidence readiness را block می‌کند."
recovery_action: "فقط لایه stale را regenerate یا rereview کن؛ Evidence unchanged قابل reuse است."
minimum_enforcement: "sequence_ci_enforced"
carrier_expectation: "staleness_assessment"
stale_behavior: "هر identity یا evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.10 `AIGOV-MERGE-001` — Conditional readiness and method-aware Merge proof

```yaml
rule_id: AIGOV-MERGE-001
title: "Conditional readiness and method-aware Merge proof"
risk: Critical
session_scope: cross_turn
profile_excludable: false
allowed_profile_exclusions: []
trigger: "اعلام READY_FOR_USER_MERGE، مشاهده Merge یا closure بعد از Merge."
predicate: "readiness از policy resolved، exact-head validation، exact Scope، Gates applicable و review required-if-triggered مشتق شده؛ Merge result با method واقعی verify شده است."
enforcement: "owner-only Merge؛ ancestry برای Squash/Rebase شرط عمومی نیست؛ comment یا technical Green به‌تنهایی Merge authorization نیست."
recovery_action: "Gate مفقود را رفع و method-aware proof را روی default branch اجرا کن."
minimum_enforcement: "sequence_ci_enforced_or_repository_hosted_equivalent"
carrier_expectation: "merge_readiness_record + merge_result_proof"
stale_behavior: "هر identity یا evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.11 `AIGOV-POLICY-TRANSITION-001` — Non-circular typed policy transition

```yaml
rule_id: AIGOV-POLICY-TRANSITION-001
title: "Non-circular typed policy transition"
risk: Critical
session_scope: per_transition
profile_excludable: false
allowed_profile_exclusions: []
trigger: "تغییر review requirement، enforcement profile یا Governance policy که Gate جاری را تغییر می‌دهد."
predicate: "policy_transition_record exact Repository/current-policy/target-policy/Head/Scope identity، owner authority، exact-head CI، Scope validation، false safety/write/mutation flags، no unrelated implementation، method-aware Merge proof، current-main validation، status reconciliation و persisted transition Receipt دارد."
enforcement: "Gate در حال حذف نمی‌تواند فقط به دلیل نبود خودش transition را deadlock کند؛ standard safety activation conditions همچنان حاکم‌اند."
recovery_action: "transition را isolate کن، predicateهای typed را تکمیل و دوباره validate کن."
minimum_enforcement: "sequence_ci_enforced"
carrier_expectation: "policy_transition_record"
stale_behavior: "هر identity یا evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.12 `AIGOV-STATUS-RECONCILIATION-001` — Post-Merge closure and status reconciliation

```yaml
rule_id: AIGOV-STATUS-RECONCILIATION-001
title: "Post-Merge closure and status reconciliation"
risk: Critical
session_scope: post_merge
profile_excludable: false
allowed_profile_exclusions: []
trigger: "Merge، policy activation، exact-main verification یا activation transition."
predicate: "live default-branch truth با canonical mutable status authority برابر و post_merge_closure_status صادقانه ثبت شده است."
enforcement: "STATUS_DRIFT closure و dependent work را block می‌کند؛ historical merge_readiness_result بازنویسی نمی‌شود."
recovery_action: "live main را inspect، Merge result و policy identity را verify، status را reconcile و closure Receipt را persist کن."
minimum_enforcement: "ci_enforced_or_sequence_ci_enforced"
carrier_expectation: "post_merge_closure + status_reconciliation_receipt"
stale_behavior: "هر identity یا Evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.13 `AIGOV-CHANGE-CLASS-001` — Evidence-bound change classification

```yaml
rule_id: AIGOV-CHANGE-CLASS-001
title: "Evidence-bound change classification"
risk: Critical
session_scope: per_increment
profile_excludable: false
allowed_profile_exclusions: []
trigger: "هر change increment یا discovery که workflow را تعیین می‌کند."
predicate: "classification از boundaries و evidence مشتق شده؛ change_class با review requirement یکی نیست."
enforcement: "abstract concern upward classification نمی‌سازد؛ blocked classification final_class=null دارد."
recovery_action: "bounded classification probe اجرا کن."
minimum_enforcement: "validator_backed"
carrier_expectation: "classification_record"
stale_behavior: "هر identity یا evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.14 `AIGOV-CHANGE-ESCALATION-001` — Mid-work escalation without silent continuation

```yaml
rule_id: AIGOV-CHANGE-ESCALATION-001
title: "Mid-work escalation without silent continuation"
risk: Critical
session_scope: per_increment
profile_excludable: false
allowed_profile_exclusions: []
trigger: "در حین کار material boundary جدید کشف می‌شود."
predicate: "escalation event، invalidated readiness، new class/workflow و revised Scope ثبت شده‌اند."
enforcement: "کار با workflow قدیمی ادامه نمی‌یابد."
recovery_action: "reclassify، replan و exact-head validation را تکرار کن."
minimum_enforcement: "sequence_ci_enforced"
carrier_expectation: "classification_escalation_event"
stale_behavior: "هر identity یا evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.15 `AIGOV-REPOSITORY-RISK-001` — Repository-risk profile integrity

```yaml
rule_id: AIGOV-REPOSITORY-RISK-001
title: "Repository-risk profile integrity"
risk: High
session_scope: cross_turn
profile_excludable: false
allowed_profile_exclusions: []
trigger: "تعیین یا تغییر repository risk/profile."
predicate: "profile با exact basis و limitations current ثبت شده و invariant safeguard را downgrade نمی‌کند."
enforcement: "stale/unresolved profile relaxation نمی‌دهد."
recovery_action: "profile basis را refresh کن."
minimum_enforcement: "validator_backed"
carrier_expectation: "repository_profile_snapshot"
stale_behavior: "هر identity یا evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.16 `AIGOV-CLASSIFICATION-DRIFT-001` — Advisory classification drift metrics

```yaml
rule_id: AIGOV-CLASSIFICATION-DRIFT-001
title: "Advisory classification drift metrics"
risk: Advisory
session_scope: periodic_or_release
profile_excludable: false
allowed_profile_exclusions: []
trigger: "وجود classification eventهای کافی."
predicate: "denominatorها فقط records resolved را شامل می‌شوند و blocked/indeterminate جدا گزارش می‌شوند."
enforcement: "metrics non-blocking و non-Merge-blocking هستند."
recovery_action: "recordهای malformed را repair و metric را recompute کن."
minimum_enforcement: "validator_backed"
carrier_expectation: "classification_metrics_report"
stale_behavior: "هر identity یا evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.17 `AIGOV-CONTROL-EFFECTIVENESS-001` — Blocking-control cost and effectiveness

```yaml
rule_id: AIGOV-CONTROL-EFFECTIVENESS-001
title: "Blocking-control cost and effectiveness"
risk: High
session_scope: per_gate_change_or_incident
profile_excludable: false
allowed_profile_exclusions: []
trigger: "ایجاد/تشدید Gate blocking، deadlock، false block یا major release."
predicate: "Gate یک failure boundary متمایز، risk reduction، نبود alternative ارزان‌تر، evidence persistence و bounded recovery دارد."
enforcement: "Gate فاقد توجیه باید automate، simplify، narrow، conditionalize یا retire_candidate شود؛ mandatory safety predicate با cost یا convenience حذف یا تضعیف نمی‌شود."
recovery_action: "blocking_control_justification و control_effectiveness_record را تکمیل کن."
minimum_enforcement: "validator_backed_at_release"
carrier_expectation: "blocking_control_justification + control_effectiveness_record"
stale_behavior: "هر identity یا evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.18 `AIGOV-DOCUMENT-INTEGRITY-001` — Exact-document consistency and Rule-level projection parity

```yaml
rule_id: AIGOV-DOCUMENT-INTEGRITY-001
title: "Exact-document consistency and Rule-level projection parity"
risk: Critical
session_scope: per_release
profile_excludable: false
allowed_profile_exclusions: []
trigger: "هر Candidate، release، migration یا activation."
predicate: "version/status/Rules/Boundaries/tables/prompts/acceptance/migration/fixtures و projection-parity-matrix همگام و exact-digest-bound هستند."
enforcement: "prompt-only Rule، stale version ref، duplicate authority یا unmapped Rule projection release را block می‌کند."
recovery_action: "تمام normative surfaces و parity matrix را reconcile و release-integrity را regenerate کن."
minimum_enforcement: "release_time_validator_backed"
carrier_expectation: "release_integrity_report + projection_parity_matrix"
stale_behavior: "هر identity یا Evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.19 `AIGOV-STANDARD-RELEASE-001` — Dual-path exact-document release lifecycle

```yaml
rule_id: AIGOV-STANDARD-RELEASE-001
title: "Dual-path exact-document release lifecycle"
risk: Critical
session_scope: per_release
profile_excludable: false
allowed_profile_exclusions: []
trigger: "ارتقا draft/candidate/active یا supersession."
predicate: "Candidate digest، parity matrix و same-context integrity معتبرند؛ سپس exact one activation path انتخاب می‌شود: PATH A با fresh independent audit و assurance INDEPENDENTLY_AUDITED، یا PATH B با same-context final audit، zero blocking findings، narrow-scope eligibility، explicit reduced-independence acceptance و assurance MAINTAINER_CONTROLLED_DETERMINISTIC؛ هر path به bounded transform، active digest، active release-integrity، activation Receipt، active Manifest و external archive digest exact-bound نیاز دارد."
enforcement: "release_candidate بدون تکمیل selected path و disclosure truthful active نیست؛ same-context audit independent نامیده نمی‌شود؛ PATH B assurance-equivalent با PATH A نیست؛ Core activation Candidate Companion را فعال نمی‌کند."
recovery_action: "selected activation path را resolve کن، audit/integrity/parity blockers را ببند، assurance disclosure را ثبت و deterministic activation transition را از Candidate تازه انجام بده."
minimum_enforcement: "release_time_validator_backed_plus_selected_path_audit"
carrier_expectation: "release_integrity + projection_parity_matrix + selected_path_audit + activation_transform + activation_receipt + external_archive_sidecar"
stale_behavior: "هر identity یا Evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.20 `AIGOV-EVIDENCE-PROPORTIONALITY-001` — Smallest sufficient evidence

```yaml
rule_id: AIGOV-EVIDENCE-PROPORTIONALITY-001
title: "Smallest sufficient evidence"
risk: High
session_scope: per_increment
profile_excludable: false
allowed_profile_exclusions: []
trigger: "انتخاب verification/evidence budget."
predicate: "Evidence برای failure boundary کافی است، duplicate فاقد ارزش افزوده نیست و urgency invariants را حذف نکرده است."
enforcement: "overengineering و under-evidence هر دو finding هستند."
recovery_action: "budget را minimal/standard/strict و compact/full/high_assurance بازتنظیم کن."
minimum_enforcement: "validator_backed_or_auditable_policy"
carrier_expectation: "evidence_budget"
stale_behavior: "هر identity یا evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.21 `AIGOV-REPORTING-001` — Smallest complete owner disclosure

```yaml
rule_id: AIGOV-REPORTING-001
title: "Smallest complete owner disclosure"
risk: High
session_scope: per_report
profile_excludable: false
allowed_profile_exclusions: []
trigger: "هر owner-facing status یا next action."
predicate: "technical_status، Review execution، Receipt publication، Merge governance، post-Merge closure و behavioral coverage gap جدا و بدون overclaim گزارش شده‌اند."
enforcement: "Technical Green به‌عنوان Merge authorization یا closure نمایش داده نمی‌شود؛ STATUS_DRIFT pre-Merge readiness را بازنویسی نمی‌کند."
recovery_action: "projection را از canonical state دوباره render کن."
minimum_enforcement: "validator_backed_projection"
carrier_expectation: "owner_result_projection"
stale_behavior: "هر identity یا Evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.22 `AIGOV-SECURITY-PROFILE-001` — Complete safety activation effects

```yaml
rule_id: AIGOV-SECURITY-PROFILE-001
title: "Complete safety activation effects"
risk: High_or_Critical
session_scope: cross_turn
profile_excludable: false
allowed_profile_exclusions: []
trigger: "Secret/Credential، permission، Production، destructive، safety، legal/contractual یا critical downstream trust Boundary."
predicate: "Activation Condition exact-bound است و minimum requirement، inspection، evidence، enforcement و urgency constraints را resolve می‌کند."
enforcement: "Repository Profile یا urgency نمی‌تواند هیچ minimum فعال را حذف کند."
recovery_action: "Activation record را تکمیل و strongest minimum per dimension را اعمال کن."
minimum_enforcement: "validator_backed; stronger_when_triggered"
carrier_expectation: "review_activation_condition + security_activation_record"
stale_behavior: "هر identity یا Evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.23 `AIGOV-HUMAN-001` — Owner action is not technical approval

```yaml
rule_id: AIGOV-HUMAN-001
title: "Owner action is not technical approval"
risk: High
session_scope: per_artifact
profile_excludable: false
allowed_profile_exclusions: []
trigger: "مالک Merge یا اقدام اداری انجام می‌دهد."
predicate: "owner authority و technical decision authority جدا ثبت شده‌اند."
enforcement: "فشردن Merge به‌عنوان technical approval بازنمایی نمی‌شود."
recovery_action: "status و wording را اصلاح کن."
minimum_enforcement: "validator_backed"
carrier_expectation: "authority_record"
stale_behavior: "هر identity یا evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.24 `AIGOV-COACH-001` — Non-technical owner guidance

```yaml
rule_id: AIGOV-COACH-001
title: "Non-technical owner guidance"
risk: High
session_scope: per_report
profile_excludable: false
allowed_profile_exclusions: []
trigger: "اقدام فنی/اداری از مالک غیرتخصصی لازم است."
predicate: "یک اقدام روشن، کم‌خطر و evidence-bound ارائه شده است."
enforcement: "مسئولیت تصمیم فنی قابل‌حل به مالک واگذار نمی‌شود."
recovery_action: "next action را دقیق و واحد بازنویسی کن."
minimum_enforcement: "validator_backed_or_fixture_tested"
carrier_expectation: "owner_action_card"
stale_behavior: "هر identity یا evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```


### 14.25 `AIGOV-SEMANTIC-CARRIER-001` — Minimum semantic completeness for composite predicates

```yaml
rule_id: AIGOV-SEMANTIC-CARRIER-001
title: "Minimum semantic completeness for composite predicates"
risk: Critical
session_scope: per_composite_predicate
profile_excludable: false
allowed_profile_exclusions: []
trigger: "یک Critical/High Rule مفهوم مرکب را با field، Boolean، enum یا object حمل می‌کند."
predicate: "semantic_complexity تعیین شده و structured_required carrier دارای Minimum Semantic Children، cross-field constraints، validator و invalid fixture است."
enforcement: "caller-supplied scalar یا shallow object به‌تنهایی semantic Evidence نیست؛ shallow compliance به BLOCKED_SEMANTIC_ILLUSION می‌رسد."
recovery_action: "Minimum Semantic Children و validator/fixture را اضافه یا claim را downgrade کن."
minimum_enforcement: "fixture_tested_minimum; ci_enforced_preferred"
carrier_expectation: "semantic_carrier_contract"
stale_behavior: "هر identity یا Evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.26 `AIGOV-BEHAVIORAL-COVERAGE-001` — Critical behavioral gates must not remain enforcement-free

```yaml
rule_id: AIGOV-BEHAVIORAL-COVERAGE-001
title: "Critical behavioral gates must not remain enforcement-free"
risk: Critical
session_scope: per_repository_release
profile_excludable: false
allowed_profile_exclusions: []
trigger: "Prompt/protocol/role/schema repository دارای Rule رفتاری Critical یا High است."
predicate: "هر Gate coverage record دارد و strongest proven enforcement status صادقانه ثبت شده است."
enforcement: "Critical EFBG یا shallow schema-backed Gate open enforcement gap است؛ status قوی‌تر بدون Evidence ممنوع است."
recovery_action: "modal scan را به semantic review تبدیل، carrier/validator/fixture/CI/downstream rejection را متناسب اضافه کن."
minimum_enforcement: "critical_fixture_tested_minimum; high_validator_backed_minimum"
carrier_expectation: "behavioral_rule_coverage_record"
stale_behavior: "هر identity یا Evidence وابسته طبق Section 9 دوباره ارزیابی می‌شود."
```

### 14.27 `AIGOV-TOOL-EXECUTION-001` — Source-bound and verifiable consequential tool execution

```yaml
rule_id: AIGOV-TOOL-EXECUTION-001
title: "Source-bound and verifiable consequential tool execution"
risk: Critical_when_consequential
session_scope: per_tool_action
profile_excludable: false
allowed_profile_exclusions: []
trigger: "Tool invocation می‌تواند state را تغییر دهد، به governed target دسترسی دهد، consequential Evidence تولید کند یا factual/readiness/completion/execution claim را پشتیبانی کند."
predicate: "Capability authority، selected tool، tool schema identity، exact target identity، authoritative source inputs، source-to-parameter bindings، authority-bound parameter constraints، declared validated transformations، actual invocation، captured result، required read-back و final result-to-claim bindings در tool_execution_attestation ثبت و validate شده‌اند."
enforcement: "Wrong/unauthorized tool، schema-invalid parameters، schema-valid but source-detached parameters، invented/omitted source value، undeclared transformation، wrong target identity، claimed execution without invocation، execution without captured result، success without result Evidence، state change without required read-back، ignored result، result-detached claim یا stale execution Evidence action و claim وابسته را block می‌کند."
recovery_action: "Capability و exact target را دوباره resolve کن؛ parameterها را از authoritative source با transformation صریح بازسازی و validate کن؛ tool دقیق را اجرا، result را capture، read-back لازم را verify و claim را فقط از result/read-back fields معتبر مشتق کن."
minimum_enforcement: "validator_backed minimum; fixture_tested for consequential actions; ci_enforced_or_downstream_rejection for release, merge, security, production or evidence-authorizing actions"
carrier_expectation: "tool_execution_attestation"
stale_behavior: "تغییر capability authority، source identity، tool/schema identity، target identity، target state یا result predicate execution authority و derived claims را دوباره ارزیابی می‌کند."
```

## 15. حداقل enforcement

> Authority: NORMATIVE

این SSOT به‌تنهایی prose است. Repository adoption باید strongest proven enforcement را ثبت کند و هیچ status قوی‌تر از Evidence ادعا نشود.

| Rule | Risk/scope | Minimum target |
|---|---|---|
| `AIGOV-START-001` | `Critical/per_session` | `validator_backed` |
| `AIGOV-APPLICABILITY-001` | `Critical/per_target` | `validator_backed` |
| `AIGOV-SCOPE-001` | `Critical/cross_turn` | `sequence_ci_enforced_or_equivalent` |
| `AIGOV-SCOPE-DISCLOSURE-001` | `Critical/cross_turn` | `sequence_ci_enforced` |
| `AIGOV-PROGRESS-001` | `Critical/cross_turn` | `sequence_ci_enforced` |
| `AIGOV-EVIDENCE-001` | `Critical/per_claim` | `ci_enforced_or_downstream_rejection` |
| `AIGOV-INDEPENDENCE-001` | `Critical_when_triggered/cross_turn` | `sequence_ci_enforced_when_required` |
| `AIGOV-REVIEW-PUBLICATION-001` | `High_or_Critical_by_policy/cross_turn` | `validator_backed; sequence_ci_when_blocking` |
| `AIGOV-STALE-001` | `Critical/cross_turn` | `sequence_ci_enforced` |
| `AIGOV-MERGE-001` | `Critical/cross_turn` | `sequence_ci_or_repository_hosted` |
| `AIGOV-POLICY-TRANSITION-001` | `Critical/per_transition` | `sequence_ci_enforced` |
| `AIGOV-STATUS-RECONCILIATION-001` | `Critical/post_merge` | `ci_or_sequence_ci_enforced` |
| `AIGOV-CHANGE-CLASS-001` | `Critical/per_increment` | `validator_backed` |
| `AIGOV-CHANGE-ESCALATION-001` | `Critical/per_increment` | `sequence_ci_enforced` |
| `AIGOV-REPOSITORY-RISK-001` | `High/cross_turn` | `validator_backed` |
| `AIGOV-CLASSIFICATION-DRIFT-001` | `Advisory/per_release` | `metrics_only` |
| `AIGOV-CONTROL-EFFECTIVENESS-001` | `High/per_control` | `validator_backed_or_auditable_policy` |
| `AIGOV-DOCUMENT-INTEGRITY-001` | `Critical/per_release` | `release_validator + parity_matrix` |
| `AIGOV-STANDARD-RELEASE-001` | `Critical/per_release` | `selected_path_audit + deterministic_integrity + activation_receipt` |
| `AIGOV-EVIDENCE-PROPORTIONALITY-001` | `High/per_increment` | `validator_backed_or_auditable_policy` |
| `AIGOV-REPORTING-001` | `High/per_report` | `validator_backed_projection` |
| `AIGOV-SECURITY-PROFILE-001` | `Critical_when_triggered/cross_turn` | `validator_backed + stronger_when_triggered` |
| `AIGOV-HUMAN-001` | `High/per_artifact` | `validator_backed` |
| `AIGOV-COACH-001` | `Medium/per_owner_action` | `projection_tested` |
| `AIGOV-SEMANTIC-CARRIER-001` | `Critical/per_composite_predicate` | `fixture_tested minimum; CI preferred` |
| `AIGOV-BEHAVIORAL-COVERAGE-001` | `Critical/per_repository_release` | `Critical fixture_tested; High validator_backed` |
| `AIGOV-TOOL-EXECUTION-001` | `Critical_when_consequential/per_tool_action` | `validator_backed; consequential fixture_tested; CI/downstream for authorizing actions` |

Critical composite predicate بدون Minimum Semantic Children open enforcement gap است. Low-risk prose نباید بی‌دلیل validator شود.

## 16. Behavioral Rule Coverage Matrix

> Authority: NORMATIVE for required fields and truthfulness; detailed implementation Contract is a separate Companion.

Canonical coverage record:

```yaml
behavioral_rule_coverage_record:
  rule_id: "<stable-id>"
  concept: "<human-readable>"
  risk: Critical | High | Medium | Low
  prose_source: "<path+section>"
  semantic_complexity: scalar_safe | structured_required
  minimum_semantic_children: []
  schema_carrier: null
  validator_rule: null
  valid_fixture: null
  invalid_fixtures: []
  ci_step: null
  downstream_contract: null
  enforcement_status: prose_only | schema_backed | validator_backed | fixture_tested | ci_enforced | downstream_contract_enforced
  semantic_enforcement_status: not_assessed | shallow_carrier_detected | minimum_children_defined | validator_proven | downstream_proven
  open_gap: true
  planned_patch: null
```

Modal-language scan فقط candidate discovery است. هر match باید `normative_gate | informative_guidance | example | false_positive` طبقه‌بندی شود.

```yaml
semantic_carrier_contract:
  carrier_id: "<id>"
  governed_rule_id: "<id>"
  semantic_complexity: scalar_safe | structured_required
  minimum_semantic_children: []
  prohibited_unknown_values: []
  cross_field_constraints: []
  validator_rule_id: null
  valid_fixture: null
  invalid_fixtures: []
  derived_projection_fields: []
```


Minimum normative obligation carrier:

```yaml
obligation_authority_binding:
  carrier_id: obligation_authority_binding
  governed_rules:
    - AIGOV-APPLICABILITY-001
    - AIGOV-SCOPE-001
    - AIGOV-EVIDENCE-001
    - AIGOV-TOOL-EXECUTION-001
  obligation_id: "<stable-id>"
  obligation_type: rule | applicability_condition | trigger | required_field | rejection_criterion | evidence_requirement | scope_exclusion | deferred_work_condition | tool_parameter_constraint
  authority_ref: "<canonical-source>"
  authority_identity: "<digest/sha/versioned-id>"
  source_locator: "<section/rule/schema-path>"
  resolution_status: VERIFIED_SOURCE_BOUND | UNRESOLVED | REJECTED_NOT_AUTHORITATIVE
```

Minimum normative tool carrier:

```yaml
tool_execution_attestation:
  carrier_id: tool_execution_attestation
  governed_rule_id: AIGOV-TOOL-EXECUTION-001
  capability_authority_ref: "<exact-ref>"
  selected_tool: "<tool-id>"
  tool_schema_identity: "<exact-version-or-digest>"
  target_identity:
    target_type: "<repository/pr/branch/head/record/resource>"
    exact_identity: "<exact-id>"
  parameter_bindings:
    - parameter_name: "<name>"
      supplied_value: "<value-or-canonical-digest>"
      source_ref: "<authoritative-source>"
      source_field_path: "<path>"
      source_identity: "<digest/sha/versioned-id>"
      parameter_constraint_authority_refs: []
      transformation:
        transformation_id: identity | "<declared-transform-id>"
        validation_ref: "<validator-ref-or-null-for-identity>"
      binding_status: VERIFIED_SOURCE_BOUND | VERIFIED_TRANSFORMATION_BOUND | INVALID_SOURCE_DETACHED | INVALID_UNDECLARED_TRANSFORMATION
  invocation_record:
    invocation_id: "<id-or-null>"
    claimed_execution: true | false
    execution_status: not_attempted | invoked | success | failed | unverified
    executed_at: "<UTC-or-null>"
  execution_result:
    result_identity: "<digest/id-or-null>"
    captured_result_fields: []
  state_changed: true | false
  readback_status: VERIFIED | READBACK_NOT_REQUIRED | FAILED | NOT_PERFORMED
  readback_ref: "<exact-ref-or-null>"
  readback_not_required_authority_ref: "<exact-ref-or-null>"
  final_claim_bindings:
    - claim_id: "<id>"
      result_field_refs: []
      binding_status: VERIFIED_RESULT_BOUND | VERIFIED_READBACK_BOUND | INVALID_RESULT_DETACHED
```

Core invariants:

```text
claimed_execution == true
requires
invocation_record.invocation_id + execution_status in {invoked, success, failed}

consequential parameter
requires
binding_status in {VERIFIED_SOURCE_BOUND, VERIFIED_TRANSFORMATION_BOUND}

parameter constraint with enforcement effect
requires
VERIFIED_SOURCE_BOUND obligation_authority_binding

state_changed == true
requires
readback_status == VERIFIED
or an exact Rule-permitted authoritative equivalent

READBACK_NOT_REQUIRED
requires
state_changed == false + exact authority + validated reason

final tool-derived claim
requires
VERIFIED_RESULT_BOUND or VERIFIED_READBACK_BOUND

target identity mismatch
invalidates
execution authority and all derived claims
```

Unstructured prose به‌تنهایی جای این carrier را نمی‌گیرد. Core minimum meaning را تعریف می‌کند؛ Companion فقط implementation methodology را توسعه می‌دهد.

| rule_id | semantic complexity | carrier | validator | invalid fixture | CI/downstream | current baseline |
|---|---|---|---|---|---|---|
| `AIGOV-START-001` | `repository_assessed` | `startup_record` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-APPLICABILITY-001` | `repository_assessed` | `rule_applicability + rule_trigger` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-SCOPE-001` | `repository_assessed` | `scope_record` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-SCOPE-DISCLOSURE-001` | `repository_assessed` | `scope_change_disclosure` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-PROGRESS-001` | `repository_assessed` | `progress_state` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-EVIDENCE-001` | `structured_required` | `evidence_manifest_or_historical_evidence_gap` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-INDEPENDENCE-001` | `repository_assessed` | `review_policy_resolution + verified_review_package` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-REVIEW-PUBLICATION-001` | `structured_required` | `review_receipt_core + publication_attempt` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-STALE-001` | `repository_assessed` | `staleness_assessment` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-MERGE-001` | `repository_assessed` | `merge_readiness_record + merge_result_proof` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-POLICY-TRANSITION-001` | `structured_required` | `policy_transition_record` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-STATUS-RECONCILIATION-001` | `structured_required` | `post_merge_closure + status_reconciliation_receipt` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-CHANGE-CLASS-001` | `repository_assessed` | `classification_record` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-CHANGE-ESCALATION-001` | `repository_assessed` | `classification_escalation_event` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-REPOSITORY-RISK-001` | `repository_assessed` | `repository_profile_snapshot` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-CLASSIFICATION-DRIFT-001` | `repository_assessed` | `classification_metrics_report` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-CONTROL-EFFECTIVENESS-001` | `repository_assessed` | `blocking_control_justification + control_effectiveness_record` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-DOCUMENT-INTEGRITY-001` | `repository_assessed` | `release_integrity_report + parity_matrix` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-STANDARD-RELEASE-001` | `structured_required` | `release artifacts + selected_path_audit + assurance disclosure + activation receipt` | release validator | required | required | `validator_backed_at_release` |
| `AIGOV-EVIDENCE-PROPORTIONALITY-001` | `repository_assessed` | `evidence_budget` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-REPORTING-001` | `repository_assessed` | `owner_result_projection` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-SECURITY-PROFILE-001` | `structured_required` | `review_activation_condition` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-HUMAN-001` | `repository_assessed` | `authority_record` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-COACH-001` | `repository_assessed` | `owner_action_card` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-SEMANTIC-CARRIER-001` | `structured_required` | `semantic_carrier_contract` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-BEHAVIORAL-COVERAGE-001` | `structured_required` | `behavioral_rule_coverage_record` | repository-defined | required | profile-dependent | `prose_only_until_adopted` |
| `AIGOV-TOOL-EXECUTION-001` | `structured_required` | `tool_execution_attestation` | repository-defined | required | required for consequential paths | `prose_only_until_adopted` |

خالی‌بودن carrier یا validator وعده محسوب نمی‌شود. `ci_enforced` بدون CI Evidence و `downstream_contract_enforced` بدون rejection proof ممنوع است. جزئیات Audit Method و Patch Strategy در `AIGOV_BEHAVIORAL_RULE_COVERAGE_CONTRACT_v1.2.0.fa.md` قرار دارد.

## 17. Authority و carrier guidance

> Authority: NORMATIVE; path examples INFORMATIVE

هر authority باید این shape را داشته باشد:

```yaml
authority_record:
  path_or_endpoint: "<stable>"
  responsibility: "<one responsibility>"
  authority_type: canonical | mutable | historical | derived
  exact_identity: "<digest/sha/id>"
  update_mechanism: "<mechanism>"
  conflict_rule: "<rule>"
```

فایل جدید فقط وقتی ساخته شود که failure boundary بدون carrier باقی می‌ماند. Minimum normative meaning مربوط به `obligation_authority_binding` و `tool_execution_attestation` در Core است؛ Companion فقط methodology و implementation guidance می‌دهد. Comment Receipt authority عمومی Repository نیست؛ publication carrier یک Review package exact است.

## 18. Cost/benefit و control effectiveness

> Authority: NORMATIVE

### 18.1 Blocking-control justification

```yaml
blocking_control_justification:
  control_id: "<id>"
  failure_boundary: "<canonical-boundary>"
  distinct_risk_reduction: true | false
  cheaper_equivalent_exists: true | false
  evidence_automatically_persisted: true | false
  bounded_recovery_exists: true | false
  owner_manual_burden: low | medium | high
  delivery_delay: low | medium | high
  operational_complexity: low | medium | high
  decision: retain | automate | simplify | conditionalize | narrow | remove
```

Blocking فقط وقتی مجاز است که failure boundary متمایز، risk reduction قابل‌توضیح، نبود alternative کافی ارزان‌تر و recovery محدود وجود داشته باشد.

### 18.2 Control-effectiveness record

```yaml
control_effectiveness_record:
  control_id: "<id>"
  incidents_prevented: []
  false_blocks_or_deadlocks: []
  material_delay_events: []
  duplicated_by: []
  latest_incident_ref: null
  disposition: retain | automate | simplify | narrow | conditionalize | retire_candidate
```

Update event-driven است: incident، deadlock، major release یا Gate change؛ periodic bureaucracy اجباری نیست.

## 19. Recommended adoption sequence

> Authority: INFORMATIVE — ordering is safety-relevant when predicates apply

```text
1. exact core Candidate، active Profile/Contract candidates و parity matrix را pin کن؛
2. authority-bound obligations و applicable deterministic prechecks را inventory کن؛
3. Critical/High behavioral gates و EFBG/Semantic Illusion gapها را ثبت کن؛
4. minimum Core carriers، bounded validators و invalid fixtures را قبل از enforcement claim بساز؛
5. consequential tool paths را با source-to-parameter، invocation، result، read-back و claim binding validate کن؛
6. PR-Inspector publisher را جدا و least-privilege پیاده و publication/read-back/retry/conflict را non-blocking آزمایش کن؛
7. Companionها را با independent audit جداگانه active کن؛
8. Repository Profile و Behavioral Coverage Contract را exact adopt کن؛
9. policy transition مستقل را اجرا کن؛
10. required Review را فقط بعد از carrier/recovery proof blocking کن؛
11. post-Merge closure و status reconciliation را اجرا کن.
```

## 20. Acceptance Criteria

> Authority: NORMATIVE

نسخه یا adoption فقط وقتی acceptable است که:

- [ ] `change_class` و Review requirement خروجی‌های جدا باشند؛
- [ ] applicability و trigger دو domain مستقل باشند؛
- [ ] هر mandatory، rejecting، blocking، scope-limiting، evidence-requiring یا tool-constraining obligation exact-bound به canonical authority باشد؛
- [ ] obligation unresolved یا invented authority جدید ایجاد نکند؛
- [ ] invented applicability، trigger یا profile exclusion enforce نشود؛
- [ ] exclusion، deferral، omission یا out-of-scope classification بدون authority binding رد شود؛
- [ ] required deterministic prechecks قبل از consequential authorization اجرا شوند؛
- [ ] `consequential_decision_authorized` فقط با `PASS` یا authority-bound `NOT_APPLICABLE_WITH_AUTHORITY` true شود؛
- [ ] deterministic failure تحلیل غیرمجازکننده و Recovery guidance را ممنوع نکند؛
- [ ] policy resolution exact، versioned و identity-bound باشد؛
- [ ] Activation Condition اثر کامل پنج‌محوره داشته باشد؛
- [ ] missing/stale/invalid/conflicting policy به `BLOCKED_POLICY_UNRESOLVED` برسد؛
- [ ] `minimal` technical-quality Review باشد؛
- [ ] `expedited` invariantهای فنی را حذف نکند؛
- [ ] Review execution، immutable Receipt Core و publication attempt جدا باشند؛
- [ ] Receipt Core با RFC 8785/JCS canonicalize و SHA-256 شود؛
- [ ] Publisher metadata یا timestamp داخل Receipt Core نباشد؛
- [ ] Inspector و Publisher identity جدا باشند؛
- [ ] Publisher capability محدود و exact-target-bound باشد؛
- [ ] هر consequential tool parameter source-bound یا transformation-bound باشد؛
- [ ] claimed tool execution invocation Evidence داشته باشد؛
- [ ] state-changing tool action read-back verified یا exact permitted equivalent داشته باشد؛
- [ ] tool-derived final claim به verified result/read-back fields متصل باشد؛
- [ ] structured carrier append-only و exact-head-bound باشد؛
- [ ] supersession chain با Retry publication مخلوط نشود؛
- [ ] publication retry روی Head ثابت rereview ایجاد نکند؛
- [ ] stale verdict و reusable Evidence جدا ارزیابی شوند؛
- [ ] typed policy transition تمام safety/write/mutation predicates را داشته باشد؛
- [ ] historical Evidence gap جعل یا پاک نشود؛
- [ ] Merge proof هر سه method را پشتیبانی کند؛
- [ ] `STATUS_DRIFT` post-Merge closure و dependent work را block کند، نه historical readiness؛
- [ ] `merge_governance_status` authority و vocabulary واحد داشته باشد؛
- [ ] هر composite Critical predicate Minimum Semantic Children داشته باشد؛
- [ ] caller-supplied Boolean به‌تنهایی semantic Evidence نباشد؛
- [ ] هر Critical/High behavioral gate coverage record داشته باشد؛
- [ ] Critical EFBG یا shallow carrier open enforcement gap باشد؛
- [ ] modal-language scan false positive و informative text را جدا کند؛
- [ ] هیچ enforcement status قوی‌تر از Evidence ادعا نشود؛
- [ ] هر Blocking Gate cost/benefit و bounded Recovery داشته باشد؛
- [ ] embedded prompt و Audit Prompt همهٔ 27 Rule را صریح پوشش دهند؛
- [ ] projection parity matrix برای هر Rule همه surfaces را map کند؛
- [ ] Companion Candidate بدون activation جداگانه adopt یا integrate نشود؛
- [ ] manifest scope و excluded files صریح باشند؛
- [ ] ZIP Digest بیرونی تولید شود؛
- [ ] exactly one activation path انتخاب و تمام prerequisites آن کامل شده باشد؛
- [ ] PATH A به fresh independent document audit و `INDEPENDENTLY_AUDITED` exact-bind باشد؛
- [ ] PATH B فقط در narrow intended scope، با same-context audit غیرمستقل، zero blocking findings، explicit reduced-independence acceptance و `MAINTAINER_CONTROLLED_DETERMINISTIC` استفاده شود؛
- [ ] same-context audit هرگز independent نامیده نشود و assurance-equivalence ادعا نکند؛
- [ ] activation Receipt، bounded transform، active integrity، active Manifest و external ZIP sidecar قبل از معتبرشدن active status وجود داشته باشند؛
- [ ] active core با metadata-only transform truthful بماند و Evidence نهایی external exact-bound باشد؛

Rule-level acceptance coverage:

- `AIGOV-START-001`
- `AIGOV-APPLICABILITY-001`
- `AIGOV-SCOPE-001`
- `AIGOV-SCOPE-DISCLOSURE-001`
- `AIGOV-PROGRESS-001`
- `AIGOV-EVIDENCE-001`
- `AIGOV-INDEPENDENCE-001`
- `AIGOV-REVIEW-PUBLICATION-001`
- `AIGOV-STALE-001`
- `AIGOV-MERGE-001`
- `AIGOV-POLICY-TRANSITION-001`
- `AIGOV-STATUS-RECONCILIATION-001`
- `AIGOV-CHANGE-CLASS-001`
- `AIGOV-CHANGE-ESCALATION-001`
- `AIGOV-REPOSITORY-RISK-001`
- `AIGOV-CLASSIFICATION-DRIFT-001`
- `AIGOV-CONTROL-EFFECTIVENESS-001`
- `AIGOV-DOCUMENT-INTEGRITY-001`
- `AIGOV-STANDARD-RELEASE-001`
- `AIGOV-EVIDENCE-PROPORTIONALITY-001`
- `AIGOV-REPORTING-001`
- `AIGOV-SECURITY-PROFILE-001`
- `AIGOV-HUMAN-001`
- `AIGOV-COACH-001`
- `AIGOV-SEMANTIC-CARRIER-001`
- `AIGOV-BEHAVIORAL-COVERAGE-001`
- `AIGOV-TOOL-EXECUTION-001`

## 21. Owner-facing result projection

> Authority: OPERATIONAL PROJECTION — NON-NORMATIVE

گزارش owner باید کوتاه اما domain-complete باشد:

```yaml
owner_result:
  deterministic_prechecks:
    status: PASS | NOT_APPLICABLE_WITH_AUTHORITY | FAIL | BLOCKED_INSUFFICIENT_EVIDENCE
  consequential_decision_authorized: true | false
  tool_execution:
    status: not_applicable | verified | blocked
    attestation_ref: null
  technical_status: "<canonical>"
  review:
    requirement: required | optional_advisory
    execution_status: not_started | in_progress | performed | failed
    validity: CURRENT | STALE | UNKNOWN
  receipt:
    publication_status: not_required | not_attempted | publishing | published_verified | publication_failed
    validation_status: not_checked | current_valid | stale | invalid | conflicting
  merge:
    readiness_result: "<canonical>"
    enforcement_profile: owner_controlled | ci_enforced | repository_enforced
  post_merge:
    status: "<qualified>"
  blocker: null
  next_owner_action: "<exactly one action>"
```

نمونه‌های مجاز:

```text
Review انجام شده، اما انتشار Receipt شکست خورده است؛ چون Head تغییر نکرده، همان Receipt باید دوباره منتشر شود.
```

```text
Review قبلی وجود دارد، اما برای Head فعلی stale است؛ Review تازه لازم است.
```

## 22. Audit Prompt

> Authority: OPERATIONAL PROJECTION — NON-NORMATIVE

```yaml
audit_prompt_metadata:
  name: AIGOV v2.5.0 Exact-Document Release and Adoption Audit Prompt
  source_standard_version: "2.5.0"
  generated_projection: false
  normative_authority: false
  parity_validation_required: true
  candidate_parity_validation_ref: AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.projection-parity-matrix.json
  active_parity_validation_ref: AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.active-release-integrity.md
```

````text
[ROLE]
Act as an exact-document and Repository-adoption auditor for AIGOV v2.5.0. For PATH A, require genuine reviewer independence and no same-pass repair. For PATH B, disclose `audit_independence=NOT_INDEPENDENT`, apply deterministic read-only audit after Candidate freeze, and never claim independent assurance.

[DOCUMENT RELEASE]
Verify exact Candidate digest, projection parity matrix, Manifest scope and Companion lifecycle. Resolve exactly one path: PATH A requires a fresh independent audit and `INDEPENDENTLY_AUDITED`; PATH B requires narrow-scope eligibility, same-context final audit, zero blocking findings, explicit reduced-independence acceptance and `MAINTAINER_CONTROLLED_DETERMINISTIC`. Verify truthful assurance disclosure, bounded metadata-only transform, active digest, active release-integrity, activation Receipt, active Manifest and external ZIP digest.

[START, DETERMINISTIC PRECHECKS, AUTHORITY-BOUND OBLIGATIONS, APPLICABILITY AND TRIGGER]
Resolve exact Repository/target/Head/authorities/capabilities. Verify required mechanically decidable prechecks precede consequential authorization and cannot be overridden by LLM judgment. Confirm blocked prechecks still permit non-authorizing analysis and Recovery guidance. Verify every mandatory/rejecting/blocking/scope-limiting/evidence-requiring/tool-constraining obligation is exact-bound to canonical authority. Evaluate rule_applicability and rule_trigger independently; invented or unknown conditions cannot become authoritative or NOT_TRIGGERED.

[SCOPE, PROGRESS AND EVIDENCE]
Verify exact Scope; authority-bound exclusions/deferrals; qualified progress states; claim-to-Evidence and obligation-to-authority binding; historical-gap truth; and smallest sufficient Evidence.

[REPOSITORY RISK AND CLASSIFICATION DRIFT]
Verify exact Repository risk profile, reject generalization of Repository-specific recovery tasks, and keep advisory drift metrics separate from classification and STATUS_DRIFT.

[BEHAVIORAL COVERAGE]
Scan modal language as a heuristic; classify normative gate vs informative/example/false positive. Audit every Critical/High gate for EFBG. Detect Semantic Illusion, shallow Boolean compliance and missing Minimum Semantic Children. Verify strongest proven enforcement only.

[POLICY AND ACTIVATION]
Verify exact Repository policy and complete Activation Condition effects across requirement, inspection, evidence, enforcement and urgency. Verify legal/contractual Boundary mapping.

[TOOL EXECUTION]
Verify capability authority, tool/schema identity, exact target identity, source-to-parameter binding, transformation validation, invocation Evidence, result capture, required read-back, staleness and result-to-claim binding. Reject schema-valid but source-detached parameters and wrong-target success.

[REVIEW AND PUBLICATION]
Verify immutable review_receipt_core, RFC 8785/JCS digest, separate publication_attempt, complete Inspector/Publisher identities, bounded capability, read-back, retry, staleness, supersession and conflict handling.

[POLICY TRANSITION]
Validate typed policy_transition_record and non-circular transition semantics.

[MERGE AND POST-MERGE]
Verify conditional pre-Merge readiness, actual Merge method, content proof for Squash/Rebase, current-main validation, post_merge_closure_status, dependent_work_authorization and blocking recoverable STATUS_DRIFT without rewriting historical readiness.

[COST, SECURITY, REPORTING AND HUMAN BOUNDARIES]
Verify distinct Failure Boundary, proportional control cost, evidence proportionality, full safety activation effects, owner-only Merge, no technical-approval inference from owner action, smallest complete reporting and one precise owner action.

[RULE PARITY]
Evaluate and report each Rule exactly once: AIGOV-START-001, AIGOV-APPLICABILITY-001, AIGOV-SCOPE-001, AIGOV-SCOPE-DISCLOSURE-001, AIGOV-PROGRESS-001, AIGOV-EVIDENCE-001, AIGOV-INDEPENDENCE-001, AIGOV-REVIEW-PUBLICATION-001, AIGOV-STALE-001, AIGOV-MERGE-001, AIGOV-POLICY-TRANSITION-001, AIGOV-STATUS-RECONCILIATION-001, AIGOV-CHANGE-CLASS-001, AIGOV-CHANGE-ESCALATION-001, AIGOV-REPOSITORY-RISK-001, AIGOV-CLASSIFICATION-DRIFT-001, AIGOV-CONTROL-EFFECTIVENESS-001, AIGOV-DOCUMENT-INTEGRITY-001, AIGOV-STANDARD-RELEASE-001, AIGOV-EVIDENCE-PROPORTIONALITY-001, AIGOV-REPORTING-001, AIGOV-SECURITY-PROFILE-001, AIGOV-HUMAN-001, AIGOV-COACH-001, AIGOV-SEMANTIC-CARRIER-001, AIGOV-BEHAVIORAL-COVERAGE-001, AIGOV-TOOL-EXECUTION-001.

[OUTPUT]
Return exact Evidence, obligation authority results, deterministic precheck/consequential authorization results, Tool Execution attestation results, per-Rule result, EFBG/Semantic Illusion findings, Critical/High/semantic-Medium findings, release-integrity verdict and exactly one next lifecycle action.
````

## 23. Migration و compatibility

> Authority: NORMATIVE

### 23.1 Version relationship

`v2.1.0`، `v2.2.0`، `v2.2.1`، `v2.3.0` و `v2.4.0` historical exact identities باقی می‌مانند. `v2.5.0` successor identity تازه دارد و هیچ digest قبلی را بازنویسی نمی‌کند. Repository adoption خودکار به lifecycle policy جدید منتقل نمی‌شود.

### 23.2 Repository migration

Policy فعلی تا migration صریح معتبر است. هیچ auto-switch به required یا optional رخ نمی‌دهد. Publication requirement فقط بعد از operational publisher و Recovery proof blocking می‌شود.

### 23.3 Safe migration order for optional→required

```text
implement bounded publisher
→ validate Core canonicalization/publication/read-back/retry/conflict
→ close Critical behavioral coverage gaps
→ activate required Companion contracts
→ adopt Repository Profile
→ run non-blocking trial
→ separate policy transition to required
→ exact-main verification and post-Merge reconciliation
```

### 23.4 Existing reviews

Review قدیمی فقط برای exact Head خود معتبر است. Receiptهای schema قدیمی historical context هستند و خودکار current acceptance نمی‌شوند.

### 23.5 Companion contracts

Core activation هیچ Companion را فعال نمی‌کند.

| Companion | Candidate use | Production adoption/integration |
|---|---|---|
| Personal Repository Profile | audit/distribution | blocked until `active_companion` + activation receipt |
| PR-Inspector Publication Contract | implementation planning/non-authoritative trial | blocked until `active_companion` + integration receipt |
| Behavioral Rule Coverage Contract | inventory/non-blocking trial with explicit owner authorization | blocked until `active_companion` + adoption receipt |
| Incident Record | informative | activation not required |

Core هیچ normative dependency به active Companion ندارد؛ Repository-specific adoption ممکن است dependency ایجاد کند.

## 24. Standard release lifecycle

> Authority: NORMATIVE

### 24.1 Candidate integrity

Candidate باید exact digest، Rule count، Boundary count، fixture count، Companion hashes، projection parity matrix، Manifest scope، Implementation Report و structural validation داشته باشد.

### 24.2 Declared stable artifact paths

```text
AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.release-integrity.md
AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.projection-parity-matrix.json
AIGOV_v2.5.0_SAME_CONTEXT_FINAL_AUDIT.fa.md
AIGOV_v2.5.0_ACTIVATION_TRANSFORM_REPORT.fa.md
AIGOV_v2.5.0_ACTIVATION_RECEIPT.fa.md
AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.active-release-integrity.md
bundle-manifest.json
AIGOV_v2.5.0_active_bundle.zip.sha256
```

Declared path Evidence نیست تا exact-bound reference و digest موجود باشد.

### 24.3 Manifest and archive checksum scope

```yaml
manifest_scope:
  normative_and_release_evidence_files_only: true
  excluded_non_normative_files:
    - README.md
    - bundle-manifest.json
  external_archive_digest_required: true
  manifest_self_hash: false
archive_digest_rule:
  location: external_sidecar
  sidecar_inside_its_own_zip: prohibited
  locally_computed_digest_is_externally_trusted: false
```

Manifest self-hash نمی‌کند. ZIP Digest در external sidecar ثبت می‌شود تا circular dependency ایجاد نشود.

### 24.4 Activation path registry

```yaml
activation_paths:
  PATH_A_INDEPENDENT_ACTIVATION:
    preferred: true
    assurance_level: INDEPENDENTLY_AUDITED
    prerequisites:
      - fresh_independent_document_audit
      - exact_candidate_identity_binding
      - same_context_release_integrity_pass
      - projection_parity_pass
      - zero_blocking_findings
      - bounded_activation_transform
  PATH_B_MAINTAINER_CONTROLLED_DETERMINISTIC_ACTIVATION:
    preferred: false
    assurance_level: MAINTAINER_CONTROLLED_DETERMINISTIC
    intended_use:
      - single-maintainer governance systems
      - personal AI-operated governance systems
      - isolated reviewer infrastructure unavailable
      - operator explicitly accepts reduced independence guarantee
    prerequisites:
      - same_context_final_audit_pass
      - audit_independence_NOT_INDEPENDENT
      - same_context_release_integrity_pass
      - projection_parity_pass
      - zero_blocking_findings
      - explicit_activation_basis_disclosure
      - bounded_activation_transform
```

`PATH A` stronger و preferred است. `PATH B` assurance-equivalent با independent review نیست و خارج از intended scope مجاز نیست. `same_context_final_audit != independent_document_audit`.

### 24.5 Deterministic activation eligibility

```yaml
activation_eligibility:
  selected_path: PATH_A_INDEPENDENT_ACTIVATION | PATH_B_MAINTAINER_CONTROLLED_DETERMINISTIC_ACTIVATION
  candidate_identity_bound: true
  candidate_release_integrity: PASS
  projection_parity: PASS
  blocking_findings: 0
  selected_path_audit_status: PASS
  activation_assurance_level: INDEPENDENTLY_AUDITED | MAINTAINER_CONTROLLED_DETERMINISTIC
  activation_basis: INDEPENDENT_DOCUMENT_AUDIT_FINALIZATION | SAME_CONTEXT_DETERMINISTIC_FINALIZATION
  reduced_independence_accepted: false | true
```

Fieldهای selected path باید mutually consistent باشند. PATH B باید `independent_document_audit_status: NOT_PERFORMED` یا exact prior independent evidence را بدون تبدیل آن به basis این activation ثبت کند.

### 24.6 Bounded metadata-only activation

```yaml
deterministic_activation_transition:
  source_status: release_candidate
  target_status: active_governing_standard
  candidate_document_digest: "<digest>"
  selected_path_audit_ref: "<stable-ref>"
  allowed_transform:
    type: exact_metadata_only_promotion
    permitted_changes:
      - lifecycle status fields
      - activation status and basis fields
      - assurance-level disclosures
      - activation timestamp and receipt references
      - active artifact identities and derived hashes
      - Manifest and release-integrity identities
      - archive filename and external checksum sidecar
  prohibited_changes:
    - normative_clause_semantics
    - rule_catalog_semantics
    - status_vocabulary
    - boundary_registry
    - embedded_prompt_semantics
    - audit_prompt_semantics
    - acceptance_criteria
    - migration_semantics
  active_document_digest: "<digest>"
  final_release_integrity_ref: "AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.active-release-integrity.md"
  activation_receipt_ref: "AIGOV_v2.5.0_ACTIVATION_RECEIPT.fa.md"
  active_bundle_manifest_ref: "bundle-manifest.json"
```

هر semantic change پس از audit freeze، audit verdict را stale می‌کند و به Candidate تازه و audit کامل نیاز دارد.

### 24.7 Companion activation independence

Core activation هیچ Companion را فعال نمی‌کند. هر lifecycle-bearing Companion باید selected activation path، exact Candidate digest، assurance level، bounded transform و receipt جدا داشته باشد. Informative Incident Record activation نمی‌خواهد.

## 25. Adversarial and regression fixtures

> Authority: INFORMATIVE — expected outcomes are truth-constrained

1. `L3` under optional_advisory و Gates pass → READY ممکن است بدون Review.
2. `L3` under required با Review مفقود → BLOCKED_REQUIRED_REVIEW.
3. Destructive/Secret/Production Trigger → effect کامل strict/high_assurance/enforcement minimum.
4. Legal/contractual Trigger بدون Boundary mapping → policy resolution failure.
5. Rule Repository-applicable ولی target not triggered → applicability حفظ و trigger جدا.
6. Unknown Trigger evidence → BLOCKED_INSUFFICIENT_EVIDENCE، نه NOT_TRIGGERED.
7. Review performed، publication failed، Head ثابت → همان Core با attempt تازه.
8. Publication failed و Head تغییر کرد → Review STALE؛ rereview.
9. Publisher metadata داخل Core → canonical schema failure.
10. YAML whitespace تغییر می‌کند ولی JCS Core digest ثابت می‌ماند.
11. Caller-modified Core field → digest mismatch.
12. دو publication attempt برای یک Core → یک review_id/Core digest، attempt IDs متفاوت.
13. دو Review Core متعارض بدون supersession → RECEIPT_CONFLICT.
14. Valid supersession chain → terminal Core current authority.
15. Implementer self-GREEN → independent acceptance نیست.
16. Stale optional advisory Review → readiness فقط به دلیل آن block نمی‌شود.
17. Stale required Review → blocked.
18. Historical Review غیرقابل‌بازتولید → no fabrication و disclosed gap.
19. Squash Merge با content equality و no ancestry → content_equivalence_verified.
20. Post-Merge status pending while main changed → blocked_status_drift؛ historical readiness unchanged.
21. STATUS_DRIFT reconciled → status_reconciled سپس closure_recorded.
22. Policy transition bundled with unrelated implementation → rejected.
23. Gate بدون distinct Failure Boundary یا bounded Recovery → control-effectiveness failure.
24. `GREEN_TECHNICALLY_READY + enforcement_unverified` → Technical Green حفظ.
25. Composite Critical Rule با boolean تنها → BLOCKED_SEMANTIC_ILLUSION.
26. Composite carrier missing one Minimum Semantic Child → invalid fixture must fail.
27. Validator-derived Boolean با canonical Evidence ref → acceptable projection.
28. Critical Rule prose_only → EFBG open gap.
29. High Rule schema_backed با documented temporary risk → allowed only per active Profile.
30. Modal word in informative example → false_positive، نه EFBG.
31. Claim `ci_enforced` بدون CI Evidence → downgrade to fixture_tested/validator_backed.
32. Claim downstream_contract_enforced بدون rejection proof → invalid overclaim.
33. Companion release_candidate adopted as production policy → blocked.
34. Core active with Candidate companions → Core may activate; companions remain unusable.
35. Audit Prompt missing one canonical Rule → projection parity failure.
36. Parity matrix row missing one surface → release-integrity failure.
37. Manifest omits declared normative file → bundle integrity failure.
38. ZIP sidecar digest mismatch → distribution integrity failure.
39. Metadata-only promotion retains truthful external-evidence architecture → allowed.
40. Cost/benefit invoked to bypass mandatory safety → rejected.
41. Valid `obligation_authority_binding` برای required field با canonical source → VERIFIED_SOURCE_BOUND و enforceable.
42. Invented required field بدون canonical source → REJECTED_NOT_AUTHORITATIVE؛ downstream rejection بر آن مجاز نیست.
43. Invented rejection criterion بدون authority binding → claim rejecting blocked و criterion حذف/رد می‌شود.
44. Scope exclusion یا deferral بدون VERIFIED_SOURCE_BOUND binding → BLOCKED_SCOPE_AUTHORITY_UNRESOLVED.
45. UNRESOLVED obligation به‌عنوان mandatory استفاده می‌شود → BLOCKED_OBLIGATION_AUTHORITY_UNRESOLVED.
46. همه deterministic precheckهای required برابر PASS یا authority-bound NOT_APPLICABLE_WITH_AUTHORITY → consequential_decision_authorized=true.
47. LLM قبل از deterministic identity failure Technical Green می‌دهد → consequential decision unauthorized و Green اثر مجازکننده ندارد.
48. LLM تلاش می‌کند FAIL یا BLOCKED_INSUFFICIENT_EVIDENCE را override کند → override rejected؛ non-authorizing analysis مجاز است.
49. Valid state-changing `tool_execution_attestation` با source-bound parameters، invocation/result و VERIFIED read-back → tool-derived claim معتبر.
50. Tool execution claimed بدون invocation record → BLOCKED_TOOL_EXECUTION_UNVERIFIED.
51. Arguments schema-valid ولی source-detached → BLOCKED_TOOL_PARAMETER_BINDING_INVALID.
52. Tool parameter value invented و فاقد source_ref → BLOCKED_TOOL_PARAMETER_BINDING_INVALID.
53. Authoritative source parameter omission بدون authority → BLOCKED_TOOL_PARAMETER_BINDING_INVALID.
54. Parameter transformation بدون transformation_id/validation_ref → BLOCKED_TOOL_PARAMETER_BINDING_INVALID.
55. Correct tool روی wrong Repository/PR/branch/Head/record target → BLOCKED_TOOL_TARGET_IDENTITY_MISMATCH.
56. Success claim بدون captured execution result → BLOCKED_TOOL_EXECUTION_UNVERIFIED.
57. Tool result موجود است ولی final claim به result/read-back fields متصل نیست → BLOCKED_TOOL_RESULT_CLAIM_UNBOUND.
58. State-changing action بدون VERIFIED read-back یا exact permitted equivalent → BLOCKED_TOOL_READBACK_UNVERIFIED.
59. Capability/source/tool-schema/target/result Evidence stale است → execution authority و derived claims تا reevaluation blocked.


60. PATH A با fresh independent audit، exact identity binding، zero blockers و bounded transform → `INDEPENDENTLY_AUDITED` و activation مجاز.
61. PATH B در personal AI-operated governance system با audit غیرمستقل، deterministic integrity PASS، parity PASS، zero blockers و reduced-independence acceptance → `MAINTAINER_CONTROLLED_DETERMINISTIC` و activation مجاز.
62. same-context audit با label `independent audit PASS` → `BLOCKING_LIFECYCLE` و activation ممنوع.
63. PATH B بدون narrow-scope eligibility یا بدون explicit reduced-independence acceptance → `BLOCKING_LIFECYCLE` و activation ممنوع.

## 26. Final normative summary

> Authority: NORMATIVE

- Core عمومی است؛ Personal Profile و Integration/Coverage Contract فقط با adoption صریح حاکم می‌شوند.
- Review requirement، inspection، evidence، enforcement و urgency مستقل‌اند.
- Activation Condition اثر کامل پنج‌محوره دارد.
- Review execution، immutable Receipt Core و publication attempt سه حقیقت جدا هستند.
- Receipt Core با RFC 8785/JCS canonicalize می‌شود؛ Publisher metadata داخل Core نیست.
- Applicability و Trigger مستقل‌اند.
- Model-generated obligation authority نیست؛ هر obligation اثرگذار باید exact-bound به canonical authority باشد.
- Deterministic prechecks قبل از consequential authorization اجرا می‌شوند، اما failure analysis و Recovery guidance غیرمجازکننده باقی می‌ماند.
- Technical Green، Merge readiness، Merge governance و post-Merge closure مستقل‌اند.
- STATUS_DRIFT post-Merge closure و dependent work را block می‌کند؛ historical readiness بازنویسی نمی‌شود.
- Content truth با Git topology یکی نیست.
- Historical Evidence جعل نمی‌شود و Fail closed به block forever تبدیل نمی‌شود.
- Prompt/protocol Repository behavioral source code است؛ Critical/High gates باید coverage record داشته باشند.
- Caller-supplied Boolean برای composite predicate semantic Evidence نیست.
- Critical Semantic Illusion و EFBG open enforcement gap هستند.
- Enforcement status فقط strongest proven carrier را نشان می‌دهد.
- Consequential tool execution باید source-to-parameter، invocation، result، read-back و result-to-claim binding قابل‌اعتبارسنجی داشته باشد.
- بهترین کنترل، کم‌هزینه‌ترین mechanism قابل‌اعتماد برای بستن Failure Boundary واقعی است.
- Core Candidate فقط با تکمیل دقیق PATH A یا PATH B، truthful assurance disclosure، bounded metadata-only transform و external exact-bound activation artifacts فعال می‌شود؛ PATH A stronger و preferred است.
- Core activation هیچ Candidate Companion را فعال نمی‌کند.
