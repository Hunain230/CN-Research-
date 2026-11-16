# Phase 12 Stage 3B — independent ground-truth design

**Status:** design and validation tooling only. No SOC data has been obtained, no lab has been run, no model has been trained, and no metric has been measured. Stage 3A reached NO-GO for event-level AIT-ADS evaluation; public-dataset hunting is paused.

This directory defines two acquisition tracks that produce the same versioned evidence package:

1. [Authorized SOC export](SOC_EXPORT_PROTOCOL.md): governed, pseudonymized real alerts and original observations, with independent incident adjudication and priority judgments.
2. [Controlled SOC lab](CONTROLLED_SOC_LAB_PROTOCOL.md): interleaved scripted attacks and benign activity with independently captured source truth and a live evidence-availability ledger.

The common [data contract](GROUND_TRUTH_CONTRACT.md) and [JSON schema](ground_truth_package.schema.json) separate source observations, detector alerts, derivation edges, incident membership, scripted actions, evidence availability, and expert judgments. [Validation tooling](validate_package.py) checks structural and temporal integrity. [Evaluation protocol](EVALUATION_AND_LEAKAGE_PROTOCOL.md) specifies seal, split, and metric gates. [Readiness checklist](READINESS_GATE.md) determines whether a package can support C only or full C/P/V claims.

The package is intentionally independent of GUIDE's feature assumptions and Phase 10 E1. `configs/field_policy.yaml` currently approves **no** GUIDE operational model fields; this design does not change it. A new dataset requires its own field-by-field approval before inference. The prior GUIDE metrics remain retrospective and cannot be relabeled as independent confirmation.

## Design boundaries

- Collection and truth recording are separate from detector output and C/P/V predictions.
- Incident membership and priority are adjudicated without access to candidate predictions.
- Every admissible inference field must have an availability timestamp no later than its decision cutoff.
- Missing source IDs, unknown arrival times, unresolved alert derivations, and ambiguous labels remain visible as missing or abstained records; they are never imputed from attack windows.
- The included fixture is synthetic validator data only. Passing it does not establish real-world readiness.

## Execution

`python validate_package.py fixtures/synthetic_valid.json` validates the synthetic contract example. `python -m unittest discover -s tests -v` exercises rejection of broken references, time travel, and split contamination. No network or third-party dependency is required.
