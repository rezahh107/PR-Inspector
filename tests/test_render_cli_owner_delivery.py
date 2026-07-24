import json
import sys

from scripts import render_review_v2


def draft_value():
    return {
        "review_summary": "Review the exact implementation against the PR intent.",
        "findings": [],
        "unverified_areas": ["No execution evidence was supplied."],
        "out_of_scope_observations": [],
        "suggested_actions": ["Collect verified execution evidence."],
        "owner_facing_explanation": "This is a reviewer-authored preview only.",
        "inspection_profile": "minimal",
    }


def test_preview_cli_stdout_is_explicitly_non_authoritative(tmp_path, monkeypatch, capsys):
    path = tmp_path / "review-draft.json"
    path.write_text(json.dumps(draft_value()), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["render_review_v2.py", str(path)])

    assert render_review_v2.main() == 0
    captured = capsys.readouterr()
    value = json.loads(captured.out)
    assert value["artifact_assurance"] == "DECLARATION"
    assert value["verification_status"] == "MANUAL_UNVERIFIED"
    assert value["official_completion"] is False
    assert "official_completion=false" in captured.err


def test_preview_cli_can_write_preview_without_owner_artifacts(tmp_path, monkeypatch, capsys):
    path = tmp_path / "review-draft.json"
    output = tmp_path / "preview.json"
    path.write_text(json.dumps(draft_value()), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["render_review_v2.py", str(path), "--output", str(output)],
    )

    assert render_review_v2.main() == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(output.read_text(encoding="utf-8"))["official_completion"] is False
    assert not (tmp_path / "OWNER_RESULT.fa.txt").exists()
    assert not (tmp_path / "DECISION_PROJECTION.json").exists()


def test_raw_review_package_is_rejected_without_partial_preview(tmp_path, monkeypatch, capsys):
    path = tmp_path / "review-package.json"
    path.write_text(
        json.dumps({"protocol_version": "v1.11.1", "review_identity": {}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["render_review_v2.py", str(path)])

    assert render_review_v2.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "No official completion or owner output occurred" in captured.err
    assert "PRI-PREVIEW-001" in captured.err
