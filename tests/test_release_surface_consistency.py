from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from pr_inspector.functional_review import assemble_review_package
from pr_inspector.verified_review import ReviewAssemblyError

ROOT = Path(__file__).resolve().parents[1]
_VERSION = re.compile(r"^v\d+\.\d+\.\d+$")
_ACTIVE_FIELD = re.compile(
    r"^\s*(?:active_protocol|active_pr_inspector_protocol):\s*(v\d+\.\d+\.\d+)\s*$",
    re.MULTILINE,
)
_LITERAL_FUNCTIONAL_CONTRACT = re.compile(
    r"protocols/v\d+\.\d+\.\d+/functional-runtime-contract\.json"
)


def _current_version() -> str:
    value = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
    assert _VERSION.fullmatch(value)
    return value


def _markdown_section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    assert marker in text
    section = text.split(marker, 1)[1]
    return section.split("\n## ", 1)[0]


def test_agents_current_protocol_derives_through_current_version():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    active = _markdown_section(agents, "Active protocol")
    assert "CURRENT_VERSION" in active
    assert "protocols/<CURRENT_VERSION>/functional-runtime-contract.json" in active
    assert _LITERAL_FUNCTIONAL_CONTRACT.search(active) is None
    assert "independent active-version authority" in active


def test_changelog_contains_current_release_heading():
    current = _current_version()
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(rf"^##\s+{re.escape(current)}\s*$", changelog, re.MULTILINE)


def test_readme_current_activation_and_lifecycle_are_truthful():
    current = _current_version()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"## Active protocol\n\n`{current}`" in readme
    assert f"[`protocols/{current}/`](protocols/{current}/)" in readme
    assert "`CURRENT_VERSION` is the authoritative pointer for current activation" in readme
    assert "this branch is a candidate until merged" not in readme.lower()
    assert "Pull Request branches remain candidate state until merged" in readme


def test_stale_active_protocol_fields_in_unversioned_docs_are_marked_historical():
    current = _current_version()
    stale_claims: list[tuple[Path, str]] = []
    for path in sorted((ROOT / "docs").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for match in _ACTIVE_FIELD.finditer(text):
            value = match.group(1)
            if value != current:
                stale_claims.append((path, value))
                assert "HISTORICAL SNAPSHOT" in text, path
                assert "CURRENT_VERSION" in text, path
    assert stale_claims


def test_known_historical_v1_11_1_snapshot_values_are_preserved():
    aigov = (ROOT / "docs/AIGOV_ADOPTION_STATUS.md").read_text(encoding="utf-8")
    canonical = (ROOT / "docs/CANONICAL_OUTPUT_ENFORCEMENT.md").read_text(encoding="utf-8")
    assert "active_pr_inspector_protocol: v1.11.1" in aigov
    assert "active_protocol: v1.11.1" in canonical


def test_unsupported_protocol_diagnostic_reports_actual_supplied_version():
    unsupported = "v9.9.9"
    with pytest.raises(ReviewAssemblyError) as exc_info:
        assemble_review_package(
            None,
            None,
            SimpleNamespace(protocol_version=unsupported),
        )
    message = str(exc_info.value)
    assert message == f"official assembler does not support protocol version {unsupported}"
    assert "active protocol v1.13.0" not in message
