# Phase 31 final report — NO-GO

## A. Historical benchmark

The historical Phase 16 reference remains **407/600 = 67.83% Incident Recall@20**. The later opened `source_depth` holdout found **444/600 = 74.00%**, but was not promoted because P@10 regressed. Phase 30 development reached **220/300 = 73.33%** with zero safe new unions. These are separate populations; none is replaced or numerically pooled with Phase 31. Historical hashes were verified against the prior freezes, and no historical file was modified.

## B. New controlled synthetic cohort

Phase 31 v2 generated 8 train and 10 development queues with distinct seeds and template variants. Its planned 15-queue holdout remained **ungenerated**. The original Phase 15 evaluator measured all matched development arms at minute 100, using unchanged 80% completeness/purity, Recall@20, P@10 and grouped-pair definitions. The initial v1 generator pilot was archived after strengthened validation identified weak same-context false challenges and inconsistent genuine event order; only v2 results below are authoritative.

| Development arm | Recall@20 | Recoverability | P@10 | Pair precision | False pairs | Mixed groups | Unions | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Original evidence subset + `source_depth` | 0/200 (0%) | 0/200 (0%) | 0/100 (0%) | 100% | 0 | 0 | 0 cross-fragment | Baseline |
| Rich claims, original one-lineage C | 155/200 (77.5%) | 160/200 (80.0%) | 62/100 (62%) | 84.23% | 2,580 | 22 | 511 one-lineage accepts | Fail safety |
| Independent-evidence V + `source_depth` | 155/200 (77.5%) | 166/200 (83.0%) | 72/100 (72%) | 100% | 0 | 0 | 446 verified unions | Fail 80% recall |
| Independent-evidence V + fixed rank bonus | **158/200 (79.0%)** | 166/200 (83.0%) | **73/100 (73%)** | 100% | 0 | 0 | 446 verified unions | **Fail 80% recall** |

All 446 verified unions were evaluator-correct; 100 false relationship tokens were rejected, along with 50 genuine tokens lacking sufficient usable evidence. No queue gained a false pair or mixed group under either verified arm. The final candidate missed the development target by **two incidents**. Because no candidate passed every development gate, no candidate was selected and **no holdout was generated or evaluated**. `HOLDOUT_RESULTS.csv` is intentionally absent.

## C. Research interpretation

Richer, independently sourced synthetic evidence raised group recoverability from 0/200 to 166/200 under the verifier while preserving measured development pair safety. Simply exposing the same claims to the original one-lineage correlator was unsafe: 2,580 false pairs and 22 mixed groups. The C-P-V architecture could safely reconstruct 166 development incidents under this generator's attestation assumptions, but ranking recalled 158 and left eight recoverable incidents outside the top 20. Thirty-four incidents remained unrecoverable, mostly because at least one required evidence family was missing or unavailable by the decision time.

The result does **not** establish 80% on development or any untouched holdout. It also does not establish real-world SOC safety: the three independent roots are simulated, and fully coordinated false attestations may be indistinguishable from genuine ones. The generator and model were not tuned on a locked holdout. A fresh holdout would be needed only after a separately predeclared candidate passes development; no further phase was started here.

Reproducibility: `config.json`, `generator.py`, `model.py`, `run_study.py`, `run_candidate3.py`, `validate_generator.py`, and `audit_phase31.py` reproduce the v2 cohort and analyses. `BASELINE_FREEZE.json`, `SPLIT_MANIFEST.json`, `artifacts/development_pre_evaluation_seal.json`, and `artifacts/development_candidate3_pre_evaluation_seal.json` record hashes and partitions. Generator validation, four controlled tests, prior-hash checks, leakage checks and post-evaluation union audits passed.
