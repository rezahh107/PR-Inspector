from pathlib import Path

import yaml

from pr_inspector.repository import validate_active_release_lock

ROOT = Path(__file__).resolve().parents[1]


def test_active_release_lock_covers_load_order_exactly():
    current = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
    manifest = yaml.safe_load((ROOT / "protocol-manifest.yaml").read_text(encoding="utf-8"))
    assert validate_active_release_lock(ROOT, current, manifest, manifest["load_order"]) == []


def test_active_release_lock_rejects_missing_canonical_path(tmp_path):
    current = "v9.9.9"
    lock_rel = f"release-locks/{current}.sha256"
    lock_path = tmp_path / lock_rel
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text("0" * 64 + "  protocols/v9.9.9/one.md\n", encoding="utf-8")
    manifest = {"release_lock": lock_rel}
    diagnostics = validate_active_release_lock(
        tmp_path,
        current,
        manifest,
        ["protocols/v9.9.9/one.md", "protocols/v9.9.9/two.md"],
    )
    assert [item.code for item in diagnostics] == ["PRI-LOCK-003"]
    assert "missing canonical paths: protocols/v9.9.9/two.md" in diagnostics[0].message


def test_active_release_lock_rejects_wrong_declared_version(tmp_path):
    diagnostics = validate_active_release_lock(
        tmp_path,
        "v9.9.9",
        {"release_lock": "release-locks/v9.9.8.sha256"},
        [],
    )
    assert [item.code for item in diagnostics] == ["PRI-LOCK-002"]
