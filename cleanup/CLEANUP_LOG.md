# Cleanup log (Task 1, 2026-11-12)

## Completion record

Repository navigation was clarified without moving, deleting, or changing any source, config, fixture, raw/derived data, historical report, metric, model, prompt, or experiment output. The working tree was clean at the start. The only task changes are the three documentation files below.

| Changed file | Reason and evidence |
|---|---|
| `README.md` | The opening status was dated 2026-11-09 and did not mention the later Phase A no-go decision or offline joint proxy comparison. Updated it from `phases_outputs/PhaseA_Implementation_2026-11-11.md` and `phases_outputs/Offline_Joint_Comparison_2026-11-11.md`; added direct navigation to current records, this cleanup map, and both dashboard viewers. Older detailed sections remain historical context. |
| `cleanup/REPOSITORY_MAP.md` (new) | Inventory of active/standalone source modules, configs, fixtures, data boundaries, records, outputs, and dashboards. Based on Git inventory, directory listing, CLI entry points, static reference search, and SHA-256 equality of tracked files. |
| `cleanup/CLEANUP_LOG.md` (new) | Records every task edit and the validation below. |

**Moved files:** none. **Deleted files:** none. **Source or behavior changes:** none. Exact-content duplicates in frozen packages and synthetic runs were retained because their paths and manifests carry historical meaning. Uncertain standalone code was retained; static imports and report references show multiple entry points beyond `src.cli`.

## Inventory and duplicate evidence

- `git status --short` was empty before editing; `git ls-files` counted 354 tracked files; `git ls-files -o --exclude-standard` returned no unignored untracked files.
- Local ignored `data/` contained two raw CSVs and 379 derived files. Their contents were not inspected or changed for cleanup.
- SHA-256 was calculated for tracked files only, then grouped by equal digest. Examples: `dashboard/index.html` and four frozen bundle copies share prefix `b4b5569c5f54`; corrected Phase 6 correlation metrics and their bundle copies share `a98fbef31a26`. Similar synthetic run metrics also match by digest. The repository map explains canonical navigation versus frozen/historical copies. No duplicate was deleted.
- `rg` searches of `src`, `README.md`, `phases_context.md`, `phases_outputs`, `dashboard`, `configs`, and `codex_tasks` found standalone CLIs and cross-module imports. No file was marked unused merely for lacking a main-CLI import.

## Validation commands and outcomes

All commands ran from the repository root using the existing `.venv`; no dependency installation or external call occurred.

| Command | Outcome |
|---|---|
| `.\.venv\Scripts\python.exe -m src.cli --help` | Exit 0; documented main CLI resolves. |
| `.\.venv\Scripts\python.exe -m src.cli self-test-phase2` | Exit 0; 23 assertions, synthetic only. |
| `.\.venv\Scripts\python.exe -m src.cli baseline-self-test` | Exit 0; 38 assertions, synthetic stub plumbing. |
| `.\.venv\Scripts\python.exe -m src.cli agent-self-test` | Exit 0; 34 assertions, zero live model calls. |
| `.\.venv\Scripts\python.exe -m src.cli evaluation-self-test` | Exit 0; 64 assertions; real-data gate closed. |
| `.\.venv\Scripts\python.exe -m src.cli phase6a-self-test` | Exit 0; seven protocol checks passed. |
| `.\.venv\Scripts\python.exe -m src.cli phase6b-self-test` | Exit 0; four assertions passed. |
| `.\.venv\Scripts\python.exe -m src.offline_joint_comparison self-test` | Exit 0; seven assertions passed. |

These checks verify import/CLI resolution and existing synthetic or protocol behavior. They do not rerun empirical data or validate research claims. No generated output path or historical artifact was overwritten.
