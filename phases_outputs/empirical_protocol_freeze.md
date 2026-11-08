# Empirical protocol freeze — conservative offline path

**Status:** Adopted working protocol for local, offline experiments  
**Effective date:** 2026-11-08  
**Authority:** User directed the implementation owner to clear gates and make assumptions where necessary. This document records those assumptions; it does not present them as publisher-confirmed facts.  
**Scope:** Makes a narrow priority-retrieval evaluation possible and permits an ambiguity-excluded correlation diagnostic. It does not authorize external model/API calls, public release of row-level data, or claims that the local data exactly reproduces the published queue snapshot.

## 1. Decision register

| Topic | Decision | Status / limitation |
|---|---|---|
| Publisher and license | Retain the source review’s attribution to Microsoft and CDLA-Permissive-2.0. Local filenames/sizes and Phase 1 hashes match the reviewed release listing. | Publisher metadata verified in the prior evidence review; download-event provenance is still unverified. |
| QueueRank direction | Interpret numeric rank `1` as the highest-priority position, increasing through `20`. | **Assumption A1**, not confirmed by the reviewed publisher materials. Top-20 membership metrics do not depend on this assumption. Report nDCG under both ascending and descending interpretations; treat ascending as the primary declared convention pending confirmation. |
| Top-20 label completeness | Treat the 20 distinct rank positions per each of 499 labeled organizations as a complete expert-selected top-20 set for the publisher-defined queue. | The paper/publisher describe a full-queue review and complete top-20 selection. This establishes the set construction for the published task, not by itself the exact local queue snapshot. |
| Local candidate/query universe | For this repository’s local experiment, define a candidate incident as every distinct `(OrgId, IncidentId)` in `GUIDE_Test.csv` for a labeled organization. Use the 499 organizations with at least 50 distinct local incidents and at least 10 distinct detectors, intersected with the ranking file. | **Assumption A2**, a reproducible local proxy for the published eligible active queue. The local file has no `Split` or active-snapshot field; conclusions must say “local GUIDE_Test candidate universe,” not claim exact reconstruction of the published snapshot. |
| Unranked candidates | For top-20 set retrieval only, treat local candidate incidents not present in the complete expert top-20 list as non-members of that top-20 set. Do not interpret them as low severity, resolved, benign, or generally irrelevant. | Supported by the full-queue top-20 selection protocol, conditional on A2’s local-universe mapping. Explicitly limit claims to top-20 retrieval. |
| Conflicting `(OrgId, AlertId)` memberships | Exclude all evidence rows for every composite alert key assigned to more than one distinct incident. Never choose, vote, or infer one of its incident assignments. Retain the restricted conflict artifact for audit only. | **Assumption A3**, a conservative exclusion rule. Publish coverage and composition effects; no correlation metric may imply these excluded keys were resolved. |
| Exact duplicate evidence | Preserve Phase 2’s deduplication/quarantine behavior and source-row ordinals; do not use `Id` as a unique evidence key. | `Id` has 291,595 duplicate-value groups and 3,844,772 excess occurrences; semantic uniqueness remains unknown. |
| Model-visible descriptors | For a local, non-generative baseline only, allow `DetectorId`, `Category`, `MitreTechniques`, `EntityType`, and `EvidenceRole`. Normalize to text with deterministic, versioned transformations. | **Assumption A4:** these are treated as alert-time descriptors. This is a narrow operational assumption, not independent field-level provenance approval. No raw entity identifiers, names, URLs, IPs, file paths, locations, timestamps, outcome/grade/action/verdict fields, labels, or join keys enter features. |
| Time | Exclude `Timestamp` from model features, windows, ordering, and tie-breaking because source documentation says timestamps are privacy-perturbed and exact semantics are not verified. | This amends the original 48-hour/1-hour candidate-window proposal. Time-based conclusions are unavailable. |
| Organization split | Freeze the already generated 10 pilot / 10 development / 30 test assignment exactly as stored in Phase 2; do not regenerate it. Verify its assignment digest against the Phase 2 record before use. | **Amendment A5:** freeze the historical hash assignment despite its earlier provisional status. It is reproducible with `configs/preprocessing.yaml` salt `CNET-Phase2-org-split-2026-11-08`; manifest itself stores the salt as blank. Preserve the assignment digest `c0e6689f78d878237adb7689c0f5b39980bb547ab3bbd83efe4e7b4e639fe024`. This split is not claimed publisher-mandated or statistically optimal. |
| Test handling | Freeze code, feature transform, candidate universe, retrieval/ranking method, tie-break, metric definitions, and seeds before test scoring. Use pilot/development only for any choices. Keep test labels inside the evaluator store. | Test org labels must not be used for feature or parameter choices. After a frozen run, test evaluation is permitted and must be recorded as a one-shot confirmatory report; reruns after changes are exploratory. |
| B0 without severity | Amend B0 to an offline deterministic comparator: same-org grouping by exact equality of permitted, non-identifying entity type/value only when an approved transform exists; rank gold-group oracle candidates by distinct alert count for ranking-only diagnostic. | **Amendment A6.** No severity is imputed from `DetectorId`, queue rank, grade, or outcomes. Because entity values remain denied, the first measurable B0 may be limited to count-only ranking under oracle groups and must be labeled as such. Do not call it a severity baseline. |
| LLM services | Keep all providers offline; do not call hosted APIs. | Project constraint remains. B2/B3 and C/P/V empirical LLM comparisons are not cleared by this protocol. Synthetic stub results remain plumbing checks only. |

## 2. Frozen experiment definitions

### 2.1 Priority retrieval

1. Build one candidate per distinct composite incident key in the frozen local candidate universe.
2. Construct candidate text only from the five approved descriptor fields in `configs/empirical_field_policy.yaml`; exclude evaluator fields and every join key.
3. Use deterministic BM25 as the first non-generative ranking baseline. The query is a deterministic organization-level profile built from the same permitted descriptors from that organization’s non-test data only. Freeze the query construction and BM25 parameters before opening test labels. If the existing BM25 implementation cannot express this task without labels, do not adapt it by reading labels; implement a separate evaluator-blind candidate scorer or report the method unavailable.
4. For diagnostic ceiling only, use evaluator gold incident groups to aggregate alert evidence and label the output **oracle-group ranking**. This measures priority ordering conditional on perfect incident grouping; it is not end-to-end system performance.
5. Score top-20 set membership with Precision@10, Recall@20, and set-based nDCG@20. The main P@10/Recall@20 values are invariant to within-top-20 rank direction. For graded nDCG, report both direction interpretations: rank `1` highest, and rank `20` highest. If the scorer supports only one nDCG convention, freeze it as rank `1` highest and prominently mark A1.
6. Report per-organization metrics and macro mean/median. The organization is the unit of analysis; do not treat candidates as independent samples. Bootstrap only over organizations, and do not run significance claims for a single baseline or small pilot.
7. Report candidate-universe counts, top-20 label coverage, unsupported/empty candidates, and the number of organizations excluded by missing candidate evidence. Never silently drop an eligible organization.

### 2.2 Correlation diagnostic

Correlation is allowed only as a restricted sensitivity diagnostic on rows remaining after A3. Ground-truth pairs are derived from evaluator-only incident membership. Model-visible pair evidence must exclude `IncidentId`, `OrgId`, `AlertId`, `Id`, rank, and outcome labels. Organization boundaries are absolute. Use no timestamp windows. Report coverage after ambiguous-key exclusion and per-organization pair counts. Do not call this a complete-set result for the original data, and do not combine with ranking into a joint metric.

### 2.3 Research experiments (Phase 6)

Once the first frozen baseline and metric outputs exist, Phase 6 can run: (a) leave-one-feature-family-out ablations among the five fields; (b) ambiguity exclusion sensitivity (all conflict keys excluded versus unresolved, non-scored control); (c) descriptor masking at fixed 20% and 40% rates with deterministic seeds; (d) tie/order and rank-direction sensitivity; and (e) organization-level plots with all denominators. Do not fabricate perturbations that alter evaluator truth. Do not label a synthetic LLM stub as a real LLM ablation.

## 3. Frozen split and protocol fingerprints

- Phase 2 split assignment SHA-256: `c0e6689f78d878237adb7689c0f5b39980bb547ab3bbd83efe4e7b4e639fe024`.
- Split sizes: 10 pilot / 10 development / 30 test; 50 sampled organizations from 499 eligible organizations.
- Split config salt: `CNET-Phase2-org-split-2026-11-08`; seed: `0`.
- Source hashes are recorded in the Phase 1/2 manifests and readiness review. Recheck both raw file hashes before every empirical run.
- The Phase 2 `split_manifest.json` currently has blank `salt` and `salt_version`; the config plus assignment digest above is the frozen provenance. Do not rewrite the historic Phase 2 artifact. Write a separate freeze manifest that contains the config hash and assignment digest.
- Do not inspect test metric values until method/config hashes and a run manifest have been written. Keep test access evaluator-only.

## 4. Explicitly uncleared claims

This protocol does **not** establish the exact local active-queue snapshot, numeric rank semantics from the publisher, the semantics of `Id`, the meaning of conflicting alert IDs, event-time validity, field-level privacy approval by the dataset owner, detector severity, or download-event provenance. It does not clear empirical LLM comparisons, citation review, operational latency/cost claims, or full end-to-end joint correlation/prioritization. Any future source-owner clarification supersedes the corresponding assumption in a versioned protocol amendment.

## 5. Reproducibility and reporting

- Offline only; no API keys, network model calls, remote telemetry, or dependency installation.
- Pin the Python interpreter and config/code hashes in each run manifest; record seeds and deterministic tie-break rules.
- Use a fresh, immutable output directory per run; refuse overwrite.
- Keep row-level sensitive artifacts under ignored `data/`; commit only aggregate reports that pass disclosure review.
- Verify raw input SHA-256 before and after processing. Processing must read raw data only.
- Label outputs as `assumption_based_local_empirical`, and distinguish them from verified-source benchmark results and synthetic plumbing checks.
- Every graph must include the evaluated organization count, metric denominator, confidence interval method, and the A1/A2/A3/A4/A5/A6 caveats.

## 6. Sources

- Microsoft publisher release and license evidence recorded in [`readiness_evidence_review.md`](readiness_evidence_review.md): https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction
- Primary AIP paper, Sections 5.1 and 5.5: https://arxiv.org/html/2607.16963v1
- CDLA-Permissive-2.0: https://cdla.dev/permissive-2-0/
