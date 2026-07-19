#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pr_inspector.planning_governance import validate_planning_repository
from pr_inspector.repository import validate_repository


def main() -> int:
    diagnostics = validate_repository(ROOT)
    diagnostics.extend(validate_planning_repository(ROOT))
    diagnostics = sorted(set(diagnostics))
    if diagnostics:
        for item in diagnostics:
            print("ERROR:", item.line())
        return 1
    print("OK: versioned repository and governed planning validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
