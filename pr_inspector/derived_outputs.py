"""Canonical derived-output facade for v1.11.1.

The private core preserves the mature deterministic renderers. This public
module installs the v1.11.1 semantic prompt boundary before exposing any builder.
"""
from __future__ import annotations

from typing import Any

from . import _derived_outputs_core as _core
from .governance import VerifiedGovernanceEvidence
from .prompt_semantics import render_prompt_contract_block, require_prompt_semantics
from .sequence_enforcement import VerifiedSequenceEnforcement

PROJECTION_NAME = _core.PROJECTION_NAME
PROMPT_NAME = _core.PROMPT_NAME
MANIFEST_NAME = _core.MANIFEST_NAME
PROFILE_COMMANDS_NAME = _core.PROFILE_COMMANDS_NAME
PROFILE_COMMANDS_TEXT = _core.PROFILE_COMMANDS_TEXT

_legacy_render_next_action_prompt = _core.render_next_action_prompt


def _insert_contract(prompt: str, package: dict[str, Any], projection: dict[str, Any]) -> str:
    marker = "[CANONICAL ACTION CONTRACT]"
    if marker in prompt:
        return prompt
    block = "\n".join(render_prompt_contract_block(package, projection))
    trust = "[TRUST BOUNDARY]"
    if trust in prompt:
        return prompt.replace(trust, block + "\n" + trust, 1)
    return block + "\n" + prompt


def render_next_action_prompt(
    pkg: dict[str, Any],
    projection: dict[str, Any] | None = None,
    *,
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> str:
    projection = projection or _core.project_decision(
        pkg,
        governance_evidence=governance_evidence,
        sequence_enforcement=sequence_enforcement,
    )
    prompt = _legacy_render_next_action_prompt(
        pkg,
        projection,
        governance_evidence=governance_evidence,
        sequence_enforcement=sequence_enforcement,
    )
    prompt = _insert_contract(prompt, pkg, projection)
    require_prompt_semantics(pkg, projection, prompt)
    return prompt


_core.render_next_action_prompt = render_next_action_prompt

_sha256 = _core._sha256
_json = _core._json
derive_action_mode = _core.derive_action_mode
structured_action_reasons = _core.structured_action_reasons
render_owner_result = _core.render_owner_result
render_owner_profile_commands = _core.render_owner_profile_commands
build_review_artifacts = _core.build_review_artifacts
write_review_artifacts = _core.write_review_artifacts

__all__ = [
    "MANIFEST_NAME",
    "PROFILE_COMMANDS_NAME",
    "PROFILE_COMMANDS_TEXT",
    "PROJECTION_NAME",
    "PROMPT_NAME",
    "build_review_artifacts",
    "derive_action_mode",
    "render_next_action_prompt",
    "render_owner_profile_commands",
    "render_owner_result",
    "structured_action_reasons",
    "write_review_artifacts",
]
