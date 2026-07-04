#!/usr/bin/env python3
"""Compatibility wrapper for active repository validation."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pr_inspector.repository import validate_repository


def main() -> int:
    diagnostics = validate_repository(ROOT)
    if diagnostics:
        for item in diagnostics:
            print("ERROR:", item.line())
        return 1
    print("OK: active repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
