# Data and Claim Audit

**Audit date:** 2026-11-12  
**Purpose:** Establish which statements the current repository can support in a research submission.  
**Current status:** Prototype with exploratory offline results; no confirmatory LLM C/P/V evaluation.

## Executive summary

The repository supports describing the project’s data validation, leakage-aware preprocessing infrastructure, synthetic baseline/agent/evaluator implementations, and several explicitly exploratory local analyses. It does **not** support claiming that the proposed LLM correlate-prioritize-verify (C/P/V) workflow outperforms baselines, meets the 95% end-to-end Recall@20 target, or is ready for deployment.

The distinction matters because code can run on synthetic fixtures without measuring real-world performance. The existing offline joint comparison measures deterministic/statistical methods and proxies, not the proposed LLM agents. The previous test cohort has already been accessed, so its results are exploratory rather than confirmatory.

## Data description and provenance

The local files are Microsoft GUIDE evidence records and a queue-ranking file associated with expert top-20 incident labels. The repository’s Phase 1 validation reports:

| Item | Recorded value | Interpretation |
|---|---:|---|
| GUIDE evidence rows | 4,147,992 | Rows represent evidence records; one row is not necessarily one alert. |
| Distinct `(OrgId, IncidentId)` keys | 303,220 | Composite incident keys in the local GUIDE file. |
| Distinct `(OrgId, AlertId)` keys | 637,320 | Composite alert keys in the local GUIDE file. |
| Conflicting alert keys | 70,702 | An alert key is assigned to more than one incident in the file; semantics are unresolved. |
| Queue-label rows | 9,980 | Reported as 499 organizations × 20 labels. |
| Organizations meeting implemented numerical eligibility checks | 499 | This count alone does not verify queue scope or label completeness. |

Phase 1 recorded local SHA-256 values of `fdfd7523efd6e3c26bd0290ba6acbcb237196cf923dd56a28e96802035db35a3` for `GUIDE_Test.csv` and `e4ea9308f45821128a3cd446ab19e6559edfc50709e72034ce957b6f0e2e65d6` for `GUIDE_Test_Queue_Rankings.csv`. The source review found publisher information for the dataset/release, but the original download receipt and publisher byte-checksum record are not available in the repository. Keep that provenance limitation explicit.

**2026-11-14 addendum:** A [fresh Kaggle download of the ranking file](../outputs/submission_kaggle_queue_alignment_20261114_v1.json) is byte-identical to the local copy. The original download receipt remains unavailable, but current publisher-file identity is now verified for that ranking file. A corrected raw join found all 855 top-20 labels missing from the unambiguous model scope in raw GUIDE_Test through ambiguous alert assignments; they are not absent from the raw file. The erroneous [v1 source-scope audit](../outputs/submission_absent_rank_scope_audit_20261114_v1.json) is superseded by the [v2 audit](../outputs/submission_absent_rank_scope_audit_20261114_v2.json). No performance metric or denominator changed.

The ranking file has one local column named `QueueRank` and no `Split` column or exact active-queue snapshot. The numeric direction—whether rank 1 or 20 is highest—and exact mapping to the publisher’s queue definition remain unresolved. Treating rank 1 as highest and all local composite incidents as the candidate universe were declared implementation assumptions, not confirmed source facts.

## Evidence status

Status meanings: **Verified** means a repository artifact directly records the fact. **Assumed** means a declared convention used for a bounded analysis without independent source confirmation. **Unresolved** means available evidence does not settle the question. **Blocked** means the current protocol disallows the corresponding stronger analysis or claim.

| Topic | Status | Evidence and submission consequence |
|---|---|---|
| Input schemas, row counts, local hashes | Verified as recorded locally | Phase 1 validation manifests and reports record the file checks. Do not imply this proves every publisher-side provenance detail. |
| GUIDE row grain | Verified | GUIDE contains evidence rows; `Id` is not unique at that grain. Do not treat each row or `Id` as a unique alert/evidence citation without source clarification. |
| Conflicting alert membership | Verified count; semantics unresolved | 70,702 composite alert keys map to multiple incident assignments. The current primary policy excludes all such keys from correlation/joint scoring; it does not determine which assignment is correct. |
| Queue rank direction and exact query universe | Unresolved; assumptions used in some reports | Report rank-direction sensitivity for nDCG and call the candidate universe a local proxy. Do not call it the exact publisher active queue. |
| Top-20 labels | Strong source context, local mapping incomplete | Local files contain 20 rank values per organization, but the exact local queue snapshot/schema mapping is unresolved. Do not treat every unranked incident as irrelevant for graded ranking. |
| Production/model-visible feature allowlist | Verified empty | `configs/field_policy.yaml` has `approved_model_fields: []`. This blocks real-data model execution under the official policy. |
| Five descriptors in past offline experiments | Assumed for local experiments only | `DetectorId`, `Category`, `MitreTechniques`, `EntityType`, and `EvidenceRole` were used in a separate local-only policy. This is not independent timing/privacy approval and does not permit hosted transmission. |
| Existing 10/10/30 split | Verified as a preserved artifact; incomplete cohort evidence | The digest is recorded, but Phase 6A says only 50 of 499 eligible organization IDs are in the manifest. A complete unused/exposure-audited pool is not established. |
| Historical test-label exposure | Verified | The original 30-organization test cohort and later exploratory cohorts were evaluated. Do not describe them as untouched confirmatory data. |
| Phase 3/4 synthetic results | Verified as software checks | Baseline and C/P/V scaffolding was exercised with deterministic offline stubs and synthetic fixtures. This is not empirical LLM behavior or GUIDE performance. |
| Phase 5 evaluator | Verified synthetic-only | It validates metrics and boundaries on synthetic fixtures; its real mode fails closed. Do not imply the Phase 5 evaluator ran an empirical full study. |
| Phase 6 and later real-data results | Exploratory | Assumption-based local runs used previously accessed data and have stated scope/metric limitations. Do not present them as confirmatory. |
| Empirical LLM C/P/V versus matched controls | Unavailable | The latest offline joint comparison did not run B2, B3, B4, or the proposed LLM C/P/V workflow. Statistical proxies cannot stand in for those methods. |
| API cost, human reviewer benefit, production readiness | Unavailable / unsupported | No current authorized LLM comparison, blinded reviewer study, or production validation supports these claims. |

## Existing evidence and safe interpretation

### Synthetic implementation checks

Phase 2 reports a 23-assertion synthetic preprocessing self-check. Phase 3 reports 38 synthetic baseline assertions, Phase 4 reports 34 synthetic agent assertions, and Phase 5 reports 64 synthetic evaluation assertions in the cleanup record. These checks support statements about software behavior on fixtures, such as schema validation, organization boundaries, citation handling, abstention, review routing, and metric calculations. They do not establish effectiveness on real alerts.

### Exploratory joint comparison

The latest offline joint comparison used 57 previously accessed organization queues, 11,219 unambiguous alerts, and 1,216,600 frozen candidate pairs. It excluded ambiguous alert keys. Methods were a rule/count amendment, rule plus label-free BM25, and offline deterministic/statistical CP and CPV proxies. The report gives the offline CPV proxy pair F1 micro as 0.0872 and end-to-end Recall@20 macro as 0.1175; B0 rule/count gives 0.1364 and 0.0746 respectively. These values are **exploratory proxy results for that bounded cohort**, not LLM results or confirmatory estimates.

On that cohort, 74 of 1,140 expert top-20 labels were represented only by ambiguous alerts under the current exclusion rule. The resulting 1,066/1,140 = 93.51% is a coverage ceiling under that exclusion policy, not measured model recall. Do not remove those labels from the denominator to make a target appear met.

### Other exploratory metrics

The Phase 6 priority experiment reports tie-aware Recall@20 of 0.3392 with gold incident groups supplied to the ranking stage. This is an **oracle-group ranking diagnostic**: it does not measure alert grouping and is not end-to-end recovery. Its nDCG depends materially on the assumed rank direction.

The ambiguity-excluded technique-overlap correlation diagnostic reports micro full-positive-pair recall around 0.00845 and candidate coverage around 0.00290. Its report identifies this as a narrow, low-coverage diagnostic rather than a competitive full-data correlation baseline. State the cohort, exclusions, denominator, and exploratory status beside any use of these values.

Phase A later reported micro candidate recall of 80.37% at about 67% pair coverage for its validation retrieval routes, below that phase’s 99% candidate-recall target. A different bounded 57-organization candidate analysis reported 81.52% micro candidate recall while emitting 80.52% of possible within-organization pairs. These are candidate-generation measurements under their own sampling and exclusions, not final system Recall@20 and not directly interchangeable.

## Claim matrix

| Proposed claim | Evidence available | Safe wording for submission |
|---|---|---|
| “We validated the dataset.” | Phase 1 schema/grain/key audit and hashes. | “We audited the supplied local files’ schemas, row counts, hashes, key integrity, joins, and rank structure; several semantics remain unresolved.” |
| “We built leakage-safe preprocessing.” | Phase 2 ledger/evaluator separation, empty feature view, synthetic boundary checks. | “We implemented preprocessing and evaluator-isolation infrastructure. The official model feature view remains empty because no fields are approved.” |
| “We implemented baselines.” | Phase 3 code and synthetic stub run. | “We implemented baseline interfaces and exercised them on synthetic fixtures; this does not constitute real-data baseline evaluation.” |
| “We implemented the multi-agent system.” | Phase 4 C/P/V schemas, orchestration, offline stub and self-check. | “We implemented C/P/V workflow plumbing and tested its control flow on synthetic data. No empirical LLM C/P/V performance was measured.” |
| “Our method improves alert correlation.” | Limited exploratory diagnostics; low recall/coverage and conflict exclusions. | “The bounded exploratory correlation diagnostic had low pooled full-pair recall and limited candidate coverage; it does not establish an improvement.” |
| “Our method improves top-20 ranking.” | Exploratory BM25/oracle-group and proxy comparisons; no valid confirmatory cohort. | “Exploratory local ranking measurements are reported with assumptions and scope. They do not establish confirmatory superiority.” |
| “The multi-agent LLM beats a single LLM.” | No empirical matched B2/B3/B4/C/P/V comparison in the latest offline joint run. | **Do not claim.** State that the comparison was unavailable and remains future work. |
| “The method reaches 95% Recall@20.” | Target not achieved; available scope has ceiling/coverage constraints. | **Do not claim.** State the target and the measured/structural limitations separately. |
| “The system reduces analyst workload or cost.” | No blinded reviewer study or current empirical LLM cost comparison. | **Do not claim.** Identify as unmeasured future work. |
| “The dashboard is an SOC system.” | Existing dashboard is an aggregate static report viewer. | “The dashboard presents aggregate research outputs. Any synthetic simulation is a software demonstration, not a live SOC feed or operational system.” |
| “The system is production-ready.” | No confirmed evaluation, privacy approval, operational validation, or deployment safeguards. | **Do not claim.** The repository records the project as a research prototype, not production ready. |

## Test access and comparison status

The original 30-organization split is not a fresh test set: labels and metrics were accessed. The later GUIDE rerun and 57-organization offline comparison also use previously accessed source labels and are exploratory. Repartitioning the same organizations cannot make them untouched. A future confirmatory study requires an independent dataset or a documented unused cohort with label-exposure evidence and a frozen protocol before evaluation.

The latest matched offline comparison does not contain empirical B2, B3, B4, or LLM C/P/V outputs. Historical synthetic stub outputs must remain labeled synthetic. One bounded GUIDE rerun had a previously documented, narrow authorization for a hosted model; that historical authorization does not authorize new calls under the current protocol.

## Gates that remain open

1. Obtain a source-owner or publisher explanation for conflicting alert assignments and duplicate `Id` semantics, or approve a defensible scope/exclusion rule for the intended claim.
2. Verify the local queue mapping, rank direction, exact query universe, and judgment completeness.
3. Obtain point-in-time and privacy approval for any real model-visible fields; the official allowlist is currently empty.
4. Establish a complete eligible organization pool and a genuinely unused/exposure-audited confirmatory cohort.
5. If LLM experiments are part of the claim, obtain explicit data/provider authorization and implement matched methods and budgets before evaluation.
6. Improve candidate generation and report its recall alongside pair workload; Phase A’s 99% micro candidate-recall target was not met.
7. Conduct reviewer, latency, cost, or deployment studies before making operational-benefit claims.

## Sources within this repository

- [`phases_outputs/Phase1.md`](../phases_outputs/Phase1.md) — file validation, key integrity, conflict counts, and initial gates.
- [`phases_outputs/Phase2.md`](../phases_outputs/Phase2.md) — preprocessing implementation, evaluator isolation, and empty approved feature view.
- [`phases_outputs/Phase6A_StudyProtocol.md`](../phases_outputs/Phase6A_StudyProtocol.md) — current frozen protocol, feature/label boundaries, test exposure, and confirmatory-cohort status.
- [`phases_outputs/Phase6B-G.md`](../phases_outputs/Phase6B-G.md) — current handoff and full-study limitations.
- [`phases_outputs/PhaseA_Implementation_2026-11-11.md`](../phases_outputs/PhaseA_Implementation_2026-11-11.md) and [`PhaseA_Progress_2026-11-11.md`](../phases_outputs/PhaseA_Progress_2026-11-11.md) — latest coverage and candidate-retrieval gates.
- [`phases_outputs/Offline_Joint_Comparison_2026-11-11.md`](../phases_outputs/Offline_Joint_Comparison_2026-11-11.md) — latest matched offline proxy comparison.
- [`phases_outputs/test_evaluation_access_log.md`](../phases_outputs/test_evaluation_access_log.md) — prior evaluation failure, label access, and exploratory re-analysis record.
- [`configs/field_policy.yaml`](../configs/field_policy.yaml) and [`configs/empirical_field_policy.yaml`](../configs/empirical_field_policy.yaml) — official empty allowlist versus local-only assumed descriptors.

