---
title: AIGOV Behavioral Rule Coverage Contract
title_fa: قرارداد پوشش اجرایی قواعد رفتاری AIGOV
version: 1.2.0
status: active_companion
parent_standard: AI Authority Deterministic Governance v2.5.0
document_role: companion implementation contract for EFBG, Semantic Illusion, authority-bound obligations and source-bound tool execution
companion_lifecycle:
  activation_scope: separate_from_core
  adoption_allowed_status: active_companion
  core_activation_effect: none
adoption_eligibility:
  production_adoption: blocked_until_active
  non_blocking_inventory_trial: explicit_owner_authorization_required
---

# AIGOV Behavioral Rule Coverage Contract v1.2.0

## 1. Purpose

Prompt، protocol، role، schema، fixture، validator و CI در LLM-agent systems behavioral source code هستند. هدف حذف prose نیست؛ هدف جلوگیری از prose-only ماندن Critical/High behavioral gates و carrierهای ظاهراً compliant ولی معنایی‌تهی است.

## 2. Definitions

### Behavioral Gate
Ruleای که اجازهٔ ادامه، output، action، assumption، transform، package emission یا downstream handoff را تعیین می‌کند.

### EFBG
`Enforcement-Free Behavioral Gate`: Gate رفتاری که فقط در prose/example/role guidance وجود دارد و schema، validator، failing fixture، CI یا downstream rejection ندارد.

### Semantic Illusion
Carrier از نظر سطحی schema را پاس می‌کند ولی مفهوم Rule را حمل نمی‌کند؛ نمونه: `reference_paradigm_lock: true` بدون ساختار معنایی لازم.

### Minimum Semantic Children
کمینهٔ fieldها و constraintهایی که Agent را مجبور می‌کند predicate مرکب را واقعاً بازنمایی کند.

## 3. Core invariants

```text
field_presence != semantic_enforcement
caller_supplied_boolean != semantic_evidence
validator_derived_projection + canonical_evidence_ref = acceptable_projection
schema_backed != validator_backed
validator_backed != ci_enforced
ci_enforced != downstream_contract_enforced
```

## 4. Risk and minimum enforcement

| risk | minimum expectation |
|---|---|
| Critical | `fixture_tested` minimum؛ `ci_enforced` preferred؛ downstream rejection final target |
| High | `validator_backed` minimum؛ `fixture_tested` preferred |
| Medium | schema یا prose با justification ممکن است کافی باشد |
| Low | prose معمولاً کافی است؛ over-engineering ممنوع |

Active Repository Profile می‌تواند minimum را قوی‌تر کند. هر downgrade باید exact justification و residual risk داشته باشد.

## 5. Coverage record

```yaml
behavioral_rule_coverage_record:
  rule_id: "<stable-id>"
  concept: "<statement>"
  risk: Critical | High | Medium | Low
  prose_source: "<path+section>"
  statement_class: normative_gate | informative_guidance | example | false_positive
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
  risk_acceptance_ref: null
  planned_patch: null
```

Stable Rule ID پس از removal reuse نمی‌شود.

## 6. Semantic carrier contract

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

`structured_required` بدون Minimum Semantic Children → `BLOCKED_SEMANTIC_ILLUSION`.

## 6.1 Core carrier authority boundary

```text
Core defines minimum normative carrier meaning.
This Companion provides implementation methodology and does not replace,
override, narrow, or independently create Core authority.
```

`obligation_authority_binding` و `tool_execution_attestation` باید از Core `AIGOV v2.5.0` خوانده شوند. Repository implementation می‌تواند fieldهای اضافی داشته باشد، اما حذف Minimum Semantic Children، تغییر enum semantics یا تضعیف cross-field constraints مجاز نیست.

## 6.2 Obligation authority binding — implementation guidance

Validator implementation باید حداقل این checks را انجام دهد:

```text
stable obligation_id
+ supported obligation_type
+ exact authority_ref
+ exact authority_identity
+ resolvable source_locator
+ canonical resolution_status
```

Cross-field checks:

```text
mandatory/rejecting/blocking/scope-limiting/evidence-requiring/tool-constraining
requires VERIFIED_SOURCE_BOUND

UNRESOLVED
cannot authorize enforcement

REJECTED_NOT_AUTHORITATIVE
must not be projected as an active obligation
```

Required fixture templates:

```text
valid-source-bound-required-field
invalid-invented-required-field
invalid-invented-rejection-criterion
invalid-unauthorized-scope-exclusion
invalid-unresolved-obligation-treated-mandatory
```

## 6.3 Tool execution attestation — implementation guidance

Schema implementation باید Core minimum fields را حفظ کند و consequential parameterها را به source field exact-bound سازد.

Recommended validator chain:

```text
capability authorization
→ tool/schema identity validation
→ target identity validation
→ source field existence and identity
→ transformation allowlist and validation
→ invocation attestation
→ execution result capture
→ state-change/read-back constraint
→ result-to-claim projection validation
```

Invalid fixture templates:

```text
tool-claimed-without-invocation
tool-schema-valid-source-detached
tool-invented-parameter-value
tool-omitted-authoritative-source
tool-undeclared-transformation
tool-wrong-target-identity
tool-success-without-result
tool-result-ignored-by-claim
tool-state-change-without-readback
tool-stale-execution-evidence
```

CI/downstream pattern:

```text
validate carrier
→ fail consequential workflow on invalid binding/execution/read-back
→ emit stable reason code
→ persist exact Evidence
→ downstream consumer rejects unverified tool-derived claim
```

A read-only action may use `READBACK_NOT_REQUIRED` only when Core predicates are satisfied and exact authority/reason is persisted.

## 7. Audit discovery method

Modal-language scan فقط heuristic است.

English patterns:

```text
must, must not, shall, should not, never, always, only, required,
forbidden, blocked, allowed only, do not, cannot
```

Persian patterns:

```text
باید، نباید، هرگز، همیشه، فقط، مجاز نیست، الزامی است، اجباری است، مسدود، متوقف شود
```

Target files:

```text
.md, .txt, .prompt, prompt JSON, YAML protocols, system instructions,
handoff templates, role boundaries, quality bars, failure pattern libraries
```

Flow:

```text
modal scan
→ candidate statement
→ normative/informative/example/false-positive classification
→ risk classification
→ carrier lookup
→ Semantic Illusion/EFBG determination
```

## 8. Red flags

- `must` بدون schema/carrier؛
- `must not` بدون invalid fixture؛
- downstream Agent بدون rejection contract؛
- vague `preserve/match/respect` بدون Minimum Semantic Children؛
- proof object بدون required shape؛
- `fail closed` در prose ولی validator missing data را می‌پذیرد؛
- `production_ready: true` بدون structured QA Evidence؛
- Boolean lock بدون semantic children.

## 9. Enforcement chain

```text
Concept
→ Canonical carrier
→ Minimum Semantic Children
→ Validator
→ Valid fixture
→ Invalid fixture
→ CI
→ Downstream rejection
```

Strongest proven status فقط آخرین مرحله‌ای است که Evidence آن واقعاً موجود است.

## 10. Example — reference paradigm lock

Unsafe:

```json
{"reference_paradigm_lock": true}
```

Minimum structured form:

```json
{
  "reference_paradigm_lock": {
    "source_reference_id": "sshot-2168",
    "paradigm_locked": true,
    "layout_paradigm": "center-anchored-symmetric",
    "primary_anchor": "house-center",
    "distribution_model": "3-left-3-right",
    "repeated_unit_form": "pill-card",
    "connector_model": "card-edge-to-house-edge",
    "completion_signature": [
      "central house visually dominates",
      "exactly 3 cards left",
      "exactly 3 cards right",
      "connector lines bind card edges to house edges"
    ]
  }
}
```

## 11. Anti-overengineering

Critical/High risk focus. Tone، style، low-risk wording و creative preference نباید بی‌دلیل validator شوند. کوچک‌ترین mechanism specific/testable/fixture-backed/downstream-aware انتخاب شود.

## 12. Incremental Patch Strategy

```text
PATCH-001: Coverage Matrix Lite
  Inventory Critical/High gates and record honest baseline.

PATCH-002: Conservative Coverage Validator
  Fail confirmed Critical prose_only/shallow schema gaps; modal scan alone verdict نیست.

PATCH-003: Close Semantic Illusion Gaps
  Add Minimum Semantic Children, cross-field constraints and invalid fixtures.

PATCH-004: CI and Downstream Alignment
  Run validators in CI and make consumers reject invalid/missing carriers.

PATCH-005: Stale Prose Cleanup
  Replace duplication with canonical carrier/validator references only after enforcement is proven.
```

## 13. Governance questions for every new Critical gate

```text
What carrier holds it?
What Minimum Semantic Children prevent shallow compliance?
What validator checks it?
What invalid fixture proves failure?
What CI step runs it?
What downstream consumer rejects it?
What bounded Recovery exists?
```

## 14. Acceptance

- every Critical/High gate has a coverage record؛
- Critical prose_only یا shallow schema_backed gap صریح است؛
- composite Critical predicate Minimum Semantic Children دارد؛
- Core-defined `obligation_authority_binding` بدون redefinition پیاده‌سازی می‌شود؛
- Core-defined `tool_execution_attestation` بدون redefinition پیاده‌سازی می‌شود؛
- invalid source-to-parameter، invocation، read-back و result-to-claim fixtures وجود دارند؛
- at least one invalid fixture برای Critical semantic carrier؛
- no CI claim without CI Evidence؛
- no downstream-enforced claim without rejection proof؛
- modal scan false positives را authoritative نمی‌کند؛
- low-risk prose over-engineered نمی‌شود؛
- Contract فقط با receipt جدا `active_companion` می‌شود. PATH A با independent companion audit stronger و preferred است؛ PATH B فقط در narrow single-maintainer/personal AI-operated scope، با audit غیرمستقل، deterministic integrity، zero blockers و explicit reduced-independence acceptance مجاز است.
