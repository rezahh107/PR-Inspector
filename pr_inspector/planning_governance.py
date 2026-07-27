from __future__ import annotations

from pathlib import Path

from .planning_authority import (
    ACTIVE_VERSION,
    CurrentPlanningArtifacts,
    PlanningAuthority,
    PlanningAuthorityError,
    ScopePolicy,
    resolve_current_planning_artifacts,
    resolve_planning_authority,
)
from .planning_governance_base import *  # noqa: F401,F403
from .planning_governance_artifacts import (
    expected_snapshot,
    extract_bounded_json,
    validate_impact,
    validate_markdown,
    validate_scope,
)
from .planning_governance_git import (
    parse_git_name_status,
    validate_git_diff,
)
from .planning_governance_registry import validate_registry
from .planning_governance_repository import validate_planning_repository

# Preserve the established facade API while deriving current artifact identity
# declaratively from the registered current Work Package. These facade-local
# bindings do not mutate planning_governance_base or create import-order state.
_CURRENT_ARTIFACTS = resolve_current_planning_artifacts(
    Path(__file__).resolve().parents[1]
)
SCOPE_PATH = Path(_CURRENT_ARTIFACTS.scope_ref)
IMPACT_PATH = Path(_CURRENT_ARTIFACTS.impact_refs[-1])
