from pathlib import Path

from pr_inspector.planning_governance import (
    IMPACT_PATH,
    SCOPE_PATH,
    validate_planning_repository,
)

ROOT = Path(__file__).resolve().parents[1]


def test_v1_13_planning_uses_current_registered_artifacts():
    assert SCOPE_PATH.as_posix() == (
        "planning/scopes/PINS-FUNCTIONAL-BOOTSTRAP-001.scope.json"
    )
    assert IMPACT_PATH.as_posix() == (
        "planning/progress/impacts/"
        "PINS-FUNCTIONAL-BOOTSTRAP-001.implementation.json"
    )
    assert validate_planning_repository(ROOT) == []
