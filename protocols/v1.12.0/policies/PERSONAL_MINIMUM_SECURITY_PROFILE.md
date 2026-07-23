# Personal Single-Operator Correctness Profile

v1.12 is optimized for a personal, single-operator repository. Correctness controls are mandatory; security hardening is optional.

The runtime derives `sequence_ci_enforced` from collected required checks bound to the exact reviewed Head. A required check must be completed successfully and its `tested_sha` must equal the collected Head. Missing, unresolved, failed, or cross-Head checks block technical Green.

Repository settings, branch protection, dedicated GitHub Apps, signing, HMAC, key management, merge queues, and CODEOWNERS are optional hardening. They are not required for the Minimal profile and do not block an otherwise correct technical Green decision.

Strict inspection may additionally require verified governance evidence. Governance evidence cannot rewrite technical findings, required-check results, technical status, or repair scope.
