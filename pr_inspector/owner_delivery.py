from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from ._official_bundle import (
    VerifiedReviewCompletion,
    is_verified_review_completion,
    json_object_bytes,
    required_artifact_bytes,
    utf8_bytes,
)
from ._official_head import CompletionError

ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
CONTRACT_PATH = ROOT / f"protocols/{CURRENT_VERSION}/policies/OWNER_DELIVERY_CONTRACT.json"
CONTRACT_SCHEMA_PATH = ROOT / f"protocols/{CURRENT_VERSION}/schemas/owner-delivery-contract.schema.json"


@lru_cache(maxsize=1)
def _delivery_contract() -> dict[str, Any]:
    try:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        schema = json.loads(CONTRACT_SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema).iter_errors(contract),
            key=lambda item: tuple(str(part) for part in item.absolute_path),
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise CompletionError(f"cannot load active owner-delivery contract: {exc}") from exc
    except Exception as exc:
        raise CompletionError(f"invalid active owner-delivery contract schema: {exc}") from exc
    if errors:
        first = errors[0]
        path = "/" + "/".join(str(item) for item in first.absolute_path)
        raise CompletionError(
            f"active owner-delivery contract is invalid at {path}: {first.message}"
        )
    if contract.get("protocol_version") != CURRENT_VERSION:
        raise CompletionError("active owner-delivery contract version mismatch")
    return contract


def _verified_bundle(value: VerifiedReviewCompletion):
    if not is_verified_review_completion(value):
        raise CompletionError("official owner delivery requires verified completion")
    return value._reverify()


def _projection(bundle: Any, contract: dict[str, Any]) -> dict[str, Any]:
    name = contract["projection_name"]
    return json_object_bytes(
        name,
        required_artifact_bytes(bundle.artifact_bytes, name),
    )


def _owner_result(bundle: Any, contract: dict[str, Any]) -> str:
    name = contract["owner_result_name"]
    return utf8_bytes(
        name,
        required_artifact_bytes(bundle.artifact_bytes, name),
    )


def _profile_commands(bundle: Any, contract: dict[str, Any]) -> str:
    name = contract["profile_commands_name"]
    return utf8_bytes(
        name,
        required_artifact_bytes(bundle.artifact_bytes, name),
    )


def _prompt(
    bundle: Any,
    projection: dict[str, Any],
    contract: dict[str, Any],
) -> str | None:
    # _verified_bundle() has already validated the captured projection against its
    # schema and deterministic canonical projection. This function consumes that
    # verified shape rather than introducing a competing validation path.
    prompt_required = projection["next_action"]["prompt_required"]
    name = contract["prompt_name"]
    prompt_bytes = bundle.artifact_bytes.get(name)

    if not prompt_required:
        if prompt_bytes is not None:
            raise CompletionError("canonical projection forbids a next-action prompt")
        return None

    if prompt_bytes is None:
        raise CompletionError("canonical projection requires a next-action prompt")
    return utf8_bytes(name, prompt_bytes)


def official_owner_delivery(value: VerifiedReviewCompletion) -> str:
    """Return one complete owner-facing delivery from one verified byte snapshot."""

    contract = _delivery_contract()
    bundle = _verified_bundle(value)
    projection = _projection(bundle, contract)
    owner_result = _owner_result(bundle, contract)
    prompt = _prompt(bundle, projection, contract)

    if prompt is None:
        return owner_result
    separator = contract["prompt_separator_template"].format(
        heading=contract["prompt_heading"]
    )
    return owner_result + separator + prompt


def official_owner_result(value: VerifiedReviewCompletion) -> str:
    """Return compact owner text only when the canonical projection needs no prompt."""

    contract = _delivery_contract()
    bundle = _verified_bundle(value)
    projection = _projection(bundle, contract)
    prompt = _prompt(bundle, projection, contract)
    if prompt is not None:
        raise CompletionError(
            "prompt-required owner output must use official_owner_delivery"
        )
    return _owner_result(bundle, contract)


def official_owner_profile_commands(value: VerifiedReviewCompletion) -> str:
    """Return the separately verified canonical profile-selection commands."""

    contract = _delivery_contract()
    bundle = _verified_bundle(value)
    if contract.get("profile_commands_behavior") != "always_generated_separate_verified_artifact":
        raise CompletionError("active profile commands behavior is unsupported")
    return _profile_commands(bundle, contract)
