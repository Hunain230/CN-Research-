# Phase 28 final report — NO-GO

**Development demonstrated a large, safe synthetic gain, but the single untouched holdout failed the hard group-safety gate.** The authoritative fresh `phase28b` development cohort has 12 training and 20 development queues. Component-aware promotion increased both official recoverability and Incident Recall@20 **107/400 → 207/400** (+25.00 percentage points; 100 incidents), with P@10 43/200 → 78/200 and zero false pairs or mixed groups. All **127 development promotions** were evaluator-correct.

On the frozen 30-queue `phase28h` holdout, the same selected rule raised both recoverability and Recall@20 **171/600 → 291/600** (+20.00 percentage points), with P@10 98/300 → 125/300. Yet false grouped pairs rose **41 → 76**. Seven queues regressed; mixed groups stayed 25. Pair precision was 99.71%, which conceals the queue-level failure. Final decision: **NO-GO**. The paired queue-bootstrap interval for holdout recall gain is 18.00–22.33 percentage points; it does not override safety.

## Focused development comparison

| Development pipeline | Recoverable /400 | Recall@20 /400 | P@10 /200 | Pair precision | False pairs | Mixed groups | Promotions |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline / progression | 107 | 96 | 42 | 100.00% | 0 | 0 | 0 |
| baseline / phase27_selected | 107 | 107 | 43 | 100.00% | 0 | 0 | 0 |
| baseline / hypothesis_aware | 107 | 107 | 43 | 100.00% | 0 | 0 | 0 |
| calibrated / phase27_selected | 273 | 273 | 78 | 99.65% | 72 | 72 | 287 |
| component / phase27_selected | 207 | 207 | 78 | 100.00% | 0 | 0 | 127 |
| selective / phase27_selected | 204 | 204 | 79 | 100.00% | 0 | 0 | 123 |

The score-only calibrated rule reached 273/400 Recall@20 but created 72 false pairs and 72 mixed groups. The component rule accepted 127 of 287 hypothesis proposals and abstained on 160. The selective rule accepted 123, recalled 204/400 and also passed development safety; the predeclared highest-recall rule selected component-aware promotion. On unchanged groups, the hypothesis-aware ranking diagnostic matched the Phase 27 selected ranker at 107/400; ranking alone did not improve recoverability.

## Exact holdout failure

The holdout generator predeclared one independent false dual-lineage challenge per queue before predictions. **Seven false promotions** out of 180 were accepted (promotion precision 173/180 = 96.11%). Each joined unrelated benign fragments through two independently rooted, mutually consistent but false relationship paths. Each added five false pairs; 14 union steps sum to all 35 added pairs. Fixed-action counterfactual replay shows that skipping exactly those seven promotions removes the 35-pair increase. The failing queues are phase28h_locked_test_q002, phase28h_locked_test_q003, phase28h_locked_test_q006, phase28h_locked_test_q009, phase28h_locked_test_q010, phase28h_locked_test_q012, phase28h_locked_test_q013. Receiver-visible host/account values were consistent at minute 100; later contradictory host evidence was never used for the original decision.

The present component guard distinguishes the correlated-controller decoys in development, but it cannot establish the truth of two independent-looking false paths. This is the remaining causal trust limit. Keep unpromoted hypotheses for discovery, and next test a truly independent attestation of the claimed cross-fragment event or a provisional, reversible analyst workflow. Do not tune against this opened holdout. Phase 27's frozen holdout remains historical and separate; its baseline recoverability was 171/600 for both pipelines, while Recall@20 was 159/600 → 171/600.
