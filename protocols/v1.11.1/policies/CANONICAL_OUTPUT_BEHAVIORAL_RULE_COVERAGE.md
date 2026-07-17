# Canonical Output Behavioral Rule Coverage — v1.11.1

| rule_id | invariant | executable carrier | mutation expectation |
|---|---|---|---|
| CO-1111-001 | one official projection authority | `tests/test_v1_11_1_output_authority.py` | Candidate projection fails closed |
| CO-1111-002 | one official prompt renderer | `tests/test_v1_11_1_output_authority.py` | PR #22 placeholder rejected |
| CO-1111-003 | one verified owner-delivery authority | `tests/test_v1_11_1_output_authority.py` | manual/Candidate composition rejected |
| CO-1111-004 | prompt semantic completeness | `tests/test_v1_11_1_output_authority.py` | hash-valid generic prompt rejected |
| CO-1111-005 | profile commands remain separate | `tests/test_v1_11_1_output_authority.py` | embedded profile commands rejected |
| CO-1111-006 | compatibility exports are allowlisted | `tests/test_v1_11_1_output_authority.py` | PR #27-style re-export rejected |

These checks supplement byte equality, manifest integrity, and the active Behavioral Rule Coverage matrix.
