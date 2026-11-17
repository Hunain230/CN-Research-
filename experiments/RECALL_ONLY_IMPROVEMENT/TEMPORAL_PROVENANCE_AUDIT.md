# Temporal and provenance audit

The Phase 16 predictor reads `generated_alerts` and the `evidence_ledger`, checks that ledger availability matches each alert, and restricts inference to evidence available by minute 100. The ranking candidate reads only those same visible alerts. The post-evaluation audit verifies the visible eligible set and availability cutoff on all 15 development and 30 fresh-holdout queues: 5,466 and 10,869 eligible alerts respectively.

Ranking inputs are severity, asset criticality, event type, source ID for duplicate-observation counting, and event minute. These are allowed receiver-visible Phase 16 fields. The candidate reads neither private incident IDs nor oracle priority, scenario/template IDs, attack-stage labels, or truth files during inference. Truth is used only by the original evaluator after prediction files are sealed. The final holdout's baseline and candidate prediction SHA-256 digests were written to `artifacts/pre_evaluation_seal.json` before the evaluator ran.

No future evidence was included; no candidate connections were proposed, so no new lineage trust assumption was introduced. The Phase 16 generator does not provide authenticated independent attestation suitable for distinguishing genuine from mutually consistent false lineage across fragments. This is the material provenance limit on safe reconstruction in this experiment.
