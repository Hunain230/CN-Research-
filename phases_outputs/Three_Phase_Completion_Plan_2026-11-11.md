# Three-phase path to a triage-system submission

**Date:** 2026-11-11. **Current verdict:** research prototype; not production ready. This plan is prospective. A phase receives a measured pass/fail verdict only after its implementation and frozen evaluation run. The target of at least 95% is **end-to-end expert top-20 Recall@20 using predicted incident groups**, not candidate retrieval recall.

## Phase A — Repair the truth contract and retrieval ceiling

**Build:** reconcile the local active-queue definition and numeric QueueRank direction with source evidence; adjudicate or formally retain whole-key exclusions for the 70,702 conflicting alert keys; investigate why 74 top-20 incidents have no in-scope alert in the 57 small-queue comparison. Verify point-in-time availability and data-use terms for each model field. Review whether a privacy-preserving, organization-scoped entity-link transform can be approved; do not use raw entity values or unreviewed hashes. Preserve historical exploratory cohorts. Acquire an independent, unused cohort for a future confirmatory test. Improve CPU-only candidate generation before any LLM call, with same-org multi-route retrieval, bounded volume, deterministic caching, and split-safe fitting.

**Evaluate after Phase A:** rerun full-file hashes/schema and leakage checks; report per-organization queue and label coverage, excluded top-20 labels, candidate-pair recall versus volume at multiple K, candidate misses, RAM/runtime, and uncertainty intervals on development/validation organizations. Use a target of at least 99% positive-pair candidate recall on validation at an affordable volume to leave room for downstream errors. Record a no-go if exclusions make the required final 95% mathematically unattainable. Do not inspect a new confirmatory cohort during tuning.

**Expected readiness verdict:** research data pipeline only; not production ready.

## Phase B — Real matched model and agent comparison

**Build:** add a provider-neutral LLM adapter with strict JSON schemas, prompt/model versioning, retries, rate-limit handling, cache/resume, token and cost ceilings, and hard failure/abstention paths. Keep local retrieval and a CPU-friendly ranker as the default; route only uncertain, bounded cases to an LLM. Implement actual B2 single-call, B3 three-call matched-budget, B4 C+P, and C/P/V methods. Use the amended B0 count baseline unless an authoritative severity source appears; keep B1 label-free. Every method receives the same organization queues, evidence, candidate rules, and evaluator-only labels. Predicted groups, never dataset incident IDs, feed each method's incident ranker. Freeze prompts, thresholds, model versions, and budget before evaluation.

**Evaluate after Phase B:** on validation then one untouched test cohort, report pair precision/recall/F1, false merges/splits, candidate recall, P@10, end-to-end Recall@20, both rank-direction nDCG sensitivities, missed high-priority incidents, review and abstention rates, unsupported citations, malformed responses, latency, tokens, and cost. Include 20%/40% masking, contradictory evidence, no-V and other agent ablations, matched single-LLM controls, and organization-level confidence intervals. The project's aspirational quality gate is end-to-end Recall@20 >=95% with a prespecified confidence bound and pair precision >=95%; failures must be reported, not hidden by changing the denominator or tuning on test results. These are project acceptance targets, not an external certification standard.

**Expected readiness verdict:** experimental model only; no production claim from offline metrics alone. A negative or below-target result can still be submitted as honest research if the paper's claim is narrowed.

## Phase C — Analyst workflow, deployment validation, and paper

**Build:** replace the static aggregate dashboard with an authenticated analyst queue showing predicted incident groups, evidence citations, rank, uncertainty, and REVIEW decisions. Add ingestion, durable state, role-based access, secret management, rate-limit fallback, monitoring, audit logs, feedback capture, rollback, and a deployment/runbook. Never auto-close or contain incidents. Keep model version and decision trace for every case.

**Evaluate after Phase C:** run end-to-end integration and load tests on the full GUIDE_Test volume, privacy/security review, failure and provider-outage drills, reproducible replay, and a shadow-mode analyst pilot. Measure the predeclared latency/throughput SLA, missed high-priority cases, false merges, analyst overrides, citation support, and drift. Repeat the frozen confirmatory evaluation on independent data when available. Assemble the paper with matched results, uncertainty, ablations, figures, negative results, data limitations, source/license details, and reproducible artifacts.

**Production verdict rule:** only human-in-the-loop triage can be considered, and only if the independent test meets the predeclared 95% end-to-end recall and pair-precision targets, operational SLAs, and security/privacy checks. Otherwise the deliverable is a research demonstrator or shadow-mode pilot, not production ready. A paper can be submission ready with transparent negative results even when deployment is not justified.

## Compute and free-provider choice

Groq's limit is driven by account/model requests and tokens, not a fixed record count. Inspect the actual 429 error, `retry-after`, remaining-request/token headers, and account limits to identify the constraint behind the observed ~17,000-record stop. The 2026-11-09 rerun used 176,473 tokens for 68 Groq calls; it is not evidence that another account can process a fixed number of GUIDE rows. Cache by input/prompt/model hash, resume after quota resets, batch compact decisions where valid, and keep bulk retrieval/ranking local. Do not send four million evidence rows to any hosted LLM.

For free hosted experiments, try Google AI Studio's `gemini-2.5-flash-lite` on **approved, sanitized descriptors only**; its standard API has a free tier, but project-specific RPM/TPM/RPD limits apply and free-tier input may be used to improve Google products. This does not provide guaranteed capacity or privacy approval. OpenRouter's `:free` variants have low daily request caps; Hugging Face free Inference Providers credits are small; Mistral's current free mode does not include API access. No free hosted provider is a dependable production capacity plan. If data-use rules prohibit free-tier hosted processing, use local CPU models for the experiment or an approved paid provider for the bounded LLM subset.

**Repository evidence:** `outputs/guide_rerun_v2/report.md`, `outputs/offline_joint_v2/report.md`, `phases_outputs/Evaluation_Contract_Decision_2026-11-11.md`, and `phases_outputs/Offline_Joint_Comparison_2026-11-11.md`.
