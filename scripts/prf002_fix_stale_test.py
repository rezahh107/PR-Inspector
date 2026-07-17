from pathlib import Path

path = Path("tests/test_behavioral_rule_coverage.py")
text = path.read_text(encoding="utf-8")
old = '''    repository_payload, commit_payload = _github_payloads(commit_sha)
    inspector_commit = verify_github_commit_payload(
        repository_payload,
        commit_payload,
        expected_commit_sha=commit_sha,
    )
    with pytest.raises(ProvenanceError, match="only a CURRENT review"):
'''
new = '''    repository_response, commit_response = _github_responses(commit_sha)
    inspector_commit = verify_github_commit_payload(
        repository_response,
        commit_response,
        expected_commit_sha=commit_sha,
    )
    with pytest.raises(ProvenanceError, match="only a CURRENT review"):
'''
if text.count(old) != 1:
    raise RuntimeError("expected one stale-review provenance fixture block")
path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")
