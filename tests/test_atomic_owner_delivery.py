import pytest

from pr_inspector._official_head import CompletionError
from pr_inspector.official_review import (
    PromptDeliveryRequiredWarning,
    official_next_action_prompt,
    official_owner_delivery,
    official_owner_result,
)
from tests.test_canonical_output_enforcement import completed_bundle


def test_prompt_required_delivery_contains_exact_prompt_bytes(
    tmp_path,
    monkeypatch,
):
    completion, _, _ = completed_bundle(
        tmp_path,
        monkeypatch,
        "repair-handoff-valid",
    )

    prompt = official_next_action_prompt(completion)
    delivery = official_owner_delivery(completion)

    assert prompt is not None
    assert "پرامپت اصلاح آماده است." in delivery
    assert "\n\n## پرامپت اقدام\n\n" in delivery
    assert delivery.endswith(prompt)


def test_prompt_required_compact_owner_accessor_warns_as_incomplete(
    tmp_path,
    monkeypatch,
):
    completion, output, _ = completed_bundle(
        tmp_path,
        monkeypatch,
        "repair-handoff-valid",
    )

    with pytest.warns(
        PromptDeliveryRequiredWarning,
        match="use official_owner_delivery",
    ):
        compact = official_owner_result(completion)

    assert compact == (output / "OWNER_RESULT.fa.txt").read_text(encoding="utf-8")
    assert "## پرامپت اقدام" not in compact


def test_no_prompt_delivery_remains_exact_compact_owner_result(
    tmp_path,
    monkeypatch,
):
    completion, _, _ = completed_bundle(tmp_path, monkeypatch)

    compact = official_owner_result(completion)
    delivery = official_owner_delivery(completion)

    assert official_next_action_prompt(completion) is None
    assert delivery == compact
    assert "## پرامپت اقدام" not in delivery


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
