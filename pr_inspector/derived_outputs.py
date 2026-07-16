"""Active derived-output boundary with v1.11 post-activation closure."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import _derived_outputs_impl as _impl
from .governance import VerifiedGovernanceEvidence
from .sequence_enforcement import VerifiedSequenceEnforcement

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

PROFILE_COMMANDS_NAME = "OWNER_PROFILE_COMMANDS.fa.txt"
PROFILE_COMMANDS_TEXT = (
    "برای بررسی حفاظت‌های Merge، تأییدهای مستقل و کنترل‌های حاکمیتی بنویس: سخت گیرانه\n"
    "برای بررسی حداقلی بنویس: حداقلی و سپس آدرس PR را ارسال کن.\n"
)

_original_manifest_data = _impl._manifest_data
_original_write_review_artifacts = _impl.write_review_artifacts


def _manifest_data(
    pkg: dict[str, Any],
    artifact_bytes: dict[str, bytes],
    projection: dict[str, Any],
    package_bytes: bytes,
) -> dict[str, Any]:
    data = _original_manifest_data(pkg, artifact_bytes, projection, package_bytes)
    data["owner_profile_commands"] = {
        "path": PROFILE_COMMANDS_NAME,
        "sha256": _impl._sha256(artifact_bytes[PROFILE_COMMANDS_NAME]),
        "hash_scope": "final_file_bytes",
    }
    return data


def build_review_artifacts(
    pkg: dict[str, Any],
    review_package_bytes: bytes | None = None,
    *,
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> dict[str, str]:
    package_bytes = (
        review_package_bytes
        if review_package_bytes is not None
        else _impl.canonical_json_bytes(pkg)
    )
    projection = _impl.project_decision(
        pkg,
        governance_evidence=governance_evidence,
        sequence_enforcement=sequence_enforcement,
    )
    artifacts = {
        _impl.PROJECTION_NAME: _impl.projection_json(projection),
        "OWNER_DECISION_CARD.fa.md": _impl.render_owner(pkg, projection),
        "TECHNICAL_HANDOFF.en.md": _impl.render_handoff(pkg, projection),
        "OWNER_RESULT.fa.txt": _impl.render_owner_result(projection),
        PROFILE_COMMANDS_NAME: PROFILE_COMMANDS_TEXT,
    }
    if projection["next_action"]["prompt_required"]:
        artifacts[_impl.PROMPT_NAME] = _impl.render_next_action_prompt(pkg, projection)
    artifact_bytes = {
        name: text.encode("utf-8") for name, text in artifacts.items()
    }
    artifacts[_impl.MANIFEST_NAME] = _impl._manifest_text(
        _manifest_data(pkg, artifact_bytes, projection, package_bytes)
    )
    return artifacts


def write_review_artifacts(
    pkg: dict[str, Any],
    output_dir: Path,
    review_package_bytes: bytes | None = None,
    *,
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> dict[str, str]:
    return _original_write_review_artifacts(
        pkg,
        output_dir,
        review_package_bytes=review_package_bytes,
        governance_evidence=governance_evidence,
        sequence_enforcement=sequence_enforcement,
    )


_impl._manifest_data = _manifest_data
_impl.build_review_artifacts = build_review_artifacts

__all__ = sorted(name for name in globals() if not name.startswith("__"))
