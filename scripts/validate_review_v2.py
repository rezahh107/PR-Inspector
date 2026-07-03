#!/usr/bin/env python3
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pr_inspector.validation_v2 import validate_directory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("review_directory", type=Path)
    parser.add_argument("--package-only", action="store_true")
    args = parser.parse_args()
    diagnostics = validate_directory(args.review_directory, compare_rendered=not args.package_only)
    if diagnostics:
        for item in diagnostics:
            print("ERROR:", item.line())
        return 1
    print("OK: review package is schema-valid, semantically valid, and artifact-consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
