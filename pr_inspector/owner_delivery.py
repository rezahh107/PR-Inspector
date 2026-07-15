from __future__ import annotations

import warnings
from typing import Any

from ._official_bundle import (
    VerifiedReviewCompletion,
    is_verified_review_completion,
    json_object_bytes,
    required_artifact_bytes,
    utf8_bytes,
)
from ._official_head import CompletionError
from .derived_outputs import PROJECTION_NAME, PROMPT_NAME

OWNER_RESULT_NAME = "OWNER_RESULT.fa.txt"
OWNER_PROMPT_HEADING = "## پرامپت اقدام"


class PromptDeliveryRequiredWarning(RuntimeWarning):
    """The compact owner result omits a canonically required action prompt."""


def _verified_bundle(value: VerifiedReviewCompletion):
    if not is_verified_review_completion(value):
        raise CompletionError("official owner delivery requires verified completion")
    return value._reverify()


def _projection(bundle: Any) -> dict[str, Any]:
    return json_object_bytes(
        PROJECTION_NAME,
        required_artifact_bytes(bundle.artifact_bytes, PROJECTION_NAME),
    )


def _owner_result(bundle: Any) -> str:
    return utf8_bytes(
        OWNER_RESULT_NAME,
        required_artifact_bytes(bundle.artifact_bytes, OWNER_RESULT_NAME),
    )


def _prompt(bundle: Any, projection: dict[str, Any]) -> str | None:
    prompt_required = projection["next_action"]["prompt_required"]
    prompt_bytes = bundle.artifact_bytes.get(PROMPT_NAME)

    if not prompt_required:
        if prompt_bytes is not None:
            raise CompletionError(
                "canonical projection forbids a next-action prompt"
            )
        return None

    if prompt_bytes is None:
        raise CompletionError(
            "canonical projection requires a next-action prompt"
        )
    return utf8_bytes(PROMPT_NAME, prompt_bytes)


def official_owner_delivery(value: VerifiedReviewCompletion) -> str:
    """Return one indivisible owner-facing result, including the exact prompt when required.

    The owner result, projection, and conditional action prompt are read from one
    fully reverified in-memory byte snapshot. Supported integrations should use
    this accessor for every owner-facing response.
    """

    bundle = _verified_bundle(value)
    projection = _projection(bundle)
    owner_result = _owner_result(bundle)
    prompt = _prompt(bundle, projection)

    if prompt is None:
        return owner_result
    return f"{owner_result}\n{OWNER_PROMPT_HEADING}\n\n{prompt}"


def official_owner_result(value: VerifiedReviewCompletion) -> str:
    """Return the legacy compact owner result.

    This accessor remains compatible with the active v1.10.1 API. When a prompt is
    required it emits ``PromptDeliveryRequiredWarning`` because the returned two-line
    artifact is not a complete owner delivery. New integrations must use
    ``official_owner_delivery`` instead.
    """

    bundle = _verified_bundle(value)
    projection = _projection(bundle)
    prompt = _prompt(bundle, projection)
    if prompt is not None:
        warnings.warn(
            "prompt-required owner output is incomplete; use official_owner_delivery",
            PromptDeliveryRequiredWarning,
            stacklevel=2,
        )
    return _owner_result(bundle)
