import json
from pathlib import Path

import pytest

from pr_inspector._official_head import CompletionError
from pr_inspector.official_review import (
    VerifiedReviewCompletion,
    complete_review,
    github_pull_request_head_source,
    is_verified_review_completion,
    official_next_action_prompt,
    official_owner_delivery,
    official_owner_result,
)
from tests.governance_test_support import sequence_capability

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "example/project"
REPOSITORY_ID = 4242
PR_NUMBER = 42
HEAD = "1" * 40
API_VERSION = "2026-03-10"
DELIVERY_HEADING = "\n## متن کامل اقدام بعدی\n\n"


def package(name: str) -> dict:
    return json.loads(
        (ROOT / "fixtures" / name / "review-package.json").read_text(
            encoding="utf-8"
        )
    )


def write_package(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def pr_payload() -> dict:
    api_url = f"https://api.github.com/repos/{REPOSITORY}/pulls/{PR_NUMBER}"
    return {
        "number": PR_NUMBER,
        "url": api_url,
        "html_url": f"https://github.com/{REPOSITORY}/pull/{PR_NUMBER}",
        "base": {"repo": {"id": REPOSITORY_ID, "full_name": REPOSITORY}},
        "head": {"sha": HEAD},
    }


def install_live_payload(monkeypatch) -> None:
    from pr_inspector import _official_head

    def fake_github_json(url, *, token, api_version):
        assert url == f"https://api.github.com/repos/{REPOSITORY}/pulls/{PR_NUMBER}"
        assert api_version == API_VERSION
        return pr_payload()

    monkeypatch.setattr(_official_head, "_github_json", fake_github_json)


def source():
    return github_pull_request_head_source(
        REPOSITORY,
        PR_NUMBER,
        token=None,
        api_version=API_VERSION,
    )


def completed_bundle(tmp_path: Path, monkeypatch, fixture_name: str):
    install_live_payload(monkeypatch)
    value = package(fixture_name)
    package_path = tmp_path / "review-package.json"
    write_package(package_path, value)
    output = tmp_path / "review"
    outcome = complete_review(
        package_path,
        output,
        head_source=source(),
        sequence_enforcement=(
            sequence_capability() if fixture_name == "golden-green" else None
        ),
    )
    assert is_verified_review_completion(outcome)
    assert isinstance(outcome, VerifiedReviewCompletion)
    return outcome, output


def test_prompt_required_owner_output_is_atomically_delivered(tmp_path, monkeypatch):
    completion, _ = completed_bundle(
        tmp_path,
        monkeypatch,
        "repair-handoff-valid",
    )
    raw_owner_result = completion.owner_result_text()
    prompt = official_next_action_prompt(completion)

    assert prompt is not None
    assert official_owner_delivery(completion) == (
        raw_owner_result + DELIVERY_HEADING + prompt
    )
    with pytest.raises(CompletionError, match="official_owner_delivery"):
        official_owner_result(completion)


def test_no_prompt_owner_delivery_remains_exact_two_line_result(tmp_path, monkeypatch):
    completion, _ = completed_bundle(tmp_path, monkeypatch, "golden-green")

    result = official_owner_result(completion)
    assert official_next_action_prompt(completion) is None
    assert official_owner_delivery(completion) == result
    assert len(result.splitlines()) == 2


def test_atomic_delivery_rejects_missing_required_prompt(tmp_path, monkeypatch):
    completion, output = completed_bundle(
        tmp_path,
        monkeypatch,
        "repair-handoff-valid",
    )
    (output / "NEXT_ACTION_PROMPT.en.md").unlink()

    with pytest.raises(CompletionError):
        official_owner_delivery(completion)


def test_atomic_delivery_rejects_forged_completion():
    with pytest.raises(CompletionError):
        official_owner_delivery(object())  # type: ignore[arg-type]
