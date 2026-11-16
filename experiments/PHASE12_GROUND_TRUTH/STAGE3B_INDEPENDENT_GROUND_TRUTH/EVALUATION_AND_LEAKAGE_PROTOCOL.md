# Evaluation and leakage protocol

## Pre-evaluation seal

Freeze the package schema, eligibility population, queue construction, decision cutoffs, split assignments, feature allowlist, matching rules, and exact metric code before opening sealed-test truth. Publish hashes of prediction files and code before evaluator-only labels are read. Report all enrolled alerts, unresolved derivations, ambiguous judgments, outages, and abstentions. Never tune thresholds on held-out truth. Previously exposed GUIDE_Test results are only retrospective context, not confirmatory evidence.

## Split unit and feature cutoff

For SOC export, keep incident lineage and organization/time blocks intact; enforce a time gap at least as long as the maximum feature lookback and case propagation window. For the lab, hold out whole runs and scenario families. Shared source observations, duplicate alerts, cases, or script templates must not cross partitions. A split is invalid if any incident family or source lineage crosses. Within a queue at cutoff `t`, inference sees only artifact versions with ledger availability at or before `t`; event, detector, and collection timestamps do not substitute. No incident ID, attack action ID, adjudication, priority judgment, scenario name, or derived membership field may enter C/P/V inputs. Detector fields need new-dataset review for leakage and operational availability.

## C — Correlate

Truth unit is an eligible alert with independently adjudicated incident membership (or explicit unrelated/negative status). Candidate generation, pair decisions, and final groups are frozen before evaluation. Report source-link coverage, candidate-connected truth incidents, group recoverability, pair precision, false grouped pairs, mixed groups, false splits, false merges, abstentions, and complete error cascade with exact counts. Full-pair true negatives are reported only if an exhaustive eligible pair universe is specified. Unjudged alerts are never treated as negatives. Keep the 80% completeness/purity definition used in the existing research only when the new population permits the same interpretation; otherwise pre-register a new metric name and do not compare numerical values directly to GUIDE.

## P — Prioritize

Use only queues with independently judged, complete priority ordering at a declared cutoff. Record every eligible incident and its judgment status. Report P@10, nDCG@20, and Incident Recall@20 only where their denominators and queue sizes support them, with exact eligible counts and missing-judgment coverage. A queue with fewer than 20 relevant ranked positions cannot be used to claim GUIDE-equivalent Recall@20. Expert rankings must be made blind to model output and independently reviewed. The current 75% child40 + 25% v7 blend may be a frozen comparator, but it is not automatically transferable or operationally approved on the new dataset.

## V — Verify

V checks source-link integrity, internal consistency, contradictory evidence, availability cutoff violations, mixed-incident risk indicators, uncertain merges, and oversized components without test truth at inference time. The evaluator later measures V's detection of independently adjudicated errors. Rejected merges and V flags must retain evidence refs and reasons. V may abstain; coverage and selective error must be reported together.

## Claims

SOC data may be observational with imperfect truth; controlled lab truth is scripted but less representative. Report them separately. Neither track inherits GUIDE's population or feature permission. Claims about 80% Incident Recall@20 or 85% recoverability require a sealed independent full C/P/V test with valid top-20 queues and predeclared denominators. No benchmark claim is made at Stage 3B.
