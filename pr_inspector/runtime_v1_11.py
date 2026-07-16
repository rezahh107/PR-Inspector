"""Active v1.11 runtime boundary.

The implementation body is retained in ``_runtime_v1_11_impl`` so the former
Candidate import path can remain a compatibility shim without remaining the
active entry point. Runtime hardening belongs here.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import _runtime_v1_11_impl as _impl


def _validate_annotation_metadata(ann: Mapping[str, Any]) -> None:
    annotation_id = ann.get("id")
    if annotation_id is not None and (
        not isinstance(annotation_id, int)
        or isinstance(annotation_id, bool)
        or annotation_id <= 0
    ):
        raise ValueError("check annotation id is malformed")

    path = ann.get("path")
    if path is not None and (not isinstance(path, str) or not path):
        raise ValueError("check annotation path is malformed")

    start_line = ann.get("start_line")
    end_line = ann.get("end_line")
    for name, value in (("start_line", start_line), ("end_line", end_line)):
        if value is not None and (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value <= 0
        ):
            raise ValueError(f"check annotation {name} is malformed")
    if start_line is not None and end_line is not None and end_line < start_line:
        raise ValueError("check annotation line range is malformed")

    level = ann.get("annotation_level")
    if not isinstance(level, str) or not level:
        raise ValueError("check annotation level is malformed")


# Functions defined in the implementation resolve globals in that module.
# Replace the validator before exporting the runtime surface.
_impl._validate_annotation_metadata = _validate_annotation_metadata

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals().setdefault(_name, getattr(_impl, _name))

globals()["_validate_annotation_metadata"] = _validate_annotation_metadata
__all__ = sorted(name for name in globals() if not name.startswith("__"))
