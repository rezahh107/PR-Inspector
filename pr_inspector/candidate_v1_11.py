"""Compatibility import path for the activated v1.11 runtime.

New code must import :mod:`pr_inspector.runtime_v1_11`. This module remains so
existing integrations and historical tests do not break after activation.
"""

from __future__ import annotations

from . import runtime_v1_11 as _runtime

for _name in dir(_runtime):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_runtime, _name)

__all__ = sorted(name for name in globals() if not name.startswith("__"))
