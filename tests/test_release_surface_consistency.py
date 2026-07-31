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
_CURRENT_PROTOCOL_PROSE = re.compile(
    r"\b(?:current(?:\s+active)?\s+protocol|active\s+protocol)\s+[`*]*(v\d+\.\d+\.\d+)[`*]*",
    re.IGNORECASE,
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


def _stale_current_protocol_claims(text: str, current: str) -> list[str]:
    if "HISTORICAL SNAPSHOT" in text and "CURRENT_VERSION" in text:
        return []

    observed = [match.group(1) for match in _ACTIVE_FIELD.finditer(text)]
    observed.extend(match.group(1) for match in _CURRENT_PROTOCOL_PROSE.finditer(text))
    return [version for version in observed if version != current]


def test_agents_current_protocol_derives_through_current_version():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    active = _markdown_section(agents, "Active protocol")
    assert "CURRENT_VERSION" in active
    assert "protocols/<CURRENT_VERSION>/functional-runtime-contract.json" in active
    assert _LITERAL_FUNCTIONAL_CONTRACT.search(active) is None
    assert "independent active-version authority" in active


def test_agents_review_startup_delegates_to_bootstrap_without_manifest_authority():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    startup = _markdown_section(agents, "Review startup")
    assert "BOOTSTRAP.md" in startup
    assert "Read only `runtime_bootstrap_inputs` from `protocol-manifest.yaml`" not in startup
    assert (
        "must not read `protocol-manifest.yaml`, run `validate_repository`, scan release locks, "
        "or perform Inspector self-verification."
    ) in startup


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


@pytest.mark.parametrize(
    "text",
    [
        "Current status: active protocol v1.5.0.",
        "The current active protocol `v1.5.0` applies here.",
        "Current protocol v1.5.0 is authoritative.",
        "active_protocol: v1.5.0",
        "active_pr_inspector_protocol: v1.5.0",
    ],
)
def test_stale_current_protocol_claim_patterns_are_detected(text: str):
    assert _stale_current_protocol_claims(text, "v1.13.1") == ["v1.5.0"]


def test_historical_promotion_wording_is_not_a_current_protocol_claim():
    text = "Promotion history: COR-INTENT-001 was promoted as PRR-INTENT-001 in protocol v1.5.0."
    assert _stale_current_protocol_claims(text, "v1.13.1") == []


def test_explicit_historical_snapshot_with_current_version_redirect_is_allowed():
    text = (
        "HISTORICAL SNAPSHOT — NOT CURRENT STATE\n"
        "Resolve current activation from CURRENT_VERSION.\n"
        "active_protocol: v1.11.1\n"
    )
    assert _stale_current_protocol_claims(text, "v1.13.1") == []


def test_unversioned_docs_have_no_unclassified_stale_current_protocol_claims():
    current = _current_version()
    stale_claims: list[tuple[Path, list[str]]] = []
    for path in sorted((ROOT / "docs").rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        claims = _stale_current_protocol_claims(text, current)
        if claims:
            stale_claims.append((path, claims))
    assert stale_claims == []


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
