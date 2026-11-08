# Phase 4 — Multi-agent system (synthetic implementation)

## Scope and baseline

Implemented Phase 4 requirements from `04-Multi-agent system.md` using the verified Phase 1–3 records. This phase implements Agent C (Correlation), Agent P (Prioritization), Agent V (Verification), deterministic orchestration, strict role schemas, a deterministic offline provider, and synthetic regression checks. It is plumbing only; no research performance was measured.

Synthetic mode reads its input fixture from `fixtures/stage4/`, plus the run config and versioned schemas. It does not read raw GUIDE, evaluator data, or Phase 1–3 derived data. The provider is deterministic and offline; the manifest records zero live calls. No dependency was added.

## Implementation

- `src/agents/common.py` enforces deny-by-default field names, value sentinels, synthetic-only lineage, organization scope, allowed fields, candidate/evidence/token caps, strict JSON duplicate-key/non-finite rejection, strict C/P/V response shapes, citations, and bounded retry.
- `src/agents/correlation.py` evaluates only supplied same-org pairs and returns LINK/NO_LINK/UNSURE with reason, uncertainty and evidence references.
- `src/agents/prioritization.py` returns uncalibrated relative scores with supporting/contradicting citations; missing evidence abstains to review.
- `src/agents/verification.py` verifies claims against only the supplied immutable evidence subset and recognizes supported, unsupported and unverifiable claims.
- `src/agents/orchestrator.py` runs deterministically in sorted order, constructs components from LINK edges only, hashes component keys from opaque keys/run salt, enforces a component size limit, records per-pair idempotency keys and retries, permits one revision, and routes unresolved or missing-evidence cases to REVIEW.
- `src/agents/providers/offline_stub.py` supplies deterministic synthetic behavior only. No external adapter, credentials, network call or automatic mode fallback is present.
- `configs/agents.yaml`, role configs, orchestration config and 10 versioned JSON schemas define the synthetic protocol and contracts.
- `fixtures/stage4/` contains synthetic examples, expected decisions and an instruction-like evidence string used to check that evidence is treated as data.
- `src/cli.py` exposes `agent-self-test` and `run-agents`.

## Commands and results

```powershell
.\.venv\Scripts\python.exe -m src.cli agent-self-test
.\.venv\Scripts\python.exe -m src.cli run-agents --config configs/agents.yaml --mode synthetic --out outputs/agents/synthetic/phase4-synthetic-final4
.\.venv\Scripts\python.exe -m src.cli run-agents --config configs/agents.yaml --mode real --out outputs/agents/real-blocked-final
```

- `agent-self-test`: **pass, 34 synthetic assertions**, zero live calls. Coverage includes LINK/NO_LINK/UNSURE, missing/shared/conflicting evidence, exact 48-hour boundary, organization isolation, citation and lineage rejection, LINK-only unions, deterministic component keys, size guard, P/V scores and statuses, malformed JSON/duplicate keys/NaN/Infinity, bounded retry, one-revision limit, budgets, sentinel rejection, and deterministic replay.
- Source compilation succeeded for 9 Python files; all 10 JSON schema files parsed successfully.
- Synthetic run `outputs/agents/synthetic/phase4-synthetic-final4/`: 4 candidate pairs, 4 components, 10 role calls, estimated 2,500 tokens, 1 revision, 1 component routed to REVIEW, zero failures/retries/truncations, and `live_model_calls: 0`. Token usage is a configured estimate, not provider tokenization. The manifest records fixture/config/code/schema/prompt/output hashes, environment, runtime, provider version and resource totals.
- Real mode exited with `ResearchGateBlocked` (status 3) and created no output directory. It names the open feature, alert-membership, ranking-scope/completeness, split and live-provider gates.

## Limitations and remaining research gates

The offline provider demonstrates schema and control-flow behavior only. Its synthetic decisions and scores are not model outputs or performance. Timeout/retry mechanics are exercised with deterministic injected functions in the self-test; the normal offline run has no failures. The current verifier checks support against supplied synthetic signals and cannot establish truth against gold labels. No comparison with B0–B3 or the proposed system is possible yet.

Empirical agent experiments remain blocked until the project approves point-in-time-safe model-visible fields with provenance/privacy review; resolves the 70,702 conflicting alert-to-incident assignments; verifies QueueRank meaning, direction, query universe and top-20 completeness; resolves duplicated `Id` semantics; freezes the organization split, candidate generation, prompts, model/version, metrics and budgets; documents data-use terms for any future live provider; and supplies authoritative detector severity or amends the B0 protocol. Correlation and joint evaluation remain no-go, priority evaluation remains blocked, and no held-out test labels may be inspected or tuned on.

No raw data or Phase 1–3 derived artifacts were modified. No real correlation pairs/results, priority scores/rankings, metrics, or test-set analysis were produced.
