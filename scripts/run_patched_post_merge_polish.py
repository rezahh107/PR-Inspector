from __future__ import annotations

import base64
import zlib
from pathlib import Path

GENERATOR = Path(__file__).with_name("generate_post_merge_polish.py")
wrapper = GENERATOR.read_text(encoding="utf-8")
prefix = "_PAYLOAD = r'''"
if prefix not in wrapper:
    raise SystemExit("generator payload prefix missing")
payload = wrapper.split(prefix, 1)[1].split("'''", 1)[0]
source = zlib.decompress(base64.b85decode(payload.encode("ascii"))).decode("utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global source
    if source.count(old) != 1:
        raise SystemExit(f"{label}: expected one source occurrence, found {source.count(old)}")
    source = source.replace(old, new, 1)


replace_once(
    '''event_schema["allOf"].append({
    "if": {"properties": {"event_type": {"enum": ["merge_authorized", "merged"]}}, "required": ["event_type"]},
    "then": {"required": ["governance_evidence_id"]},
})
''',
    "",
    "semantic governance carrier",
)
replace_once(
    "replacement = needle + '''            else:\\n",
    "replacement = needle + '''            elif event_type == \\\"merge_authorized\\\":\\n",
    "merge authorization scope",
)
replace_once(
    '''test_text = test_text.replace(
    'assert sequence_codes(sequence) == {"PRI-SEQUENCE-001", "PRI-SEQUENCE-008"}',
    'assert sequence_codes(sequence) == {"PRI-GOV-001", "PRI-SEQUENCE-001", "PRI-SEQUENCE-008"}',
)
''',
    "",
    "review short-circuit expectation",
)
replace_once(
    '''# Schema-version-only orphan tests.
replace_text("tests/test_rereview_orphan_acceptance.py", '"schema_version": 2', '"schema_version": 3')
''',
    '''# Existing owner-output tests must assert the new non-authorization wording.
replace_text(
    "tests/test_dual_audience_outputs.py",
    '.endswith("مرج کن.\\\\n")',
    '.endswith("حفاظت ادغام در GitHub جداگانه بررسی شود.\\\\n")',
)

# Schema-version-only orphan tests. Missing governance remains a semantic gate,
# so orphan events still exercise sequence ordering rather than schema shape.
replace_text("tests/test_rereview_orphan_acceptance.py", '"schema_version": 2', '"schema_version": 3')
''',
    "owner and orphan tests",
)

compiled = compile(source, str(GENERATOR), "exec")
namespace = {
    "__name__": "__main__",
    "__file__": str(GENERATOR),
    "__package__": None,
}
exec(compiled, namespace, namespace)
