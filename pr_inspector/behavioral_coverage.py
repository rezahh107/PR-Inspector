from __future__ import annotations

import ast
import json
from functools import lru_cache
from pathlib import Path

from .diagnostics import Diagnostic
from .functional_runtime import load_json_strict, render_rule_view

ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
CONTRACT_PATH = ROOT / f"protocols/{CURRENT_VERSION}/functional-runtime-contract.json"
MATRIX_PATH = ROOT / f"protocols/{CURRENT_VERSION}/policies/BEHAVIORAL_RULE_COVERAGE.md"
GOVERNANCE_MATRIX_PATH = ROOT / (
    f"protocols/{CURRENT_VERSION}/policies/GOVERNANCE_BEHAVIORAL_RULE_COVERAGE.md"
)
MUTATIONS_PATH = ROOT / "fixtures/behavioral-rules/mutation-cases.json"
GOVERNANCE_MUTATIONS_PATH = ROOT / "fixtures/governance/mutation-cases.json"
FOCUSED_COMMAND = (
    "python -m pytest -q tests/test_behavioral_rule_coverage.py "
    "tests/test_governance_enforcement.py"
)
EXTERNAL_COVERAGE_COMMAND = "python -m pytest -q tests/test_coverage_trust_gate.py"
AUTHORITY_COMMAND = (
    "python -m pytest -q tests/test_v1_13_verified_review_authority.py "
    "tests/test_v1_13_evidence_completeness.py"
)


@lru_cache(maxsize=1)
def _rules() -> tuple[dict, ...]:
    return tuple(load_json_strict(CONTRACT_PATH)["functional_rules"])


REQUIRED_RULE_IDS = frozenset(rule["rule_id"] for rule in _rules())


def parse_coverage_matrix(text: str) -> list[dict[str, str]]:
    rows = []
    headers = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if headers is None:
            headers = cells
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def load_mutation_cases(path: Path | None = None) -> dict[str, dict]:
    paths = (
        (MUTATIONS_PATH, GOVERNANCE_MUTATIONS_PATH)
        if path is None
        else (Path(path),)
    )
    out: dict[str, dict] = {}
    for source in paths:
        value = json.loads(source.read_text(encoding="utf-8"))
        for item in value["cases"]:
            case_id = item["case_id"]
            if case_id in out:
                raise ValueError(f"duplicate mutation case: {case_id}")
            out[case_id] = item
    return out


def _reference_symbol(root: Path, reference: str) -> tuple[Path, str | None]:
    normalized = reference.replace("::", ":", 1)
    if ":" not in normalized:
        return root / normalized.split("#", 1)[0], None
    path, symbol = normalized.rsplit(":", 1)
    return root / path, symbol


def _symbol_exists(path: Path, symbol: str | None) -> bool:
    if not path.is_file():
        return False
    if symbol is None or path.suffix != ".py":
        return True
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return False
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.name == symbol
        for node in ast.walk(tree)
    )


def validate_behavioral_coverage(root: Path = ROOT) -> list[Diagnostic]:
    root = Path(root).resolve()
    contract = load_json_strict(
        root / f"protocols/{CURRENT_VERSION}/functional-runtime-contract.json"
    )
    rules = list(contract["functional_rules"])
    diagnostics = []
    ids = [item["rule_id"] for item in rules]
    if len(ids) != len(set(ids)):
        diagnostics.append(
            Diagnostic("PRI-COVERAGE-001", "/functional_rules", "duplicate rule id")
        )

    mutations: dict[str, dict] = {}
    for relative in (
        "fixtures/behavioral-rules/mutation-cases.json",
        "fixtures/governance/mutation-cases.json",
    ):
        for case_id, case in load_mutation_cases(root / relative).items():
            if case_id in mutations:
                diagnostics.append(
                    Diagnostic(
                        "PRI-COVERAGE-002",
                        f"/mutations/{case_id}",
                        "duplicate mutation case",
                    )
                )
            mutations[case_id] = case
    by_rule: dict[str, list[str]] = {}
    for case_id, case in mutations.items():
        by_rule.setdefault(case["rule_id"], []).append(case_id)
    if set(ids) != set(by_rule):
        diagnostics.append(
            Diagnostic(
                "PRI-COVERAGE-002",
                "/functional_rules",
                "rule/mutation set mismatch",
            )
        )

    workflow_text = (root / ".github/workflows/validate-repository.yml").read_text(
        encoding="utf-8"
    )
    negative_refs = []
    for rule in rules:
        rid = rule["rule_id"]
        negative_refs.append(rule["negative_mutation"])
        if len(by_rule.get(rid, [])) != 1:
            diagnostics.append(
                Diagnostic(
                    "PRI-COVERAGE-003",
                    f"/functional_rules/{rid}",
                    "requires one dedicated mutation",
                )
            )
        expected = (
            EXTERNAL_COVERAGE_COMMAND
            if rid.startswith("PRR-COV-")
            else AUTHORITY_COMMAND
            if rid.startswith("PRR-AUTH-")
            else FOCUSED_COMMAND
        )
        if rule["ci_command"] != expected or expected not in workflow_text:
            diagnostics.append(
                Diagnostic(
                    "PRI-COVERAGE-004",
                    f"/functional_rules/{rid}",
                    "invalid or unwired CI command",
                )
            )
        for field in ("validator", "positive_control"):
            path, symbol = _reference_symbol(root, rule[field])
            if not _symbol_exists(path, symbol):
                diagnostics.append(
                    Diagnostic(
                        "PRI-COVERAGE-006",
                        f"/functional_rules/{rid}/{field}",
                        f"unresolved executable reference: {rule[field]}",
                    )
                )
        case_id = rule["negative_mutation"].split("#", 1)[-1]
        case = mutations.get(case_id)
        if case is None or case.get("rule_id") != rid:
            diagnostics.append(
                Diagnostic(
                    "PRI-COVERAGE-003",
                    f"/functional_rules/{rid}/negative_mutation",
                    "negative mutation does not resolve uniquely to this rule",
                )
            )
    if len(negative_refs) != len(set(negative_refs)):
        diagnostics.append(
            Diagnostic(
                "PRI-COVERAGE-003",
                "/functional_rules",
                "negative mutation references must be unique",
            )
        )

    expected_all = render_rule_view(
        rules, title=f"Behavioral Rule Coverage {CURRENT_VERSION}"
    )
    governance_rules = [
        rule
        for rule in rules
        if rule["rule_id"].startswith(("PRR-DOC-", "PRR-GOV-", "PRR-HISTORY-"))
    ]
    expected_governance = render_rule_view(
        governance_rules,
        title=f"Merge Governance Rule Coverage {CURRENT_VERSION}",
    )
    for path, expected in (
        (root / MATRIX_PATH.relative_to(ROOT), expected_all),
        (root / GOVERNANCE_MATRIX_PATH.relative_to(ROOT), expected_governance),
    ):
        try:
            observed = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            diagnostics.append(
                Diagnostic("PRI-COVERAGE-005", f"/{path}", str(exc))
            )
            continue
        if observed != expected:
            diagnostics.append(
                Diagnostic(
                    "PRI-COVERAGE-005",
                    f"/{path.relative_to(root)}",
                    "generated view drift",
                )
            )
    return sorted(set(diagnostics))
