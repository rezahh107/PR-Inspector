from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
PINNED = ROOT / "governance/aigov/v2.5.0"
LOCK_PATH = ROOT / "governance/aigov/AIGOV_ADOPTION_LOCK.json"
MANIFEST_PATH = PINNED / "bundle-manifest.json"
EXPECTED_ARCHIVE_SHA256 = "450299a201aea9f75400cbbb4debf3c7dbb64cf49bb90ba27ea93d9826df86a3"
EXPECTED_MANIFEST_SHA256 = "2dfa34847809f72a20d525a91d9d6dc7ec42588da4deb36940c1a5541eb32e03"
EXPECTED_ACTIVE_RELEASE_LOCK_SHA256 = "b55b767de2bd859af750a69bb901343ae8f4fb3a666264a0b04e5df7f7d985eb"

EXPECTED_FILES = {
    "AIGOV_BEHAVIORAL_RULE_COVERAGE_CONTRACT_v1.2.0.fa.md": ("7bfe410a0e6e1db79f2d38719219ea119f0a13601c1ce7f462c8d55bdd3de361", 11277, 333),
    "AIGOV_BEHAVIORAL_RULE_COVERAGE_CONTRACT_v1.2.0_ACTIVATION_RECEIPT.fa.md": ("662d5917ddfd0667fc94e34e57e1e29aeab8e9cae3fc05afa30ecbf4320afc48", 980, 20),
    "AIGOV_v2.5.0_ACTIVATION_RECEIPT.fa.md": ("6ba682831d99cb0973e04a823dae813724c326f181d1be7f31e506c37171ca29", 1010, 20),
    "AIGOV_v2.5.0_ACTIVATION_TRANSFORM_REPORT.fa.md": ("b98b17ec334b78e0d432dbfc4773ac81da205aea5b87c8d4f50aa9ef6c73e295", 1973, 39),
    "AIGOV_v2.5.0_IMPLEMENTATION_REPORT.fa.md": ("044c16280bf0350ba07a8225ec2dbacb9c1b64f9abbb298acc386a1adc3e7ff6", 3407, 88),
    "AIGOV_v2.5.0_INCIDENT_AND_MIGRATION_RECORD.fa.md": ("1bde9b9e17bcd551e8712e3dc93e5cf3f13b7921e279b5c36c0e5b9809f79520", 2052, 46),
    "AIGOV_v2.5.0_SAME_CONTEXT_FINAL_AUDIT.fa.md": ("165f00cb11f9b31cf29ecfd1d4b36138ec5cb9e6fa6356c7ed122a6a84bb110b", 2285, 52),
    "AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.active-release-integrity.md": ("96e1c352ac70427205127b96c906e6a0e011b5985d91259cb699d2f8b74f2e55", 6285, 169),
    "AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.fa.md": ("a8310ca60ba5577256789b5fcc7c5620a3f24af0deafc3587e8a2a60310d4186", 129878, 2500),
    "AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0.projection-parity-matrix.json": ("87c8c9dea5775283e8e2ae0f2410c8c4a669526f643a42233d70ab413046e160", 16598, 341),
    "PERSONAL_AI_OPERATED_REPOSITORY_REVIEW_PROFILE_v1.2.0.fa.md": ("9b7d8cd1f1c1b744b89edb0ada8c882d50cd2aa3d99001e85f88de8c541b44b5", 5554, 144),
    "PERSONAL_AI_OPERATED_REPOSITORY_REVIEW_PROFILE_v1.2.0_ACTIVATION_RECEIPT.fa.md": ("057e59646c0929b4c7f4ad70ab6ab5f2fcddfeb3743e15fe8604fca36cbb8436", 975, 20),
    "PR_INSPECTOR_REVIEW_RECEIPT_PUBLICATION_CONTRACT_v1.2.0.fa.md": ("a49c47cd2c4275c9134c70fbb3f3a15eaf3f7a0b2f6495fa64d076e2d57afd2a", 6819, 195),
    "PR_INSPECTOR_REVIEW_RECEIPT_PUBLICATION_CONTRACT_v1.2.0_ACTIVATION_RECEIPT.fa.md": ("580c80b00d9088b0d1eb31483b747759f3eb4c0f9adee98f616cf822c407f1c8", 989, 20),
    "README.md": ("1a2c62afcaf4a4251dff3f17c52a91bcdd2585db371bd81db9daf9b4c0d5cbf1", 917, 17),
    "bundle-manifest.json": ("2dfa34847809f72a20d525a91d9d6dc7ec42588da4deb36940c1a5541eb32e03", 7767, 228),
}
EXPECTED_ORDER = tuple(EXPECTED_FILES)
MANIFEST_GOVERNED = set(EXPECTED_FILES) - {"README.md", "bundle-manifest.json"}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _verify_text_bytes(path: Path, expected_bytes: int, expected_lines: int) -> None:
    raw = path.read_bytes()
    assert len(raw) == expected_bytes, path.name
    assert b"\r" not in raw, path.name
    assert raw.endswith(b"\n"), path.name
    text = raw.decode("utf-8")
    assert len(text.splitlines()) == expected_lines, path.name


def _verify_bundle_and_lock(pinned: Path, lock_path: Path) -> None:
    actual = {path.name for path in pinned.iterdir() if path.is_file()}
    assert actual == set(EXPECTED_FILES)
    assert all(path.is_file() for path in pinned.iterdir())

    for name, (digest, byte_count, line_count) in EXPECTED_FILES.items():
        path = pinned / name
        assert _sha256(path) == digest, name
        _verify_text_bytes(path, byte_count, line_count)

    assert _sha256(pinned / "bundle-manifest.json") == EXPECTED_MANIFEST_SHA256
    manifest = _load_json(pinned / "bundle-manifest.json")
    assert manifest["bundle"] == "AIGOV_v2.5.0_active"
    assert manifest["status"] == "active_governing_standard"
    assert manifest["version_decision"]["core"] == "2.5.0"
    assert manifest["same_context_final_audit"] == "PASS"
    assert manifest["independent_document_audit"] == "NOT_PERFORMED"
    assert manifest["text_convention"]["newline_sequence"] == "LF"
    assert manifest["text_convention"]["final_newline_required"] is True

    manifest_files = {item["path"]: item for item in manifest["files"]}
    assert set(manifest_files) == MANIFEST_GOVERNED
    for name in MANIFEST_GOVERNED:
        digest, byte_count, line_count = EXPECTED_FILES[name]
        item = manifest_files[name]
        assert item["sha256"] == digest
        assert item["bytes"] == byte_count
        assert item["lines"] == line_count
        assert item["line_count"] == {
            "value": line_count,
            "method": "utf8_logical_lines_splitlines",
            "newline_sequence": "LF",
            "final_newline_present": True,
        }

    lock = _load_json(lock_path)
    assert lock["schema_version"] == 1
    assert lock["standard_id"] == "AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT"
    assert lock["standard_version"] == "2.5.0"
    assert lock["bundle_identity"] == "AIGOV_v2.5.0_active"
    assert lock["bundle_status"] == "active_governing_standard"
    assert lock["pinned_directory"] == "governance/aigov/v2.5.0"
    assert lock["source_archive_filename"] == "AIGOV_v2.5.0_active_bundle(2).zip"
    assert lock["source_archive_sha256"] == EXPECTED_ARCHIVE_SHA256
    assert lock["source_archive_digest_provenance"] == "locally_computed_not_externally_pinned"
    assert lock["bundle_manifest_path"] == "governance/aigov/v2.5.0/bundle-manifest.json"
    assert lock["bundle_manifest_sha256"] == EXPECTED_MANIFEST_SHA256
    assert lock["file_count"] == 16
    assert lock["canonical_rule_count"] == 27
    assert lock["canonical_boundary_count"] == 18
    assert lock["canonical_fixture_count"] == 63
    assert lock["companion_contract_count"] == 4
    assert lock["same_context_final_audit"] == "PASS"
    assert lock["independent_document_audit"] == "NOT_PERFORMED"
    assert lock["external_sidecar_status"] == "not_provided"
    assert lock["repository_adoption_status"] == "not_adopted"
    assert lock["runtime_activation"] is False
    assert lock["protocol_support_activation"] is False
    assert lock["receipt_publication_activation"] is False

    inventory = lock["ordered_file_inventory"]
    assert tuple(item["relative_path"] for item in inventory) == EXPECTED_ORDER
    assert len(inventory) == len(EXPECTED_FILES)
    for item in inventory:
        name = item["relative_path"]
        digest, byte_count, line_count = EXPECTED_FILES[name]
        assert item["repository_relative_path"] == f"governance/aigov/v2.5.0/{name}"
        assert item["sha256"] == digest
        assert item["byte_count"] == byte_count
        assert item["logical_line_count"] == line_count
        assert item["manifest_governed"] is (name in MANIFEST_GOVERNED)
        assert item["line_ending_requirement"] == "LF"
        assert item["final_newline_required"] is True
        if name in MANIFEST_GOVERNED:
            assert item["manifest_declared_byte_count"] == byte_count
            assert item["manifest_declared_logical_line_count"] == line_count
        else:
            assert item["manifest_declared_byte_count"] is None
            assert item["manifest_declared_logical_line_count"] is None


def test_exact_pinned_bundle_manifest_and_lock_parity():
    _verify_bundle_and_lock(PINNED, LOCK_PATH)


def test_successor_protocol_activates_without_aigov_runtime_or_receipt_activation():
    current = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
    protocol_manifest = yaml.safe_load((ROOT / "protocol-manifest.yaml").read_text(encoding="utf-8"))
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version_match = re.search(r'(?ms)^\[project\].*?^version\s*=\s*"([^"]+)"', pyproject)
    lock = _load_json(LOCK_PATH)

    assert current == "v1.12.0"
    assert protocol_manifest["active_version"] == "v1.12.0"
    assert protocol_manifest["operation_mode"] == "read_only_review"
    assert protocol_manifest["release_lock"] == "release-locks/v1.12.0.sha256"
    assert all("governance/aigov" not in path for path in protocol_manifest["load_order"])
    assert "protocols/v1.12.0/policies/VERIFIED_REVIEW_AUTHORITY.md" in protocol_manifest["load_order"]
    assert version_match and version_match.group(1) == "1.12.0"
    assert lock["repository_adoption_status"] == "not_adopted"
    assert lock["runtime_activation"] is False
    assert lock["protocol_support_activation"] is False
    assert lock["receipt_publication_activation"] is False


def test_active_and_historical_protocol_release_locks_remain_byte_valid():
    assert _sha256(ROOT / "release-locks/v1.11.1.sha256") == EXPECTED_ACTIVE_RELEASE_LOCK_SHA256
    for lock_path in sorted((ROOT / "release-locks").glob("v*.sha256")):
        entries: dict[str, str] = {}
        for number, line in enumerate(lock_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line or line.startswith("#"):
                continue
            separator = line.find("  ")
            assert separator >= 0, f"Malformed entry in release-lock file {lock_path} at line {number}: missing double-space separator"
            digest = line[:separator]
            relative = line[separator + 2 :]
            assert re.fullmatch(r"[0-9a-f]{64}", digest), f"Malformed entry in release-lock file {lock_path} at line {number}: digest must be a 64-character hex string, got '{digest}'"
            assert relative not in entries, f"Duplicate entry in release-lock file {lock_path} at line {number}: path '{relative}' already defined"
            entries[relative] = (number, digest)
        assert entries, f"Invalid release-lock file {lock_path}: file is empty or contains no valid entries"
        for relative, (number, digest) in entries.items():
            path = ROOT / relative
            assert path.is_file(), f"Invalid entry in release-lock file {lock_path} at line {number}: referenced path '{relative}' does not exist or is not a file"
            actual_hash = _sha256(path)
            assert actual_hash == digest, f"Integrity mismatch in release-lock file {lock_path} at line {number}: expected digest '{digest}' for '{relative}', but got '{actual_hash}'"


def test_pinned_documents_are_not_executable_runtime_configuration():
    executable_roots = (ROOT / "pr_inspector", ROOT / "scripts", ROOT / ".github/workflows")
    assert all(path.exists() for path in executable_roots)
    forbidden = ("governance/aigov", "AIGOV_ADOPTION_LOCK", "AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0")
    for base in executable_roots:
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".py", ".yml", ".yaml", ".json", ".toml"}:
                continue
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                assert token not in text, f"runtime reference in {path.relative_to(ROOT)}: {token}"


def _copy_fixture(tmp_path: Path) -> tuple[Path, Path]:
    pinned = tmp_path / "v2.5.0"
    shutil.copytree(PINNED, pinned)
    lock_path = tmp_path / "AIGOV_ADOPTION_LOCK.json"
    shutil.copyfile(LOCK_PATH, lock_path)
    return pinned, lock_path


def _rewrite_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


@pytest.mark.parametrize(
    "mutation",
    (
        "one_byte",
        "newline_conversion",
        "removed_file",
        "added_file",
        "changed_manifest_value",
        "changed_lock_digest",
        "false_adoption_claim",
        "false_runtime_activation",
        "false_protocol_support_activation",
        "false_receipt_publication_activation",
        "false_independent_audit_claim",
    ),
)
def test_integrity_verifier_fails_closed_on_mutation(tmp_path: Path, mutation: str):
    pinned, lock_path = _copy_fixture(tmp_path)
    target = pinned / "README.md"
    if mutation == "one_byte":
        raw = bytearray(target.read_bytes())
        raw[0] ^= 1
        target.write_bytes(raw)
    elif mutation == "newline_conversion":
        target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n"))
    elif mutation == "removed_file":
        target.unlink()
    elif mutation == "added_file":
        (pinned / "undeclared.txt").write_text("undeclared\n", encoding="utf-8")
    elif mutation == "changed_manifest_value":
        value = _load_json(pinned / "bundle-manifest.json")
        value["status"] = "candidate"
        _rewrite_json(pinned / "bundle-manifest.json", value)
    else:
        lock = _load_json(lock_path)
        if mutation == "changed_lock_digest":
            lock["ordered_file_inventory"][0]["sha256"] = "0" * 64
        elif mutation == "false_adoption_claim":
            lock["repository_adoption_status"] = "adopted"
        elif mutation == "false_runtime_activation":
            lock["runtime_activation"] = True
        elif mutation == "false_protocol_support_activation":
            lock["protocol_support_activation"] = True
        elif mutation == "false_receipt_publication_activation":
            lock["receipt_publication_activation"] = True
        elif mutation == "false_independent_audit_claim":
            lock["independent_document_audit"] = "PASS"
        _rewrite_json(lock_path, lock)

    with pytest.raises((AssertionError, FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError)):
        _verify_bundle_and_lock(pinned, lock_path)
