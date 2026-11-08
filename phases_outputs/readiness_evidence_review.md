# Empirical-readiness evidence review

**Review date:** 2026-11-08  
**Scope:** Source and ranking semantics, ambiguous alert memberships, feature eligibility, organization split/protocol, and B0 detector severity. This review did not train or run baselines/agents, inspect test outcomes, produce real predictions/metrics, or call external models. Raw files remained read-only.

## Findings

### 1. Dataset release, license, and ranking task

The publisher's Kaggle API metadata identifies Microsoft as owner, the title as *Microsoft Security Incident Prediction*, and current version 2 with a version update on 2026-07-18. Its version-2 file listing contains `GUIDE_Test.csv` (1,087,963,831 bytes) and `GUIDE_Test_Queue_Rankings.csv` (136,325 bytes); the local files have the same names and byte sizes. Their local SHA-256 hashes match the Phase 1 baseline. The public dataset description says Microsoft releases the dataset under CDLA-Permissive-2.0. This verifies the publisher's release record and license statement, and strongly matches the local file artifacts by filename and size; Kaggle does not publish file checksums in the metadata reviewed, and the repository has no original download receipt/date, so cryptographic provenance from the download event remains unverified.

The primary AIP paper distinguishes prioritization from triage: its labels express queue-relative priority, not incident outcome. It says reviewers sweep the full eligible active queue, select an expert top 20, and that the selected set is drawn from the full queue rather than method outputs or a prefiltered candidate pool. The benchmark's eligibility statement is the GUIDE test split with at least 50 incidents and 10 distinct detectors. The paper reports 499 queues and 9,980 labeled incidents. The publisher page gives the same high-level protocol. Local audit facts are consistent: 499 qualifying organizations, 9,980 ranked incidents, every ranking key joined to a distinct `(OrgId, IncidentId)` key, and 20 distinct rank values for each of the 499 ranking organizations.

**Still unresolved:** the paper and publisher description reviewed do not explicitly state the numeric direction (for example, whether value 1 is the first/highest-priority position). Local `QueueRank` values begin at 1 and span 20, but that is not sufficient authority to infer direction. The local rank file uses `QueueRank` and omits the publisher-described `Split` column, whereas public documentation calls the field `Rank`. The publisher metadata's matching names and sizes support a release match but do not prove a byte-identical download or explain this schema difference. The published query universe is the eligible full active queue in the GUIDE test split; the local GUIDE file and label file do not encode an explicit queue snapshot/active filter or split column, so mapping that definition to the exact local candidate set requires confirmation. The top-20 *set* is documented as expert-selected and complete for the publisher's defined eligible queues, but ranks are not full rankings of all incidents. The remaining 293,240 local GUIDE incidents without a ranking row are unjudged, not negatives.

### 2. Conflicting alert membership

The restricted Phase 2 investigation artifact `data/derived/preprocessing/review/ambiguous_alert_memberships.csv` preserves all conflict assignments and source-row ordinals. A bounded aggregate pass found:

| Diagnostic | Count |
|---|---:|
| Conflicting composite `(OrgId, AlertId)` keys | 70,702 |
| Distinct alert-to-incident assignment groups within those keys | 150,743 |
| GUIDE evidence rows attached to those keys | 830,109 |
| Assignment groups repeated across multiple evidence rows | 149,239 |
| Conflict keys with at least one repeated assignment | 69,982 |
| Conflict keys with exactly one source row per distinct assignment | 720 |

Repeated evidence is therefore common among conflicting keys, but it cannot explain why a single composite alert key receives multiple distinct incident assignments. Phase 2 parsed all 4,147,992 GUIDE rows without malformed CSV rows; that does not rule out semantic errors. The sources reviewed do not define whether reuse of an alert key across incidents is permitted. The overlap between conflict keys and the 104 exact full-row duplicate groups was not calculated. No selection, vote, exclusion, or pair label was created. The aggregate is `data/derived/preprocessing/review/conflict_investigation_aggregate.json`; the identifier-bearing source/provenance artifact remains restricted under ignored `data/` storage.

**Resolution needed:** Microsoft/publisher confirmation of the intended `(OrgId, AlertId)` to incident relationship and duplicate-row semantics, or a researcher/data-owner approved exclusion policy justified without arbitrary incident selection. Until then, correlation and joint evaluation remain no-go.

### 3. Feature eligibility

No field was newly allowlisted. The field-by-field Phase 1 decisions and rationales are in [`field_disposition.csv`](../data/derived/audit/field_disposition.csv); `configs/field_policy.yaml` remains deny-by-default with an empty approved field list, and `feature_view.csv` remains schema-only with zero rows. In that field review, candidate context fields remain pending timing/provenance/safe-encoding confirmation; high-cardinality entities/locations remain denied for privacy review and approved transformation; potential post-event fields remain denied pending timing/provenance; and join keys and evaluator outcomes remain prohibited. The publisher documentation says timestamps are perturbed for privacy, so timestamps cannot be treated as exact event time without a documented adjustment and reviewed use case. Identifier/entity values being scrubbed does not itself approve model use.

**Approval needed:** a researcher/data owner/privacy reviewer must approve a field-by-field allowlist with source definition, temporal availability, transform, citation lineage, privacy/data-use basis, and leakage audit. Until then, no feature export may contain data rows.

### 4. Organization split and protocol

The publisher's numeric eligibility criteria and the local audit both support 499 eligible organization queues; local ranking labels form 499 groups of 20 matched incidents. This is enough organizations for the proposed 10 pilot / 10 development / 30 test counts numerically. The Phase 2 assignment remains provisional: the exact selection/hash procedure has not been reconciled with a published protocol rule, the local release/schema correspondence and numeric rank direction are unresolved, and the query/candidate universe and test-access freeze have not been signed off. No test-label outcomes were inspected during this review, and no split assignments or labels were changed.

Before test access, the researcher must approve and hash the organization selection rule, query snapshot/universe, candidate generation, unjudged-item treatment, all metric/abstention/failure denominators, method/config versions, and test-seal process. Preserve the Phase 2 split as provisional until that freeze is complete. Do not treat unlabeled incidents as negatives.

### 5. B0 detector severity

The local observed GUIDE schema has no severity column. The AIP paper describes severity as one production component and evaluates a max-severity baseline in a separate production experiment, but that does not provide a severity value or authoritative `DetectorId`-to-severity crosswalk for the local public GUIDE files. Detector IDs must not be ordered or converted to severity. B0 severity is unavailable for this dataset.

`phases_outputs/proposed_B0_protocol_amendment.md` proposes removing the unsupported severity component and defining B0 as deterministic entity/time clustering only. It is **not approved** and must not be implemented for empirical comparison until the researcher approves the amendment or supplies an authoritative field/crosswalk.

## Source evidence (accessed 2026-11-08)

1. [Microsoft Security Incident Prediction, Kaggle publisher page](https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction), including current description, release metadata, file listing, privacy description, and license. Exact publisher statements reviewed: “queue-relative priority, not triage outcome”; the extension contains “expert-derived priority rankings for 9,980 incidents across 499 organization queues”; files describe the `Rank` ordering; Microsoft releases the dataset under CDLA-Permissive-2.0. Current metadata reports version 2, updated 2026-07-18, and file sizes matching the local files.
2. Freitas, Gharib, and Magenheim, [“Adaptive Incident Prioritization for Security Operations at Scale,” arXiv HTML](https://arxiv.org/html/2607.16963v1), especially Sections 5.1 and 5.5. Exact statements reviewed include “full-queue sweep over all active incidents” and top-20 selection “from the full queue”; Section 5.5 documents the GUIDE test-split eligibility (at least 50 incidents and 10 detectors), 499 queues, 9,980 labeled incidents, expert ranking, and queue-relative priority rather than triage outcome. Neither reviewed section explicitly states which numeric rank value is highest.
3. [CDLA-Permissive-2.0 official license](https://cdla.dev/permissive-2-0/). The publisher specifies this license for the Kaggle release.

No secondary summaries were used as evidence for the conclusions above.

## Reproducibility record

Run environment: repository `.venv`, Python 3.12.10, Windows 11. Reproduce the aggregate with `\.venv\Scripts\python.exe -m src.investigate_ambiguous_memberships`; the utility streams the already-produced restricted ambiguity artifact and prints aggregate counts only. It does not read raw inputs or write identifiers into its output. No dependency was installed, and no raw input was modified.

| Artifact | SHA-256 |
|---|---|
| `data/raw/GUIDE_Test.csv` | `fdfd7523efd6e3c26bd0290ba6acbcb237196cf923dd56a28e96802035db35a3` |
| `data/raw/GUIDE_Test_Queue_Rankings.csv` | `e4ea9308f45821128a3cd446ab19e6559edfc50709e72034ce957b6f0e2e65d6` |
| `configs/field_policy.yaml` | `0636d2f4e4f17edcd5402d67cac291484d3a39493b2c7377b562735771065ee5` |
| `configs/preprocessing.yaml` | `a87d47e61a11721e9d41ee62df225e72040d502ff364ec603bcc15b54c979263` |
| `src/cli.py` | `69a563f06d6968a90b2758d3957dbc803fc2157c1781c1e20654757756723f0f` |
| `src/phase2.py` | `56fa179b1a04e54f14f3ef228bf790e60894ba7838523b4e4666c2b1dbd59129` |
| `src/evaluator_store.py` | `b2a0c8d8792da642530ea7b708e7e0156d150f8cd3e7fa003c6e4136a0548a71` |
| `src/investigate_ambiguous_memberships.py` | `d0225bf018297c848eb81f58f94fb35b0a650abd402ca05781b2c05190293dc3` |
| `data/derived/preprocessing/review/ambiguous_alert_memberships.csv` | `1355ba97e623023faa59c5e78ef90679029ccfbe8346d2ac415ccf57493135a9` |
| `data/derived/preprocessing/review/conflict_investigation_aggregate.json` | `7c2c9522e26b5091e286f6d0c0c6a357c4a2226219fef0ca558c3695e86d9dc8` |

The ambiguity artifact is a restricted derived file and remains under the existing Git-ignored `data/` tree. The separate JSON diagnostic contains aggregates only. No validation/preprocessing artifacts were regenerated or overwritten.

## Decision

Prioritization *preprocessing development* may continue under the current empty-feature and evaluator-isolation controls. No field is approved. Correlation and joint evaluation remain no-go. Real prioritization evaluation remains blocked by numeric rank direction and local release/schema/query-universe reconciliation, along with the provisional split and unfrozen protocol. No real-data evaluation is permitted by this review.
