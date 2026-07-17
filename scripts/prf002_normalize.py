from pathlib import Path


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[:start] + replacement + text[end:]


def normalize_candidate_tests() -> None:
    path = Path("tests/test_candidate_v1_11.py")
    text = path.read_text(encoding="utf-8")

    copy_block = '''def _copy_response(response: GitHubApiResponse) -> GitHubApiResponse:
    copied = object.__new__(GitHubApiResponse)
    for name in GitHubApiResponse.__slots__:
        if name == "__weakref__":
            continue
        object.__setattr__(copied, name, getattr(response, name))
    return copied


'''
    text = replace_between(
        text,
        "def _copy_response(",
        "def _replace_exact(",
        copy_block,
    )

    tests_block = '''def test_plain_mappings_and_direct_commit_construction_cannot_mint_evidence():
    repository_payload, commit_payload = _inspector_payloads()
    with pytest.raises(ProvenanceError, match="sealed verifier-created"):
        verify_github_commit_payload(
            repository_payload,
            commit_payload,
            expected_commit_sha=INSPECTOR_COMMIT,
        )
    with pytest.raises(TypeError, match="sealed operational"):
        VerifiedInspectorCommit()


def test_operational_https_responses_mint_commit_and_minimal_reference(
    tmp_path,
    monkeypatch,
):
    repository_response, commit_response = _fetch_inspector_responses()
    inspector = verify_github_commit_payload(
        repository_response,
        commit_response,
        expected_commit_sha=INSPECTOR_COMMIT,
    )
    assert is_verified_inspector_commit(inspector)
    completion = _completion(tmp_path, monkeypatch, HEAD)
    reference = candidate.minimal_reference_from_official_completion(
        completion,
        target_identity=_target_identity(),
        inspector_commit=inspector,
    )
    assert reference.inspector_commit_sha == INSPECTOR_COMMIT


@pytest.mark.parametrize(
    ("payload_kind", "field", "value", "message"),
    (
        ("repository", "id", 999, "repository id"),
        (
            "repository",
            "url",
            "https://api.github.com/repos/attacker/fake",
            "repository API URL",
        ),
        (
            "repository",
            "html_url",
            "https://github.com/attacker/fake",
            "repository HTML URL",
        ),
        ("commit", "sha", "9" * 40, "commit SHA"),
        (
            "commit",
            "url",
            "https://api.github.com/repos/attacker/fake/commits/" + "3" * 40,
            "commit API URL",
        ),
        (
            "commit",
            "html_url",
            "https://github.com/attacker/fake/commit/" + "3" * 40,
            "commit HTML URL",
        ),
    ),
)
def test_forged_operational_payload_fields_are_rejected(
    payload_kind,
    field,
    value,
    message,
):
    repository_payload, commit_payload = _inspector_payloads()
    target = repository_payload if payload_kind == "repository" else commit_payload
    target[field] = value
    repository_response, commit_response = _fetch_inspector_responses(
        repository_payload=repository_payload,
        commit_payload=commit_payload,
    )
    with pytest.raises(ProvenanceError, match=message):
        verify_github_commit_payload(
            repository_response,
            commit_response,
            expected_commit_sha=INSPECTOR_COMMIT,
        )


def test_arbitrary_expected_commit_requires_matching_official_endpoint_response():
    repository_response, commit_response = _fetch_inspector_responses()
    with pytest.raises(ProvenanceError, match="request URL"):
        verify_github_commit_payload(
            repository_response,
            commit_response,
            expected_commit_sha="9" * 40,
        )


def test_wrong_status_origin_response_url_and_copied_receipts_are_rejected():
    repository_payload, commit_payload = _inspector_payloads()
    bad_status_repository, good_commit = _fetch_inspector_responses(
        repository_status=404,
    )
    with pytest.raises(ProvenanceError, match="did not succeed"):
        verify_github_commit_payload(
            bad_status_repository,
            good_commit,
            expected_commit_sha=INSPECTOR_COMMIT,
        )

    repository_url = f"https://api.github.com/repos/{INSPECTOR_REPOSITORY}"
    commit_url = f"{repository_url}/commits/{INSPECTOR_COMMIT}"
    wrong_origin_repository = _mint_response(
        request_url=repository_url,
        response_url=repository_url,
        status_code=200,
        fetched_at=datetime.now(timezone.utc),
        payload=repository_payload,
        transport_origin="test_factory",
    )
    good_repository, good_commit = _fetch_inspector_responses()
    with pytest.raises(ProvenanceError, match="operational GitHub HTTPS"):
        verify_github_commit_payload(
            wrong_origin_repository,
            good_commit,
            expected_commit_sha=INSPECTOR_COMMIT,
        )

    redirected_commit = _mint_response(
        request_url=commit_url,
        response_url=repository_url,
        status_code=200,
        fetched_at=datetime.now(timezone.utc),
        payload=commit_payload,
        transport_origin="github_https",
    )
    with pytest.raises(ProvenanceError, match="response URL"):
        verify_github_commit_payload(
            good_repository,
            redirected_commit,
            expected_commit_sha=INSPECTOR_COMMIT,
        )

    with pytest.raises(ProvenanceError, match="sealed verifier-created"):
        verify_github_commit_payload(
            _copy_response(good_repository),
            good_commit,
            expected_commit_sha=INSPECTOR_COMMIT,
        )


def test_reconstructed_commit_capability_cannot_mint_minimal_reference(
    tmp_path,
    monkeypatch,
):
    genuine = _inspector_commit()
    forged = object.__new__(VerifiedInspectorCommit)
    for name in VerifiedInspectorCommit.__slots__:
        if name == "__weakref__":
            continue
        object.__setattr__(forged, name, getattr(genuine, name))
    assert not is_verified_inspector_commit(forged)
    completion = _completion(tmp_path, monkeypatch, HEAD)
    with pytest.raises(ValueError, match="verified Inspector commit identity"):
        candidate.minimal_reference_from_official_completion(
            completion,
            target_identity=_target_identity(),
            inspector_commit=forged,
        )


'''
    text = replace_between(
        text,
        "def test_plain_mappings_and_direct_commit_construction_cannot_mint_evidence",
        "def _reconstruct(reference",
        tests_block,
    )
    path.write_text(text, encoding="utf-8", newline="")


def normalize_behavioral_tests() -> None:
    path = Path("tests/test_behavioral_rule_coverage.py")
    text = path.read_text(encoding="utf-8")
    helper_block = '''class _InspectorHttpResponse:
    def __init__(self, url: str, payload: object, status: int = 200):
        self._url = url
        self._payload = payload
        self.status = status

    def geturl(self) -> str:
        return self._url

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def close(self) -> None:
        pass


def _github_responses(
    commit_sha: str,
    *,
    repository_payload: dict | None = None,
    commit_payload: dict | None = None,
):
    default_repository, default_commit = _github_payloads(commit_sha)
    repository_payload = repository_payload or default_repository
    commit_payload = commit_payload or default_commit
    repository_url = "https://api.github.com/repos/rezahh107/PR-Inspector"
    commit_url = f"{repository_url}/commits/{commit_sha}"
    responses = {
        repository_url: _InspectorHttpResponse(
            repository_url,
            repository_payload,
        ),
        commit_url: _InspectorHttpResponse(commit_url, commit_payload),
    }

    def fake_urlopen(request, timeout):
        return responses[request.full_url]

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            _governance_transport.urllib.request,
            "urlopen",
            fake_urlopen,
        )
        repository_response = fetch_github_api_response(
            repository_url,
            token=None,
            api_version="2026-03-10",
        )
        commit_response = fetch_github_api_response(
            commit_url,
            token=None,
            api_version="2026-03-10",
        )
    return repository_response, commit_response


'''
    text = replace_between(
        text,
        "class _InspectorHttpResponse:",
        "def verified_sequence(",
        helper_block,
    )
    path.write_text(text, encoding="utf-8", newline="")


if __name__ == "__main__":
    normalize_candidate_tests()
    normalize_behavioral_tests()
