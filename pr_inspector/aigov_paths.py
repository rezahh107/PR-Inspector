from __future__ import annotations

import re


_WINDOWS_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")


def normalize_repository_relative_path(value: str) -> str:
    """Return one deterministic repository-relative path representation.

    Both slash styles are normalized before boundary checks. Traversal, POSIX
    absolute paths, Windows drive paths, UNC paths, and empty/root-only paths
    are rejected. Repository-relative glob tokens are preserved.
    """

    if not isinstance(value, str):
        raise TypeError("repository path must be a string")

    normalized = value.replace("\\", "/")
    if normalized.startswith("//"):
        raise ValueError("UNC paths are forbidden")
    if normalized.startswith("/"):
        raise ValueError("POSIX absolute paths are forbidden")
    if _WINDOWS_DRIVE_PREFIX.match(normalized):
        raise ValueError("Windows drive paths are forbidden")

    parts: list[str] = []
    for part in normalized.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            raise ValueError("parent traversal segments are forbidden")
        parts.append(part)

    if not parts:
        raise ValueError("empty or root-only repository paths are forbidden")
    return "/".join(parts)
