# Stage 3 synthetic baseline fixtures

Run the regression suite with `python -m src.cli baseline-self-test` in the
project virtual environment. It reads only `synthetic_inputs.json`; the
expected gate and output properties are in `expected.json`. The fixture has
only synthetic opaque keys/evidence. It includes rule timing, organization
isolation, common values, ATT&CK-only matches, chaining, cap/tie behavior,
BM25 reference scoring, empty/no-overlap retrieval, prompt-injection-like
untrusted text, stub malformed/timeout cases, and B3 aggregation/budget checks.
All emitted records must be marked synthetic/stub, not empirical.
