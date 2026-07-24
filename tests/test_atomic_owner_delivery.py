import json
import warnings

import pytest

from pr_inspector._official_head import CompletionError
from pr_inspector.official_review import (
    official_next_action_prompt,
    official_owner_delivery,
    official_owner_result,
    verify_completed_review,
)
from tests.test_behavioral_rule_coverage import write_directory
from tests.test_canonical_output_enforcement import (
    completed_bundle,
    install_live_payloads,
    package,
    profile_sequence_capability,
    source,
)


def test_prompt_required_delivery_contains_exact_prompt_bytes(
    tmp_path,
    monkeypatch,
):
    completion, output, _ = completed_bundle(
        tmp_path,
        monkeypatch,
        "repair-handoff-valid",
    )

    owner_result = (output / "OWNER_RESULT.fa.txt").read_text(encoding="utf-8")
    prompt = official_next_action_prompt(completion)
    delivery = official_owner_delivery(completion)

    assert prompt is not None
    assert delivery == f"{owner_result}\n## پرامپت اقدام\n\n{prompt}"


def test_prompt_required_compact_owner_accessor_fails_closed(
    tmp_path,
    monkeypatch,
):
    completion, _, _ = completed_bundle(
        tmp_path,
        monkeypatch,
        "repair-handoff-valid",
    )

    with pytest.raises(CompletionError, match="must use official_owner_delivery"):
        official_owner_result(completion)


def test_ignored_warning_filters_cannot_bypass_compact_access_invariant(
    tmp_path,
    monkeypatch,
):
    completion, _, _ = completed_bundle(
        tmp_path,
        monkeypatch,
        "repair-handoff-valid",
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(CompletionError, match="must use official_owner_delivery"):
            official_owner_result(completion)


def test_persisted_historical_bundle_requires_a_fresh_official_review(
    tmp_path,
    monkeypatch,
):
    output = tmp_path / "historical-review"
    output.mkdir()
    sequence = profile_sequence_capability()
    write_directory(output, package(), sequence_enforcement=sequence)
    install_live_payloads(monkeypatch)
    with pytest.raises(CompletionError, match="genuine VerifiedReviewCompletion"):
        verify_completed_review(output)  # type: ignore[arg-type]


def test_atomic_delivery_rejects_missing_required_prompt(
    tmp_path,
    monkeypatch,
):
    completion, output, _ = completed_bundle(
        tmp_path,
        monkeypatch,
        "repair-handoff-valid",
    )
    (output / "NEXT_ACTION_PROMPT.en.md").unlink()

    with pytest.raises(CompletionError):
        official_owner_delivery(completion)


def test_atomic_delivery_rejects_tampered_prompt_bytes(
    tmp_path,
    monkeypatch,
):
    completion, output, _ = completed_bundle(
        tmp_path,
        monkeypatch,
        "repair-handoff-valid",
    )
    prompt_path = output / "NEXT_ACTION_PROMPT.en.md"
    prompt_path.write_bytes(prompt_path.read_bytes() + b"truncated-or-rebuilt\n")

    with pytest.raises(CompletionError):
        official_owner_delivery(completion)


def test_malformed_projection_is_blocked_by_reverification_before_prompt_read(
    tmp_path,
    monkeypatch,
):
    completion, output, _ = completed_bundle(
        tmp_path,
        monkeypatch,
        "repair-handoff-valid",
    )
    projection_path = output / "DECISION_PROJECTION.json"
    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    del projection["next_action"]["prompt_required"]
    projection_path.write_text(
        json.dumps(projection, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(CompletionError) as captured:
        official_owner_delivery(completion)
    assert not isinstance(captured.value.__cause__, (KeyError, TypeError))
