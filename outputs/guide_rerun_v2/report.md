# GUIDE_Test exploratory rerun v2

Source rows: GUIDE_Test.csv; 193,311 oracle-group incident candidates and 369,347 unambiguous alerts from 469 selected organizations.

## Ranking validation

Selected logistic C=0.1. The first tested K meeting >=95% macro candidate recall was K=500; this means up to 500 candidate incidents per organization. This is a retrieval workload measure, not final Recall@20.

| Candidate K | Validation recall | Holdout recall |
|---:|---:|---:|
| 20 | 0.3791 | 0.4044 |
| 50 | 0.6440 | 0.6735 |
| 100 | 0.8104 | 0.8390 |
| 200 | 0.9142 | 0.9301 |
| 500 | 0.9746 | 0.9721 |
| 1000 | 0.9993 | 0.9809 |

## Holdout ranking (68 exploratory organizations)

| Method | Precision@10 | Recall@20 | nDCG@20 rank 1 high | nDCG@20 rank 20 high |
|---|---:|---:|---:|---:|
| descriptor_count | 0.3787 | 0.3036 | 0.4288 | 0.0991 |
| fielded_bm25 | 0.3025 | 0.2872 | 0.1745 | 0.1306 |
| fused | 0.4566 | 0.4018 | 0.4583 | 0.1393 |
| groq_rerank | 0.5088 | 0.4243 | 0.4828 | 0.1210 |
| logistic | 0.7127 | 0.5516 | 0.5489 | 0.1658 |

Groq calls: 68; actual tokens: 176,473; statuses: {'invalid_output': 1, 'ok': 67}. Missing/invalid Groq output falls back to fused offline ordering and must be interpreted with the fallback fraction. Model: openai/gpt-oss-120b. Token usage is measured; billing tier and zero cost were not verified.

## Correlation diagnostic (500 label-blind selected alerts per organization)

Validation best tested candidate recall: 0.8013; target met: False. Holdout candidate recall: 0.8125; candidate coverage: 0.6948. Final pair precision: 0.0363; recall: 0.6590; F1: 0.0688.

## Interpretation and data controls

This run uses the local GUIDE_Test data and queue labels. Ranking incident candidates were formed by the dataset IncidentId and are an oracle-group diagnostic; no end-to-end C/P/V grouping or military certification is demonstrated. The 30 previously evaluated organizations were excluded. The 68 new holdout organizations are exploratory because complete prior label-exposure evidence is unavailable. Model and candidate settings were selected on training/validation only and frozen before holdout label access. QueueRank numeric direction and the exact publisher active queue remain unverified; both nDCG directions are reported.

All 70,702 conflicting alert keys were excluded from feature construction; correlation truth uses only unambiguous keys. The correlation estimate is restricted to 500 opaque-hash-selected alerts per organization. The hosted prompts contained only Category, MitreTechniques, EntityType, EvidenceRole and temporary candidate numbers. No raw IDs, evaluator labels, or entity values were sent. Groq may retain inference inputs for reliability/abuse monitoring for up to 30 days unless ZDR is enabled (see provider documentation).

Raw source hashes: `{'GUIDE_Test.csv': 'fdfd7523efd6e3c26bd0290ba6acbcb237196cf923dd56a28e96802035db35a3', 'GUIDE_Test_Queue_Rankings.csv': 'e4ea9308f45821128a3cd446ab19e6559edfc50709e72034ce957b6f0e2e65d6'}`. Prediction freeze and restricted artifacts are in ignored `data/derived/guide_rerun_v2`; aggregate outputs are in `outputs/guide_rerun_v2`.


## Retrieval-to-reranking limit

The Groq request contained only the top 50 fused candidates. The holdout candidate recall ceiling at K=50 was 0.6735; the 95% target at K=500 therefore does not transfer to Groq Recall@20.
The highest observed offline Recall@20 was logistic 0.5516; Groq achieved 0.4243. These post-evaluation observations cannot be used to claim a confirmatory model selection.
