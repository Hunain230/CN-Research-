# Phase 5 — Evaluation pipeline (synthetic implementation)

## Scope and isolation

Implemented the evaluator specified in `05-Evaluation.md` and Phases 1–4. The evaluation package is separate under `src/evaluation/`; its truth reader is the sole interface that opens label JSON. `src/agents/` and `src/baselines/` do not import evaluator code or `evaluator_store`. Synthetic evaluation accepts only predictions and labels under `fixtures/stage5/`, configs under `configs/`, and writes only under `outputs/evaluation/synthetic/`. It rejects evaluator fields, label sentinels, invalid or duplicate predictions/pairs, cross-organization pair claims, non-finite values, invalid ranks, duplicate JSON keys, and partial judgment sets.

Real evaluation fails closed before reading prediction/label paths or creating the output directory. It cannot silently switch modes. No GUIDE, real evaluator labels, real predictions, Phase 1–4 derived artifacts, or external services were used. No dependency was added.

## Implemented metrics and procedures

- Correlation returns candidate-set metrics and, when an explicit full eligible pair universe is supplied, full-universe recall accounting for positive candidate-generation misses. Pair false negatives are reported separately for the candidate-set and full-eligible-pair denominators; they are never labeled as cluster false splits. Abstentions, failures and missing predictions count as pair false negatives for positive recall. `decision_coverage` is valid, non-abstained, non-failed predictions divided by the candidate-pair count. `candidate_generation_coverage`, when available, is candidate pairs present in the explicit full universe divided by the full eligible pair count; the field is omitted and its status says unavailable when no full universe is supplied. TN is emitted only when the explicitly exhaustive universe equals the scored universe. Zero denominators return zero with flags.
- False merges count predicted components spanning multiple verified truth groups; false splits count verified truth groups spanning multiple predicted components. These are cluster-level diagnostics, reported separately from pair false positives/negatives. Singleton counts are reported separately.
- Prioritization implements Precision@10 with denominator 10, Recall@20 over judged expert top-20 items, and nDCG@20 with gain `2^(21-r)-1` for expert ranks 1–20 and discount `log2(position+1)`. Incomplete judgments invalidate the metric; unknown items are never treated as irrelevant. Candidate omissions and judgment coverage are reported.
- End-to-end Recall@20 requires both at least 80% gold-group completeness and at least 80% predicted-component purity, with exact-boundary checks.
- Organization-level mean/median aggregation, paired 10,000-resample bootstrap intervals, paired two-sided organization sign-flip permutation tests, and Holm adjustment are implemented. Pairing uses organizations present in both methods; unpaired organizations are excluded and counted. Exact permutation enumeration is used for up to 16 organizations; larger samples use the configured seeded Monte Carlo procedure.
- Reviewer agreement/Kappa, citation support rate, conflict-detection recall, high-priority misses among auto-decided cases, and operational coverage/failure/latency/token summaries have synthetic calculation support only.

## Files and outputs

- `src/evaluation/`: `truth_reader.py`, `prediction_validation.py`, `metrics.py`, `statistics.py`, `report.py`, `runner.py`.
- `src/cli.py`: `evaluation-self-test` and `evaluate` commands; evaluation dispatch occurs before importing Phase 2 preprocessing.
- `configs/evaluation.yaml`, `configs/metrics.yaml`, `configs/statistics.yaml`, `configs/evaluation_schema.json`.
- `fixtures/stage5/`: synthetic `predictions.json`, evaluator-only `labels.json`, hand-calculated `expected.json`, and README.
- `outputs/evaluation/synthetic/phase5-synthetic-final5/`: metrics, synthetic report and run manifest with prediction/fixture/config/code/output hashes, versions, environment, seed and runtime.

## Commands and results

```powershell
.\.venv\Scripts\python.exe -m src.cli evaluation-self-test
.\.venv\Scripts\python.exe -m src.cli evaluate --mode synthetic --predictions fixtures/stage5/predictions.json --labels fixtures/stage5/labels.json --config configs/evaluation.yaml --out outputs/evaluation/synthetic/phase5-synthetic-final5
.\.venv\Scripts\python.exe -m src.cli evaluate --mode real --predictions <path> --labels <evaluator-only-path> --config configs/evaluation.yaml --out outputs/evaluation/real-blocked-final
```

`evaluation-self-test` passed **59 assertions**. Checks include perfect/zero/intermediate pair results; abstention, failure, missing pair, empty denominator, candidate miss and false merge/split; org-scoped reuse of the same synthetic incident identifier; top-10/top-20 ranking, partial judgments and duplicate candidates; exact graded nDCG gain; exact 80% end-to-end boundaries and just-below failures; aggregation; bootstrap, permutation and Holm expected calculations; reviewer agreement and conflict/citation calculations; malformed/duplicate/non-finite and label-contaminated predictions; evaluator import isolation; deterministic replay; and the real gate.

The fixture's hand-checkable outputs include candidate-set pair precision/recall/F1 of 0.5/0.5/0.5, one candidate-set pair false negative (two for the full eligible universe), one pair false positive, and cluster false merges/splits of 1/0. Decision coverage is 0.5; candidate-generation coverage is 4/6 (approximately 0.666667), with its numerator and denominator reported. Full-universe recall is 1/3 after an omitted positive pair. Ranking values remain Precision@10 0.2, Recall@20 2/3, and nDCG@20 approximately 0.785114 using the required gain. These are synthetic expectations only and have no research interpretation. The bootstrap/permutation/Holm fixture values likewise exercise implementation only; they are not significance evidence.

The corrected run is stored separately under `outputs/evaluation/synthetic/phase5-metric-terminology-fix/`; earlier synthetic runs were not overwritten.

Python compilation succeeded for 8 evaluation/CLI source files, and all 4 evaluation configs/schemas parsed. The real-mode check used nonexistent prediction and label paths, returned `ResearchGateBlocked`, and created no output directory, confirming the gate precedes label reads and output creation.

## Limitations and gates before empirical evaluation

No real metrics, p-values, rankings, test results, plots, or conclusions were produced. No reviewer study was conducted. Candidate pair metrics only become meaningful with an approved eligible pair universe and unambiguous truth; top-20 metrics require confirmed query and judgment scope. Synthetic demo statistical values must not be reported as research results.

Real evaluation remains blocked until all applicable gates are cleared:

1. Approve time-valid model-visible features with provenance/privacy review and rebuild the empty feature view with leakage audit.
2. Resolve or formally exclude the 70,702 conflicting alert memberships under an approved rule before correlation or joint metrics.
3. Verify QueueRank meaning, direction, scope, query universe and top-20 completeness before prioritization evaluation.
4. Freeze a non-provisional organization split, query/candidate universe, and test protocol before test access.
5. Provide authoritative detector severity or approve a documented protocol amendment for B0.
6. Freeze metric, partial-label, abstention/failure, candidate miss, tie and denominator rules; perturbation protocol; method/prompt/model versions and budgets.
7. Resolve `Id` semantics and complete required data-use/privacy review.

No raw data or prior phase artifacts were modified. Phase 5 establishes an isolated synthetic evaluator only; empirical evaluation remains blocked.
