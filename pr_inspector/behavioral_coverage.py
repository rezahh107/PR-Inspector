from __future__ import annotations

import json
from pathlib import Path

import yaml

from .diagnostics import Diagnostic

ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
MATRIX_PATH = ROOT / f"protocols/{CURRENT_VERSION}/policies/BEHAVIORAL_RULE_COVERAGE.md"
MUTATION_PATH = ROOT / "fixtures/behavioral-rules/mutation-cases.json"
WORKFLOW_PATH = ROOT / ".github/workflows/validate-repository.yml"
FOCUSED_COMMAND = "python -m pytest -q tests/test_behavioral_rule_coverage.py"
EXTERNAL_COVERAGE_COMMAND = "python -m pytest -q tests/test_coverage_trust_gate.py"

COLUMNS = (
    "rule_id",
    "concept",
    "risk",
    "prose_source",
    "schema_carrier",
    "validator_rule",
    "valid_fixture",
    "invalid_fixture",
    "CI_step",
    "downstream_contract",
    "session_scope",
    "recovery_action",
    "status",
)

REQUIRED_RULE_IDS = {
    "PRR-OWNER-MERGE-001",
    "PRR-OWNER-TWO-LINE-001",
    "PRR-OWNER-PROMPT-ATOMIC-001",
    "PRR-DECISION-SOURCE-001",
    "PRR-REASON-REGISTRY-001",
    "PRR-VERIFY-NOMODIFY-001",
    "PRR-STALE-NOREPAIR-001",
    "PRR-RECIPIENT-BOUNDARY-001",
    "PRR-MANIFEST-BYTES-001",
    "PRR-CI-IDENTITY-001",
    "PRR-EXACT-HEAD-CLAIM-001",
    "PRR-PENDING-REREVIEW-001",
    "PRR-PROMPT-INJECTION-001",
    "PRR-COV-AUTHORITY-001",
    "PRR-COV-WORKFLOW-001",
    "PRR-COV-SUPPLY-001",
    "PRR-COV-PLANNING-001",
    "PRR-COV-INTEGRATION-001",
    "PRR-GOV-PERSONAL-PROFILE-001",
    "PRR-GOV-PROFILE-TRIGGER-001",
    "PRR-GOV-CLAIM-SEPARATION-001",
    "PRR-GOV-PROJECTION-AUTHORITY-001",
}

STATUS_RANK = {
    "prose_only": 0,
    "schema_backed": 1,
    "validator_backed": 2,
    "fixture_tested": 3,
    "advisory_ci_observed": 3,
    "ci_enforced": 4,
    "sequence_ci_enforced": 5,
    "runtime_monitor_enforced": 6,
    "os_harness_enforced": 7,
    "downstream_contract_enforced": 8,
}


class CoverageParseError(ValueError):
    pass


def _strip_cell(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        return value[1:-1]
    return value


def parse_coverage_matrix(text: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    expected_header = "| " + " | ".join(COLUMNS) + " |"
    try:
        header_index = lines.index(expected_header)
    except ValueError as exc:
        raise CoverageParseError("coverage matrix header is missing or has the wrong columns") from exc

    if header_index + 1 >= len(lines):
        raise CoverageParseError("coverage matrix separator is missing")
    separator = lines[header_index + 1]
    if not separator.startswith("|---"):
        raise CoverageParseError("coverage matrix separator is invalid")

    rows: list[dict[str, str]] = []
    for line in lines[header_index + 2 :]:
        if not line.startswith("|"):
            break
        cells = [_strip_cell(cell) for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(COLUMNS):
            raise CoverageParseError(
                f"coverage row has {len(cells)} cells; expected {len(COLUMNS)}"
            )
        rows.append(dict(zip(COLUMNS, cells, strict=True)))
    if not rows:
        raise CoverageParseError("coverage matrix has no rule rows")
    return rows


def load_mutation_cases(path: Path = MUTATION_PATH) -> dict[str, dict[str, str]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CoverageParseError(f"cannot load mutation fixture: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise CoverageParseError("mutation fixture schema_version must be 1")
    cases = raw.get("cases")
    if not isinstance(cases, list):
        raise CoverageParseError("mutation fixture cases must be an array")
    out: dict[str, dict[str, str]] = {}
    for index, item in enumerate(cases):
        if not isinstance(item, dict):
            raise CoverageParseError(f"mutation case {index} is not an object")
        case_id = item.get("case_id")
        rule_id = item.get("rule_id")
        if not isinstance(case_id, str) or not case_id:
            raise CoverageParseError(f"mutation case {index} has no case_id")
        if not isinstance(rule_id, str) or not rule_id:
            raise CoverageParseError(f"mutation case {case_id} has no rule_id")
        if case_id in out:
            raise CoverageParseError(f"duplicate mutation case_id {case_id}")
        out[case_id] = item
    return out


def _required_minimum(row: dict[str, str]) -> tuple[str, int]:
    if row["risk"] == "Critical" and row["session_scope"] == "cross_turn":
        return "sequence_ci_enforced", STATUS_RANK["sequence_ci_enforced"]
    if row["risk"] == "Critical":
        return "ci_enforced", STATUS_RANK["ci_enforced"]
    return "validator_backed", STATUS_RANK["validator_backed"]


def validate_behavioral_coverage(root: Path = ROOT) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    matrix_path = root / MATRIX_PATH.relative_to(ROOT)
    mutation_path = root / MUTATION_PATH.relative_to(ROOT)
    workflow_path = root / WORKFLOW_PATH.relative_to(ROOT)

    try:
        rows = parse_coverage_matrix(matrix_path.read_text(encoding="utf-8"))
    except (OSError, CoverageParseError) as exc:
        return [Diagnostic("PRI-BRC-001", f"/{matrix_path.relative_to(root)}", str(exc))]

    try:
        mutations = load_mutation_cases(mutation_path)
    except CoverageParseError as exc:
        diagnostics.append(Diagnostic("PRI-BRC-002", f"/{mutation_path.relative_to(root)}", str(exc)))
        mutations = {}

    seen: set[str] = set()
    for index, row in enumerate(rows):
        path = f"/{matrix_path.relative_to(root)}#row-{index + 1}"
        rule_id = row["rule_id"]
        if rule_id in seen:
            diagnostics.append(Diagnostic("PRI-BRC-003", path, f"duplicate rule_id {rule_id}"))
        seen.add(rule_id)

        if row["risk"] not in {"Critical", "High"}:
            diagnostics.append(Diagnostic("PRI-BRC-004", path, "risk must be Critical or High"))
        if row["session_scope"] not in {"per_artifact", "cross_turn"}:
            diagnostics.append(Diagnostic("PRI-BRC-005", path, "session_scope must be per_artifact or cross_turn"))
        if row["recovery_action"] not in {"block", "repair_request", "rollback", "flag_for_review"}:
            diagnostics.append(Diagnostic("PRI-BRC-006", path, "invalid recovery_action"))
        status = row["status"]
        if status not in STATUS_RANK:
            diagnostics.append(Diagnostic("PRI-BRC-007", path, f"unknown enforcement status {status}"))
        else:
            minimum_name, minimum_rank = _required_minimum(row)
            if STATUS_RANK[status] < minimum_rank:
                diagnostics.append(
                    Diagnostic(
                        "PRI-BRC-008",
                        path,
                        f"{rule_id} requires at least {minimum_name}; observed {status}",
                    )
                )

        invalid = row["invalid_fixture"]
        prefix = "fixtures/behavioral-rules/mutation-cases.json#"
        if not invalid.startswith(prefix):
            diagnostics.append(Diagnostic("PRI-BRC-009", path, "invalid_fixture must reference a dedicated mutation case"))
        else:
            case_id = invalid.removeprefix(prefix)
            case = mutations.get(case_id)
            if case is None:
                diagnostics.append(Diagnostic("PRI-BRC-009", path, f"unknown mutation case {case_id}"))
            elif case.get("rule_id") != rule_id:
                diagnostics.append(Diagnostic("PRI-BRC-009", path, f"mutation case {case_id} belongs to {case.get('rule_id')}"))

        expected_command = (
            EXTERNAL_COVERAGE_COMMAND
            if rule_id.startswith("PRR-COV-")
            else FOCUSED_COMMAND
        )
        if row["CI_step"] != expected_command:
            diagnostics.append(Diagnostic("PRI-BRC-010", path, f"CI_step must be exactly {expected_command}"))

        for field in ("prose_source", "schema_carrier", "validator_rule", "valid_fixture"):
            if row[field] in {"", "None"}:
                diagnostics.append(Diagnostic("PRI-BRC-011", path, f"{field} is required for active Critical/High rules"))

    missing = sorted(REQUIRED_RULE_IDS - seen)
    if missing:
        diagnostics.append(
            Diagnostic(
                "PRI-BRC-012",
                f"/{matrix_path.relative_to(root)}",
                "missing required rules: " + ", ".join(missing),
            )
        )
    extra_mutation_rules = sorted({case["rule_id"] for case in mutations.values()} - seen)
    if extra_mutation_rules:
        diagnostics.append(
            Diagnostic(
                "PRI-BRC-013",
                f"/{mutation_path.relative_to(root)}",
                "mutation fixture references untracked rules: " + ", ".join(extra_mutation_rules),
            )
        )

    try:
        workflow = workflow_path.read_text(encoding="utf-8")
        yaml.safe_load(workflow)
    except (OSError, yaml.YAMLError) as exc:
        diagnostics.append(Diagnostic("PRI-BRC-014", f"/{workflow_path.relative_to(root)}", str(exc)))
    else:
        for command in (FOCUSED_COMMAND, EXTERNAL_COVERAGE_COMMAND):
            if command not in workflow:
                diagnostics.append(
                    Diagnostic(
                        "PRI-BRC-015",
                        f"/{workflow_path.relative_to(root)}",
                        f"focused command is not wired into CI: {command}",
                    )
                )

    return sorted(set(diagnostics))
