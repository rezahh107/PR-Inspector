#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pr_inspector.derived_outputs import write_review_artifacts
from pr_inspector.validation_v2 import validate_package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    package_bytes = args.package.read_bytes()
    package = json.loads(package_bytes.decode("utf-8"))
    diagnostics = validate_package(package)
    if diagnostics:
        for item in diagnostics:
            print("ERROR:", item.line())
        return 1

    write_review_artifacts(
        package,
        args.output_dir,
        review_package_bytes=package_bytes,
    )
    print(
        "OK: rendered canonical projection and deterministic "
        "review artifacts from final file bytes."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
