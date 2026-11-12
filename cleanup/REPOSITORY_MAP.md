# Repository map (Task 1, 2026-11-12)

This is a navigation map, not a new experiment or a change to the research protocol. Paths are relative to the repository root. `git status --short` was clean before this task; Git listed 354 tracked files and no unignored untracked files. `data/` is ignored and contains two raw files plus 379 derived files locally. Do not publish the ignored data tree.

## Read first

| Location | Role |
|---|---|
| `PROJECT_CONTEXT.md`, `phases_context.md` | Research protocol and current phase index. |
| `phases_outputs/PhaseA_Implementation_2026-11-11.md` | Latest readiness decision: Phase A no-go; the 99% candidate-recall target failed. |
| `phases_outputs/Offline_Joint_Comparison_2026-11-11.md` | Latest matched exploratory joint comparison, using offline deterministic/statistical proxies. |
| `phases_outputs/research_gate_register.csv`, `phases_outputs/UNBLOCKED.md`, `phases_outputs/Evaluation_Contract_Decision_2026-11-11.md` | Gate status and unresolved evaluation contract. Interpret older readiness records by their dates. |
| `codex_tasks/00_START_HERE.md`, `codex_tasks/01_REPOSITORY_CLEANUP.md` | Work-plan index and this cleanup task. Later numbered tasks are separate work. |

The root `01_dataset_validation.md` through `06-Research-experiments.md`, plus `6A.md`, are phase specifications. `phases_outputs/Phase1.md` through `Phase6.md`, `Phase6A.md` through `Phase6G.md`, and dated amendments are implementation and decision records. The two root PDFs are supplied background and course documents. Historical records remain intact even where later findings supersede their status.

## Source and entry points

| Location | Role and entry point |
|---|---|
| `src/cli.py` | Main `python -m src.cli` command dispatcher: validation, preprocessing, synthetic baseline/agent/evaluation checks, Phase 6A/B audits, dashboard generation, and packaging. Run `python -m src.cli --help` for exact commands. |
| `src/phase2.py`, `src/evaluator_store.py` | Restricted preprocessing and evaluator separation. |
| `src/baselines/`, `src/agents/`, `src/evaluation/` | Phase 3–5 implementation and offline synthetic checks. The Phase 3/4 synthetic providers are plumbing, not empirical LLM runs. |
| `src/empirical_priority.py`, `src/empirical_correlation.py`, related `empirical_*_tie_eval.py`, `empirical_correlation_report_fix.py`, `plot_phase6_*.py` | Separate Phase 6 exploratory offline analysis and figure CLIs. |
| `src/phase6a.py`, `src/phase6b.py`, `src/phase6f_package.py`, `src/phase6g_dashboard.py` | Protocol/disposition audits, frozen package builder, aggregate dashboard builder. |
| `src/guide_rerun_v2.py`, `src/guide_correlation_v2.py`, `src/guide_report_v2.py` | Historical exploratory GUIDE rerun and its report/dashboard. The prior bounded Groq authorization does not authorize new external calls. |
| `src/offline_joint_comparison.py` | Current v2 offline predicted-group comparison; `src/offline_joint_comparison_v1.py` is a preserved v1 method, referenced by the v1 record. |
| `src/phase_a_*.py` | Phase A coverage, candidate, miss, multi-membership, local entity/title retrieval, and contract audits. Some are standalone CLIs and therefore have no import from `src/cli.py`; retain them. |
| `src/investigate_ambiguous_memberships.py` | Restricted aggregate diagnostic CLI. |

Static source checks found direct imports between some standalone modules (for example, title retrieval imports entity retrieval; Phase A miss/candidate audits import the v2 joint comparison). A file with no import from the main CLI is not thereby unused. No source file was classified as safe to remove, and no source was moved or refactored in this task.

## Configs and synthetic fixtures

| Location | Role |
|---|---|
| `configs/validation.yaml`, `preprocessing.yaml`, `field_policy.yaml` | Phase 1/2 validation and deny-by-default model-field policy. The official approved model-input allowlist is empty. |
| `configs/baselines.yaml`, `rules.yaml`, `bm25.yaml`, `llm_baseline.yaml` | Phase 3 baseline settings. |
| `configs/agents.yaml`, `correlation_agent.yaml`, `prioritization_agent.yaml`, `verification_agent.yaml`, `orchestration.yaml`, `agent_schemas/` | Phase 4 agent settings and schemas. |
| `configs/evaluation.yaml`, `metrics.yaml`, `statistics.yaml`, `prediction_schema.json`, `evaluation_schema.json` | Phase 5 metric/evaluation contract. |
| `configs/phase6_protocol.yaml`, `empirical_field_policy.yaml`, `empirical_priority.json`, `empirical_correlation.json`, `offline_joint_v1.json`, `offline_joint_v2.json` | Phase 6 and later exploratory assumptions and runs. The five-field empirical policy was a local-only assumption, not independent approval. |
| `fixtures/stage1/` through `fixtures/stage5/`, `fixtures/stage6a/` | Small synthetic or protocol test material. Preserve all fixture expectations. |

## Data and outputs

| Location | Handling |
|---|---|
| `data/raw/` | Two supplied GUIDE CSVs. Read-only; ignored by Git. Do not move, edit, or copy to a public artifact. |
| `data/derived/audit/` | Phase 1 aggregate audit and schema. |
| `data/derived/preprocessing/` | Restricted row ledger, ambiguity review, evaluator labels, and split records. |
| `data/derived/empirical/`, `guide_rerun_v2/`, `offline_joint_v1/`, `offline_joint_v2/`, `phase_a_entity_retrieval/`, `phase_a_title_retrieval/` | Restricted derived predictions, candidate or evaluator material. Ignored by Git; do not publish. |
| `outputs/` | Tracked run reports, aggregate metrics, figures, and manifests. Preserve every run, including synthetic, exploratory, amended, and proxy records. `outputs/offline_joint_v2/` is the latest matched proxy comparison; `outputs/phase_a/` contains the latest gate audits. |
| `outputs/phase6/phase6-final-offline-20261109-v4/` and `.zip` | Frozen aggregate-only historical handoff bundle and portable archive; its manifest defines bundle contents. Earlier v1–v3 bundles are historical. |
| `phases_outputs/` | Phase completion reports, amendments, protocol freeze, gate register, and dated decisions. This is the authoritative decision trail, with later dated decisions taking precedence for current status. |
| `dashboard/index.html` | Static aggregate Phase 6 report viewer generated by `src.phase6g_dashboard`. |
| `dashboard/guide_rerun_v2.html` | Historical exploratory GUIDE rerun viewer generated by `src.guide_report_v2`. |

## Duplicate and retention assessment

SHA-256 grouping of all 354 tracked files found exact-content groups. `dashboard/index.html` matches copies in Phase 6 frozen bundles (SHA-256 prefix `b4b5569c5f54`). The corrected correlation metrics match bundle copies (prefix `a98fbef31a26`), as do several phase reports, priority metrics/figures, and synthetic fixture outputs. These are embedded snapshots or separate run histories, not candidates for deletion. The live repository paths above are navigation targets; bundle copies are authoritative **for their own frozen manifests**. Similar filenames without equal hashes were not treated as duplicates. The v1 and v2 joint-comparison scripts and outputs have distinct method histories and are retained.

No raw or restricted files were hashed for duplicate grouping, moved, or changed. Unknown references in historical reports and bundles are left intact. No code was declared unused based on age or CLI import reachability.
