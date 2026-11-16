# Test results

`python -m unittest discover -s experiments/PHASE15_CONTROLLED_SOC/tests -p 'test_*.py' -v` ran **six tests; all passed**. Coverage: template and source-lineage split separation; model-visible schema and private-file exclusion; append-order ledger and point-in-time replay; deterministic groups and 100-alert cap; locked-test metric arithmetic; and selected code/config hashes against the pre-test freeze. The complete suite ran in about 0.35 seconds.

The tests do not certify real-world sensor timing, signed ledger integrity, human priority judgments, or cross-template distributional independence. The locked-test evaluator checked group partitions, cap, 60 top-20 denominator, and pair metric arithmetic during execution.
