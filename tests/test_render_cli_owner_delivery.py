import sys

from scripts import render_review_v2
from tests.test_canonical_output_enforcement import completed_bundle


def test_cli_stdout_contains_owner_result_and_required_prompt(
    tmp_path,
    monkeypatch,
    capsys,
):
    completion, _, _ = completed_bundle(
        tmp_path,
        monkeypatch,
        "repair-handoff-valid",
    )

    monkeypatch.setattr(
        render_review_v2,
        "trust_policy",
        lambda: {"github_api_version": "2026-03-10"},
    )
    monkeypatch.setattr(
        render_review_v2,
        "github_pull_request_head_source",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        render_review_v2,
        "complete_review",
        lambda *args, **kwargs: completion,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "render_review_v2.py",
            str(tmp_path / "review-package.json"),
            "--output-dir",
            str(tmp_path / "output"),
            "--target-repository",
            "example/project",
            "--pr-number",
            "42",
        ],
    )

    assert render_review_v2.main() == 0
    captured = capsys.readouterr()

    assert "پرامپت اصلاح آماده است." in captured.out
    assert "## پرامپت اقدام" in captured.out
    assert "[ROLE AND AUTHORITY]" in captured.out
    assert "atomic owner delivery completed verified validation" in captured.err


def test_cli_stdout_has_no_prompt_section_when_not_required(
    tmp_path,
    monkeypatch,
    capsys,
):
    completion, _, _ = completed_bundle(tmp_path, monkeypatch)

    monkeypatch.setattr(
        render_review_v2,
        "trust_policy",
        lambda: {"github_api_version": "2026-03-10"},
    )
    monkeypatch.setattr(
        render_review_v2,
        "github_pull_request_head_source",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        render_review_v2,
        "complete_review",
        lambda *args, **kwargs: completion,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "render_review_v2.py",
            str(tmp_path / "review-package.json"),
            "--output-dir",
            str(tmp_path / "output"),
            "--target-repository",
            "example/project",
            "--pr-number",
            "42",
        ],
    )

    assert render_review_v2.main() == 0
    captured = capsys.readouterr()

    assert "🟢 وضعیت: از نظر فنی آماده" in captured.out
    assert "## پرامپت اقدام" not in captured.out
