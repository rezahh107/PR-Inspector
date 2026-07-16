"""Official bundle boundary with complete active v1.11 artifact capture."""

from __future__ import annotations

from . import _official_bundle_impl as _impl
from .derived_outputs import PROFILE_COMMANDS_NAME

_impl._OFFICIAL = set(_impl._OFFICIAL) | {PROFILE_COMMANDS_NAME}
_impl._CAPTURE_CANDIDATES = frozenset({*_impl._OFFICIAL, _impl.PROMPT_NAME})


def _owner_profile_commands_text(self: _impl.VerifiedReviewCompletion) -> str:
    bundle = self._reverify()
    return _impl.utf8_bytes(
        PROFILE_COMMANDS_NAME,
        _impl.required_artifact_bytes(bundle.artifact_bytes, PROFILE_COMMANDS_NAME),
    )


_impl.VerifiedReviewCompletion.owner_profile_commands_text = (
    _owner_profile_commands_text
)


def official_owner_profile_commands(
    value: _impl.VerifiedReviewCompletion,
) -> str:
    if not _impl.is_verified_review_completion(value):
        raise _impl.CompletionError(
            "official profile guidance requires verified completion"
        )
    return value.owner_profile_commands_text()


for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

globals()["official_owner_profile_commands"] = official_owner_profile_commands
__all__ = sorted(name for name in globals() if not name.startswith("__"))
