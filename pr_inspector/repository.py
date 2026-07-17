from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from .behavioral_coverage import validate_behavioral_coverage
from .decision_projection import ProjectionError, reason_registry_entries
from .diagnostics import Diagnostic

ROOT = Path(__file__).resolve().parents[1]
QUALITY_FOUNDATION = "docs/QUALITY_ATTRIBUTE_MODEL.md"
QUALITY_REQUIRED_PHRASES = {
    "Status: repository-required planning infrastructure.": (
        "must be marked as repository-required planning infrastructure"
    ),
    "It is not part of the active protocol `load_order`.": (
        "must state it is outside the active protocol load_order"
    ),
    "It defines no active review rule.": (
        "must state it defines no active review rule"
    ),
    (
        "Its seed rules are planning-only until promoted through a new "
        "protocol snapshot, schema/validator/fixture, and release lock."
    ): "must state seed rules are planning-only until properly promoted",
    (
        "Repository validation keeps this document guarded and outside "
        "the active protocol `load_order`."
    ): "must state repository validation guards the protocol boundary",
    "If this document conflicts with the active protocol, the active protocol wins.": (
        "must state active-protocol precedence"
    ),
    "COR-INTENT-001": "must include the intent-fit seed rule",
    "PRR-INTENT-001": (
        "must record that intent-fit has a promoted active protocol rule"
    ),
    "COR-REG-001": "must include the regression-risk seed rule",
    "COR-STATE-001": "must include the consistency seed rule",
    "COR-TEST-001": "must include the validation-adequacy seed rule",
    "COR-RESEARCH-001": (
        "must include the research-backed-claims seed rule"
    ),
    (
        "Validation does not make this document part of the active "
        "protocol and does not make the seed rules active review rules."
    ): (
        "must distinguish repository validation from active review-rule "
        "enforcement"
    ),
    "No active protocol behavior is changed": (
        "must not claim the planning document itself changes active "
        "protocol enforcement"
    ),
}

CANDIDATE_ALLOWED_EXPORTS = {
    "CandidateOutputMigrationError",
    "MINIMAL",
    "MinimalRefreshResult",
    "PROTOCOL_VERSION",
    "STRICT",
    "VerifiedLivePrHead",
    "VerifiedMinimalReviewReference",
    "VerifiedTargetIdentity",
    "bytes_sha256",
    "candidate_owner_delivery_stdout",
    "canonical_sha256",
    "minimal_reference_from_official_completion",
    "orchestrate_strict_after_minimal",
    "parse_intake",
    "render_owner_profile_commands",
    "verify_base_review_reference",
    "verify_live_pr_head_response",
    "verify_target_identity_response",
}

CANDIDATE_FAIL_CLOSED_FUNCTIONS = {
    "project_decision",
    "render_candidate_owner_result",
    "render_candidate_owner_card",
    "render_candidate_technical_handoff",
    "render_candidate_next_action_prompt",
    "build_candidate_review_artifacts",
    "verify_candidate_review_artifact_bytes",
    "verify_minimal_review_artifact_bytes",
    "build_candidate_owner_delivery_artifacts",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_lock(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split("  ", 1)
        out[rel] = digest
    return out


def validate_quality_foundation(
    root: Path, load_order: list[str]
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    path = root / QUALITY_FOUNDATION
    if not path.is_file():
        return [
            Diagnostic(
                "PRI-QUAL-001",
                f"/{QUALITY_FOUNDATION}",
                (
                    "repository-required quality foundation planning "
                    "infrastructure is missing"
                ),
            )
        ]
    if QUALITY_FOUNDATION in load_order:
        diagnostics.append(
            Diagnostic(
                "PRI-QUAL-002",
                f"/{QUALITY_FOUNDATION}",
                (
                    "repository-required planning infrastructure must not "
                    "be listed in active protocol load_order"
                ),
            )
        )
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [
            Diagnostic(
                "PRI-QUAL-003",
                f"/{QUALITY_FOUNDATION}",
                str(exc),
            )
        ]
    for phrase, message in QUALITY_REQUIRED_PHRASES.items():
        if phrase not in text:
            diagnostics.append(
                Diagnostic(
                    "PRI-QUAL-004",
                    f"/{QUALITY_FOUNDATION}",
                    message,
                )
            )
    return diagnostics


def validate_active_release_lock(
    root: Path,
    current: str,
    manifest: dict,
    load_order: list[str],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    expected_rel = f"release-locks/{current}.sha256"
    declared_rel = manifest.get("release_lock")
    if declared_rel != expected_rel:
        diagnostics.append(
            Diagnostic(
                "PRI-LOCK-002",
                "/protocol-manifest.yaml/release_lock",
                f"active release lock must be {expected_rel}",
            )
        )
        return diagnostics

    lock_path = root / expected_rel
    if not lock_path.is_file():
        diagnostics.append(
            Diagnostic(
                "PRI-LOCK-002",
                f"/{expected_rel}",
                "active release lock is missing",
            )
        )
        return diagnostics

    try:
        locked_paths = set(parse_lock(lock_path))
    except (OSError, ValueError) as exc:
        diagnostics.append(
            Diagnostic(
                "PRI-LOCK-002",
                f"/{expected_rel}",
                str(exc),
            )
        )
        return diagnostics

    canonical_paths = set(load_order)
    if locked_paths != canonical_paths:
        missing = sorted(canonical_paths - locked_paths)
        extra = sorted(locked_paths - canonical_paths)
        details: list[str] = []
        if missing:
            details.append(
                f"missing canonical paths: {', '.join(missing)}"
            )
        if extra:
            details.append(
                f"unexpected locked paths: {', '.join(extra)}"
            )
        diagnostics.append(
            Diagnostic(
                "PRI-LOCK-003",
                f"/{expected_rel}",
                "; ".join(details),
            )
        )
    return diagnostics


def validate_active_schemas(
    root: Path, load_order: list[str]
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    schema_paths = [
        rel for rel in load_order if str(rel).endswith(".schema.json")
    ]
    if not schema_paths:
        return [
            Diagnostic(
                "PRI-REPO-SCHEMA-002",
                "/protocol-manifest.yaml/load_order",
                "active load_order contains no JSON Schema",
            )
        ]
    for rel in schema_paths:
        path = root / rel
        if not path.is_file():
            continue
        try:
            Draft202012Validator.check_schema(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except Exception as exc:
            diagnostics.append(
                Diagnostic(
                    "PRI-REPO-SCHEMA-001",
                    f"/{rel}",
                    str(exc),
                )
            )
    return diagnostics


def validate_reason_registry() -> list[Diagnostic]:
    try:
        reason_registry_entries.cache_clear()
        reason_registry_entries()
    except ProjectionError as exc:
        return [
            Diagnostic(
                "PRI-REASON-001",
                "/decision-reason-registry",
                str(exc),
            )
        ]
    return []


def _literal_all(tree: ast.Module) -> set[str] | None:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            continue
        if not isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
            return None
        values: set[str] = set()
        for item in node.value.elts:
            if (
                not isinstance(item, ast.Constant)
                or not isinstance(item.value, str)
            ):
                return None
            values.add(item.value)
        return values
    return None


def _function_sources(
    source: str, tree: ast.Module
) -> dict[str, str]:
    lines = source.splitlines()
    out: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        end = getattr(node, "end_lineno", node.lineno)
        out[node.name] = "\n".join(lines[node.lineno - 1 : end])
    return out


def validate_candidate_output_closure(
    root: Path,
) -> list[Diagnostic]:
    path = root / "pr_inspector/candidate_v1_11.py"
    logical_path = "/pr_inspector/candidate_v1_11.py"
    if not path.is_file():
        return [
            Diagnostic(
                "PRI-CANDIDATE-OUTPUT-001",
                logical_path,
                "compatibility module is missing",
            )
        ]
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        return [
            Diagnostic(
                "PRI-CANDIDATE-OUTPUT-001",
                logical_path,
                str(exc),
            )
        ]

    diagnostics: list[Diagnostic] = []
    exports = _literal_all(tree)
    if exports is None:
        diagnostics.append(
            Diagnostic(
                "PRI-CANDIDATE-OUTPUT-001",
                f"{logical_path}/__all__",
                "Candidate compatibility requires a literal allowlist",
            )
        )
    elif exports != CANDIDATE_ALLOWED_EXPORTS:
        missing = sorted(CANDIDATE_ALLOWED_EXPORTS - exports)
        extra = sorted(exports - CANDIDATE_ALLOWED_EXPORTS)
        details: list[str] = []
        if missing:
            details.append(
                "missing compatibility exports: " + ", ".join(missing)
            )
        if extra:
            details.append(
                "unauthorized exports: " + ", ".join(extra)
            )
        diagnostics.append(
            Diagnostic(
                "PRI-CANDIDATE-OUTPUT-001",
                f"{logical_path}/__all__",
                "; ".join(details),
            )
        )

    forbidden_text = (
        "Repair independently validated technical findings before rereview.",
        "Repair indepently validated technical findings before rereview.",
        "for _name in dir(",
        "for name in tuple(dir(",
        'raw_owner + "\n## پرامپت اقدام',
    )
    for text in forbidden_text:
        if text in source:
            diagnostics.append(
                Diagnostic(
                    "PRI-CANDIDATE-OUTPUT-001",
                    logical_path,
                    (
                        "forbidden Candidate output implementation "
                        f"remains: {text}"
                    ),
                )
            )

    functions = _function_sources(source, tree)
    for name in sorted(CANDIDATE_FAIL_CLOSED_FUNCTIONS):
        function_source = functions.get(name)
        if function_source is None:
            diagnostics.append(
                Diagnostic(
                    "PRI-CANDIDATE-OUTPUT-001",
                    logical_path,
                    f"migration tombstone is missing: {name}",
                )
            )
        elif "raise _migration_error" not in function_source:
            diagnostics.append(
                Diagnostic(
                    "PRI-CANDIDATE-OUTPUT-001",
                    logical_path,
                    f"Candidate output authority does not fail closed: {name}",
                )
            )

    delivery_source = functions.get(
        "candidate_owner_delivery_stdout", ""
    )
    if (
        "official_owner_delivery(completion)" not in delivery_source
        or "is_verified_review_completion" not in delivery_source
    ):
        diagnostics.append(
            Diagnostic(
                "PRI-CANDIDATE-OUTPUT-001",
                logical_path,
                (
                    "Candidate owner delivery must delegate exact verified "
                    "official bytes"
                ),
            )
        )

    profile_source = functions.get(
        "render_owner_profile_commands", ""
    )
    if (
        "official_owner_profile_commands(completion)"
        not in profile_source
        or "is_verified_review_completion" not in profile_source
    ):
        diagnostics.append(
            Diagnostic(
                "PRI-CANDIDATE-OUTPUT-001",
                logical_path,
                (
                    "Candidate profile commands must delegate exact "
                    "verified official bytes"
                ),
            )
        )

    validation_path = root / "pr_inspector/validation_v2.py"
    try:
        validation_source = validation_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        diagnostics.append(
            Diagnostic(
                "PRI-PROMPT-SEMANTICS-001",
                "/pr_inspector/validation_v2.py",
                str(exc),
            )
        )
    else:
        required_fragments = (
            "from .prompt_semantics import validate_prompt_semantics",
            "validate_prompt_semantics(package, projection, prompt)",
        )
        for fragment in required_fragments:
            if fragment not in validation_source:
                diagnostics.append(
                    Diagnostic(
                        "PRI-PROMPT-SEMANTICS-001",
                        "/pr_inspector/validation_v2.py",
                        (
                            "canonical directory validation is missing "
                            "independent prompt semantic enforcement"
                        ),
                    )
                )
                break

    return diagnostics


def validate_repository(root: Path = ROOT) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    required = [
        "README.md",
        "BOOTSTRAP.md",
        "AGENTS.md",
        "CURRENT_VERSION",
        "protocol-manifest.yaml",
        "CHANGELOG.md",
        "LICENSE",
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        QUALITY_FOUNDATION,
    ]
    for rel in required:
        if not (root / rel).is_file():
            diagnostics.append(
                Diagnostic(
                    "PRI-REPO-001",
                    f"/{rel}",
                    "required file is missing",
                )
            )
    if diagnostics:
        return sorted(diagnostics)

    try:
        manifest = yaml.safe_load(
            (root / "protocol-manifest.yaml").read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:
        return [
            Diagnostic(
                "PRI-REPO-002",
                "/protocol-manifest.yaml",
                str(exc),
            )
        ]

    current = (
        root / "CURRENT_VERSION"
    ).read_text(encoding="utf-8").strip()
    if manifest.get("active_version") != current:
        diagnostics.append(
            Diagnostic(
                "PRI-REPO-003",
                "/protocol-manifest.yaml",
                "active_version does not match CURRENT_VERSION",
            )
        )

    load_order = manifest.get("load_order") or []
    if len(load_order) != len(set(load_order)):
        diagnostics.append(
            Diagnostic(
                "PRI-REPO-004",
                "/protocol-manifest.yaml/load_order",
                "duplicate canonical path",
            )
        )

    diagnostics.extend(
        validate_quality_foundation(root, load_order)
    )

    prefix = f"protocols/{current}/"
    for index, rel in enumerate(load_order):
        if not str(rel).startswith(prefix):
            diagnostics.append(
                Diagnostic(
                    "PRI-REPO-005",
                    (
                        "/protocol-manifest.yaml/load_order/"
                        f"{index}"
                    ),
                    "active canonical path is not version-scoped",
                )
            )
        if not (root / rel).is_file():
            diagnostics.append(
                Diagnostic(
                    "PRI-REPO-006",
                    f"/{rel}",
                    "canonical file is missing",
                )
            )

    diagnostics.extend(
        validate_active_release_lock(
            root, current, manifest, load_order
        )
    )
    diagnostics.extend(validate_active_schemas(root, load_order))
    diagnostics.extend(validate_reason_registry())
    diagnostics.extend(validate_behavioral_coverage(root))
    diagnostics.extend(validate_candidate_output_closure(root))

    lifecycle_paths = [
        root / "README.md",
        root / f"protocols/{current}/PR_REVIEW_CONTRACT.md",
    ]
    forbidden_lifecycle = (
        "active candidate on the unmerged pr branch",
        "default branch remains authoritative until this pr is merged",
    )
    for lifecycle_path in lifecycle_paths:
        text = lifecycle_path.read_text(encoding="utf-8").lower()
        for phrase in forbidden_lifecycle:
            if phrase in text:
                diagnostics.append(
                    Diagnostic(
                        "PRI-LIFECYCLE-001",
                        f"/{lifecycle_path.relative_to(root)}",
                        f"stale lifecycle wording remains: {phrase}",
                    )
                )

    lock_dir = root / "release-locks"
    if not lock_dir.is_dir():
        diagnostics.append(
            Diagnostic(
                "PRI-LOCK-000",
                "/release-locks",
                "release lock directory is missing",
            )
        )
    else:
        for lock in sorted(lock_dir.glob("v*.sha256")):
            for rel, digest in parse_lock(lock).items():
                path = root / rel
                if not path.is_file():
                    diagnostics.append(
                        Diagnostic(
                            "PRI-LOCK-001",
                            f"/{rel}",
                            f"file listed by {lock.name} is missing",
                        )
                    )
                elif sha256(path) != digest:
                    diagnostics.append(
                        Diagnostic(
                            "PRI-LOCK-001",
                            f"/{rel}",
                            f"SHA-256 differs from {lock.name}",
                        )
                    )

    return sorted(set(diagnostics))
