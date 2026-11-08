# Phase 2 synthetic regression checks

Run `python -m src.cli self-test-phase2` with the project virtual environment.
The check consumes `synthetic_cases.json` and asserts ordinal identity despite
repeated `Id`, exact-row duplicate detection, repeated and conflicting alert
assignments, composite organization scoping, missing/naive/invalid timestamps,
typed IP/ATT&CK normalization, null/tied/gapped/incomplete rank examples,
label-sentinel exclusion from both feature output and serialized logs, and
deterministic disjoint split ordering.

Expected result is recorded in `expected.json`. No real source values are used
or printed by the fixture check.
