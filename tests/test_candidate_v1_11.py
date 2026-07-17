import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from pr_inspector import candidate_v1_11 as candidate
from pr_inspector._governance_transport import fetch_github_api_response


class FakeHTTPResponse:
    def __init__(self, url, payload, status=200):
        self._url = url
        self._payload = json.dumps(payload).encode("utf-8")
        self.status = status
        self.code = status

    def geturl(self):
        return self._url

    def read(self):
        return self._payload

    def close(self):
        pass


def response(url, payload, status=200):
    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(url, payload, status)):
        return fetch_github_api_response(
            url,
            token=None,
            api_version="2022-11-28",
            fetched_at=datetime.now(timezone.utc),
        )


def test_candidate_supported_exports_are_pre_package_only():
    forbidden = {
        "project_decision",
        "render_candidate_next_action_prompt",
        "render_candidate_owner_result",
        "render_candidate_owner_card",
        "render_candidate_technical_handoff",
        "build_candidate_review_artifacts",
        "verify_candidate_review_artifact_bytes",
        "verify_minimal_review_artifact_bytes",
        "build_candidate_owner_delivery_artifacts",
        "candidate_owner_delivery_stdout",
    }
    assert forbidden.isdisjoint(candidate.__all__)
    assert {
        "parse_intake",
        "verify_target_identity_response",
        "verify_live_pr_head_response",
        "verify_review_surface_inventory_responses",
        "reconcile_bot_reviews",
        "bind_minimal_review_completion",
    }.issubset(candidate.__all__)


@pytest.mark.parametrize(
    "name",
    [
        "project_decision",
        "render_candidate_next_action_prompt",
        "render_candidate_owner_result",
        "render_candidate_owner_card",
        "render_candidate_technical_handoff",
        "build_candidate_review_artifacts",
        "verify_candidate_review_artifact_bytes",
        "verify_minimal_review_artifact_bytes",
        "build_candidate_owner_delivery_artifacts",
        "candidate_owner_delivery_stdout",
    ],
)
def test_candidate_output_tombstones_fail_closed(name):
    with pytest.raises(candidate.CandidateOutputMigrationError, match="no longer an output authority"):
        getattr(candidate, name)(object())


def test_candidate_module_contains_no_historical_placeholder_or_broad_runtime_reexport():
    source = open(candidate.__file__, encoding="utf-8").read()
    assert "Repair independently validated technical findings before rereview" not in source
    assert "for _name in dir(" not in source
    assert "for name in tuple(dir(" not in source


def test_intake_preserves_default_minimal_and_explicit_strict():
    url = "https://github.com/o/r/pull/7"
    assert candidate.parse_intake(url)["inspection_profile"] == "minimal"
    assert candidate.parse_intake(f"حداقلی\n{url}")["inspection_profile"] == "minimal"
    strict = candidate.parse_intake(f"سخت گیرانه\n{url}")
    assert strict["inspection_profile"] == "strict"
    assert strict["target"] == {
        "repository": "o/r",
        "pull_request": 7,
        "url": url,
    }
    assert candidate.parse_intake("سخت گیرانه")["missing"] == ["pull_request_url"]


def test_profile_commands_delegate_to_official_bytes_and_remain_two_lines():
    assert candidate.render_owner_profile_commands("minimal") == candidate.PROFILE_COMMANDS_BYTES
    assert candidate.render_owner_profile_commands("strict") == candidate.PROFILE_COMMANDS_BYTES
    assert candidate.validate_owner_profile_commands(candidate.PROFILE_COMMANDS_BYTES) == []
    assert len(candidate.PROFILE_COMMANDS_BYTES.decode("utf-8").splitlines()) == 2


def test_verified_target_and_live_head_helpers_remain_fail_closed():
    repo = "o/r"
    repo_id = 100
    pr = 7
    head = "a" * 40
    base = f"https://api.github.com/repos/{repo}"
    identity = candidate.verify_target_identity_response(
        response(
            base,
            {
                "full_name": repo,
                "id": repo_id,
                "url": base,
                "html_url": f"https://github.com/{repo}",
            },
        ),
        expected_repository=repo,
    )
    live = candidate.verify_live_pr_head_response(
        response(
            f"{base}/pulls/{pr}",
            {
                "number": pr,
                "base": {"repo": {"full_name": repo, "id": repo_id}},
                "head": {"sha": head, "repo": {"full_name": repo, "id": repo_id}},
            },
        ),
        target_repository=repo,
        target_repository_id=repo_id,
        pull_request=pr,
    )
    assert identity.repository_id == repo_id
    assert live.head_sha == head


def test_review_surface_and_reconciliation_helpers_remain_operational():
    repo = "o/r"
    repo_id = 100
    pr = 7
    head = "a" * 40
    base = f"https://api.github.com/repos/{repo}"
    identity = candidate.verify_target_identity_response(
        response(base, {"full_name": repo, "id": repo_id, "url": base, "html_url": f"https://github.com/{repo}"}),
        expected_repository=repo,
    )
    responses = {
        "review_comments": response(
            f"{base}/pulls/{pr}/comments?per_page=100",
            [{"id": 1, "node_id": "RC1", "user": {"login": "bot", "type": "Bot"}}],
        ),
        "review_threads": response(f"{base}/pulls/{pr}/threads?per_page=100", []),
        "reviews": response(f"{base}/pulls/{pr}/reviews?per_page=100", []),
        "issue_comments": response(f"{base}/issues/{pr}/comments?per_page=100", []),
        "check_runs": response(f"{base}/commits/{head}/check-runs?per_page=100", {"check_runs": []}),
        "check_summaries": response(f"{base}/commits/{head}/status", {"statuses": []}),
    }
    inventory = candidate.verify_review_surface_inventory_responses(
        responses,
        target_repository=repo,
        target_identity=identity,
        pull_request=pr,
        reviewed_head_sha=head,
    )
    assert inventory.complete is True
    assert inventory.sources[0]["github_source_key"] == "review_comments:RC1"

    source = dict(inventory.sources[0])
    source["inspected"] = True
    result = candidate.reconcile_bot_reviews(
        [source],
        [
            {
                "suggestion_id": "S1",
                "source_id": source["source_id"],
                "triage_decision": "accepted",
                "linked_finding_ids": ["PRF-001"],
            }
        ],
        [{"finding_id": "PRF-001", "severity": "HIGH", "blocking": True}],
    )
    assert result["collection_status"] == "COMPLETE"
    assert result["valid_blocking_finding_ids"] == ["PRF-001"]


def test_unverified_minimal_reference_cannot_unlock_strict_reuse():
    result = candidate.verify_base_review_reference(
        object(),
        "a" * 40,
        target_repository="o/r",
        target_repository_id=100,
        pull_request=7,
    )
    assert result == {
        "status": "INVALID",
        "reason": "verified_minimal_review_required",
    }
