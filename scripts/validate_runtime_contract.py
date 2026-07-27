#!/usr/bin/env python3
"""Maintenance smoke check for the retrieval-only startup boundary."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pr_inspector.functional_runtime import RUNTIME_BOOTSTRAP_INPUTS, connector_startup
reads = []
def read(path):
    reads.append(path)
    return (ROOT / path).read_text(encoding="utf-8")
result = connector_startup(read)
if tuple(reads) != RUNTIME_BOOTSTRAP_INPUTS or not result.intake_response.strip():
    raise SystemExit("ERROR: retrieval-only startup boundary drift")
print(f"OK: retrieval-only startup {result.protocol_version}; reads={','.join(reads)}")
