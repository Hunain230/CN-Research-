# CNET Research: SOC Threat Correlation and Alert Prioritization

**Phase 3 submission update (2026-11-13):** The [hybrid implementation report](submission/FINAL_REPORT.md) now documents a full ranked GUIDE_Test offline pass and a bounded localhost `qwen2.5:3b` C/P/V prototype. The [reproduction guide](submission/REPRODUCE.md), [limitations](submission/KNOWN_LIMITATIONS.md), and [fictional dashboard simulation](dashboard/simulation.html) accompany it. Both empirical runs are exploratory; the full offline candidate rule missed the 99% recall target by a wide margin. The raw GUIDE export is retrospective research data, not a live feed.

This repository contains the implementation and audit records for a retrospective research study of alert correlation and incident prioritization in Microsoft GUIDE. The proposed workflow is correlate–prioritize–verify (C/P/V), compared with rule, retrieval, and single-LLM baselines when empirical gates permit.

**Earlier status (2026-11-11):** The [Phase A gate decision](phases_outputs/PhaseA_Implementation_2026-11-11.md) remains no-go for confirmatory evaluation and production use. Its validation candidate recall was 80.37% at about 67.00% pair coverage, below the stated 99% retrieval target. The [then-current offline joint comparison](phases_outputs/Offline_Joint_Comparison_2026-11-11.md) is exploratory and uses deterministic/statistical proxies: its best reported end-to-end Recall@20 was 11.75%, with a 1,140-label denominator. B2, B3, B4, and the proposed LLM C/P/V workflow were not measured in that comparison. An earlier [GUIDE rerun](outputs/guide_rerun_v2/report.md) reported 97.21% **oracle-group candidate** recall at K=500, a different metric. The bounded Groq authorization recorded for that historical rerun does not authorize new hosted calls. No confirmatory end-to-end C/P/V result or military certification exists.

## Start here

For the current handoff, use this map:

1. [Repository map](cleanup/REPOSITORY_MAP.md) — source, config, data, output, and dashboard locations; [cleanup log](cleanup/CLEANUP_LOG.md) records this navigation update.
2. [Phase A implementation and gate decision](phases_outputs/PhaseA_Implementation_2026-11-11.md) — latest readiness decision; [offline joint comparison](phases_outputs/Offline_Joint_Comparison_2026-11-11.md) — latest matched exploratory metrics.
3. [phases_context.md](phases_context.md) — phase index; [research gate register](phases_outputs/research_gate_register.csv) — per-gate status.
4. [dashboard/index.html](dashboard/index.html) — static aggregate Phase 6 viewer; [dashboard/simulation.html](dashboard/simulation.html) — separate fictional playback. Neither is a live SOC dashboard.

Before changing research behavior, read these records in order:

1. [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) — research question, protocol, and non-negotiable safeguards.
2. [phases_context.md](phases_context.md) — concise phase and readiness index.
3. [phases_outputs/UNBLOCKED.md](phases_outputs/UNBLOCKED.md) — latest readiness findings and remaining decisions.
4. [phases_outputs/research_gate_register.csv](phases_outputs/research_gate_register.csv) — status and action for each research gate.
5. The relevant phase record in `phases_outputs/` and its implementation specification in the repository root.

The detailed authoritative-source review is [phases_outputs/readiness_evidence_review.md](phases_outputs/readiness_evidence_review.md). The research protocol and evaluator requirements are in [02_preprocessing.md](02_preprocessing.md), [03_Baselines.md](03_Baselines.md), [04-Multi-agent system.md](04-Multi-agent%20system.md), and [05-Evaluation.md](05-Evaluation.md).

## Repository contents

| Path | Purpose |
|---|---|
| `data/raw/` | Supplied GUIDE and queue-ranking CSVs. Read-only; do not commit. |
| `data/derived/audit/` | Phase 1 aggregate validation reports and schema. |
| `data/derived/preprocessing/` | Phase 2 restricted evidence ledger, evaluator-only store, schema-only feature view, provisional split, and review artifacts. Ignored by Git. |
| `configs/` | Versioned field policies, phase configuration, and JSON schemas. |
| `fixtures/stage2/` … `fixtures/stage5/` | Small synthetic cases and hand-checkable expectations. |
| `src/` | CLI, preprocessing, baselines, agents, evaluation, and the aggregate ambiguity diagnostic. |
| `outputs/` | Run-specific synthetic outputs and manifests. |
| `phases_outputs/` | Phase completion reports, readiness decisions, and proposed amendments. |

Use `.venv` for all project commands. The project uses Python 3.12.10 in the recorded runs and currently needs only the Python standard library; see [requirements.txt](requirements.txt). Never put secrets or sensitive derived data in source control.

## Data baseline

The supplied raw files and Phase 1 hash baseline are:

| File | Rows | SHA-256 |
|---|---:|---|
| `data/raw/GUIDE_Test.csv` | 4,147,992 evidence rows | `fdfd7523efd6e3c26bd0290ba6acbcb237196cf923dd56a28e96802035db35a3` |
| `data/raw/GUIDE_Test_Queue_Rankings.csv` | 9,980 labels | `e4ea9308f45821128a3cd446ab19e6559edfc50709e72034ce957b6f0e2e65d6` |

GUIDE rows are evidence rows; one row must not be treated as one alert. `Id` is not unique at this grain, so Phase 2 assigned stable `source_row_ordinal` values. Join incident labels only on `(OrgId, IncidentId)` and start from distinct incident keys so evidence multiplicity cannot multiply labels.

Phase 1 found 303,220 distinct composite incident keys, 637,320 composite alert keys, and 70,702 alert keys with conflicting incident assignments. The Phase 2 restricted review artifact preserves all conflicting assignments and their source-row ordinals. A later aggregate investigation counted 150,743 distinct assignments across those conflict keys and 830,109 evidence rows. Repeated evidence does not explain why one alert key maps to multiple incidents; no mapping has been selected, voted, discarded, or converted into pair truth.

All 9,980 queue labels join to distinct composite incident keys. The publisher and primary AIP paper document a queue-relative expert top-20 selected from a full eligible queue, not triage outcomes. Local structure is consistent with the documented 499 queues and 20 labels per queue. Still unresolved are numeric rank direction and how the publisher's `Rank`/`Split` and full active-queue definition correspond exactly to the local `QueueRank` file, which has no `Split` column. The 293,240 unmatched GUIDE incidents are unlabeled, not negative examples. Source links and precise findings are in the [readiness evidence review](phases_outputs/readiness_evidence_review.md).

## Current Phase 6 follow-on status

See [the Phase 6B–6G handoff](phases_outputs/Phase6B-G.md). Module records: `Phase6B.md`, `Phase6C.md`, `Phase6D.md`, `Phase6E.md`, `Phase6F.md`, and `Phase6G.md` under `phases_outputs/`. The interactive aggregate dashboard is [dashboard/index.html](dashboard/index.html). The final offline bundle is under `outputs/phase6/phase6-final-offline-20261109-v4/`, with a portable [ZIP archive](outputs/phase6/phase6-final-offline-20261109-v4.zip).

## Phase status

| Phase | Implemented | Empirical status |
|---|---|---|
| 1 — Dataset validation | Full CSV schema, grain, keys, timestamps, nulls, duplicate and rank integrity, composite joins, eligibility, and privacy-safe reports. | Verified local data baseline; important research questions remain open. |
| 2 — Preprocessing | Stable source ordinals, restricted evidence ledger, isolated evaluator labels, preserved ambiguity provenance, deny-by-default field export, provisional organization split. | Ran on raw files. Feature view remains empty; split is provisional; no final pairs or model inputs. |
| 3 — Baselines | Deterministic rule clustering, BM25, B2 single-call and matched-budget B3 orchestration with offline stub. | Synthetic plumbing only; no GUIDE features or empirical baseline results. B0 severity unavailable. |
| 4 — C/P/V agents | Strict schemas, organization boundaries, citation checks, LINK-only components, one verifier revision, deterministic offline provider. | Synthetic plumbing only; zero live model calls and no real agent results. |
| 5 — Evaluation | Isolated truth reader, metric functions, statistical procedures, synthetic fixtures, and closed real-data gate. | Synthetic checks only; no real metrics, p-values, rankings, test analysis, or conclusions. |

Phase details, commands, and acceptance results are recorded in [Phase1](phases_outputs/Phase1.md), [Phase2](phases_outputs/Phase2.md), [Phase3](phases_outputs/Phase3.md), [Phase4](phases_outputs/Phase4.md), and [Phase5](phases_outputs/Phase5.md).

## Setup

From PowerShell at the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `.venv` already exists, activate it with `\.venv\Scripts\Activate.ps1` or call `.\.venv\Scripts\python.exe` directly. No network/model credentials are required. No external model provider is configured.

## Commands

### Phase 1: validate raw files

```powershell
.\.venv\Scripts\python.exe -m src.cli validate --alerts data/raw/GUIDE_Test.csv --rankings data/raw/GUIDE_Test_Queue_Rankings.csv --out data/derived/audit --chunk-rows 250000 --config configs/validation.yaml
```

### Phase 2: preprocessing and boundary checks

```powershell
.\.venv\Scripts\python.exe -m src.cli self-test-phase2
.\.venv\Scripts\python.exe -m src.cli preprocess --alerts data/raw/GUIDE_Test.csv --rankings data/raw/GUIDE_Test_Queue_Rankings.csv --audit data/derived/audit --config configs/preprocessing.yaml --out data/derived/preprocessing --seed 0
.\.venv\Scripts\python.exe -m src.cli check-leakage --features data/derived/preprocessing/feature_view.csv --policy configs/field_policy.yaml --audit data/derived/preprocessing/leakage_audit.json
.\.venv\Scripts\python.exe -m src.cli check-splits --manifest data/derived/preprocessing/split_manifest.json --expected 10,10,30
```

The preprocessing output contains restricted identifiers and evaluator truth. Do not export or commit it. Re-running preprocessing may overwrite or conflict with the existing output; read the CLI/config behavior and current artifacts before attempting another run.

### Restricted alert-membership aggregate

```powershell
.\.venv\Scripts\python.exe -m src.investigate_ambiguous_memberships
```

This diagnostic reads only `data/derived/preprocessing/review/ambiguous_alert_memberships.csv` and writes aggregate counts to the adjacent `conflict_investigation_aggregate.json`. It does not print assignment identifiers or create correlation pairs.

### Phase 3–5 synthetic plumbing

```powershell
.\.venv\Scripts\python.exe -m src.cli baseline-self-test
.\.venv\Scripts\python.exe -m src.cli run-baselines --config configs/baselines.yaml --methods rules,bm25,single_llm,repeated_single_llm --mode synthetic --out outputs/baselines/synthetic-run

.\.venv\Scripts\python.exe -m src.cli agent-self-test
.\.venv\Scripts\python.exe -m src.cli run-agents --config configs/agents.yaml --mode synthetic --out outputs/agents/synthetic/run

.\.venv\Scripts\python.exe -m src.cli evaluation-self-test
.\.venv\Scripts\python.exe -m src.cli evaluate --mode synthetic --predictions fixtures/stage5/predictions.json --labels fixtures/stage5/labels.json --config configs/evaluation.yaml --out outputs/evaluation/synthetic/run
```

Use a new output directory for each run. Synthetic artifacts are fixtures/stubs for implementation checks, never empirical results. Real-mode commands intentionally fail closed under the current gates; do not try to bypass them.

### End-to-end synthetic MVP demonstration

This separate fictional fixture connects the deterministic Phase 4 C/P/V stub to the existing evaluator metrics and writes a dashboard event trace. It is a software integration demonstration only; the stub scores and fixture metrics are not empirical performance.

```powershell
.\.venv\Scripts\python.exe -m src.mvp_demo self-test
.\.venv\Scripts\python.exe -m src.mvp_demo run --run-id mvp-demo-new-id
```

The run writes predictions and a freeze file before opening the separate fictional truth fixture. Outputs go to a new directory under `outputs/mvp/`; run IDs cannot overwrite prior runs. See [the synthetic MVP fixture guide](fixtures/mvp/README.md) and [the completed run record](submission/MVP_SYNTHETIC_RUN.md).

### Phase 6: offline priority-only experiment

This is the separate assumption-based, oracle-group ranking path described in [Phase6.md](phases_outputs/Phase6.md). Use a fresh run ID. Test labels are already accessed, so new runs are exploratory.

```powershell
.\.venv\Scripts\python.exe -m src.empirical_priority predict --root . --out outputs/phase6/priority/new-run-id
.\.venv\Scripts\python.exe -m src.empirical_priority evaluate --root . --run outputs/phase6/priority/new-run-id
.\.venv\Scripts\python.exe -m src.empirical_priority_tie_eval --root . --run outputs/phase6/priority/new-run-id
.\.venv\Scripts\python.exe -m src.plot_phase6_priority --run outputs/phase6/priority/new-run-id --tie-aware

.\.venv\Scripts\python.exe -m src.empirical_correlation predict --root . --out outputs/phase6/correlation/new-run-id
.\.venv\Scripts\python.exe -m src.empirical_correlation evaluate --root . --run outputs/phase6/correlation/new-run-id
.\.venv\Scripts\python.exe -m src.empirical_correlation_report_fix --root . --run outputs/phase6/correlation/new-run-id
.\.venv\Scripts\python.exe -m src.plot_phase6_correlation --run outputs/phase6/correlation/new-run-id
```

Raw candidate-level predictions and opaque evaluator mappings are restricted under ignored `data/derived/empirical/`. Only aggregate reports and figures are written under `outputs/`. The plotting packages are pinned in `requirements.txt`; they were already present in the project `.venv` and were not installed during this run.

## Current empirical status and limits

The user directed the implementation owner to make conservative assumptions where source evidence was missing. Those decisions are documented in the [empirical protocol freeze](phases_outputs/empirical_protocol_freeze.md), and the first priority-only experiment is recorded in [Phase6.md](phases_outputs/Phase6.md). Its held-out results are exploratory, tie-aware, offline, and conditional on oracle gold groups; they are not end-to-end system results or an exact reconstruction of the publisher's active queues.

1. **Local descriptor policy:** `DetectorId`, `Category`, `MitreTechniques`, `EntityType`, and `EvidenceRole` are permitted only for local offline experiments by explicit project assumption. This is not independent publisher/privacy review. Raw entities, timestamps, locations, join keys, grades, outcomes, and queue labels remain denied as model inputs.
2. **Correlation truth:** exclude all evidence for the 70,702 conflicting composite alert keys. A bounded ambiguity-excluded diagnostic exists, but full correlation and joint evaluation remain closed; do not resolve assignments by guessing.
3. **Priority interpretation:** use the local GUIDE candidate universe as an explicit proxy. `QueueRank=1` is assumed highest; report nDCG under both directions. Unranked incidents count as nonmembers only for top-20 retrieval, not as low priority or benign.
4. **Organization split:** freeze the existing Phase 2 10/10/30 assignment by the digest recorded in the protocol manifest. Test labels have already been accessed in the logged evaluator run; future runs are exploratory unless a new held-out dataset is obtained.
5. **GUIDE `Id`:** it is not row-unique. Use `source_row_ordinal` as internal row provenance; never treat `Id` as a unique evidence or citation key.
6. **B0/time:** severity baseline and timestamp-window claims are withdrawn because severity/crosswalk and exact timestamp semantics are unavailable. Any count-only gold-group ranking is an oracle diagnostic, not B0 severity or end-to-end performance.
7. **Evaluator isolation:** labels remain confined to evaluator code/stores; never pass them to a scorer, prompt, feature, or model. The Phase 3–5 real-mode runners are still synthetic-only; the Phase 6 offline ranking path is separate.
8. **External calls:** hosted model calls, external APIs, and data transmission remain unauthorized. Synthetic LLM stubs are not empirical LLM systems.

See the [updated gate register](phases_outputs/research_gate_register.csv), [test-label access log](phases_outputs/test_evaluation_access_log.md), and [tie-metric amendment](phases_outputs/metric_tie_amendment.md) for exact evidence, limitations, and re-analysis history.

## Authoritative references

- [Microsoft Security Incident Prediction dataset documentation](https://www.kaggle.com/datasets/Microsoft/microsoft-security-incident-prediction)
- Freitas, Gharib, and Magenheim, [Adaptive Incident Prioritization for Security Operations at Scale](https://arxiv.org/html/2607.16963v1)
- [CDLA-Permissive-2.0](https://cdla.dev/permissive-2-0/)

