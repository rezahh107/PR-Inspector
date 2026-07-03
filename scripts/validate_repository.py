#!/usr/bin/env python3
"""Validate PR Inspector repository structure without external packages."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "BOOTSTRAP.md",
    "AGENTS.md",
    "CURRENT_VERSION",
    "protocol-manifest.yaml",
    "pipeline/REVIEW_PIPELINE.md",
    "policies/SECURITY_AND_TRUST.md",
    "policies/DECISION_GATES.md",
    "policies/OWNER_OUTPUT_UX.md",
    "templates/OWNER_DECISION_CARD.fa.md",
    "templates/TECHNICAL_HANDOFF.en.md",
    "prompts/INTAKE_RESPONSE.fa.md",
    ".github/copilot-instructions.md",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def manifest_value(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*([^\n#]+)", text)
    return match.group(1).strip() if match else None


def manifest_load_order(text: str) -> list[str]:
    block = re.search(r"(?m)^load_order:\s*\n(?P<body>(?:  - .*(?:\n|$))+)", text)
    if not block:
        return []
    return [line.split("-", 1)[1].strip() for line in block.group("body").splitlines()]


def main() -> int:
    errors: list[str] = []

    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            errors.append(f"missing required file: {rel}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    current = read("CURRENT_VERSION").strip()
    manifest = read("protocol-manifest.yaml")
    active = manifest_value(manifest, "active_version")
    contract_path = manifest_value(manifest, "canonical_contract")

    if active != current:
        errors.append(f"CURRENT_VERSION={current!r} but active_version={active!r}")

    if not contract_path or not (ROOT / contract_path).is_file():
        errors.append(f"canonical contract missing: {contract_path!r}")
    else:
        contract = read(contract_path)
        if f"**Version:** {current.removeprefix('v')}" not in contract:
            errors.append("contract Version header does not match CURRENT_VERSION")

    load_order = manifest_load_order(manifest)
    if not load_order:
        errors.append("manifest load_order is missing or empty")
    for rel in load_order:
        if not (ROOT / rel).is_file():
            errors.append(f"load_order path does not exist: {rel}")

    bootstrap = read("BOOTSTRAP.md")
    for token in ("CURRENT_VERSION", "protocol-manifest.yaml", "INTAKE_RESPONSE.fa.md"):
        if token not in bootstrap:
            errors.append(f"BOOTSTRAP.md does not reference {token}")

    intake = read("prompts/INTAKE_RESPONSE.fa.md")
    for phrase in ("آدرس ریپوی پروژه", "شماره یا لینک PR"):
        if phrase not in intake:
            errors.append(f"intake response missing phrase: {phrase}")

    owner = read("templates/OWNER_DECISION_CARD.fa.md")
    for heading in ("وضعیت:", "این تغییر چه کاری می‌کند؟", "چه چیزی ممکن است خراب شود؟", "چه چیزی بررسی شده؟", "چه چیزی هنوز مشخص نیست؟", "الان چه کار کنیم؟", "آیا متخصص لازم است؟"):
        if heading not in owner:
            errors.append(f"owner template missing heading: {heading}")

    handoff = read("templates/TECHNICAL_HANDOFF.en.md")
    for heading in ("Review Identity", "Decision Header", "Capability Manifest", "Checks and Evidence Records", "Owner-Card Consistency Map"):
        if heading not in handoff:
            errors.append(f"technical handoff missing heading: {heading}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"OK: PR Inspector {current} repository structure is valid.")
    print(f"OK: {len(load_order)} canonical files are in deterministic load order.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
