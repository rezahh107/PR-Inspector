"""Active v1.11 runtime entry point.

The former Candidate import path and the active entry point both resolve the
same hardened private implementation boundary.
"""

from __future__ import annotations

from . import _runtime_v1_11_impl as _source

for name in tuple(dir(_source)):
    if not name.startswith("__"):
        globals()[name] = getattr(_source, name)

__all__ = sorted(
    name for name in globals() if not name.startswith("__") and name != "_source"
)
