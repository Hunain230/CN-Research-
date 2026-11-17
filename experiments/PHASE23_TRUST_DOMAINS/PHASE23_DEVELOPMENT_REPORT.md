# Phase 23 — Trust-domain diversity (development counterfactual)

**Decision: NO-GO.** This is a mechanistic replay on Phase 22's ten development queues, not a new holdout result. Phase 19 and Phase 22 locked cohorts remain sealed. Phase 16 v4 remains the selected safe synthetic result and its scoreboard is unchanged.

## Question and method

Can a receiver-authenticated upstream controller map prevent two locally verified receipts from one common failure from authorizing a union? The Phase 22 verifier counts sensor labels and distinct event roots. The Phase 23 diagnostic additionally requires two distinct trust roots from a separate registry. Missing registry entries cause abstention. The registry is assumed authenticated outside the sensors; sensor supplied domain labels would not establish independence.

The replay keeps Phase 22's development alerts, claims, receipt values, cutoff, and private physical truth. It applies three counterfactual controller maps:

1. **Shared controller:** every auth and network receipt in a queue maps to one controller; endpoint receipts map to another. This includes the two corrupted receipts in each shared-upstream queue.
2. **Independent corruption stress:** auth and network map to separate controllers, while the same already corrupted receipt bytes remain in place. This tests what the verifier can infer when two independent-looking roots agree on a false relationship. It changes the topology assumption, not the Phase 22 fault generation; a future fixture should inject separate failures from independently generated sources.
3. **Missing root:** the shared-controller map applies, but endpoint registry entries are absent. This is a severe missing-attestation stress, not a typical missing-rate estimate.

All predictions and decisions were written and hashed before private audit. The evaluator replays accepted unions and checks each increment against final false grouped pairs. A 100-pair premerge exposure cap is a diagnostic of group-size control, not a calibrated threshold.

## Development results

| Scenario and rule | Recoverable / 120 | False grouped pairs | False-pair-creating unions | Worst queue / union |
| --- | ---: | ---: | ---: | ---: |
| Shared controller, Phase 22 verifier | 44 | 300 | 3 | 168 / 132 |
| Shared controller, trust domains | 45 | 0 | 0 | 0 / 0 |
| Independent-root stress, trust domains | 44 | 300 | 3 | 168 / 132 |
| Shared controller, trust domains plus cap 100 | 4 | 0 | 0 | 0 / 0 |
| Missing root, trust domains | 0 | 0 | 0 | 0 / 0 |

The shared-controller diagnostic blocks the two physically invalid unions and the later union that would have spread contamination. The one-incident recovery difference (45 versus 44) is a consequence of avoiding that contamination, not evidence of better general recovery. In the independent-root stress, both false receipts satisfy local checks and domain diversity, so the same three unions create 300 false pairs. A 100-pair exposure cap avoids these unions but collapses recovery to 4/120. Removing endpoint attestations causes complete abstention under this fixture's support pattern.

Missing and delayed Phase 22 receipts remain excluded at the decision cutoff. In the shared-controller diagnostic's two missing/delayed queues, 5/24 incidents are recoverable. This study does not solve recovery from partial evidence.

## Interpretation and next gate

Controller diversity catches *known shared provenance* if the external registry is accurate and tamper resistant. It cannot identify two independently corrupted receipts whose visible claims and receipts are mutually consistent. The independent-root case is an indistinguishability limit for this rule, not a measured independent-failure rate. Domain claims or registry errors could also defeat it. No candidate meets a safe development gate across both topology cases while retaining useful recovery, so no locked cohort is eligible for evaluation.

Next, generate a fresh development cohort with explicit authenticated controller lineage, separately injected correlated and independent failures, uncertain or delayed attestation, and a provenance signal independent of the two challenged receipts. Calibrate a group-level risk rule on that cohort and require zero false-pair-creating unions in every development queue before considering any sealed evaluation. Keep queue and union accounting alongside aggregate pair precision.

## Reproduce

From the repository root:

```powershell
python experiments/PHASE23_TRUST_DOMAINS/run_study.py
python -m unittest discover -s experiments/PHASE23_TRUST_DOMAINS/tests -q
```

Artifacts: `predictions_and_decisions.jsonl`, `freeze_manifest.json`, `queue_audit.jsonl`, `union_pair_increments.jsonl`, and `summary.json`. The study imports the frozen Phase 22 verifier and evaluator without changing them.
