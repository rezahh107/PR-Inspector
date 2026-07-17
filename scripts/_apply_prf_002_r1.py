from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, value: str) -> None:
    (ROOT / path).write_text(value, encoding="utf-8", newline="")


def replace_once(path: str, old: str, new: str) -> None:
    value = read(path)
    count = value.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one exact match, found {count}")
    write(path, value.replace(old, new, 1))


def replace_regex_once(path: str, pattern: str, replacement: str) -> None:
    value = read(path)
    updated, count = re.subn(pattern, replacement, value, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"{path}: expected one regex match, found {count}")
    write(path, updated)


transport_path = "pr_inspector/_governance_transport.py"
replace_once(
    transport_path,
    '''class VerifiedGitHubGovernanceSource:\n''',
    '''class TestGitHubApiResponse:\n    """Structurally similar, non-operational response for negative tests only."""\n\n    __slots__ = GitHubApiResponse.__slots__\n\n    def __init__(self, *_: object, **__: object) -> None:\n        raise TypeError("TestGitHubApiResponse can only be created by the test factory")\n\n    def __setattr__(self, _name: str, _value: object) -> None:\n        raise AttributeError("TestGitHubApiResponse is immutable")\n\n\nclass VerifiedGitHubGovernanceSource:\n''',
)
replace_once(
    transport_path,
    "_RESPONSE_CAPABILITIES: weakref.WeakSet[GitHubApiResponse] = weakref.WeakSet()\n",
    "",
)
new_transport_boundary = r'''def _assign_response_fields(
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
'''
replace_regex_once(
    transport_path,
    r"def _mint_response\([\s\S]*?\n\ndef _validate_check_annotation_payload",
    new_transport_boundary + "\n\ndef _validate_check_annotation_payload",
)

write(
    "pr_inspector/evidence_adapter.py",
    '''from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._governance_transport import fetch_github_api_response
from .governance import (
    VerifiedGovernanceEvidence,
    verify_github_governance_source,
    verify_governance_record,
)
from .sequence_enforcement import (
    SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
    VerifiedSequenceEnforcement,
    verify_sequence_ci_enforcement,
    verify_sequence_producer_evidence,
)


def _fixture_endpoint_urls(path: Path) -> dict[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    responses = value.get("responses")
    if not isinstance(responses, dict):
        raise ValueError("governance evidence fixture must contain a responses object")
    endpoints: dict[str, str] = {}
    for name, item in responses.items():
        if not isinstance(name, str) or not name or not isinstance(item, dict):
            raise ValueError("governance evidence fixture contains an invalid response entry")
        url = item.get("url")
        if not isinstance(url, str) or not url:
            raise ValueError(f"governance evidence fixture endpoint {name} has no URL")
        endpoints[name] = url
    return endpoints


def _fetch_responses_from_fixture_urls(
    path: Path,
    *,
    token: str | None,
    api_version: str,
) -> dict[str, Any]:
    return {
        name: fetch_github_api_response(
            url,
            token=token,
            api_version=api_version,
        )
        for name, url in _fixture_endpoint_urls(path).items()
    }


def mint_evidence_from_governance_fixture(
    path: Path,
    *,
    repository: str,
    pr_number: int,
    head_sha: str,
    sequence_app_id: int,
    sequence_workflow_path: str,
    sequence_workflow_sha: str,
    sequence_validator_command: str,
    token: str | None = None,
    api_version: str = "2022-11-28",
) -> tuple[VerifiedGovernanceEvidence, VerifiedSequenceEnforcement]:
    """Fetch and verify live evidence for the endpoint set declared by a fixture.

    The file supplies endpoint names and canonical URLs only. Its status codes and payloads
    are untrusted and ignored; every capability is minted by the operational HTTPS fetch
    boundary from the response actually observed during this invocation.
    """

    source = verify_github_governance_source(
        _fetch_responses_from_fixture_urls(
            path,
            token=token,
            api_version=api_version,
        ),
        expected_repository=repository,
        expected_pr_number=pr_number,
        expected_head_sha=head_sha,
    )
    governance = verify_governance_record(
        source,
        expected_repository=repository,
        expected_pr_number=pr_number,
        expected_head_sha=head_sha,
    )
    producer = verify_sequence_producer_evidence(
        governance,
        check_context=SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
        app_id=sequence_app_id,
        workflow_path=sequence_workflow_path,
        workflow_sha=sequence_workflow_sha,
        validator_command=sequence_validator_command,
    )
    sequence = verify_sequence_ci_enforcement(
        governance,
        check_context=SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
        app_id=sequence_app_id,
        producer_evidence=producer,
    )
    return governance, sequence
''',
)

write(
    "tests/governance_test_support.py",
    '''from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pr_inspector._governance_transport as governance_transport
from pr_inspector._governance_transport import fetch_github_api_response

ROOT = Path(__file__).resolve().parents[1]
HEAD = "1" * 40
REPOSITORY = "example/project"
PR_NUMBER = 42
API_VERSION = "2026-03-10"
_CACHED_SEQUENCE_CAPABILITY = None


class _FakeHttpResponse:
    def __init__(self, url: str, payload: object, status: int):
        self._url = url
        self._payload = copy.deepcopy(payload)
        self.status = status
        self.code = status

    def geturl(self) -> str:
        return self._url

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def close(self) -> None:
        pass


def fixture() -> dict[str, Any]:
    return json.loads(
        (ROOT / "fixtures/governance/verified-enforced.json").read_text(
            encoding="utf-8"
        )
    )


def urlopen_for_fixture(value: dict[str, Any] | None = None):
    source = copy.deepcopy(value or fixture())
    by_url = {
        item["url"]: item
        for item in source["responses"].values()
    }

    def fake_urlopen(request, timeout):
        item = by_url[request.full_url]
        return _FakeHttpResponse(
            item.get("response_url", item["url"]),
            item["payload"],
            item["status_code"],
        )

    return fake_urlopen


def _fetch_item(item: dict[str, Any], *, fetched_at: datetime):
    source = {"responses": {"single": copy.deepcopy(item)}}
    with patch.object(
        governance_transport.urllib.request,
        "urlopen",
        urlopen_for_fixture(source),
    ):
        return fetch_github_api_response(
            item["url"],
            token=None,
            api_version=API_VERSION,
            fetched_at=fetched_at,
        )


def responses(
    value: dict[str, Any] | None = None,
    *,
    fetched_at: datetime | None = None,
):
    source = copy.deepcopy(value or fixture())
    observed = fetched_at or datetime.now(timezone.utc)
    return {
        name: _fetch_item(item, fetched_at=observed)
        for name, item in source["responses"].items()
    }


def membership_response(
    reviewer: str = "independent-reviewer",
    *,
    state: str = "active",
    fetched_at: datetime | None = None,
):
    url = (
        "https://api.github.com/orgs/example-org/teams/security-reviewers/"
        f"memberships/{reviewer}"
    )
    return _fetch_item(
        {
            "url": url,
            "status_code": 200,
            "payload": {"state": state, "role": "member", "url": url},
        },
        fetched_at=fetched_at or datetime.now(timezone.utc),
    )


def sequence_capability():
    global _CACHED_SEQUENCE_CAPABILITY
    if _CACHED_SEQUENCE_CAPABILITY is not None:
        return _CACHED_SEQUENCE_CAPABILITY
    from pr_inspector.governance import (
        verify_github_governance_source,
        verify_governance_record,
    )
    from pr_inspector.sequence_enforcement import (
        SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
        verify_sequence_ci_enforcement,
        verify_sequence_producer_evidence,
    )

    value = fixture()
    value["responses"]["checks"]["payload"]["check_runs"][0]["name"] = (
        SEQUENCE_ENFORCEMENT_CHECK_CONTEXT
    )
    required = value["responses"]["branch_protection"]["payload"][
        "required_status_checks"
    ]
    required["checks"][0]["context"] = SEQUENCE_ENFORCEMENT_CHECK_CONTEXT
    required["contexts"] = [SEQUENCE_ENFORCEMENT_CHECK_CONTEXT]
    source = verify_github_governance_source(
        responses(value),
        expected_repository=REPOSITORY,
        expected_pr_number=PR_NUMBER,
        expected_head_sha=HEAD,
    )
    governance = verify_governance_record(
        source,
        expected_repository=REPOSITORY,
        expected_pr_number=PR_NUMBER,
        expected_head_sha=HEAD,
    )
    producer = verify_sequence_producer_evidence(
        governance,
        check_context=SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
        app_id=15368,
        workflow_path=".github/workflows/validate-rereview-sequence.yml",
        workflow_sha="2" * 40,
        validator_command="python scripts/validate_rereview_sequence.py sequence.json --review EVENT=review",
    )
    _CACHED_SEQUENCE_CAPABILITY = verify_sequence_ci_enforcement(
        governance,
        check_context=SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
        app_id=15368,
        producer_evidence=producer,
    )
    return _CACHED_SEQUENCE_CAPABILITY
''',
)

candidate_path = "tests/test_candidate_v1_11.py"
replace_once(
    candidate_path,
    '''from pr_inspector._governance_transport import (\n    GitHubApiResponse,\n    _mint_response,\n    fetch_github_api_response,\n)\n''',
    '''from pr_inspector._governance_transport import (\n    GitHubApiResponse,\n    _mint_response,\n    fetch_github_api_response,\n    is_verified_github_api_response,\n)\n''',
)
replace_regex_once(
    candidate_path,
    r"def _fetch_inspector_responses\([\s\S]*?\n    return repository_response, commit_response\n",
    '''def _fetch_response(\n    url: str,\n    payload: object,\n    *,\n    status: int = 200,\n    response_url: str | None = None,\n):\n    def fake_urlopen(request, timeout):\n        assert request.full_url == url\n        return _FakeHttpResponse(response_url or url, payload, status)\n\n    with pytest.MonkeyPatch.context() as patch:\n        patch.setattr(\n            _governance_transport.urllib.request,\n            "urlopen",\n            fake_urlopen,\n        )\n        return fetch_github_api_response(\n            url,\n            token=None,\n            api_version=API_VERSION,\n        )\n\n\ndef _fetch_inspector_responses(\n    *,\n    repository_payload=None,\n    commit_payload=None,\n    repository_status: int = 200,\n    commit_status: int = 200,\n    repository_response_url: str | None = None,\n    commit_response_url: str | None = None,\n):\n    default_repository, default_commit = _inspector_payloads()\n    repository_payload = repository_payload or default_repository\n    commit_payload = commit_payload or default_commit\n    repository_url = f"https://api.github.com/repos/{INSPECTOR_REPOSITORY}"\n    commit_url = f"{repository_url}/commits/{INSPECTOR_COMMIT}"\n    return (\n        _fetch_response(\n            repository_url,\n            repository_payload,\n            status=repository_status,\n            response_url=repository_response_url,\n        ),\n        _fetch_response(\n            commit_url,\n            commit_payload,\n            status=commit_status,\n            response_url=commit_response_url,\n        ),\n    )\n''',
)
replace_regex_once(
    candidate_path,
    r"def _target_identity\(\):[\s\S]*?\n\ndef _live_head\(head_sha: str\):[\s\S]*?\n    \)\n",
    '''def _target_identity():\n    url = f"https://api.github.com/repos/{REPOSITORY}"\n    response = _fetch_response(\n        url,\n        {\n            "id": REPOSITORY_ID,\n            "full_name": REPOSITORY,\n            "url": url,\n            "html_url": f"https://github.com/{REPOSITORY}",\n        },\n    )\n    return candidate.verify_target_identity_response(\n        response,\n        expected_repository=REPOSITORY,\n    )\n\n\ndef _live_head(head_sha: str):\n    url = f"https://api.github.com/repos/{REPOSITORY}/pulls/{PR_NUMBER}"\n    response = _fetch_response(url, _pr_payload(head_sha))\n    return candidate.verify_live_pr_head_response(\n        response,\n        target_repository=REPOSITORY,\n        target_repository_id=REPOSITORY_ID,\n        pull_request=PR_NUMBER,\n    )\n''',
)
insert_before_plain = '''def test_test_factory_cannot_mint_operational_receipt():\n    repository_payload, _ = _inspector_payloads()\n    repository_url = f"https://api.github.com/repos/{INSPECTOR_REPOSITORY}"\n    with pytest.raises(TypeError, match="transport_origin"):\n        _mint_response(\n            request_url=repository_url,\n            response_url=repository_url,\n            status_code=200,\n            fetched_at=datetime.now(timezone.utc),\n            payload=repository_payload,\n            transport_origin="github_https",\n        )\n\n    forged = _mint_response(\n        request_url=repository_url,\n        response_url=repository_url,\n        status_code=200,\n        fetched_at=datetime.now(timezone.utc),\n        payload=repository_payload,\n    )\n    assert not is_verified_github_api_response(forged)\n    _, genuine_commit = _fetch_inspector_responses()\n    with pytest.raises(ProvenanceError, match="sealed verifier-created"):\n        verify_github_commit_payload(\n            forged,\n            genuine_commit,\n            expected_commit_sha=INSPECTOR_COMMIT,\n        )\n\n\n'''
replace_once(
    candidate_path,
    "def test_plain_mappings_and_direct_commit_construction_cannot_mint_evidence():\n",
    insert_before_plain + "def test_plain_mappings_and_direct_commit_construction_cannot_mint_evidence():\n",
)
replace_regex_once(
    candidate_path,
    r"    repository_url = f\"https://api.github.com/repos/\{INSPECTOR_REPOSITORY\}\"\n    commit_url = f\"\{repository_url\}/commits/\{INSPECTOR_COMMIT\}\"\n    wrong_origin_repository = _mint_response\([\s\S]*?\n    with pytest.raises\(ProvenanceError, match=\"sealed verifier-created\"\):\n        verify_github_commit_payload\(\n            _copy_response\(good_repository\),\n            good_commit,\n            expected_commit_sha=INSPECTOR_COMMIT,\n        \)\n",
    '''    repository_url = f"https://api.github.com/repos/{INSPECTOR_REPOSITORY}"\n    test_factory_repository = _mint_response(\n        request_url=repository_url,\n        response_url=repository_url,\n        status_code=200,\n        fetched_at=datetime.now(timezone.utc),\n        payload=repository_payload,\n    )\n    good_repository, good_commit = _fetch_inspector_responses()\n    with pytest.raises(ProvenanceError, match="sealed verifier-created"):\n        verify_github_commit_payload(\n            test_factory_repository,\n            good_commit,\n            expected_commit_sha=INSPECTOR_COMMIT,\n        )\n\n    _, redirected_commit = _fetch_inspector_responses(\n        commit_response_url=repository_url,\n    )\n    assert is_verified_github_api_response(redirected_commit)\n    with pytest.raises(ProvenanceError, match="response URL"):\n        verify_github_commit_payload(\n            good_repository,\n            redirected_commit,\n            expected_commit_sha=INSPECTOR_COMMIT,\n        )\n\n    copied = _copy_response(good_repository)\n    assert not is_verified_github_api_response(copied)\n    with pytest.raises(ProvenanceError, match="sealed verifier-created"):\n        verify_github_commit_payload(\n            copied,\n            good_commit,\n            expected_commit_sha=INSPECTOR_COMMIT,\n        )\n\n    class ResponseSubclass(GitHubApiResponse):\n        pass\n\n    subclassed = object.__new__(ResponseSubclass)\n    for name in GitHubApiResponse.__slots__:\n        if name != "__weakref__":\n            object.__setattr__(subclassed, name, getattr(good_repository, name))\n    assert not is_verified_github_api_response(subclassed)\n    with pytest.raises(ProvenanceError, match="sealed verifier-created"):\n        verify_github_commit_payload(\n            subclassed,\n            good_commit,\n            expected_commit_sha=INSPECTOR_COMMIT,\n        )\n''',
)
replace_once(
    candidate_path,
    '''    bad_status_repository, good_commit = _fetch_inspector_responses(\n        repository_status=404,\n    )\n    with pytest.raises(ProvenanceError, match="did not succeed"):\n''',
    '''    bad_status_repository, good_commit = _fetch_inspector_responses(\n        repository_status=404,\n    )\n    assert is_verified_github_api_response(bad_status_repository)\n    with pytest.raises(ProvenanceError, match="did not succeed"):\n''',
)

post_path = "tests/test_v1_11_post_activation_closure.py"
replace_once(post_path, "from datetime import datetime, timezone\n", "")
replace_once(
    post_path,
    "from pathlib import Path\n",
    "from pathlib import Path\nfrom unittest.mock import patch\n",
)
replace_once(
    post_path,
    '''from pr_inspector._governance_transport import (\n    GovernanceEvidenceError,\n    _mint_response,\n    github_response_payload,\n)\n''',
    '''import pr_inspector._governance_transport as governance_transport\nfrom pr_inspector._governance_transport import (\n    GovernanceEvidenceError,\n    fetch_github_api_response,\n    github_response_payload,\n)\n''',
)
replace_regex_once(
    post_path,
    r"def _annotation_response\(payload: object\):[\s\S]*?\n    \)\n",
    '''class _FakeAnnotationResponse:\n    def __init__(self, url: str, payload: object):\n        self._url = url\n        self._payload = payload\n        self.status = 200\n\n    def geturl(self) -> str:\n        return self._url\n\n    def read(self) -> bytes:\n        return json.dumps(self._payload).encode("utf-8")\n\n    def close(self) -> None:\n        pass\n\n\ndef _annotation_response(payload: object):\n    url = "https://api.github.com/repos/o/r/check-runs/7/annotations?per_page=100"\n\n    def fake_urlopen(request, timeout):\n        assert request.full_url == url\n        return _FakeAnnotationResponse(url, payload)\n\n    with patch.object(\n        governance_transport.urllib.request,\n        "urlopen",\n        fake_urlopen,\n    ):\n        return fetch_github_api_response(\n            url,\n            token=None,\n            api_version="2026-03-10",\n        )\n''',
)

personal_path = "tests/test_personal_minimum_security_profile.py"
replace_once(personal_path, "import json\n", "import json\nimport sys\n\nimport pytest\n")
replace_once(
    personal_path,
    "from tests.governance_test_support import fixture, responses\n",
    "from tests.governance_test_support import fixture, responses, urlopen_for_fixture\n",
)
replace_regex_once(
    personal_path,
    r"def test_manifest_validation_cli_replays_opaque_evidence_from_raw_receipts\([\s\S]*\Z",
    '''def _validation_cli_argv(tmp_path: Path, fixture_path: Path, command: str) -> list[str]:\n    return [\n        "validate_review_v2.py",\n        str(tmp_path),\n        "--target-repository",\n        REPOSITORY,\n        "--pr-number",\n        str(PR_NUMBER),\n        "--reviewed-head-sha",\n        HEAD,\n        "--governance-fixture",\n        str(fixture_path),\n        "--sequence-workflow-sha",\n        "2" * 40,\n        "--sequence-validator-command",\n        command,\n    ]\n\n\ndef test_manifest_validation_cli_fetches_live_evidence_for_fixture_urls(\n    tmp_path,\n    monkeypatch,\n    capsys,\n):\n    from pr_inspector import _governance_transport\n    from scripts import validate_review_v2\n\n    value = package()\n    package_path = tmp_path / "review-package.json"\n    package_bytes = write_package(package_path, value)\n    capability = verified_sequence()\n    write_review_artifacts(\n        value,\n        tmp_path,\n        review_package_bytes=package_bytes,\n        sequence_enforcement=capability,\n    )\n\n    raw = governance_fixture(check_context=SEQUENCE_CONTEXT)\n    fixture_path = tmp_path / "governance-responses.json"\n    fixture_path.write_text(json.dumps(raw), encoding="utf-8")\n    monkeypatch.setattr(\n        _governance_transport.urllib.request,\n        "urlopen",\n        urlopen_for_fixture(raw),\n    )\n    monkeypatch.setattr(\n        sys,\n        "argv",\n        _validation_cli_argv(\n            tmp_path,\n            fixture_path,\n            "python scripts/validate_rereview_sequence.py sequence.json --review EVENT=review",\n        ),\n    )\n\n    assert validate_review_v2.main() == 0\n    assert "OK: review package" in capsys.readouterr().out\n\n\ndef test_manifest_validation_cli_rejects_wrong_sequence_command(\n    tmp_path,\n    monkeypatch,\n):\n    from pr_inspector import _governance_transport\n    from scripts import validate_review_v2\n\n    value = package()\n    package_path = tmp_path / "review-package.json"\n    package_bytes = write_package(package_path, value)\n    capability = verified_sequence()\n    write_review_artifacts(\n        value,\n        tmp_path,\n        review_package_bytes=package_bytes,\n        sequence_enforcement=capability,\n    )\n\n    raw = governance_fixture(check_context=SEQUENCE_CONTEXT)\n    fixture_path = tmp_path / "governance-responses.json"\n    fixture_path.write_text(json.dumps(raw), encoding="utf-8")\n    monkeypatch.setattr(\n        _governance_transport.urllib.request,\n        "urlopen",\n        urlopen_for_fixture(raw),\n    )\n    monkeypatch.setattr(\n        sys,\n        "argv",\n        _validation_cli_argv(tmp_path, fixture_path, "python -m pytest"),\n    )\n\n    with pytest.raises(ValueError, match="sequence validator"):\n        validate_review_v2.main()\n''',
)

write(
    "scripts/validate_review_v2.py",
    '''#!/usr/bin/env python3
from pathlib import Path
import argparse
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pr_inspector.validation_v2 import validate_directory
from pr_inspector.evidence_adapter import mint_evidence_from_governance_fixture
from pr_inspector.review_provenance import trust_policy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("review_directory", type=Path)
    parser.add_argument("--package-only", action="store_true")
    parser.add_argument("--target-repository")
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--reviewed-head-sha")
    parser.add_argument("--governance-fixture", type=Path)
    parser.add_argument("--sequence-app-id", type=int, default=15368)
    parser.add_argument("--sequence-workflow-path", default=".github/workflows/validate-rereview-sequence.yml")
    parser.add_argument("--sequence-workflow-sha")
    parser.add_argument("--sequence-validator-command", default="python scripts/validate_rereview_sequence.py SEQUENCE.json --review EVENT=REVIEW_DIRECTORY")
    parser.add_argument("--github-token-env", default="GITHUB_TOKEN")
    args = parser.parse_args()
    governance_evidence = None
    sequence_enforcement = None
    if args.governance_fixture is not None:
        if not (args.target_repository and args.pr_number and args.reviewed_head_sha and args.sequence_workflow_sha):
            print("ERROR: --governance-fixture requires --target-repository, --pr-number, --reviewed-head-sha, and --sequence-workflow-sha")
            return 1
        governance_evidence, sequence_enforcement = mint_evidence_from_governance_fixture(
            args.governance_fixture,
            repository=args.target_repository,
            pr_number=args.pr_number,
            head_sha=args.reviewed_head_sha,
            sequence_app_id=args.sequence_app_id,
            sequence_workflow_path=args.sequence_workflow_path,
            sequence_workflow_sha=args.sequence_workflow_sha,
            sequence_validator_command=args.sequence_validator_command,
            token=os.environ.get(args.github_token_env),
            api_version=trust_policy()["github_api_version"],
        )
    diagnostics = validate_directory(
        args.review_directory,
        compare_rendered=not args.package_only,
        governance_evidence=governance_evidence,
        sequence_enforcement=sequence_enforcement,
    )
    if diagnostics:
        for item in diagnostics:
            print("ERROR:", item.line())
        return 1
    print("OK: review package is schema-valid, semantically valid, and artifact-consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
)
replace_once(
    "scripts/render_review_v2.py",
    '''            sequence_workflow_sha=args.sequence_workflow_sha,\n            sequence_validator_command=args.sequence_validator_command,\n        )\n''',
    '''            sequence_workflow_sha=args.sequence_workflow_sha,\n            sequence_validator_command=args.sequence_validator_command,\n            token=os.environ.get(args.github_token_env),\n            api_version=api_version,\n        )\n''',
)

closure_path = "tests/test_repository_closure.py"
replace_once(closure_path, "import hashlib\n", "import ast\nimport hashlib\n")
closure_test = r'''


def test_operational_github_receipt_factory_is_closure_bound():
    transport_path = ROOT / "pr_inspector/_governance_transport.py"
    source = transport_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    top_level_functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "_mint_operational_response" not in top_level_functions
    assert "_build_operational_response_boundary" in top_level_functions
    assert "_mint_response" in top_level_functions

    test_factory = top_level_functions["_mint_response"]
    argument_names = {
        argument.arg
        for argument in (
            list(test_factory.args.posonlyargs)
            + list(test_factory.args.args)
            + list(test_factory.args.kwonlyargs)
        )
    }
    assert "transport_origin" not in argument_names
    assert "object.__new__(GitHubApiResponse)" not in ast.unparse(test_factory)

    assigned_names = {
        target.id
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (
            node.targets if isinstance(node, ast.Assign) else [node.target]
        )
        if isinstance(target, ast.Name)
    }
    assert "_RESPONSE_CAPABILITIES" not in assigned_names
    assert "fetch_github_api_response, is_verified_github_api_response" in source

    for directory in (ROOT / "pr_inspector", ROOT / "scripts"):
        for path in directory.glob("*.py"):
            if path == transport_path:
                continue
            candidate_tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(candidate_tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.endswith("_governance_transport"):
                        assert all(alias.name != "_mint_response" for alias in node.names), path
'''
value = read(closure_path)
if "def test_operational_github_receipt_factory_is_closure_bound" in value:
    raise RuntimeError("closure test already exists")
write(closure_path, value.rstrip() + closure_test + "\n")

replace_once(
    "CHANGELOG.md",
    "- Sealed Inspector repository and commit provenance behind operational GitHub HTTPS response capabilities; plain mappings and copied response fields cannot mint reusable Minimal-review authority.\n",
    "- Sealed Inspector repository and commit provenance behind operational GitHub HTTPS response capabilities; plain mappings and copied response fields cannot mint reusable Minimal-review authority.\n- Closed PRF-002-R1 by moving operational response minting and its registry into the production fetch closure, fixing the test factory to a separate non-operational class, and making governance fixtures supply URL plans for live HTTPS fetches rather than authoritative payloads.\n",
)
write(
    "docs/PRF-002_INSPECTOR_COMMIT_PROVENANCE.md",
    '''# PRF-002 — Inspector Commit Provenance

Status: `implemented_pending_rereview`

The Inspector repository and commit verifier accepts only exact, registry-backed `GitHubApiResponse` capabilities produced by the operational GitHub HTTPS adapter. The registry and operational mint are enclosed inside the production fetch boundary; no module-level helper can register a response or select the `github_https` origin.

The compatibility `_mint_response` test factory creates a separate `TestGitHubApiResponse`, fixes its origin to `test_factory`, and never touches the operational registry. Governance fixture files now supply endpoint names and URLs only; their payloads and status fields are ignored while the adapter performs live fetches.

Plain mappings, copied JSON, manually reconstructed response objects, response subclasses, test-factory responses, copied capability fields, and reconstructed `VerifiedInspectorCommit` objects cannot mint reusable Minimal-review authority. Unsuccessful and redirected HTTPS observations remain sealed negative receipts but fail the canonical status and URL requirements.

The bounded repair preserves the existing `VerifiedMinimalReviewReference` seal, source-artifact revalidation, same-Head Minimal reuse, mandatory genuine refresh after Head drift, and fail-closed Candidate output tombstones.

This document does not claim independent review, approval, merge authorization, repository-hosted enforcement, or merge readiness. A fresh independent PR Inspector review and separate exact-bound enforcement evidence remain required.
''',
)

for directory in (ROOT / "pr_inspector", ROOT / "scripts"):
    for path in directory.glob("*.py"):
        if path.name in {"_governance_transport.py", "_apply_prf_002_r1.py"}:
            continue
        text = path.read_text(encoding="utf-8")
        if "_mint_response" in text:
            raise RuntimeError(f"production code still references _mint_response: {path}")

candidate_text = read(candidate_path)
if candidate_text.count("_mint_response(") != 3:
    raise RuntimeError("candidate tests should contain exactly three negative factory calls")
if 'transport_origin="github_https"' not in candidate_text:
    raise RuntimeError("missing explicit adversarial operational-origin factory test")

print("PRF-002-R1 patch applied")
