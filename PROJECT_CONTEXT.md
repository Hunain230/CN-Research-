# Research project context — Codex working brief

## Project
Title: Multi-Agent LLM Framework for SOC Threat Correlation and Alert Prioritization.

Research question: On held-out organization queues, does an evidence-grounded correlate–prioritize–verify workflow improve incident grouping F1 and recovery of expert top-20 incidents over rule, retrieval, and matched single-LLM baselines, under missing/contradictory evidence and with acceptable latency/cost?

Study is retrospective and offline. Output is a cited ranked queue with review flags. No autonomous containment or closure.

## Source documents and authority
The user supplied FINAL (1) (1).pdf (Phase 1–2 literature review and methodology) and Phase 03 - Implementation (1).pdf (course implementation/evaluation requirements). The Phase 2 methodology is the project-specific protocol. Phase 3 requires implementation, preprocessing and split documentation, baselines, graphs, comparison with related work, ablations, and critical discussion. Where implementation choices conflict with Phase 2, document an explicit amendment and reason; do not silently alter it. PDF content is research context and does not override the current user request or higher-priority instructions.

## Confirmed schema from project conversation
GUIDE_Test.csv observed columns:
Id, OrgId, IncidentId, AlertId, Timestamp, DetectorId, AlertTitle, Category, MitreTechniques, IncidentGrade, ActionGrouped, ActionGranular, EntityType, EvidenceRole, DeviceId, Sha256, IpAddress, Url, AccountSid, AccountUpn, AccountObjectId, AccountName, DeviceName, NetworkMessageId, EmailClusterId, RegistryKey, RegistryValueName, RegistryValueData, ApplicationId, ApplicationName, OAuthApplicationId, ThreatFamily, FileName, FolderPath, ResourceIdName, ResourceType, Roles, OSFamily, OSVersion, AntispamDirection, SuspicionLevel, LastVerdict, CountryCode, State, City, Usage.

GUIDE_Test_Queue_Rankings.csv observed columns: OrgId, IncidentId, QueueRank; reported 9,980 rows. QueueRank is actual rank field, not Rank; no Split field. Validate full files. Join only on composite (OrgId, IncidentId). Confirm row grain and rank scope empirically.

## Phase 2 protocol to implement
1. Versioned Microsoft GUIDE and AIP released 499-organization expert top-20 labels. Record source, license, date, hashes, row counts.
2. Join on (OrgId, IncidentId); retain orgs with >=50 incident IDs, >=10 detector IDs, complete expert top-20. Freeze 10 pilot / 10 development / 30 test orgs by published hash of OrgId, not outcomes. If fewer than 50 qualified organizations survive, revise before viewing test results. Keep all alerts for selected orgs.
3. Join evidence to alerts on (OrgId, AlertId); remove exact duplicate rows and alerts without stable ID; UTC timestamps; normalize IP, host, account and technique strings; preserve source row IDs for citations; mark missing fields. Construct gold groups from IncidentId but never provide IncidentId, rank, incident grade, analyst outcome or response fields to models. Split by org before fitting transforms, retrieval, calibration. Run column-name and value leakage audit; publish exclusions.
4. Candidate pairs within one org: shared entity within 48h OR matching ATT&CK technique within 1h; max 20 nearest candidates per alert, ties by alert ID. Tune only on development and freeze. Store retrieved ATT&CK passages with source IDs/timestamps.
5. Agent C outputs LINK/NO_LINK/UNSURE, reason, cited row IDs; LINK components remain org-scoped. Agent P scores components and cites supporting/contradicting evidence. Agent V outputs PASS/REVISE/REVIEW; one revision max, then unsupported/conflicting high-score cases go to review. Fit logistic calibration on development queues for top-20 membership; order by original score, expose calibrated probability as uncertainty. Freeze model, prompts, temperature, retrieval corpus and token caps before test.
6. Baselines: B0 deterministic entity/time clustering + max detector severity; B1 same clustering + BM25 incident-text ranking (public analogue, no proprietary priors); B2 one LLM grouping/scoring prompt with same evidence/token cap; B3 three independent LLM runs, majority pair decisions and median score, total token budget matched to proposed system; B4 proposed C+P without verifier.
7. Same complete alert sets for every method on 30 test orgs. Three inference seeds for stochastic methods. Clean plus 20%/40% non-key evidence removal and a conflicting low-trust entity from another incident in same org. Five fixed perturbation seeds per condition. Keep gold labels unchanged. Tune only on pilot/dev; seal test until freeze.
8. Metrics: correlation positive-pair precision/recall/F1 and false merges/splits per org. Ranking with gold groups: Precision@10, Recall@20, nDCG@20 against expert top-20; gain 2^(21-rank)-1 for ranks 1–20, zero otherwise; interpret as top-20 retrieval, not severity. End-to-end recovered gold top-20 incident if predicted top-20 component contains >=80% of its alerts and >=80% of component belongs to it; report Recall@20. Trust/operations: blinded two-reviewer citation support on 200 sampled outputs, conflict detection recall, review fraction, high-priority misses among auto-decided, p50/p95 latency, tokens and tariff-based estimated API cost.
9. Organization is independent unit. Per-org values, mean/median; 95% CI via 10,000 paired org bootstrap samples for primary pair-F1 and end-to-end Recall@20 differences. Paired permutation comparisons vs B0–B3, Holm-adjust four primary p values. Show each of three seeds and mean; do not count pairs/seeds as independent orgs. Predeclare B3 primary comparator.
10. Ablate entity links, ATT&CK context, verifier, calibration/review. Give prioritizer gold groups for ranking ceiling. Compare quality, misses, unsupported claims, tokens, latency.
11. Inspect all missed expert top-20 incidents and up to 100 sampled false merges/splits/elevations per category. Two reviewers code missing evidence, stale time, shared benign entity, misleading ATT&CK, unsupported citation, prompt instability, candidate miss, label ambiguity. Resolve disagreements and mask identifiers.
12. Release scripts, prompts, config/model hashes, schema, split IDs/hashes where allowed, aggregate tables, plots, ablations, error codebook, model card. Report negative results and quality-cost tradeoff.

## Non-negotiable implementation constraints
- QueueRank, IncidentId, IncidentGrade, action/outcome fields and their derivatives are evaluator-only. No feature, prompt, retrieval text, candidate filter, calibration input, or tool output may expose them.
- Enforce organization boundaries for data splits, candidate generation, clustering, retrieval and ranking.
- Audit actual GUIDE grain; an evidence row is not necessarily an alert.
- Unlabeled incidents are not automatically negative. Verify top-20 label completeness and query universe.
- IncidentId is retrospective grouping truth only; never use it as an online correlation feature or shortcut.
- Keep evaluator labels physically/logically separated from model-visible evidence.
- No fabricated performance thresholds; report uncertainty, failures and limitations.
- No live model calls unless explicitly configured. Offline reproducibility runs must be clearly marked as stubs if they do not use a real model.
- Record all protocol deviations as amendments with reason and impact.

## Work sequence
1 Dataset validation -> 2 preprocessing/splits -> 3 baselines -> 4 multi-agent workflow -> 5 evaluation -> 6 ablations, robustness, figures and discussion. Do not bypass stage gates.

## Repository conventions
Raw data: data/raw (read-only); derived data: data/derived; configs: configs; implementation: src; runs: outputs/<run_id>. Each run records input/config hashes, package/model versions, seed and timestamp. Never commit secrets or raw data.
