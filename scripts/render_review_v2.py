#!/usr/bin/env python3
"""Render a clearly non-authoritative ReviewDraft preview.

The historical raw review-package official-completion interface was removed in
v1.12.0. Official initial publication requires a CanonicalReviewPackage minted by
the in-process assembler. Persisted artifacts cannot reconstruct completion
authority; re-verification requires the original genuine VerifiedReviewCompletion.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pr_inspector.verified_review import (
    ReviewAssemblyError,
    parse_review_draft,
    render_unverified_preview,
)


def _bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render a non-authoritative DECLARATION preview from a v1.12 ReviewDraft. "
            "This command cannot create official owner output, a Gate decision, or a Receipt."
        )
    )
    parser.add_argument("draft", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional preview JSON path. Stdout is used when omitted.",
    )
    args = parser.parse_args()

    try:
        raw = json.loads(args.draft.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            raw = dict(raw)
            raw.pop("inspection_profile", None)
        draft = parse_review_draft(raw)
        preview = render_unverified_preview(draft)
        rendered = _bytes(preview)
        if args.output is None:
            sys.stdout.buffer.write(rendered)
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(rendered)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ReviewAssemblyError) as exc:
        print(
            "ReviewDraft preview was not produced. No official completion or owner output occurred.",
            file=sys.stderr,
        )
        print(f"ERROR: PRI-PREVIEW-001 /review-draft: {exc}", file=sys.stderr)
        return 1

    print(
        "OK: non-authoritative DECLARATION preview rendered; official_completion=false.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
