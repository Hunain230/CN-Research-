# Evaluation contract decision — GUIDE exploratory study

**Decision date:** 2026-11-11  
**Status:** adopted reporting contract for existing real-data results; no confirmatory cohort is established.  
**Scope:** interpret and report the existing GUIDE_Test analyses. This document does not alter frozen runs, historical split files, predictions, or raw data.

## Decision in plain language

The current project can support a **reproducible, exploratory, local GUIDE_Test study**. It cannot yet support a confirmatory claim that the proposed C/P/V system improves full-data incident correlation and priority ranking. The best observed ranking Recall@20 is 0.5516 (local logistic), while Groq reranking reached 0.4243. Candidate retrieval recall of 0.9721 at K=500 is a different, earlier-stage measure. Sampled correlation pair F1 is 0.0688. None establishes final recall >=0.95, operational safety, or deployment readiness.

## Frozen interpretation for existing results

| Contract item | Decision | Evidence limit / required wording |
|---|---|---|
| Source | Refer to the local Microsoft GUIDE_Test and AIP ranking files with the recorded SHA-256 hashes in the run manifests. | Publisher filename/size match and source/license review exist; original download receipt and publisher byte checksum do not. |
| Ranking label | `QueueRank` identifies expert top-20 queue-relative priority. Use the 20 labeled incidents per eligible organization as a top-20 membership set. | It is neither severity nor a binary maliciousness label. Other local incidents are non-members of this selected set only under the local queue-proxy assumption; do not call them benign, low priority, or globally judged negatives. |
| Numeric direction | Report rank 1 as highest as the predeclared primary assumption, with rank 20 highest as nDCG sensitivity. | Publisher confirmation is still missing. Precision@10 and Recall@20 use top-20 membership and do not depend on rank direction. Do not choose a direction after comparing outcomes. |
| Query universe | One organization is one queue; candidates are all distinct local `(OrgId, IncidentId)` keys for a labeled organization meeting the recorded eligibility rules. | This is a reproducible local proxy. The exact published active-queue snapshot and local `Split` mapping are unavailable. State candidate and labeled counts for each experiment. |
| Correlation truth | Use `(OrgId, AlertId)` as the alert key. Exclude the entire key and every associated evidence row when it maps to multiple incidents. | 70,702 keys conflict; never resolve by first row, majority, or predicted outcome. Report exclusions and the sampled evaluation universe. The resulting metric is not full-data correlation. |
| Model fields | For existing assumption-based local runs, allow only `DetectorId`, `Category`, `MitreTechniques`, `EntityType`, `EvidenceRole`. The prior bounded Groq prompts used only the last four. | The official Phase 2 allowlist remains empty. These five are local alert-time assumptions, not independently verified point-in-time/privacy approvals. Keep join IDs, labels, outcomes, raw entities, names, locations, and perturbed timestamps out of features. Do not broaden external transmission without a reviewed field policy. |
| Cohorts | Preserve the historical 10/10/30 split and the rerun's 334/67/68 assignment. Classify the historical 30 and newer 68 evaluated organizations as exploratory. | Both holdout label sets have been accessed. All 499 eligible organizations appear in the historical or newer experiment allocation; this repository does not establish an untouched local confirmatory cohort. Do not relabel an accessed group as untouched. |
| Ranking implementation | Keep the executed metrics and prediction manifests unchanged. Report Precision@10, Recall@20, and both rank directions for nDCG@20 with organization-level denominators and intervals. | The original Phase 1–2 methodology specified **linear** nDCG gain `21-r`; Phase 5 and empirical code use **exponential** gain `2^(21-r)-1`. Label existing nDCG as exponential and resolve this deviation in a versioned amendment before any new study. Do not mix the two formulas in one table. |
| Candidate generation | Report relevant top-20 items retrieved at K separately from final top-20 ranking and end-to-end recovery. | K=500 reached 0.9721 macro candidate recall on the 68 exploratory organizations. The Groq reranker saw only K=50, whose candidate-recall ceiling was 0.6735. The >=0.95 target applies to K=500 candidate retrieval only, not final ranking or correlation. |
| Pair classification | Give pair precision, recall, F1, candidate recall, and coverage with explicit sampled-pair denominators and abstention/failure counts. | The 500-alert-per-organization correlation diagnostic cannot be generalized to every alert in GUIDE_Test. |
| Joint outcome | End-to-end top-20 recovery requires predicted groups, not dataset `IncidentId` oracle groups. | No empirical full C/P/V joint result exists. Oracle-group ranking must retain that label in every figure and claim. |
| Baseline B0 | Do not claim a detector-severity baseline; no severity field or authoritative crosswalk is available. | Count-only oracle-group ranking may be reported as a different comparator, with its amendment named. |

## Confirmatory path

The existing data and access record do not demonstrate a genuinely untouched test cohort. To make a future result confirmatory, first obtain a new independent dataset/release or a separately evidenced unused cohort; verify that its labels did not influence any feature, method, threshold, prompt, metric, or publication choice. Freeze its organization membership and hashes, the field and conflict policies, candidate and query universe, all metric formulas, model/configuration versions, and failure rules **before** label access. Evaluate once under that frozen protocol. A changed method after viewing results creates a new exploratory analysis, not a second confirmatory test.

If no independent cohort can be obtained, submit the real-data findings as exploratory. Report uncertainty intervals as descriptive, avoid a confirmatory superiority claim, and describe the tested system as an oracle-group priority diagnostic plus sampled correlation analysis rather than a validated end-to-end C/P/V system.

## Evidence and deviations to carry into the paper

- Prior source, license, label, and conflict review: `readiness_evidence_review.md` and `research_gate_register.csv`.
- Original protocol and later assumption amendments: `Phase6A_StudyProtocol.md`, `empirical_protocol_freeze.md`, and `GUIDE_RERUN_V2_PROTOCOL.md`.
- Executed results: `../outputs/guide_rerun_v2/report.md` and its `run_manifest.json`.
- The bounded Groq protocol contains inconsistent token caps (200,000 in its opening paragraph and 150,000 in its run definition); the manifest records 176,473 actual tokens. Preserve and disclose this deviation. Do not describe the run as complying with the 150,000-token cap.
- The project can proceed with exploratory reporting without new user input. Publisher clarification of rank direction/queue snapshot, independent confirmation of field timing and data-use terms, and an independently unused test cohort would be needed for stronger benchmark or confirmatory claims.
