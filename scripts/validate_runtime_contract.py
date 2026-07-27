#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pr_inspector.functional_runtime import FunctionalBootstrapError, validate_runtime_contract
try:
    value=validate_runtime_contract(ROOT)
except FunctionalBootstrapError as exc:
    print(f"ERROR: {exc}")
    raise SystemExit(1)
print(f"OK: functional runtime {value.protocol_version} {value.functional_runtime_sha256}")
