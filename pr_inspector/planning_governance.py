from __future__ import annotations

from pathlib import Path

# The planning engine remains the existing fail-closed implementation.  The active
# protocol migration only rebinds its current authoritative artifacts and permits
# the new successor namespace before the implementation modules import the policy.
from . import planning_governance_base as _base

_base.SCOPE_PATH = Path("planning/scopes/PINS-FUNCTIONAL-BOOTSTRAP-001.scope.json")
_base.IMPACT_PATH = Path(
    "planning/progress/impacts/PINS-FUNCTIONAL-BOOTSTRAP-001.implementation.json"
)
_base.PROTOCOL_ALLOWED_EXACT = set(_base.PROTOCOL_ALLOWED_EXACT) | {
    "AGENTS.md",
    "BOOTSTRAP.md",
}
_base.PROTOCOL_ALLOWED_PREFIXES = tuple(
    dict.fromkeys((*_base.PROTOCOL_ALLOWED_PREFIXES, "protocols/v1.13.0/"))
)
_base.PROTOCOL_REQUIRED_EXCLUDED = {
    _base._PINNED_GOVERNANCE_EXCLUSION,
    "protocols/v1.12.0/**",
    "release-locks/v1.12.0.sha256",
}
_base.SCOPE_POLICIES["protocol_authority_migration"] = {
    "allowed_exact": _base.PROTOCOL_ALLOWED_EXACT,
    "allowed_prefixes": _base.PROTOCOL_ALLOWED_PREFIXES,
    "required_excluded": _base.PROTOCOL_REQUIRED_EXCLUDED,
    "required_forbidden": _base.PROTOCOL_REQUIRED_FORBIDDEN,
}

from .planning_governance_base import *  # noqa: E402,F401,F403
from .planning_governance_artifacts import (  # noqa: E402
    expected_snapshot,
    extract_bounded_json,
    validate_impact,
    validate_markdown,
    validate_scope,
)
from .planning_governance_git import parse_git_name_status, validate_git_diff  # noqa: E402
from .planning_governance_registry import validate_registry  # noqa: E402
from .planning_governance_repository import validate_planning_repository  # noqa: E402
