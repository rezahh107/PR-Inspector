from __future__ import annotations
import copy
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from pr_inspector.planning_authority import PlanningAuthorityError, resolve_current_planning_artifacts, resolve_planning_authority
from pr_inspector.planning_governance import validate_planning_repository
from pr_inspector.planning_governance_base import REGISTRY_PATH, SCHEMAS, load_json_strict
from pr_inspector.planning_governance_repository import _validate_registered_artifacts
ROOT = Path(__file__).resolve().parents[1]

def _run_isolated(code: str, *, cwd: Path=ROOT) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env['PYTHONPATH'] = str(cwd)
    return subprocess.run([sys.executable, '-c', code], cwd=cwd, env=env, text=True, capture_output=True, check=False)

def _direct_validation_program(imports: tuple[str, ...]) -> str:
    prefix = '\n'.join((f'import {name}' for name in imports))
    return prefix + '\nfrom pathlib import Path\nfrom pr_inspector.planning_governance_base import REGISTRY_PATH, SCHEMAS, load_json_strict\nfrom pr_inspector.planning_governance_repository import _validate_registered_artifacts\nroot = Path(".")\nregistry = load_json_strict(root / REGISTRY_PATH)\nschemas = {name: load_json_strict(root / path) for name, path in SCHEMAS.items()}\ndiagnostics, _, _ = _validate_registered_artifacts(root, registry, schemas)\nfor item in diagnostics:\n    print(item.line())\nraise SystemExit(bool(diagnostics))\n'

def test_fresh_direct_repository_import_validates_current_artifacts():
    result = _run_isolated(_direct_validation_program(('pr_inspector.planning_governance_base', 'pr_inspector.planning_governance_repository')))
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ''

@pytest.mark.parametrize('imports', [('pr_inspector.planning_governance',), ('pr_inspector.planning_governance_base', 'pr_inspector.planning_governance'), ('pr_inspector.planning_governance_repository', 'pr_inspector.planning_governance'), ('pr_inspector.planning_governance', 'pr_inspector.planning_governance_base', 'pr_inspector.planning_governance_repository'), ('pr_inspector.planning_governance_repository', 'pr_inspector.planning_governance_base', 'pr_inspector.planning_governance', 'pr_inspector.planning_governance')])
def test_import_permutations_have_identical_empty_diagnostics(imports):
    result = _run_isolated(_direct_validation_program(imports))
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ''

def test_public_facade_does_not_mutate_base_policy_state():
    code = '\nimport json\nimport pr_inspector.planning_governance_base as base\nbefore = {\n    "scope_path": base.SCOPE_PATH.as_posix(),\n    "impact_path": base.IMPACT_PATH.as_posix(),\n    "protocol_prefixes": list(base.PROTOCOL_ALLOWED_PREFIXES),\n    "protocol_excluded": sorted(base.PROTOCOL_REQUIRED_EXCLUDED),\n}\nimport pr_inspector.planning_governance\nafter = {\n    "scope_path": base.SCOPE_PATH.as_posix(),\n    "impact_path": base.IMPACT_PATH.as_posix(),\n    "protocol_prefixes": list(base.PROTOCOL_ALLOWED_PREFIXES),\n    "protocol_excluded": sorted(base.PROTOCOL_REQUIRED_EXCLUDED),\n}\nassert before == after\nprint(json.dumps(after, sort_keys=True))\n'
    result = _run_isolated(code)
    assert result.returncode == 0, result.stdout + result.stderr
    observed = json.loads(result.stdout)
    assert 'protocols/v1.13.0/' not in observed['protocol_prefixes']

def test_registry_owns_current_scope_and_impact_identity():
    current = resolve_current_planning_artifacts(ROOT)
    assert current.work_package_id == 'PINS-FUNCTIONAL-BOOTSTRAP-001-WP01'
    assert current.task_id == 'PINS-FUNCTIONAL-BOOTSTRAP-001'
    assert current.scope_ref == 'planning/scopes/PINS-FUNCTIONAL-BOOTSTRAP-001.scope.json'
    assert current.impact_refs == ('planning/progress/impacts/PINS-FUNCTIONAL-BOOTSTRAP-001.implementation.json',)

def test_active_v1_13_policy_is_declarative_and_immutable():
    authority = resolve_planning_authority(ROOT)
    assert authority.active_version == 'v1.13.0'
    protocol = authority.protocol_policies['v1.13.0']
    assert 'protocols/v1.13.0/' in protocol.allowed_prefixes
    assert 'protocols/v1.12.0/**' in protocol.required_excluded
    with pytest.raises(TypeError):
        authority.protocol_policies['other'] = protocol

def test_unsupported_active_version_fails_closed(tmp_path):
    (tmp_path / 'CURRENT_VERSION').write_text('v9.9.9\n', encoding='utf-8')
    with pytest.raises(PlanningAuthorityError, match='PINS-PLANNING-AUTHORITY-002'):
        resolve_planning_authority(tmp_path)

@pytest.mark.parametrize('mutation', ['missing_id', 'ambiguous_flag', 'mismatched_flag', 'missing_refs'])
def test_current_package_policy_drift_fails_closed(tmp_path, mutation):
    (tmp_path / 'planning/tasks').mkdir(parents=True)
    (tmp_path / 'CURRENT_VERSION').write_text('v1.13.0\n', encoding='utf-8')
    registry = load_json_strict(ROOT / REGISTRY_PATH)
    candidate = copy.deepcopy(registry)
    if mutation == 'missing_id':
        candidate['current_work_package_id'] = 'UNKNOWN-WP'
    elif mutation == 'ambiguous_flag':
        candidate['work_packages'][0]['current'] = True
    elif mutation == 'mismatched_flag':
        candidate['current_work_package_id'] = candidate['work_packages'][0]['work_package_id']
    else:
        current = next((item for item in candidate['work_packages'] if item['current'] is True))
        current['impact_refs'] = []
    (tmp_path / REGISTRY_PATH).write_text(json.dumps(candidate, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    with pytest.raises(PlanningAuthorityError, match='PINS-PLANNING-BINDING-'):
        resolve_current_planning_artifacts(tmp_path)

def test_direct_and_public_validation_are_semantically_identical():
    registry = load_json_strict(ROOT / REGISTRY_PATH)
    schemas = {name: load_json_strict(ROOT / path) for name, path in SCHEMAS.items()}
    direct, _, _ = _validate_registered_artifacts(ROOT, registry, schemas)
    public = validate_planning_repository(ROOT)
    assert direct == []
    assert public == []

def test_historical_v1_12_scope_uses_historical_policy_but_current_drift_fails():
    from pr_inspector.planning_governance_artifacts import validate_scope
    registry = load_json_strict(ROOT / REGISTRY_PATH)
    schema = load_json_strict(ROOT / SCHEMAS['scope'])
    historical_ref = next((item['scope_ref'] for item in registry['work_packages'] if item['work_package_id'] == 'PINS-VERIFIED-REVIEW-001-WP01'))
    historical = load_json_strict(ROOT / historical_ref)
    assert validate_scope(historical, schema, registry, historical_ref, root=ROOT) == []
    current = load_json_strict(ROOT / 'planning/scopes/PINS-FUNCTIONAL-BOOTSTRAP-001.scope.json')
    mutated = copy.deepcopy(current)
    mutated['committed_paths'] = [*mutated['committed_paths'], 'protocols/v1.12.0/PR_REVIEW_CONTRACT.md']
    diagnostics = validate_scope(mutated, schema, registry, 'planning/scopes/PINS-FUNCTIONAL-BOOTSTRAP-001.scope.json', root=ROOT)
    assert any((item.code == 'PINS-SCOPE-FORBIDDEN-PATH' for item in diagnostics))
