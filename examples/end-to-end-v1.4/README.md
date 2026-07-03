# End-to-End Example — v1.4.0

This example is generated from the synthetic canonical package at [`../../fixtures/golden-green/review-package.json`](../../fixtures/golden-green/review-package.json).

It is a **synthetic protocol fixture**, not evidence from a real repository or Elementor/EDIS project.

## Reproduce

```bash
python scripts/validate_review_v2.py fixtures/golden-green --package-only
python scripts/render_review_v2.py fixtures/golden-green/review-package.json --output-dir examples/end-to-end-v1.4
python scripts/validate_review_v2.py examples/end-to-end-v1.4
```

The generated files demonstrate the required order and synchronization of the Persian Owner Decision Card and English Technical Handoff.
