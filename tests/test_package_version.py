from pathlib import Path
import re

import pr_inspector


ROOT = Path(__file__).resolve().parents[1]


def test_package_dunder_version_matches_pyproject_version():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']\s*$', text, re.MULTILINE)
    assert match is not None, "Could not find a valid 'version' field in pyproject.toml"
    assert pr_inspector.__version__ == match.group(1)
