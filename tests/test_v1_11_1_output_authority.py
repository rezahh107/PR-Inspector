import copy
import hashlib
import json
from pathlib import Path

import pytest

from pr_inspector import candidate_v1_11 as candidate
from pr_inspector.decision_projection import project_decision
from pr_inspector.derived_outputs import (
    PROFILE_COMMANDS_TEXT,
    PROMPT_NAME,
    build_review_artifacts,
    render_next_action_prompt,
)
from pr_inspector.prompt_semantics import (
    HISTORICAL_PLACEHOLDER,
    PROMPT_CONTRACT_CLOSE,
    PROMPT_CONTRACT_HEADING,
    PROMPT_CONTRACT_OPEN,
    extract_prompt_contract,
    validate_prompt_semantics,
)
from pr_inspector.validation_v2 import validate_directory

ROOT = Path(__file__).resolve().parents[1]
CURRENT = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()


def repair_package() -> dict:
    value = json.loads(
        (ROOT / "fixtures/repair-handoff-valid/review-package.json").read_text(
            encoding="utf-8"
        )
    )
    value["protocol_version"] = CURRENT
    return value


def replace_contract(prompt: str, mutate) -> str:
    contract = extract_prompt_contract(prompt)
    mutate(contract)
    raw = json.dumps(
        contract,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    start = prompt.index(PROMPT_CONTRACT_HEADING)
    open_index = prompt.index(PROMPT_CONTRACT_OPEN, start)
    json_start = prompt.index("\n", open_index) + 1
    close_index = prompt.index("\n" + PROMPT_CONTRACT_CLOSE, json_start)
    return prompt[:json_start] + raw + prompt[close_index:]


def codes(diags):
    return {item.code for item in diags}


def write_bundle(path: Path, package: dict, artifacts: dict[str, str]) -> None:
    path.mkdir()
    (path / "review-package.json").write_text(
        json.dumps(package, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for name, text in artifacts.items():
        (path / name).write_text(text, encoding="utf-8")


def test_official_prompt_contains_structured_contract_and_excludes_profile_commands():
    package = repair_package()
    projection = project_decision(package)
    prompt = render_next_action_prompt(package, projection)
    contract = extract_prompt_contract(prompt)
    assert contract["protocol_version"] == CURRENT
    assert contract["target_repository"] == package["review_identity"]["target_repository"]
    assert contract["pull_request"] == package["review_identity"]["pr_number"]
    assert contract["reviewed_head_sha"] == package["review_identity"]["reviewed_head_sha"]
    assert contract["action_kind"] in {"repair", "repair_and_verify"}
    assert contract["may_modify_code"] is True
    assert contract["finding_ids"]
    assert contract["evidence_references"]
    assert contract["required_tests"]
    assert contract["fresh_review_required"] is True
    assert PROFILE_COMMANDS_TEXT not in prompt
    assert validate_prompt_semantics(package, projection, prompt) == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c.pop("target_repository"),
        lambda c: c.pop("pull_request"),
        lambda c: c.pop("reviewed_head_sha"),
        lambda c: c.__setitem__("reason_codes", []),
        lambda c: c.__setitem__("finding_ids", []),
        lambda c: c.__setitem__("evidence_references", []),
        lambda c: c.__setitem__("required_tests", []),
        lambda c: c.__setitem__("fresh_review_required", False),
        lambda c: c.__setitem__("profile_commands_separate", False),
        lambda c: c.__setitem__("recipient", "reviewer_model"),
        lambda c: c.__setitem__("may_modify_code", False),
    ],
)
def test_structured_contract_mutations_fail_semantic_validation(mutate):
    package = repair_package()
    projection = project_decision(package)
    prompt = render_next_action_prompt(package, projection)
    mutated = replace_contract(prompt, mutate)
    assert validate_prompt_semantics(package, projection, mutated)


def test_exact_pr22_placeholder_and_generic_nonempty_prompt_fail():
    package = repair_package()
    projection = project_decision(package)
    placeholder = HISTORICAL_PLACEHOLDER + "\n"
    assert "PRI-PROMPT-SEM-001" in codes(
        validate_prompt_semantics(package, projection, placeholder)
    )
    generic = "Please fix the validated findings and rerun review.\n"
    assert "PRI-PROMPT-SEM-001" in codes(
        validate_prompt_semantics(package, projection, generic)
    )


def test_profile_commands_appended_to_prompt_fail():
    package = repair_package()
    projection = project_decision(package)
    prompt = render_next_action_prompt(package, projection) + PROFILE_COMMANDS_TEXT
    assert "PRI-PROMPT-SEM-002" in codes(
        validate_prompt_semantics(package, projection, prompt)
    )


def test_verify_cannot_authorize_modification_and_rerun_cannot_authorize_repair():
    package = repair_package()
    projection = project_decision(package)
    prompt = render_next_action_prompt(package, projection)

    verify_prompt = replace_contract(
        prompt,
        lambda c: c.update(
            {
                "action_kind": "verify",
                "recipient": "reviewer_model",
                "prompt_kind": "verification_prompt",
                "may_modify_code": True,
            }
        ),
    )
    assert "PRI-PROMPT-SEM-007" in codes(
        validate_prompt_semantics(package, projection, verify_prompt)
    )

    rerun_prompt = replace_contract(
        prompt,
        lambda c: c.update(
            {
                "action_kind": "rerun_review",
                "recipient": "reviewer_model",
                "prompt_kind": "fresh_review_prompt",
                "may_modify_code": False,
                "review_validity": "CURRENT",
            }
        ),
    )
    assert "PRI-PROMPT-SEM-007" in codes(
        validate_prompt_semantics(package, projection, rerun_prompt)
    )


def test_hash_valid_but_semantically_incomplete_prompt_is_rejected(tmp_path):
    package = repair_package()
    artifacts = build_review_artifacts(package)
    prompt = replace_contract(artifacts[PROMPT_NAME], lambda c: c.pop("finding_ids"))
    artifacts[PROMPT_NAME] = prompt
    manifest = json.loads(artifacts["artifact-manifest.json"])
    manifest["next_action_artifact"]["sha256"] = hashlib.sha256(
        prompt.encode("utf-8")
    ).hexdigest()
    artifacts["artifact-manifest.json"] = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    output = tmp_path / "review"
    write_bundle(output, package, artifacts)
    diagnostics = validate_directory(output)
    assert "PRI-PROMPT-SEM-003" in codes(diagnostics) or "PRI-PROMPT-SEM-004" in codes(diagnostics)


def test_historical_four_segment_candidate_output_is_impossible():
    with pytest.raises(candidate.CandidateOutputMigrationError):
        candidate.candidate_owner_delivery_stdout(object())
    source = Path(candidate.__file__).read_text(encoding="utf-8")
    assert HISTORICAL_PLACEHOLDER not in source
    assert "raw_owner + \"\\n## پرامهت اقدام\"" not in source


def test_candidate_and_official_output_authorities_cannot_diverge():
    output_symbols = {
        "project_decision",
        "render_candidate_next_action_prompt",
        "render_candidate_owner_result",
        "render_candidate_owner_card",
        "render_candidate_technical_handoff",
        "build_candidate_review_artifacts",
        "verify_candidate_review_artifact_bytes",
        "verify_minimal_review_artifact_bytes",
        "build_candidate_owner_delivery_artifacts",
        "candidate_owner_delivery_stdout",
    }
    assert output_symbols.isdisjoint(candidate.__all__)
    for name in output_symbols:
        with pytest.raises(candidate.CandidateOutputMigrationError):
            getattr(candidate, name)(None)


def test_governance_only_gap_does_not_mint_repair_authority():
    package = repair_package()
    projection = project_decision(package)
    prompt = render_next_action_prompt(package, projection)
    forged_projection = copy.deepcopy(projection)
    forged_projection["technical_status_reason_codes"] = []
    forged_projection["governance_decision"] = {
        "status": "GAP_FOUND",
        "reason_codes": ["merge_authorization_unverified"],
    }
    assert "PRI-PROMPT-SEM-008" in codes(
        validate_prompt_semantics(package, forged_projection, prompt)
    )
