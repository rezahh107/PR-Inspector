from __future__ import annotations

import builtins
from pathlib import Path

from pr_inspector.functional_runtime import (
    ACTIVE_VERSION,
    CONTRACT_PATH,
    INTAKE_PATH,
    RUNTIME_BOOTSTRAP_INPUTS,
    connector_startup,
)
from pr_inspector.verified_review import ProtocolContext

ROOT = Path(__file__).resolve().parents[1]


def _content_reader(files: dict[str, str], reads: list[str]):
    def read(path: str) -> str:
        reads.append(path)
        if path not in files:
            raise AssertionError(f"unexpected connector read: {path}")
        return files[path]
    return read


def _startup_files() -> dict[str, str]:
    return {
        "CURRENT_VERSION": (ROOT / "CURRENT_VERSION").read_text(),
        CONTRACT_PATH: (ROOT / CONTRACT_PATH).read_text(),
        INTAKE_PATH: (ROOT / INTAKE_PATH).read_text(),
    }


def test_connector_only_startup_returns_intake_and_can_begin_inspection(monkeypatch):
    reads: list[str] = []
    forbidden = lambda *a, **k: (_ for _ in ()).throw(AssertionError("local execution forbidden"))
    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    monkeypatch.setattr("os.system", forbidden)
    result = connector_startup(_content_reader(_startup_files(), reads))
    assert result.protocol_version == ACTIVE_VERSION
    assert result.intake_response.strip()
    assert result.contract["pipeline_stages"][0]["stage_id"] == "intake"
    assert tuple(reads) == RUNTIME_BOOTSTRAP_INPUTS


def test_startup_never_invokes_old_validators_or_recursive_scan(monkeypatch):
    import pr_inspector.functional_runtime as runtime

    def forbidden(*args, **kwargs):
        raise AssertionError("validator or repository scan invoked")

    # Former entrypoints are intentionally absent; future compatibility aliases
    # must still be caught if somebody wires one back into startup.
    monkeypatch.setattr(runtime, "validate_runtime_contract", forbidden, raising=False)
    monkeypatch.setattr(runtime, "validate_local_functional_digest", forbidden, raising=False)
    monkeypatch.setattr(Path, "rglob", forbidden)
    monkeypatch.setattr(Path, "glob", forbidden)
    result = connector_startup(_content_reader(_startup_files(), []))
    assert result.intake_response


def test_minimal_read_boundary_excludes_manifest_digest_and_schema_inputs():
    reads: list[str] = []
    result = connector_startup(_content_reader(_startup_files(), reads))
    assert reads == ["CURRENT_VERSION", CONTRACT_PATH, INTAKE_PATH]
    assert all("schema" not in path and "digest" not in path and "release-lock" not in path for path in reads)
    assert "functional_digest_paths" not in result.contract


def test_local_compatibility_entrypoint_uses_same_retrieval_only_flow(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Git or subprocess invoked")
    monkeypatch.setattr("subprocess.run", forbidden)
    context = ProtocolContext.from_repository(ROOT)
    assert context.protocol_version == ACTIVE_VERSION
    assert context.inspector_repository == "rezahh107/PR-Inspector"
