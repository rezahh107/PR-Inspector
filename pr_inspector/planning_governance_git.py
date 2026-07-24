from __future__ import annotations

from .planning_governance_base import *

def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git failed")
    return result.stdout.strip()


def parse_git_name_status(raw: str) -> tuple[list[str], dict[str, str], list[Diagnostic]]:
    fields = raw.split("\x00")
    if fields and fields[-1] == "":
        fields.pop()
    paths: list[str] = []
    statuses: dict[str, str] = {}
    diagnostics: list[Diagnostic] = []
    index = 0
    while index < len(fields):
        token = fields[index]
        index += 1
        status = token[:1]
        path_count = 2 if status in {"C", "R"} else 1
        if not token or index + path_count > len(fields):
            diagnostics.append(diagnostic("PINS-GIT-STATUS-UNSUPPORTED", "/git/diff", f"malformed name-status record: {token!r}"))
            break
        record_paths = fields[index : index + path_count]
        index += path_count
        if status not in _SUPPORTED_GIT_STATUSES:
            diagnostics.append(diagnostic("PINS-GIT-STATUS-UNSUPPORTED", "/git/diff", f"unsupported Git status {token}"))
        for path in record_paths:
            paths.append(path)
            statuses[path] = token
    return sorted(set(paths)), dict(sorted(statuses.items())), sorted(set(diagnostics))


def validate_git_diff(
    root: Path,
    authoritative_base_sha: str,
    head_sha: str,
) -> tuple[list[Diagnostic], dict[str, Any]]:
    output: list[Diagnostic] = []
    report: dict[str, Any] = {
        "authoritative_base_sha": authoritative_base_sha,
        "head_sha": head_sha,
        "declared_base_sha": None,
        "merge_base_sha": None,
        "actual_changed_paths": [],
        "changed_path_statuses": {},
        "declared_changed_paths": [],
        "status": "invalid",
    }
    try:
        scope = load_json_strict(root / SCOPE_PATH)
        if not isinstance(scope, dict):
            raise ValueError("Scope must be a JSON object")
        committed = scope.get("committed_paths", [])
        deleted = scope.get("deleted_paths", [])
        if not isinstance(committed, list) or not isinstance(deleted, list):
            raise ValueError("Scope committed_paths and deleted_paths must be arrays")
        declared = sorted([*committed, *deleted])
        report["declared_base_sha"] = scope.get("base_sha")
        report["declared_changed_paths"] = declared

        if not _FULL_SHA.fullmatch(authoritative_base_sha):
            output.append(diagnostic("PINS-SCOPE-BASE-MISMATCH", "/git/base", "authoritative PR base must be an exact 40-character SHA"))
        if not _FULL_SHA.fullmatch(head_sha):
            output.append(diagnostic("PINS-SCOPE-DISCLOSURE-MISMATCH", "/git/head", "runtime Head must be an exact 40-character SHA"))
        if scope.get("base_sha") != authoritative_base_sha:
            output.append(diagnostic("PINS-SCOPE-BASE-MISMATCH", "/scope/base_sha", "declared base does not equal authoritative pull-request base"))

        resolved_base = _git(root, "rev-parse", f"{authoritative_base_sha}^{{commit}}")
        resolved_head = _git(root, "rev-parse", f"{head_sha}^{{commit}}")
        checkout = _git(root, "rev-parse", "HEAD")
        if resolved_base != authoritative_base_sha:
            output.append(diagnostic("PINS-SCOPE-BASE-MISMATCH", "/git/base", f"resolved {resolved_base}"))
        if resolved_head != head_sha or checkout != head_sha:
            output.append(diagnostic("PINS-SCOPE-DISCLOSURE-MISMATCH", "/git/head", "runtime Head identity mismatch"))

        merge_base = _git(root, "merge-base", authoritative_base_sha, head_sha)
        report["merge_base_sha"] = merge_base
        if merge_base != authoritative_base_sha:
            output.append(diagnostic("PINS-SCOPE-BASE-MISMATCH", "/git/merge-base", f"authoritative base is not the exact merge base; observed {merge_base}"))
        try:
            _git(root, "merge-base", "--is-ancestor", authoritative_base_sha, head_sha)
        except RuntimeError:
            output.append(diagnostic("PINS-SCOPE-BASE-MISMATCH", "/git/ancestry", "authoritative base is not an ancestor of Head"))

        raw = _git(
            root,
            "diff",
            "--name-status",
            "-z",
            "--find-renames",
            "--find-copies",
            f"{authoritative_base_sha}..{head_sha}",
        )
        actual, statuses, status_diagnostics = parse_git_name_status(raw)
        output += status_diagnostics
    except Exception as exc:
        output.append(diagnostic("PINS-SCOPE-BASE-MISMATCH", "/git", str(exc)))
        return sorted(set(output)), report

    report["actual_changed_paths"] = actual
    report["changed_path_statuses"] = statuses
    for path in actual:
        error = validate_repo_path(path)
        if error:
            output.append(diagnostic("PINS-SCOPE-PATH-INVALID", f"/{path}", error))
    for path in sorted(set(actual) - set(declared)):
        output.append(diagnostic("PINS-SCOPE-UNDECLARED-PATH", f"/{path}", "changed path is not declared"))
    for path in sorted(set(declared) - set(actual)):
        output.append(diagnostic("PINS-SCOPE-DECLARED-PATH-UNCHANGED", f"/{path}", "declared path is unchanged"))
    for path in actual:
        for pattern in scope.get("excluded_paths", []):
            if _pattern_error(pattern) is None and pattern_matches(pattern, path):
                output.append(diagnostic("PINS-SCOPE-FORBIDDEN-PATH", f"/{path}", f"matches {pattern}"))
    if actual != declared:
        output.append(diagnostic("PINS-SCOPE-DISCLOSURE-MISMATCH", "/git/diff", "actual paths differ from declared paths"))
    if not output:
        report["status"] = "valid"
    return sorted(set(output)), report
