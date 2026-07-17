from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path

from pr_inspector.decision_projection import project_decision
from pr_inspector.derived_outputs import (
    PROFILE_COMMANDS_TEXT,
    build_review_artifacts,
    render_next_action_prompt,
)
from pr_inspector.prompt_semantics import (
    HISTORICAL_PLACEHOLDER,
    validate_prompt_semantics,
)
from pr_inspector.validation_v2 import validate_directory


ROOT = Path(__file__).resolve().parents[1]


def _repair_package() -> tuple[dict, dict, str]:
    package = json.loads(
        (ROOT / "fixtures/golden-green/review-package.json").read_text(encoding="utf-8")
    )
    package["protocol_version"] = "v1.11.1"
    package["checks"][0]["result"] = "FAIL"
    package["evidence_records"][0]["result"] = "FAIL"
    projection = project_decision(package)
    package["technical_decision"] = copy.deepcopy(projection["technical_decision"])
    package["governance_decision"] = copy.deepcopy(projection["governance_decision"])
    package["overall_recommendation"] = copy.deepcopy(projection["overall_recommendation"])
    prompt = render_next_action_prompt(package, projection)
    return package, projection, prompt


def _messages(diagnostics):
    return [item.message for item in diagnostics]


def test_official_prompt_is_semantically_complete_and_profile_commands_are_separate():
    package, projection, prompt = _repair_package()
    assert validate_prompt_semantics(package, projection, prompt) == []
    assert "example/project" in prompt
    assert "pull_request: `42`" in prompt
    assert "reviewed_head_sha: `1111111111111111111111111111111111111111`" in prompt
    assert "RSN-REQUIRED-CHECK-FAILED" in prompt
    assert "[MANDATORY PR INSPECTOR RE-REVIEW]" in prompt
    assert PROFILE_COMMANDS_TEXT.strip() not in prompt


def test_pr22_placeholder_and_arbitrary_generic_prompt_fail_semantic_validation():
    package, projection, _ = _repair_package()
    placeholder = validate_prompt_semantics(package, projection, HISTORICAL_PLACEHOLDER)
    generic = validate_prompt_semantics(
        package,
        projection,
        "Repair the findings and rerun the review.\n",
    )
    assert any("PR #22 placeholder" in message for message in _messages(placeholder))
    assert any("operationally incomplete" in message for message in _messages(generic))


def test_identity_reason_profile_command_and_rereview_mutations_fail():
    package, projection, prompt = _repair_package()
    mutations = {
        "repository": prompt.replace("example/project", "example/other"),
        "pull request": prompt.replace("pull_request: `42`", "pull_request: `43`"),
        "Head": prompt.replace("1" * 40, "9" * 40),
        "reason": prompt.replace("RSN-REQUIRED-CHECK-FAILED", "RSN-REMOVED"),
        "profile commands": prompt + "\n" + PROFILE_COMMANDS_TEXT,
        "rereview": prompt.replace("independently reviewed again", "reviewed later"),
    }
    for label, mutated in mutations.items():
        diagnostics = validate_prompt_semantics(package, projection, mutated)
        assert diagnostics, label


def test_verify_and_rerun_review_cannot_gain_repair_authority():
    package, projection, prompt = _repair_package()
    verify_projection = copy.deepcopy(projection)
    verify_projection["next_action"].update(
        {
            "kind": "verify",
            "recipient": "reviewer_model",
            "max_modify_code": False,
            "prompt_kind": "verification_prompt",
        }
    )
    diagnostics = validate_prompt_semantics(package, verify_projection, prompt)
    assert any("does not bind action kind" in item.message or "verify must not authorize repair" in item.message for item in diagnostics)

    rerun_projection = copy.deepcopy(verify_projection)
    rerun_projection["next_action"].update(
        {"kind": "rerun_review", "prompt_kind": "fresh_review_prompt"}
    )
    diagnostics = validate_prompt_semantics(package, rerun_projection, prompt)
    assert any("rerun_review" in item.message for item in diagnostics)


def test_hash_valid_but_semantically_incomplete_prompt_is_rejected(tmp_path):
    package, projection, _ = _repair_package()
    package_bytes = (
        json.dumps(package, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    artifacts = build_review_artifacts(package, review_package_bytes=package_bytes)
    for name, text in artifacts.items():
        (tmp_path / name).write_text(text, encoding="utf-8", newline="")
    (tmp_path / "review-package.json").write_bytes(package_bytes)

    bad_prompt = HISTORICAL_PLACEHOLDER + "\n"
    (tmp_path / "NEXT_ACTION_PROMPT.en.md").write_text(bad_prompt, encoding="utf-8", newline="")
    manifest_path = tmp_path / "artifact-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["next_action_artifact"]["sha256"] = hashlib.sha256(
        bad_prompt.encode("utf-8")
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="",
    )

    diagnostics = validate_directory(tmp_path)
    assert any(item.code == "PRI-PROMPT-SEMANTICS-001" for item in diagnostics)


def test_historical_candidate_shape_cannot_be_produced_by_supported_active_code():
    import pr_inspector.candidate_v1_11 as candidate
    import pr_inspector.owner_delivery as owner_delivery

    candidate_source = inspect.getsource(candidate)
    owner_source = inspect.getsource(owner_delivery)
    assert HISTORICAL_PLACEHOLDER not in candidate_source
    assert "raw_owner +" not in candidate_source
    assert "official_owner_delivery" in candidate_source
    assert "return owner_result + separator + prompt" in owner_source
    assert "profile commands" not in inspect.getsource(owner_delivery.official_owner_delivery)
