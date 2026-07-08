from pathlib import Path
import re

import yaml

import pr_inspector


ROOT = Path(__file__).resolve().parents[1]


def test_package_dunder_version_matches_pyproject_version():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r"^version\s*=\s*[\"\']([^\"\']+)[\"\']\s*$", text, re.MULTILINE)
    assert match is not None, "Could not find a valid 'version' field in pyproject.toml"
    assert pr_inspector.__version__ == match.group(1)


def test_readme_active_protocol_matches_current_version_and_manifest():
    current = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
    manifest = yaml.safe_load((ROOT / "protocol-manifest.yaml").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert manifest["active_version"] == current
    assert f"## Active protocol\n\n`{current}`" in readme
    assert f"[`protocols/{current}/`](protocols/{current}/)" in readme
    assert f"[`release-locks/{current}.sha256`](release-locks/{current}.sha256)" in readme
