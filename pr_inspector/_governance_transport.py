from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import weakref
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
SCHEMA_PATH = ROOT / f"protocols/{CURRENT_VERSION}/schemas/governance-evidence.schema.json"
MAX_RESPONSE_AGE_SECONDS = 300
MAX_CLOCK_SKEW_SECONDS = 30
_UNVERIFIED_MESSAGE = (
    "merge readiness appears satisfied, but repository-level enforcement is unverified"
)
_HUMAN_GOVERNANCE_MESSAGE = (
    "human_governance_required: specialist qualification is not authoritatively verified"
)
_CHECK_ANNOTATIONS_PATH = re.compile(
    r"^/repos/[^/]+/[^/]+/check-runs/[1-9][0-9]*/annotations$"
)


class GovernanceEvidenceError(ValueError):
    pass


class GitHubApiResponse:
    """Sealed receipt minted only after an HTTPS GitHub API response is read."""

    __slots__ = (
        "request_url",
        "response_url",
        "status_code",
        "fetched_at",
        "payload_json",
        "receipt_id",
        "content_id",
        "transport_origin",
        "__weakref__",
    )

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("GitHubApiResponse can only be created by fetch_github_api_response")

    def __setattr__(self, _name: str, _value: object) -> None:
        raise AttributeError("GitHubApiResponse is immutable")


class TestGitHubApiResponse:
    """Structurally similar, non-operational response for negative tests only."""

    __slots__ = GitHubApiResponse.__slots__

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("TestGitHubApiResponse can only be created by the test factory")

    def __setattr__(self, _name: str, _value: object) -> None:
        raise AttributeError("TestGitHubApiResponse is immutable")


class VerifiedGitHubGovernanceSource:
    """Sealed payload-derived governance source."""

    __slots__ = (
        "canonical_record_json",
        "repository",
        "repository_id",
        "response_urls",
        "response_receipt_ids",
        "response_content_ids",
        "__weakref__",
    )

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError(
            "VerifiedGitHubGovernanceSource can only be created by the governance verifier"
        )

    def __setattr__(self, _name: str, _value: object) -> None:
        raise AttributeError("VerifiedGitHubGovernanceSource is immutable")


class VerifiedGovernanceEvidence:
    __slots__ = (
        "evidence_id",
        "repository",
        "default_branch",
        "pull_request_number",
        "exact_head_sha",
        "enforcement_status",
        "valid_approval_reviewers",
        "required_status_checks",
        "exact_head_checks_satisfied",
        "approval_complete",
        "specialist_satisfied",
        "specialist_status",
        "bypass_actors",
        "merge_readiness_satisfied",
        "merge_authorized",
        "conclusion",
        "source_response_urls",
        "__weakref__",
    )

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError(
            "VerifiedGovernanceEvidence can only be created by the governance verifier"
        )

    def __setattr__(self, _name: str, _value: object) -> None:
        raise AttributeError("VerifiedGovernanceEvidence is immutable")


@dataclass(frozen=True)
class SpecialistRequirement:
    """A policy requirement. Qualification still needs an authoritative team response."""

    organization: str
    team_slug: str

    def __post_init__(self) -> None:
        if not self.organization or "/" in self.organization:
            raise GovernanceEvidenceError("specialist organization is invalid")
        if not self.team_slug or "/" in self.team_slug:
            raise GovernanceEvidenceError("specialist team slug is invalid")


_SOURCE_CAPABILITIES: weakref.WeakSet[VerifiedGitHubGovernanceSource] = weakref.WeakSet()
_EVIDENCE_CAPABILITIES: weakref.WeakSet[VerifiedGovernanceEvidence] = weakref.WeakSet()


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _validate_schema(record: Mapping[str, Any]) -> None:
    errors = sorted(
        _validator().iter_errors(record),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        rendered = "; ".join(
            f"/{'/'.join(map(str, error.absolute_path))}: {error.message}"
            for error in errors
        )
        raise GovernanceEvidenceError(
            f"governance evidence schema validation failed: {rendered}"
        )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise GovernanceEvidenceError(f"{field_name} is missing or invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GovernanceEvidenceError(f"{field_name} is not a valid date-time") from exc
    if parsed.tzinfo is None:
        raise GovernanceEvidenceError(f"{field_name} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise GovernanceEvidenceError(f"GitHub response is not canonical JSON: {exc}") from exc


def _require_api_url(url: str) -> str:
    if not isinstance(url, str):
        raise GovernanceEvidenceError("GitHub API URL must be a string")
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.github.com"
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or not parsed.path.startswith(("/repos/", "/orgs/"))
        or any(part in {".", ".."} for part in parsed.path.split("/"))
    ):
        raise GovernanceEvidenceError(f"GitHub API URL is not canonical HTTPS: {url}")
    return url


def _assign_response_fields(
    value: object,
    *,
    request_url: str,
    response_url: str,
    status_code: int,
    fetched_at: datetime,
    payload: Any,
    transport_origin: str,
) -> object:
    payload_json = _canonical_json(payload)
    content_id = hashlib.sha256(
        _canonical_json(
            {
                "request_url": request_url,
                "response_url": response_url,
                "status_code": status_code,
                "payload": json.loads(payload_json),
            }
        ).encode("utf-8")
    ).hexdigest()
    receipt_id = hashlib.sha256(
        _canonical_json(
            {
                "content_id": content_id,
                "fetched_at": _iso(fetched_at),
            }
        ).encode("utf-8")
    ).hexdigest()
    object.__setattr__(value, "request_url", request_url)
    object.__setattr__(value, "response_url", response_url)
    object.__setattr__(value, "status_code", status_code)
    object.__setattr__(value, "fetched_at", _iso(fetched_at))
    object.__setattr__(value, "payload_json", payload_json)
    object.__setattr__(value, "receipt_id", receipt_id)
    object.__setattr__(value, "content_id", content_id)
    object.__setattr__(value, "transport_origin", transport_origin)
    return value


def _mint_response(
    *,
    request_url: str,
    response_url: str,
    status_code: int,
    fetched_at: datetime,
    payload: Any,
) -> TestGitHubApiResponse:
    """Create only a non-operational structural response for adversarial tests.

    This compatibility helper deliberately has no caller-selectable transport origin,
    never touches the operational registry, and is rejected by production verifiers.
    """

    value = object.__new__(TestGitHubApiResponse)
    return _assign_response_fields(
        value,
        request_url=request_url,
        response_url=response_url,
        status_code=status_code,
        fetched_at=fetched_at,
        payload=payload,
        transport_origin="test_factory",
    )


def _build_operational_response_boundary():
    capabilities: weakref.WeakSet[GitHubApiResponse] = weakref.WeakSet()
    issuer = object()

    def _mint_operational_response(
        *,
        request_url: str,
        response_url: str,
        status_code: int,
        fetched_at: datetime,
        payload: Any,
        issuer_token: object,
    ) -> GitHubApiResponse:
        if issuer_token is not issuer:
            raise GovernanceEvidenceError("operational GitHub response issuer is invalid")
        value = object.__new__(GitHubApiResponse)
        _assign_response_fields(
            value,
            request_url=request_url,
            response_url=response_url,
            status_code=status_code,
            fetched_at=fetched_at,
            payload=payload,
            transport_origin="github_https",
        )
        capabilities.add(value)
        return value

    def is_verified(value: object) -> bool:
        return type(value) is GitHubApiResponse and value in capabilities

    def fetch(
        url: str,
        *,
        token: str | None,
        api_version: str,
        fetched_at: datetime | None = None,
    ) -> GitHubApiResponse:
        """Fetch one GitHub API response and seal the observed HTTPS receipt.

        HTTP errors and redirects are retained as negative receipts. Only a 200 response
        whose observed URL exactly matches the canonical request can satisfy a positive
        provenance verifier. Transport and JSON failures remain hard errors.
        """

        request_url = _require_api_url(url)
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": api_version,
            "User-Agent": "PR-Inspector-governance-verifier",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(request_url, headers=headers)
        try:
            response = urllib.request.urlopen(request, timeout=20)
        except urllib.error.HTTPError as exc:
            response = exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise GovernanceEvidenceError(
                f"insufficient_evidence: GitHub governance request failed for {url}: {exc}"
            ) from exc

        try:
            response_url = response.geturl()
            if not isinstance(response_url, str) or not response_url:
                raise TypeError("response URL is missing")
            status_code = int(getattr(response, "status", getattr(response, "code", 0)))
            payload = json.loads(response.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
            raise GovernanceEvidenceError(
                f"insufficient_evidence: GitHub governance response is invalid: {exc}"
            ) from exc
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()

        if not isinstance(payload, (dict, list)):
            raise GovernanceEvidenceError(
                "insufficient_evidence: GitHub governance response must be a JSON object or array"
            )
        return _mint_operational_response(
            request_url=request_url,
            response_url=response_url,
            status_code=status_code,
            fetched_at=fetched_at or _utcnow(),
            payload=payload,
            issuer_token=issuer,
        )

    return fetch, is_verified


fetch_github_api_response, is_verified_github_api_response = (
    _build_operational_response_boundary()
)


def _validate_check_annotation_payload(response: GitHubApiResponse, payload: Any) -> None:
    parsed = urllib.parse.urlsplit(response.request_url)
    if not _CHECK_ANNOTATIONS_PATH.fullmatch(parsed.path):
        return
    if response.status_code != 200:
        return
    if not isinstance(payload, list):
        raise GovernanceEvidenceError("check annotation payload is malformed")
    for index, annotation in enumerate(payload):
        if not isinstance(annotation, Mapping):
            raise GovernanceEvidenceError(
                f"check annotation {index} is not an object"
            )
        annotation_id = annotation.get("id")
        if annotation_id is not None and (
            not isinstance(annotation_id, int)
            or isinstance(annotation_id, bool)
            or annotation_id <= 0
        ):
            raise GovernanceEvidenceError(
                f"check annotation {index} identity is malformed"
            )
        start_line = annotation.get("start_line")
        end_line = annotation.get("end_line")
        for field_name, value in (
            ("start_line", start_line),
            ("end_line", end_line),
        ):
            if value is not None and (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value <= 0
            ):
                raise GovernanceEvidenceError(
                    f"check annotation {index} {field_name} is malformed"
                )
        if (
            start_line is not None
            and end_line is not None
            and end_line < start_line
        ):
            raise GovernanceEvidenceError(
                f"check annotation {index} line range is malformed"
            )


def github_response_payload(response: GitHubApiResponse) -> Any:
    if not is_verified_github_api_response(response):
        raise GovernanceEvidenceError(
            "GitHub response is not a verifier-created HTTPS response capability"
        )
    payload = json.loads(response.payload_json)
    _validate_check_annotation_payload(response, payload)
    return payload


def _fresh_response(
    responses: Mapping[str, GitHubApiResponse],
    key: str,
    *,
    expected_url: str,
    now: datetime,
    required: bool,
) -> GitHubApiResponse | None:
    response = responses.get(key)
    if response is None:
        if required:
            raise GovernanceEvidenceError(
                f"insufficient_evidence: required GitHub endpoint {key} was not fetched"
            )
        return None
    if not is_verified_github_api_response(response):
        raise GovernanceEvidenceError(
            f"insufficient_evidence: {key} is not a verifier-created GitHub response"
        )
    if response.request_url != expected_url or response.response_url != expected_url:
        raise GovernanceEvidenceError(
            f"insufficient_evidence: {key} response URL does not match {expected_url}"
        )
    fetched_at = _parse_time(response.fetched_at, field_name=f"{key}.fetched_at")
    age = (now - fetched_at).total_seconds()
    if age > MAX_RESPONSE_AGE_SECONDS:
        raise GovernanceEvidenceError(
            f"insufficient_evidence: stale or replayed GitHub response for {key}"
        )
    if age < -MAX_CLOCK_SKEW_SECONDS:
        raise GovernanceEvidenceError(
            f"insufficient_evidence: future-dated GitHub response for {key}"
        )
    return response


def _payload_or_none(response: GitHubApiResponse | None) -> Any | None:
    if response is None or response.status_code != 200:
        return None
    return github_response_payload(response)


def _evidence_urls(*responses: GitHubApiResponse | None) -> list[str]:
    return sorted({item.response_url for item in responses if item is not None})
