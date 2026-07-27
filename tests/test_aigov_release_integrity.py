from __future__ import annotations

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
EXPECTED_ARCHIVE_SHA256 = "450299a201aea9f75400cbbb4debf3c7dbb64cf49bb90ba27ea93d9826df86a3"
EXPECTED_MANIFEST_SHA256 = "2dfa34847809f72a20d525a91d9d6dc7ec42588da4deb36940c1a5541eb32e03"
EXPECTED_HISTORICAL_LOCK_SHA256 = "b55b767de2bd859af750a69bb901343ae8f4fb3a666264a0b04e5df7f7d985eb"

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
    "bundle-manifest.json": (EXPECTED_MANIFEST_SHA256, 7767, 228),
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _verify_bundle_and_lock(pinned: Path, lock_path: Path) -> None:
    assert {path.name for path in pinned.iterdir() if path.is_file()} == set(EXPECTED_FILES)
    for name, (digest, byte_count, line_count) in EXPECTED_FILES.items():
        raw = (pinned / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest
        assert len(raw) == byte_count
        assert b"\r" not in raw and raw.endswith(b"\n")
        assert len(raw.decode("utf-8").splitlines()) == line_count
    manifest = _load(pinned / "bundle-manifest.json")
    assert manifest["bundle"] == "AIGOV_v2.5.0_active"
    assert manifest["status"] == "active_governing_standard"
    assert manifest["same_context_final_audit"] == "PASS"
    assert manifest["independent_document_audit"] == "NOT_PERFORMED"
    lock = _load(lock_path)
    assert lock["source_archive_sha256"] == EXPECTED_ARCHIVE_SHA256
    assert lock["bundle_manifest_sha256"] == EXPECTED_MANIFEST_SHA256
    assert lock["repository_adoption_status"] == "not_adopted"
    assert lock["runtime_activation"] is False
    assert lock["protocol_support_activation"] is False
    assert lock["receipt_publication_activation"] is False


def test_exact_pinned_bundle_manifest_and_lock_parity():
    _verify_bundle_and_lock(PINNED, LOCK_PATH)


def test_successor_protocol_activates_without_aigov_runtime_or_receipt_activation():
    current = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
    manifest = yaml.safe_load((ROOT / "protocol-manifest.yaml").read_text(encoding="utf-8"))
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'(?ms)^\[project\].*?^version\s*=\s*"([^"]+)"', pyproject)
    lock = _load(LOCK_PATH)
    assert current == "v1.13.0"
    assert manifest["active_version"] == current
    assert manifest["release_lock"] == "release-locks/v1.13.0.sha256"
    assert all("governance/aigov" not in path for path in manifest["load_order"])
    assert version and version.group(1) == "1.13.0"
    assert lock["repository_adoption_status"] == "not_adopted"
    assert lock["runtime_activation"] is False
    assert lock["protocol_support_activation"] is False
    assert lock["receipt_publication_activation"] is False


def test_active_and_historical_protocol_release_locks_remain_byte_valid():
    assert _sha(ROOT / "release-locks/v1.11.1.sha256") == EXPECTED_HISTORICAL_LOCK_SHA256
    for lock_path in sorted((ROOT / "release-locks").glob("v*.sha256")):
        entries = {}
        for number, line in enumerate(lock_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line or line.startswith("#"):
                continue
            separator = line.find("  ")
            assert separator >= 0, f"{lock_path}:{number}: missing double-space separator"
            digest, relative = line[:separator], line[separator + 2:]
            assert re.fullmatch(r"[0-9a-f]{64}", digest)
            assert relative not in entries
            entries[relative] = digest
        assert entries
        for relative, digest in entries.items():
            path = ROOT / relative
            assert path.is_file()
            assert _sha(path) == digest


def test_pinned_documents_are_not_executable_runtime_configuration():
    forbidden = ("governance/aigov", "AIGOV_ADOPTION_LOCK", "AI_AUTHORITY_DETERMINISTIC_GOVERNANCE_SSOT_v2.5.0")
    for base in (ROOT / "pr_inspector", ROOT / "scripts", ROOT / ".github/workflows"):
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".py", ".yml", ".yaml", ".json", ".toml"}:
                text = path.read_text(encoding="utf-8")
                assert all(token not in text for token in forbidden)


@pytest.mark.parametrize("mutation", ["one_byte", "removed_file", "added_file", "false_adoption", "false_runtime"])
def test_integrity_verifier_fails_closed_on_mutation(tmp_path: Path, mutation: str):
    pinned = tmp_path / "v2.5.0"
    shutil.copytree(PINNED, pinned)
    lock_path = tmp_path / "AIGOV_ADOPTION_LOCK.json"
    shutil.copyfile(LOCK_PATH, lock_path)
    if mutation == "one_byte":
        target = pinned / "README.md"
        raw = bytearray(target.read_bytes()); raw[0] ^= 1; target.write_bytes(raw)
    elif mutation == "removed_file":
        (pinned / "README.md").unlink()
    elif mutation == "added_file":
        (pinned / "undeclared.txt").write_text("undeclared\n", encoding="utf-8")
    else:
        lock = _load(lock_path)
        lock["repository_adoption_status" if mutation == "false_adoption" else "runtime_activation"] = "adopted" if mutation == "false_adoption" else True
        lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises((AssertionError, FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError)):
        _verify_bundle_and_lock(pinned, lock_path)
