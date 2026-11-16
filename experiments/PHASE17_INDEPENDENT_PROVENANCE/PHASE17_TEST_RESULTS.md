# Phase 17 tests

`python -m unittest discover -s experiments/PHASE17_INDEPENDENT_PROVENANCE/tests -p 'test_*.py' -v` ran **six tests; all passed**. They check fresh namespace and split template separation, distinct sensor RNG seeds, absence of private labels in model-visible alerts, per-field future-value masking, alert availability cutoff, fragment partition and 100-alert cap, training-only reliability calibration, pre-test source hashes, one locked-test prediction set, and locked metric arithmetic. The final run completed in about 0.47 seconds.

Tests do not establish independent physical sensors, real receiver clock integrity, human priority judgment quality or external generalization. The unchanged evaluator additionally checked the 600-label denominator and group partitions during the locked run.
