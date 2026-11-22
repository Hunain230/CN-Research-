# Dashboard data contract

This document is the source contract for the recorded-evidence dashboard. The
frontend must not add fields to these artifacts or present derived values as
saved model output. Files below are relative to the repository root.

## Frozen Phase 33 holdout

| Artifact | Path and schema | Fields used / fields absent |
| --- | --- | --- |
| Receiver-visible alert rows | `experiments/PHASE33_FROZEN_GENERALIZATION/dataset/receiver_visible/locked_test/alerts/<queue>.jsonl`; one JSON object per row, 15 queues, 5,039 rows total. | `queue_id`, `alert_id`, `event_minute`, `evidence_available_minute`, `event_type`, `severity`, `asset_criticality`, and recorded context / identifiers (`host`, `source_host`, `destination_host`, `account`, `source_id`, `event_id`, `observation_id`, process, network and auth references). Rows must be replayed in file order. They are **not** sorted by `event_minute`: all 15 queues contain inversions (2,504 adjacent decreases in aggregate). The minute chart groups actual rows by their recorded minute; a replay cursor can move backwards on that axis. |
| Receiver-visible claims | `.../dataset/receiver_visible/locked_test/claims/<queue>.jsonl`; 15 JSONL files. | `queue_id`, `relationship_token`, `left_alert_id`, `right_alert_id`, `left_event_id`, `right_event_id`, `family`, `upstream_root_id`, `observation_id`, `observed_minute`, `evidence_available_minute`, `sensor_clock_minute`, `derived_from`, `collection_mechanism`, and optional context fields. Not every field is non-null on every claim. |
| Evidence availability ledger | `.../dataset/receiver_visible/locked_test/evidence_ledger/<queue>.jsonl`; 15 JSONL files, one row per alert in the inspected queues. | `sequence`, `artifact_id`, `event_minute`, `evidence_available_minute`. `sequence` is source order; it does not make event minutes chronological. |
| Candidate predictions | `experiments/PHASE33_FROZEN_GENERALIZATION/artifacts/candidate_predictions.jsonl`; 15 rows. Baseline is the sibling `baseline_predictions.jsonl`. | `queue_id`, `split`, `method`, `ranker`, `cutoff`, `candidate_pairs`, `eligible_alert_ids`, `groups_ranked`, `decisions`, `runtime_seconds`. There is no per-alert score or attack class. `groups_ranked` contains ranked lists of alert IDs. |
| Saved verifier decisions | `experiments/PHASE33_FROZEN_GENERALIZATION/artifacts/candidate_decisions.jsonl`; 15 rows. Baseline is the sibling `baseline_decisions.jsonl`. | Queue record fields: `queue_id`, `accepted`, `rejected`, `decision_counts`, `visible_claims`. Accepted relationship fields include `left_alert_id`, `right_alert_id`, `relationship_token`, `upstream_roots`; candidate may also include `evidence_kind`. Rejected fields are `relationship_token` and `reason`. There is no explicit `abstained` field or status in this schema; do not infer one from a reason string. `decision_counts` are model reason counters, not a separate event-time series. **The saved audit lacks endpoint IDs and event times for rejected and abstained decisions.** Rejected entries may only appear in the static handoff lane. |
| Frozen evaluation | `experiments/PHASE33_FROZEN_GENERALIZATION/artifacts/{candidate,baseline}_evaluation.json`; each has `queues` and `summary`. | Summary includes `split`, `method`, `ranker`, `queues`, `eligible_alerts`, `expert_top20`, `recoverable`, `recall20_count`, `p10_count`, `pair_tp`, `false_grouped_pairs`, `mixed_predicted_groups`, `predicted_groups`, `candidate_pairs`, `accepted_merges`, `rejected_merges`, `abstained`, `group_recoverability`, `incident_recall20`, `p10`, `ndcg20`, `mrr`, `grouped_pair_precision`, `runtime_seconds`, `prediction_sha256`, and `cohort`. These are completed holdout aggregates, not replay-time values. The `abstained` aggregate field is not an item-level decision status. |
| Holdout summary and post-evaluation audit | `experiments/PHASE33_FROZEN_GENERALIZATION/HOLDOUT_SUMMARY.json`, `POST_EVALUATION_AUDIT.json`, `PHASE33_FREEZE.json`. | Summary has `baseline`, `candidate`, `gates`, `provisional_go_pending_post_evaluation_audit`, `queue_safety_regressions`. Audit has accepted/rejected truth audit counts, fallback counts, recovery/recall deltas, queue count, temporal/private-feature violations, seal/metric gates and decision. Freeze records method names, split seed/queue count, and integrity hashes. Private evaluator labels are never loaded into Recorded replay. |
| Evaluator-only truth | `experiments/PHASE33_FROZEN_GENERALIZATION/dataset/evaluator_only/locked_test/{ground_truth_private,relationship_truth}/<queue>.jsonl`. | Exists on disk for official evaluation. It is not part of the receiver-visible replay API and must not be exposed in replay, counts, charts, or exports. |

The API returns the selected queue's receiver-visible `alerts`, `claims`,
`ledger`, saved `prediction`, saved `decisions`, `groupByAlert`, and an
`evidence` row-count/source summary plus `artifactPaths` object from
`GET /api/replay/{arm}/{queue_id}`. `artifactPaths` names the exact prediction,
decision, alert, claim and ledger files used for evidence export. A missing
required artifact produces an HTTP 503 error naming the expected repository
relative path.
The UI may locate an accepted relationship endpoint's minute by joining its
recorded endpoint alert ID to that alert's recorded `event_minute`. That join
is the only allowed basis for accepted endpoint markers. The rejected audit
entries have no endpoint join and must never be attached to a chart point.
For replay-progress views, an accepted relationship becomes visible only when
the later of its two endpoint rows has been reached in recorded file order.
This is a deterministic UI replay rule based on the saved endpoint IDs, not a
backend stream event. The handoff lane remains static and is never assigned a
replay position.

## New experiment run lifecycle

`POST /api/runs` runs the frozen Phase 31 baseline and Phase 32 +1 / +2
functions on the fixed 10-queue development split (seed `31102`). The backend
persists events to SQLite and emits them over `/ws`; `GET /api/runs/{id}/events`
provides replayable persisted lifecycle events. Emitted `kind` values observed
in source are `started`, `queue_complete`, `sealed`, `completed`, `cancelled`,
`failed`, `paused`, `resumed`, and `stop_requested`. `queue_complete` carries
`progress`, `completed`, `total`, `queueId`, `arm`, `alerts`, `groups`,
`accepted`, and `runtimeSeconds`. Other events carry their actual status and
message / result where emitted. **The backend does not stream per-sample
predictions.** Run progress must stay queue-level and must not be represented
as a per-row replay stream. This development split has been used for model
selection; run results are development evidence, not a new confirmation set.

## Missing / unsupported data

- No live sensor or external alert ingestion source exists in this app.
- No explicit item-level abstention status is saved in the decision JSONL.
- The saved audit lacks endpoint IDs and event times for rejected and
  abstained decisions. Such records are static handoff items only; even the
  wording “abstained” is not available for an individual rejected record.
- The backend does not stream per-sample predictions.
- Saved predictions have no confidence scores, probabilities, or attack
  classifications. The system reconstructs and prioritizes alert groups; it
  does not label attacks or produce an anomaly score.
- No item-level review-state persistence or remediation endpoint exists.
- The locked-test data are a completed holdout; replay is playback of saved
  artifacts and does not rerun inference.

If a future screen requires any missing field, add and validate a new research
artifact contract first. Do not synthesize, infer from reason-name substrings,
interpolate, or assign placeholder values.
