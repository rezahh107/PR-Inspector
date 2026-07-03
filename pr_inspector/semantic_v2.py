from __future__ import annotations
import copy
from typing import Any

from .semantic import validate_semantics as _validate_semantics


def validate_semantics(pkg: dict[str, Any]):
    normalized = copy.deepcopy(pkg)
    capabilities = normalized.get("capabilities", {})
    if "credential_access" in capabilities and "protected_credentials" not in capabilities:
        capabilities["protected_credentials"] = capabilities["credential_access"]
    return _validate_semantics(normalized)
