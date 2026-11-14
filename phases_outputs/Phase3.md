# Phase 3 — Baseline systems (synthetic implementation)

## Scope and specification

Implemented the Stage 3 baseline plumbing described in [03_Baselines.md](../03_Baselines.md). The requested `phases_outputs/Phase3.md` did not exist before this work, so the project-root specification was used and this file records the result. Phase 1 and Phase 2 remain the verified data baseline. This phase produced no empirical results and did not read GUIDE or evaluator records during synthetic execution.

Implemented B0 deterministic rule clustering, B1 BM25 retrieval, B2 single-call interface with a deterministic offline stub, and B3 three-call repeated single-LLM control. The shared typed contract rejects prohibited field names and prohibited field lineage, enforces same-organization candidate access, and validates output citations, scores, uncertainty and schema. Model calls remain offline; no dependencies were installed (standard library only).

## Files added or changed

- `src/baselines/`: shared boundary/schema validation, deterministic rules, BM25, B2/B3 orchestration, offline stub provider and runner.
- `src/cli.py`: `baseline-self-test` and `run-baselines` commands.
- `configs/baselines.yaml`, `configs/rules.yaml`, `configs/bm25.yaml`, `configs/llm_baseline.yaml`, `configs/prediction_schema.json`.
- `fixtures/stage3/`: synthetic inputs, expected assertions and usage notes.
- `outputs/baselines/synthetic-final2/`: synthetic results, retrieval probes and run manifest.
- `phases_outputs/Phase3.md`, `PROJECT_ITERATIONS.md`.

## Synthetic implementation behavior

- **B0 rules:** deterministic, same-organization entity/time rules, stable tie handling, a 20-candidate cap and component-size guard. Edges carry synthetic evidence citations. B0's detector-severity component is unavailable because the dataset has no verified severity field or authoritative crosswalk; no severity values or detector ordering were invented. Its priority/ranking component is therefore marked non-runnable.
- **B1 BM25:** standard-library tokenizer and BM25 implementation with configured parameters and deterministic ranking. The synthetic fixture checks fixed expected order/scores and citations. Synthetic corpus fit is explicitly synthetic, not pilot/development fitting on real data.
- **B2:** one-call pipeline contract exercised with an offline deterministic stub. Output is labeled stub plumbing and not LLM judgment or performance.
- **B3:** preserves each of three call outputs; pair decisions combine by configured majority/UNSURE policy; valid scores and uncertainty use the median. The synthetic run allocated 1,000 estimated tokens per call (3 calls = 3,000), matching the configured 3,000-token comparison target. Estimated use was 144 tokens, within budget. Token counts are word-count estimates for stub plumbing, not provider tokenization.
- Evidence content is bounded, treated as untrusted data, and citations must refer to supplied evidence. Labels and outcome fields are denied by name and lineage.

## Commands and results

All commands used the project virtual environment. No external model endpoint was contacted.

```powershell
.\.venv\Scripts\python.exe -m src.cli baseline-self-test
.\.venv\Scripts\python.exe -m src.cli run-baselines --config configs/baselines.yaml --methods rules,bm25,single_llm,repeated_single_llm --mode synthetic --out outputs/baselines/synthetic-final2
.\.venv\Scripts\python.exe -m src.cli run-baselines --config configs/baselines.yaml --methods rules,bm25,single_llm,repeated_single_llm --mode real --out outputs/baselines/real-blocked-final
```

`baseline-self-test` passed 38 synthetic assertions. It verified rule timing/org boundaries, component and candidate caps, citation integrity, BM25 reference scores and empty/no-overlap handling, leakage rejection, B2 malformed/timeout/empty-evidence paths, B3 majority and median behavior, call preservation, budget match and synthetic isolation from raw/evaluator file reads. Python compilation succeeded for all 9 baseline/CLI source files.

The synthetic run completed with classification `synthetic_stub_plumbing_only_not_empirical`, B0 severity unavailable, B1 two synthetic retrieval candidates, B2 one call, B3 three calls, zero live model calls, and B3 matched budget true. The manifest records source/config/input/prompt/output hashes, runtime, seeds, environment, provider version and resource estimates. Output files are under `outputs/baselines/synthetic-final2/`.

The real-data command exited with status 3 and a `ResearchGateBlocked` message. It did not create `outputs/baselines/real-blocked-final/`. It reported the open correlation gate, empty feature view, unverified priority label scope/completeness, ambiguous alert assignments, provisional/unfrozen split, no approved model-visible fields, unavailable severity source, and no approved live provider configuration.

## Gates and Stage 4 readiness

Baseline code and synthetic plumbing are ready for review. Empirical baselines and comparisons are not ready. Before real-data comparisons, the project must:

1. Approve model-visible fields with point-in-time provenance and privacy review; the feature view currently has zero rows.
2. Investigate the 70,702 conflicting alert-to-incident memberships before correlation or joint evaluation.
3. Verify QueueRank meaning/direction, query universe and top-20 completeness before any priority baseline or evaluation.
4. Supply an authoritative detector severity source/crosswalk or amend the B0 protocol.
5. Seal/freeze the organization split and candidate universe, and document data-use conditions before any live model receives data.
6. Freeze budgets, metrics, prompt/model versions and evaluation protocol before opening held-out test data.

No multi-agent system, real-data baseline, ranking, correlation pair set, metric, or test-set analysis was implemented or produced. Stub outputs must not be described as empirical baseline results.
