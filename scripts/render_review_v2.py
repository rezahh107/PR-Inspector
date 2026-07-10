#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pr_inspector.derived_outputs import PROMPT_NAME, build_review_artifacts
from pr_inspector.validation_v2 import validate_package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    package = json.loads(args.package.read_text(encoding="utf-8"))
    diagnostics = validate_package(package)
    if diagnostics:
        for item in diagnostics:
            print("ERROR:", item.line())
        return 1
    args.output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = build_review_artifacts(package)
    for name, text in artifacts.items():
        (args.output_dir / name).write_text(text, encoding="utf-8", newline="\n")
    stale_prompt = args.output_dir / PROMPT_NAME
    if PROMPT_NAME not in artifacts and stale_prompt.exists():
        stale_prompt.unlink()
    print("OK: rendered deterministic review artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
