#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pr_inspector.validation import validate_package
from pr_inspector.render import render_owner, render_handoff


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
    (args.output_dir / "OWNER_DECISION_CARD.fa.md").write_text(render_owner(package), encoding="utf-8", newline="\n")
    (args.output_dir / "TECHNICAL_HANDOFF.en.md").write_text(render_handoff(package), encoding="utf-8", newline="\n")
    print("OK: rendered deterministic review artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
