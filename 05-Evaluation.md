# Phase 5 — Evaluation: metrics, statistical comparison, and reporting

Status: Codex implementation specification. Read PROJECT_CONTEXT.md, phases_outputs/Phase1.md through Phase4.md, and 05-Evaluation.md before implementing. This phase may build evaluator code and test it on synthetic fixtures. It must not calculate or report empirical metrics on GUIDE/AIP until the research gates below are cleared.

## 1. Purpose

Implement a separate, reproducible evaluation pipeline for:
- alert-correlation quality;
- prioritization against expert top-20 labels;
- end-to-end recovery after predicted grouping;
- evidence-verification and analyst-review behavior;
- operational cost, latency, failures, and coverage;
- paired statistical comparison between baselines and the proposed workflow.

Evaluation code is not a model component. It is the only code permitted to read the evaluator-only truth store. Keep it isolated from feature building, retrieval, prompts, agents, and candidate generation. Do not let labels flow back into predictions, tuning, calibration, feature selection, or test-time decisions.

Phase 5 produces evaluator implementation, metric definitions, synthetic fixtures, and reporting templates. With current data gates open, it cannot produce valid real-data results.

## 2. Current gate status

From Phase 1–4:
- The Phase 2 feature view has zero approved model-visible fields.
- 70,702 composite (OrgId, AlertId) keys have conflicting IncidentId assignments. Correlation truth is ambiguous; correlation and joint evaluation remain no-go.
- QueueRank direction, semantic meaning, scope, query universe and top-20 completeness remain unverified. Priority evaluation remains blocked.
- The 10/10/30 organization split is provisional.
- Phase 3 baselines and Phase 4 agents have only synthetic plumbing; no real predictions exist.
- Duplicate Id semantics remain unresolved. Id must never be used as a unique row/citation key.
- B0 detector severity lacks an authoritative source/crosswalk.

Therefore:
- Implement metric functions only against synthetic labeled fixtures.
- Do not load real evaluator files, rank labels, IncidentId labels or test predictions.
- Do not generate real F1, Precision@10, Recall@20, nDCG, confidence intervals, p-values, plots or qualitative claims.
- Real evaluation command must fail closed before creating an output directory.
- Do not call synthetic scores, stubs, hand-authored expected values, or fixtures research results.

## 3. Evaluation architecture and data boundaries

Build two separate interfaces:

### 3.1 Prediction input
Predictions from Phases 3–4, with method/run identifiers, opaque query/candidate keys, organization partition key, score/rank or pair decision, evidence citations, abstention/failure status and resource metadata. Predictions may not contain gold labels or label-derived fields. Validate schemas, finite values, uniqueness, candidate eligibility, same-organization scope, and run/config hashes.

### 3.2 Evaluator-only truth input
Read-only labels, accessible only through an explicit evaluation module/process:
- correlation truth: unambiguous composite incident membership only, once conflicts are adjudicated or excluded under an approved protocol;
- prioritization truth: QueueRank with verified rank direction/scope/query universe and completeness;
- organization partition manifest and candidate universe;
- any human review labels for citation support/conflict detection.

Fail if prediction files contain evaluator-only fields, if a model artifact is present in evaluator input, or if run/method/query keys cannot be reconciled without leaking labels. No evaluator exports may be re-used as model input.

The evaluator must be read-only and must not update model outputs. Separate paths, APIs, and code ownership boundaries; do not merely rely on developers remembering not to pass labels.

## 4. Freeze evaluation protocol before test access

Before any real test evaluation, freeze and hash:
- approved features/field policy and preprocessing version;
- organization split and query universe;
- correlation candidate generator, candidate cap and pair eligibility;
- ranking relevance mapping and incomplete-judgment policy;
- prediction schema, abstention and failure treatment;
- metric definitions, denominators, averaging and tie handling;
- bootstrap/permutation procedure and multiple-comparison correction;
- method versions, configs, prompts, model versions, decoding, token limits and budgets;
- reviewer sampling and adjudication codebook.

Use pilot/development only for method selection, threshold selection and calibration. Test data remain sealed until the protocol is frozen. Evaluate all methods on the exact same selected organization queries and eligible candidate sets. Any amendment after test opening must be logged and results labeled exploratory.

## 5. Correlation evaluation

### 5.1 Eligibility
Correlation pair metrics require one unambiguous truth membership per alert key (OrgId, AlertId). Exclude or quarantine unresolved assignments only under a predeclared, defensible rule; report counts and reasons. Do not choose an arbitrary IncidentId. No correlation scoring is allowed while the 70,702 conflicting assignments remain unresolved.

### 5.2 Pair metrics
For an eligible set of alert pairs:
- TP: predicted LINK and same verified composite incident.
- FP: predicted LINK and different verified composite incident.
- FN: predicted NO_LINK for a positive pair, or an eligible positive pair omitted by candidate generation if reporting end-to-end candidate recall.
- TN: predicted NO_LINK and different verified incidents only when the pair belongs to a defined, exhaustively enumerated negative universe.
- UNSURE/abstain must be reported separately. Define whether it counts as false negative for recall and report coverage/conditional metrics; never silently drop abstentions.
- Compute precision, recall, and F1 with explicit zero-denominator behavior. Report both candidate-set and full-eligible-pair denominators where possible.
- Report false-merge and false-split counts per organization, and explain their counting rules.
- Report macro mean/median by organization and pooled micro counts. Organization is the independent statistical unit; never treat pair rows as independent samples for confidence intervals.
- State pair sampling, class balance and any negative sampling correction. Sampled-pair metrics do not estimate full-universe performance without a valid correction.

### 5.3 Clustering diagnostics
If cluster truth becomes valid, include component purity/completeness or explicit false merge/split definitions, singleton handling, and candidate-generation recall ceiling. Do not evaluate transitive components using ambiguous truth. Preserve a mapping from each predicted component to eligible alerts and evaluator truth only inside evaluator process.

## 6. Prioritization metrics

### 6.1 Judgment and candidate universe
Define the query unit (organization queue/snapshot), eligible candidate incidents, and list length before scoring. Confirm what absence from the expert queue means. Never assume an unlabeled incident is irrelevant. If labels are top-20 only, report judgment-limited metrics and do not imply full severity ranking.

### 6.2 Required metrics
Once QueueRank semantics are authoritatively verified:
- Precision@10: proportion of top 10 predicted candidates judged relevant under the declared relevance rule.
- Recall@20: relevant expert top-20 items retrieved in the predicted top 20, divided by number of relevant expert top-20 items in that query.
- nDCG@20: use the methodology's stated gain for rank r in expert labels: gain = 2^(21-r) - 1 for ranks 1 through 20, zero otherwise. Use predicted position discount log2(position+1), and define ideal DCG over the same judged candidate universe. Document this exact gain convention; do not replace with a different relevance mapping silently.
- Report reciprocal rank or rank correlation only if specified in the frozen protocol and the judged universe supports it.

For every metric report:
- query count and organization count;
- k and exact denominator;
- candidate list size and missing/duplicate candidates;
- how unjudged candidates, empty result lists, ties, duplicates, and abstentions are handled;
- macro mean/median across organizations and any micro/pooled form;
- judgment coverage and fraction of candidate universe with labels.

If labels are incomplete, do not count unjudged items as negative by default. Implement a partial-judgment policy only after protocol confirmation; otherwise mark the metric invalid/blocked.

## 7. End-to-end joint recovery

The Phase 2 methodology defines a gold expert top-20 incident as recovered when a predicted top-20 component:
1. contains at least 80% of that gold incident's alerts, and
2. has at least 80% of its own alerts belonging to that gold incident.

Implement this exactly when alert membership is valid. Report end-to-end Recall@20 as the number of recovered gold top-20 incidents divided by eligible gold top-20 incidents per organization, then aggregate by organization. Report failures due to:
- candidate-generation miss;
- false split (completeness <80%);
- false merge (purity <80%);
- ranking outside top 20;
- ambiguous or missing truth.

Do not calculate this while mappings conflict. The gold-group-only prioritization ceiling is a separate diagnostic and must be labeled separately from the end-to-end result.

## 8. Verification, review, and operational measures

After a defensible evidence review protocol exists, report:
- citation support rate from a blinded two-reviewer sample of 200 outputs;
- inter-reviewer agreement and adjudication method;
- conflict-detection recall on labeled conflicts;
- review/abstention fraction;
- high-priority misses among auto-decided cases, with exact denominator;
- p50/p95 latency, failures, retries, throughput;
- input/output tokens and estimated API cost using recorded tariff for real model calls.

Do not fabricate reviewer labels or conduct a real-data human review in this phase. Synthetic fixtures may test calculation only. Separate model-verification support from gold-label correctness.

## 9. Statistical comparison

The organization is the independent unit.

Protocol when real evaluation is permitted:
- Report per-organization results plus mean and median.
- For the predeclared primary outcomes (correlation pair-F1 and end-to-end Recall@20), compute 95% confidence intervals from 10,000 paired bootstrap resamples of organizations, preserving method pairing.
- Use paired permutation tests for predeclared comparisons against B0–B3. Apply Holm adjustment to the four primary p-values as specified in the methodology.
- Predeclare B3 (three repeated single-LLM calls with matched budget) as primary comparator for the proposed multi-agent system.
- Show all three inference seeds separately and their mean; seeds and pairs are not independent organizations.
- State random seeds, interval/test implementation, alternative hypothesis, missing organization handling and exact multiplicity family.
- Report effect sizes and intervals, not only p-values. Do not interpret statistical significance as operational value.
- If fewer organizations are eligible than the protocol requires, stop and propose an amendment before test inspection.

Implement statistical procedures on small synthetic fixtures with hand-calculated expectations. Do not bootstrap or test synthetic demo outcomes as if they demonstrate research significance.

## 10. Failure, abstention, and denominator policy

Every prediction must land in one of: valid decision, abstention/REVIEW, malformed output, failed call, missing candidate, or ineligible item. Preserve all categories in output.

Before real evaluation, freeze rules for:
- whether abstention counts as FN for recall and how it affects precision;
- whether failed/missing outputs count as missed relevant items;
- duplicate predictions and invalid evidence citations;
- candidates absent from the ranked list;
- no-positive and no-prediction queries;
- partial labels and sampled pair universes.

Report both coverage and quality conditional on decisions when useful. Never improve metrics by silently dropping failed, abstained, malformed, or unjudged cases.

## 11. Synthetic test fixtures and evaluator assertions

Implement synthetic-only evaluator fixtures with known labels/predictions for:
- perfect, zero, and intermediate pair precision/recall/F1;
- false merge, false split, candidate-generation miss, abstention and empty prediction;
- duplicate pairs and same IncidentId reused in another organization;
- top-10/top-20 boundary cases, ties, duplicate candidates and missing candidates;
- top-20 graded nDCG using the specified gain formula;
- partial judgments to ensure unknown is not silently treated as irrelevant;
- end-to-end 80% completeness and purity boundaries (exactly 0.8 passes; just below fails);
- empty/no-positive queries and zero denominators;
- per-organization aggregation and deterministic ordering;
- paired bootstrap and permutation calculations on small hand-checkable samples;
- Holm adjustment with known p-values;
- reviewer agreement and conflict-detection calculations on synthetic annotations;
- malformed predictions, invalid ranks, NaN/Infinity and evaluator-field contamination;
- proof that evaluator labels never enter prediction/config/prompt artifacts;
- real-mode gate refuses and creates no output while current blockers remain.

Fixtures must be synthetic. Test expected numbers exactly or with a documented numeric tolerance. Synthetic outputs must carry a prominent synthetic-only classification.

## 12. Config, CLI, and outputs

Add versioned configs such as:
- configs/evaluation.yaml;
- configs/metrics.yaml;
- configs/statistics.yaml;
- configs/evaluation_schema.json.

Implement evaluator code under src/evaluation/ with separate truth reader, prediction validator, metric functions, statistics, report builder and real-data gate. Use standard library where reasonable; pin and justify scientific dependencies if needed. Do not add dependencies merely for convenience.

CLI contract:
~~~
.\.venv\Scripts\python.exe -m src.cli evaluation-self-test
.\.venv\Scripts\python.exe -m src.cli evaluate --mode synthetic --predictions fixtures/stage5/predictions.json --labels fixtures/stage5/labels.json --config configs/evaluation.yaml --out outputs/evaluation/synthetic/<run_id>
.\.venv\Scripts\python.exe -m src.cli evaluate --mode real --predictions <path> --labels <evaluator-only-path> --config configs/evaluation.yaml --out outputs/evaluation/real-blocked
~~~

Synthetic mode may read fixtures/stage5 only; it must not read data/raw or data/derived/preprocessing. Real mode must fail before reading labels or creating outputs if any gate is closed. Do not silently fall back to synthetic mode.

For legitimate future runs, record:
- prediction/input/label/split/config/code hashes;
- evaluator and metric versions;
- environment and package versions;
- seed, run time, eligible queries, exclusions, denominators;
- metric values and confidence intervals;
- gate status and protocol freeze hash.

Never place sensitive identifiers or raw evidence in aggregate reports. Keep per-query outputs access-controlled and evaluator-only.

## 13. Acceptance criteria

Phase 5 implementation is accepted only when:
1. Evaluation module alone can access labels; model and prediction code cannot.
2. Metric formulas and denominators are versioned, explicit, and covered by hand-checkable synthetic tests.
3. Correlation metrics distinguish candidate-set vs full eligible universe and report abstention/failure handling.
4. Prioritization metrics implement Precision@10, Recall@20 and the specified nDCG@20 gain, with partial-label safeguards.
5. End-to-end recovery implements both 80% completeness and 80% purity thresholds.
6. Organization-level aggregation and paired statistical procedures use organizations as the unit.
7. Holm correction, 10,000 paired bootstrap and paired permutation logic have deterministic synthetic checks.
8. Human-review measures have schemas and synthetic calculations but no fabricated real reviewer results.
9. Real-data evaluation fails closed under current gates and creates no output directory.
10. No real metrics, p-values, test inspections, rankings or performance claims are emitted prematurely.
11. All synthetic runs are explicitly marked not empirical and reproducible.
12. Phase record and phase index distinguish evaluation implementation from empirical evaluation readiness.

## 14. Gates before empirical evaluation

- Approve time-valid model features and rebuild non-empty feature view with leakage audit.
- Resolve or formally exclude conflicting alert membership before correlation/joint metrics.
- Verify QueueRank meaning, direction, scope, query universe and top-20 completeness.
- Freeze a non-provisional organization split and candidate universe before test access.
- Make B0 severity available through an authoritative source or document an approved amendment.
- Freeze metric definitions, abstention/failure denominators, perturbation protocol, model/prompt versions and budgets.
- Complete any required data-use and privacy review.

Phase 5 may produce a sound evaluator and synthetic metric checks. It cannot currently produce valid empirical F1, Precision@10, Recall@20, nDCG, confidence intervals, p-values, or research conclusions on the GUIDE/AIP data.
