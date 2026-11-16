# Test results

The Phase 14 suite initially exposed a real arithmetic mismatch: the legacy displayed count 5,066 differs from the 5,066.5 tie-aware expected labels underlying the stored recall rate. The test was corrected to assert the actual evaluator definition; no evaluator or baseline result changed.

Final runs:

| Command | Result |
| --- | --- |
| `python -m unittest discover -s experiments/PHASE14_RECOVERABILITY_GAP -p 'test_audit.py' -v` | 7 tests passed; covers E1 object, cap, bounds, category reconciliation, graph counterexample, metrics, provenance, and leakage separation. |
| `python -m unittest discover -s experiments/PHASE13_RECOVERY -p 'test_phase13.py' -v` | 3 tests passed. |
| `python -m unittest discover -s experiments/PHASE10_FRAGMENT_RECONSTRUCTION -p 'test_reconstruction.py' -v` | 4 tests passed. |

No Phase 14 candidate algorithm exists, so candidate-specific merge, decision-time provenance, and changed-group end-to-end tests could not be run. The synthetic graph counterexample checks the logic behind the upper-bound correction; it does not prove a GUIDE recovery opportunity.
