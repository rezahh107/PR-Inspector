from __future__ import annotations

from typing import Any, Mapping, Sequence

from ._governance_transport import GitHubApiResponse, _payload_or_none


def _combine_bool(values: Sequence[bool | None]) -> bool | None:
    if any(value is True for value in values):
        return True
    if values and all(value is False for value in values):
        return False
    return None


def _combine_int(values: Sequence[int | None]) -> int | None:
    known = [value for value in values if isinstance(value, int)]
    if known:
        return max(known)
    return None


def _ruleset_targets_default_branch(payload: Mapping[str, Any], branch: str) -> bool:
    conditions = payload.get("conditions")
    if not isinstance(conditions, Mapping):
        return True
    ref_name = conditions.get("ref_name")
    if not isinstance(ref_name, Mapping):
        return True
    include = ref_name.get("include")
    exclude = ref_name.get("exclude")
    if not isinstance(include, list) or not all(isinstance(item, str) for item in include):
        return False
    if not isinstance(exclude, list) or not all(isinstance(item, str) for item in exclude):
        return False
    candidates = {"~DEFAULT_BRANCH", branch, f"refs/heads/{branch}"}
    return bool(candidates.intersection(include)) and not bool(
        candidates.intersection(exclude)
    )


def _derive_settings(
    *,
    branch: str,
    protection_response: GitHubApiResponse | None,
    rulesets_response: GitHubApiResponse | None,
    ruleset_details: Mapping[int, GitHubApiResponse],
    limitations: list[str],
) -> dict[str, Any]:
    protection_payload = _payload_or_none(protection_response)
    branch_values: dict[str, Any] = {
        "pull_request_required": None,
        "required_status_checks": None,
        "required_approvals": None,
        "dismiss_stale_approvals": None,
        "code_owner_review_required": None,
        "bypass_actors": None,
        "merge_queue_required": False,
    }
    if isinstance(protection_payload, Mapping):
        reviews = protection_payload.get("required_pull_request_reviews")
        if reviews is None:
            branch_values.update(
                {
                    "pull_request_required": False,
                    "required_approvals": 0,
                    "dismiss_stale_approvals": False,
                    "code_owner_review_required": False,
                }
            )
        elif isinstance(reviews, Mapping):
            count = reviews.get("required_approving_review_count")
            dismiss = reviews.get("dismiss_stale_reviews")
            code_owner = reviews.get("require_code_owner_reviews")
            if isinstance(count, int) and isinstance(dismiss, bool) and isinstance(code_owner, bool):
                branch_values.update(
                    {
                        "pull_request_required": True,
                        "required_approvals": count,
                        "dismiss_stale_approvals": dismiss,
                        "code_owner_review_required": code_owner,
                    }
                )
            else:
                limitations.append("branch protection pull-request review payload is partial")

        required_checks = protection_payload.get("required_status_checks")
        if required_checks is None:
            branch_values["required_status_checks"] = []
        elif isinstance(required_checks, Mapping):
            checks = required_checks.get("checks")
            if isinstance(checks, list):
                normalized: list[dict[str, Any]] = []
                valid = True
                for check in checks:
                    if not isinstance(check, Mapping):
                        valid = False
                        break
                    context = check.get("context")
                    app_id = check.get("app_id")
                    if not isinstance(context, str) or not context or not isinstance(app_id, int) or app_id <= 0:
                        valid = False
                        break
                    normalized.append({"context": context, "app_id": app_id})
                if valid:
                    branch_values["required_status_checks"] = normalized
                else:
                    limitations.append(
                        "required check producer identity is missing or invalid in branch protection"
                    )
            else:
                limitations.append(
                    "required check producer identity is unavailable in branch protection"
                )

        bypass = reviews.get("bypass_pull_request_allowances") if isinstance(reviews, Mapping) else None
        admins = protection_payload.get("enforce_admins")
        if isinstance(bypass, Mapping) and isinstance(admins, Mapping) and isinstance(admins.get("enabled"), bool):
            actors: list[str] = []
            bypass_complete = True
            for kind in ("users", "teams", "apps"):
                values = bypass.get(kind)
                if not isinstance(values, list):
                    bypass_complete = False
                    break
                for item in values:
                    if not isinstance(item, Mapping):
                        bypass_complete = False
                        break
                    identity = item.get("slug") or item.get("login") or item.get("name") or item.get("id")
                    if identity is None:
                        bypass_complete = False
                        break
                    actors.append(f"{kind}:{identity}")
                if not bypass_complete:
                    break
            if bypass_complete:
                if admins.get("enabled") is False:
                    actors.append("repository_admins")
                branch_values["bypass_actors"] = sorted(set(actors))
        if branch_values["bypass_actors"] is None:
            limitations.append("branch-protection bypass actors are unknown")
    else:
        limitations.append("branch protection endpoint is missing, inaccessible, or partial")

    ruleset_values: dict[str, Any] = {
        "pull_request_required": None,
        "required_status_checks": None,
        "required_approvals": None,
        "dismiss_stale_approvals": None,
        "code_owner_review_required": None,
        "bypass_actors": None,
        "merge_queue_required": None,
    }
    rulesets_payload = _payload_or_none(rulesets_response)
    if isinstance(rulesets_payload, list):
        applicable_details: list[Mapping[str, Any]] = []
        ruleset_bypass: list[str] = []
        details_complete = True
        for summary in rulesets_payload:
            if not isinstance(summary, Mapping) or summary.get("enforcement") != "active":
                continue
            ruleset_id = summary.get("id")
            detail_response = ruleset_details.get(ruleset_id) if isinstance(ruleset_id, int) else None
            detail_payload = _payload_or_none(detail_response)
            if not isinstance(detail_payload, Mapping):
                details_complete = False
                continue
            if not _ruleset_targets_default_branch(detail_payload, branch):
                continue
            applicable_details.append(detail_payload)
            bypass_actors = detail_payload.get("bypass_actors")
            if not isinstance(bypass_actors, list):
                details_complete = False
                continue
            for actor in bypass_actors:
                if not isinstance(actor, Mapping):
                    details_complete = False
                    continue
                actor_type = actor.get("actor_type")
                actor_id = actor.get("actor_id")
                bypass_mode = actor.get("bypass_mode")
                if not isinstance(actor_type, str) or not isinstance(actor_id, int) or not isinstance(bypass_mode, str):
                    details_complete = False
                    continue
                ruleset_bypass.append(f"{actor_type}:{actor_id}:{bypass_mode}")

        if details_complete:
            ruleset_values["bypass_actors"] = sorted(set(ruleset_bypass))
        else:
            limitations.append("active ruleset detail or bypass actor payload is incomplete")

        pr_values: list[bool] = []
        approval_values: list[int] = []
        stale_values: list[bool] = []
        owner_values: list[bool] = []
        required_checks: list[dict[str, Any]] = []
        checks_complete = True
        merge_queue = False
        for detail in applicable_details:
            rules = detail.get("rules")
            if not isinstance(rules, list):
                details_complete = False
                continue
            for rule in rules:
                if not isinstance(rule, Mapping):
                    details_complete = False
                    continue
                rule_type = rule.get("type")
                parameters = rule.get("parameters")
                if rule_type == "pull_request" and isinstance(parameters, Mapping):
                    count = parameters.get("required_approving_review_count")
                    stale = parameters.get("dismiss_stale_reviews_on_push")
                    owner = parameters.get("require_code_owner_review")
                    if isinstance(count, int) and isinstance(stale, bool) and isinstance(owner, bool):
                        pr_values.append(True)
                        approval_values.append(count)
                        stale_values.append(stale)
                        owner_values.append(owner)
                    else:
                        details_complete = False
                elif rule_type == "required_status_checks" and isinstance(parameters, Mapping):
                    configured = parameters.get("required_status_checks")
                    if not isinstance(configured, list):
                        checks_complete = False
                        continue
                    for item in configured:
                        if not isinstance(item, Mapping):
                            checks_complete = False
                            continue
                        context = item.get("context")
                        app_id = item.get("integration_id")
                        if not isinstance(context, str) or not context or not isinstance(app_id, int) or app_id <= 0:
                            checks_complete = False
                            continue
                        required_checks.append({"context": context, "app_id": app_id})
                elif rule_type == "merge_queue":
                    merge_queue = True

        if details_complete:
            ruleset_values["pull_request_required"] = bool(pr_values)
            ruleset_values["required_approvals"] = max(approval_values, default=0)
            ruleset_values["dismiss_stale_approvals"] = all(stale_values) if stale_values else False
            ruleset_values["code_owner_review_required"] = all(owner_values) if owner_values else False
            ruleset_values["merge_queue_required"] = merge_queue
        if checks_complete and details_complete:
            ruleset_values["required_status_checks"] = required_checks
        elif applicable_details:
            limitations.append("required check producer identity is unknown in active ruleset")
    else:
        limitations.append("rulesets endpoint is missing, inaccessible, or partial")

    protection_url = protection_response.response_url if protection_response else None
    ruleset_urls = [rulesets_response.response_url] if rulesets_response else []
    ruleset_urls.extend(item.response_url for item in ruleset_details.values())

    branch_bypass = branch_values["bypass_actors"]
    ruleset_bypass = ruleset_values["bypass_actors"]
    if branch_bypass is None or ruleset_bypass is None:
        bypass_actors: list[str] | None = None
    else:
        bypass_actors = sorted(set(branch_bypass + ruleset_bypass))

    branch_checks = branch_values["required_status_checks"]
    ruleset_checks = ruleset_values["required_status_checks"]
    if branch_checks is None or ruleset_checks is None:
        required_status_checks: list[dict[str, Any]] | None = None
    else:
        by_identity = {
            (item["context"], item["app_id"]): item
            for item in branch_checks + ruleset_checks
        }
        required_status_checks = [by_identity[key] for key in sorted(by_identity)]

    values = {
        "pull_request_required": _combine_bool(
            [branch_values["pull_request_required"], ruleset_values["pull_request_required"]]
        ),
        "required_status_checks": required_status_checks,
        "required_approvals": _combine_int(
            [branch_values["required_approvals"], ruleset_values["required_approvals"]]
        ),
        "dismiss_stale_approvals": _combine_bool(
            [branch_values["dismiss_stale_approvals"], ruleset_values["dismiss_stale_approvals"]]
        ),
        "code_owner_review_required": _combine_bool(
            [branch_values["code_owner_review_required"], ruleset_values["code_owner_review_required"]]
        ),
        "bypass_actors": bypass_actors,
        "merge_queue_required": _combine_bool(
            [branch_values["merge_queue_required"], ruleset_values["merge_queue_required"]]
        ),
    }
    setting_urls = sorted(
        {url for url in [protection_url, *ruleset_urls] if isinstance(url, str)}
    )
    return {
        key: {"value": value, "evidence": setting_urls}
        for key, value in values.items()
    }


def derive_enforcement_status(record: Mapping[str, Any]) -> str:
    limitations = record.get("limitations")
    if isinstance(limitations, list) and limitations:
        return "insufficient_evidence"
    values = {
        "pull_request_required": record.get("pull_request_required", {}).get("value"),
        "required_status_checks": record.get("required_status_checks", {}).get("value"),
        "required_approvals": record.get("required_approvals", {}).get("value"),
        "dismiss_stale_approvals": record.get("dismiss_stale_approvals", {}).get("value"),
        "code_owner_review_required": record.get("code_owner_review_required", {}).get("value"),
        "bypass_actors": record.get("bypass_actors", {}).get("value"),
    }
    if any(value is None for value in values.values()):
        return "insufficient_evidence"
    checks = values["required_status_checks"]
    checks_bound = isinstance(checks, list) and bool(checks) and all(
        isinstance(item, Mapping)
        and isinstance(item.get("context"), str)
        and isinstance(item.get("app_id"), int)
        and item.get("app_id", 0) > 0
        for item in checks
    )
    protections = [
        values["pull_request_required"] is True,
        checks_bound,
        isinstance(values["required_approvals"], int)
        and values["required_approvals"] >= 1,
        values["dismiss_stale_approvals"] is True,
        values["code_owner_review_required"] is True,
    ]
    no_bypass = values["bypass_actors"] == []
    if all(protections) and no_bypass:
        return "verified_enforced"
    if not any(protections) and no_bypass:
        return "verified_not_enforced"
    return "partially_enforced"

