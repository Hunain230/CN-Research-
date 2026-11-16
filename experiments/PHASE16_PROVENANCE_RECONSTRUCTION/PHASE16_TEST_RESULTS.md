# Phase 16 test results

The final v4 command `python -m unittest discover -s experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4/tests -p 'test_*.py' -v` ran **six tests, all passed**. It checked model schema isolation, template split assignment, evidence cutoff, four-distinct-source witness logic, duplicate witness suppression, host/account abstention, 100-alert cap, source/config/evaluator freeze hashes, locked metric arithmetic and safety gates, fresh queue namespace, and all generated data hashes.

One initial v3 synthetic test had an incorrect expected assertion for duplicate sources; it failed, was corrected without changing frozen predictor/evaluator code, and the v3 suite then passed five tests. One initial v4 test had misplaced metric assertions causing a `NameError`; it was corrected, and the final six-test suite passed. These test-code errors did not alter any locked prediction or metric.
