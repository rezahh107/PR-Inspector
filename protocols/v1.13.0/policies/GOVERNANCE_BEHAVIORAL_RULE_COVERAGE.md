# Merge Governance Rule Coverage v1.13.0

Status: generated, non-authoritative view of `../functional-runtime-contract.json`.

Validation command: `python -m pytest -q tests/test_governance_enforcement.py`
| rule_id | risk | validator | positive_control | negative_mutation | CI_step | recovery_action |
|---|---|---|---|---|---|---|
| `PRR-GOV-PERSONAL-PROFILE-001` | High | scripts/validate_repository.py:main | scripts/validate_repository.py:main | README.md#profile_minimum_enforcement_absent | python -m pytest -q tests/test_behavioral_rule_coverage.py tests/test_governance_enforcement.py | block |
| `PRR-GOV-PROFILE-TRIGGER-001` | High | scripts/validate_repository.py:main | scripts/validate_repository.py:main | README.md#profile_trigger_without_verified_enforcement | python -m pytest -q tests/test_behavioral_rule_coverage.py tests/test_governance_enforcement.py | block |
| `PRR-GOV-CLAIM-SEPARATION-001` | High | scripts/validate_repository.py:main | scripts/validate_repository.py:main | README.md#profile_self_asserted_stronger_claims | python -m pytest -q tests/test_behavioral_rule_coverage.py tests/test_governance_enforcement.py | block |
| `PRR-GOV-PROJECTION-AUTHORITY-001` | High | scripts/validate_repository.py:main | scripts/validate_repository.py:main | README.md#profile_manual_projection_override | python -m pytest -q tests/test_behavioral_rule_coverage.py tests/test_governance_enforcement.py | block |
| `PRR-DOC-LIFECYCLE-001` | High | scripts/validate_repository.py:main | scripts/validate_repository.py:main | README.md#stale_unmerged_candidate_wording | python -m pytest -q tests/test_behavioral_rule_coverage.py tests/test_governance_enforcement.py | block |
| `PRR-GOV-CLAIM-001` | Critical | scripts/validate_repository.py:main | scripts/validate_repository.py:main | README.md#missing_settings_evidence | python -m pytest -q tests/test_behavioral_rule_coverage.py tests/test_governance_enforcement.py | block |
| `PRR-GOV-PAYLOAD-PROVENANCE-001` | Critical | scripts/validate_repository.py:main | scripts/validate_repository.py:main | README.md#fabricated_record_with_canonical_urls | python -m pytest -q tests/test_behavioral_rule_coverage.py tests/test_governance_enforcement.py | block |
| `PRR-GOV-REVIEW-001` | Critical | scripts/validate_repository.py:main | scripts/validate_repository.py:main | README.md#bot_author_or_stale_review | python -m pytest -q tests/test_behavioral_rule_coverage.py tests/test_governance_enforcement.py | block |
| `PRR-GOV-CHECK-PRODUCER-001` | Critical | scripts/validate_repository.py:main | scripts/validate_repository.py:main | README.md#same_name_check_wrong_app | python -m pytest -q tests/test_behavioral_rule_coverage.py tests/test_governance_enforcement.py | block |
| `PRR-GOV-SPECIALIST-001` | High | scripts/validate_repository.py:main | scripts/validate_repository.py:main | README.md#specialist_boolean_without_membership | python -m pytest -q tests/test_behavioral_rule_coverage.py tests/test_governance_enforcement.py | block |
| `PRR-GOV-FRESHNESS-001` | Critical | scripts/validate_repository.py:main | scripts/validate_repository.py:main | README.md#stale_or_replayed_api_receipt | python -m pytest -q tests/test_behavioral_rule_coverage.py tests/test_governance_enforcement.py | block |
| `PRR-GOV-AUTHORIZATION-001` | Critical | scripts/validate_repository.py:main | scripts/validate_repository.py:main | README.md#missing_governance_capability | python -m pytest -q tests/test_behavioral_rule_coverage.py tests/test_governance_enforcement.py | block |
| `PRR-GOV-CLI-001` | Critical | scripts/validate_repository.py:main | scripts/validate_repository.py:main | README.md#merge_authorized_cli_without_governance | python -m pytest -q tests/test_behavioral_rule_coverage.py tests/test_governance_enforcement.py | block |
| `PRR-GOV-BYPASS-001` | Critical | scripts/validate_repository.py:main | scripts/validate_repository.py:main | README.md#unknown_or_present_bypass_actor | python -m pytest -q tests/test_behavioral_rule_coverage.py tests/test_governance_enforcement.py | block |
| `PRR-HISTORY-NOFABRICATION-001` | High | scripts/validate_repository.py:main | scripts/validate_repository.py:main | README.md#fabricated_pr12_approval | python -m pytest -q tests/test_behavioral_rule_coverage.py tests/test_governance_enforcement.py | block |
