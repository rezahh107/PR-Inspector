"""Retrieval-only startup for the active PR Inspector protocol.

Repository validation belongs to maintenance tooling.  Review startup deliberately
uses only a repository-content reader so it also works with connector-backed refs.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_VERSION = "v1.13.1"
ENTRYPOINT = "BOOTSTRAP.md"
CONTRACT_PATH = "protocols/v1.13.1/functional-runtime-contract.json"
INTAKE_PATH = "protocols/v1.13.1/prompts/INTAKE_RESPONSE.fa.md"
RUNTIME_BOOTSTRAP_INPUTS = ("CURRENT_VERSION", CONTRACT_PATH, INTAKE_PATH)


class FunctionalBootstrapError(RuntimeError):
    pass


@dataclass(frozen=True)
class StartupResult:
    protocol_version: str
    contract: dict[str, Any]
    intake_response: str
    reads: tuple[str, ...]


def connector_startup(read_content: Callable[[str], str]) -> StartupResult:
    """Load the minimal active inputs from one connector-selected ref.

    ``read_content`` is the sole I/O boundary.  No filesystem discovery,
    validation, hashing, Git, network attestation, or process execution occurs.
    """
    reads: list[str] = []

    def read(path: str) -> str:
        reads.append(path)
        return read_content(path)

    version = read("CURRENT_VERSION").strip()
    contract_path = f"protocols/{version}/functional-runtime-contract.json"
    intake_path = f"protocols/{version}/prompts/INTAKE_RESPONSE.fa.md"
    contract = json.loads(read(contract_path))
    intake = read(intake_path)
    return StartupResult(version, contract, intake, tuple(reads))


def resolve_rules(contract: dict[str, Any]) -> tuple[dict[str, str], ...]:
    rules = contract.get("functional_rules", [])
    if not rules or isinstance(rules[0], dict):
        return tuple(rules)
    defaults = contract["rule_defaults"]
    return tuple({"rule_id": rid, "risk": risk, "validator": defaults["validator"],
                  "positive_control": defaults["positive_control"],
                  "negative_mutation": defaults["negative_prefix"] + mutation,
                  "ci_command": defaults["ci_commands"][key],
                  "recovery_action": defaults["recovery_action"]}
                 for rid, risk, mutation, key in rules)


def load_json_strict(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if path.name == "functional-runtime-contract.json":
        value = {**value, "functional_rules": list(resolve_rules(value))}
    return value


def render_rule_view(rules: Iterable[dict[str, str]], *, title: str) -> str:
    columns = ("rule_id", "risk", "validator", "positive_control", "negative_mutation", "CI_step", "recovery_action")
    lines = [f"# {title}", "", "Status: generated, non-authoritative view of `../functional-runtime-contract.json`.", "", "| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for rule in rules:
        values = (rule["rule_id"], rule["risk"], rule["validator"], rule["positive_control"], rule["negative_mutation"], rule["ci_command"], rule["recovery_action"])
        lines.append("| " + " | ".join(map(str, values)) + " |")
    return "\n".join(lines) + "\n"


def install_active_protocol_adapters() -> None:
    from . import decision_projection as projection
    from . import verified_review as legacy
    from .functional_review import assemble_review_package
    original = projection.project_decision

    def project(package: Any, governance_evidence: Any = None, sequence_enforcement: Any = None) -> Any:
        result = original(package, governance_evidence, sequence_enforcement)
        version = package.get("protocol_version") if isinstance(package, dict) else None
        if version in {"v1.12.0", "v1.13.0", ACTIVE_VERSION}:
            result["protocol_version"] = version
            projection.validate_projection_invariants(result)
        return result
    projection.project_decision = project
    for name, module in tuple(sys.modules.items()):
        if name.startswith("pr_inspector.") and module is not None and getattr(module, "project_decision", None) is original:
            setattr(module, "project_decision", project)

    legacy_method = legacy.ProtocolContext.from_verified_repository.__func__

    def from_repo(cls: Any, repository_directory: Path = ROOT, **kwargs: Any) -> Any:
        root = Path(repository_directory)
        try:
            active = (root / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
        except OSError:
            active = ""
        if active != ACTIVE_VERSION:
            return legacy_method(cls, root, **kwargs)
        result = connector_startup(lambda path: (root / path).read_text(encoding="utf-8"))
        protocol = result.contract["protocol"]
        return cls(result.protocol_version, protocol["inspector_repository"], protocol["inspector_repository_id"], "0" * 40, tuple(result.contract["required_check_names"]))
    legacy.ProtocolContext.from_verified_repository = classmethod(from_repo)
    legacy.ProtocolContext.from_repository = classmethod(from_repo)
    legacy.ASSESSMENT_SCHEMA = ROOT / "protocols/v1.13.1/schemas/review-assessment.schema.json"
    legacy.assemble_review_package = assemble_review_package
