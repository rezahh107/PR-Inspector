"""PR Inspector deterministic validators and renderers."""

from __future__ import annotations

from typing import Any

__version__ = "1.13.0"

from .functional_runtime import (
    ACTIVE_VERSION,
    CONTRACT_PATH,
    ROOT,
    install_active_protocol_adapters,
    load_json_strict,
)

install_active_protocol_adapters()

# Compatibility-only adapter for explicit historical provenance verification.
# Active v1.13 identity is derived from the local functional contract; no
# active trust file or network operation is introduced into Runtime bootstrap.
from . import review_provenance as _provenance

_historical_trust_policy = _provenance.trust_policy


def _contract_derived_trust_policy(
    protocol_version: str | None = None,
) -> dict[str, Any]:
    version = protocol_version or ACTIVE_VERSION
    if version != ACTIVE_VERSION:
        return _historical_trust_policy(version)

    contract = load_json_strict(ROOT / CONTRACT_PATH)
    protocol = contract.get("protocol")
    if not isinstance(protocol, dict):
        raise _provenance.ProvenanceError(
            "active functional contract protocol identity is unavailable"
        )
    repository = protocol.get("inspector_repository")
    repository_id = protocol.get("inspector_repository_id")
    if not isinstance(repository, str) or not isinstance(repository_id, int):
        raise _provenance.ProvenanceError(
            "active functional contract Inspector identity is invalid"
        )
    return {
        "schema_version": 1,
        "protocol_version": ACTIVE_VERSION,
        "inspector_repository": repository,
        "inspector_repository_id": repository_id,
        "github_api_version": "2026-03-10",
        "commit_evidence_source": "github_rest_api_https",
        "required_review_artifacts": sorted(
            _provenance._EXPECTED_ARTIFACTS
        ),
        "required_review_hashes": sorted(
            _provenance._EXPECTED_HASH_FIELDS
        ),
    }


_provenance.trust_policy = _contract_derived_trust_policy
