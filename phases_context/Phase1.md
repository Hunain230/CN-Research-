# Phase 1 — Dataset validation

## Purpose and scope

Phase 1 checked whether the supplied GUIDE evidence data and GUIDE/AIP queue rankings could support the proposed offline correlation and prioritization study. Work was limited to validation: no preprocessing pipeline, model, baseline, candidate-pair set, or evaluation result was produced. Raw files were read only.

The audit was implemented in `src/cli.py` and run through the repository virtual environment. GUIDE was streamed in bounded batches; identifiers were preserved as strings; per-field cardinality was estimated with fixed-memory HyperLogLog registers. Report files contain aggregate statistics and field names, not raw entity values or identifiers. Evaluator labels remain denied from model-visible use by default.

## Inputs and reproducibility

| Input | Rows | SHA-256 |
|---|---:|---|
| `data/raw/GUIDE_Test.csv` | 4,147,992 | `fdfd7523efd6e3c26bd0290ba6acbcb237196cf923dd56a28e96802035db35a3` |
| `data/raw/GUIDE_Test_Queue_Rankings.csv` | 9,980 | `e4ea9308f45821128a3cd446ab19e6559edfc50709e72034ce957b6f0e2e65d6` |

The run used Python 3.12.10 on Windows, UTF-8 with BOM support, seed 0, and a 250,000-row chunk size. The validation config SHA-256 is `2d4d2b8e8c1ee7e75bc90aeb545dfbaefde6687194738a665fa5b338ad139c1b`.

Run command:

```powershell
.\.venv\Scripts\python.exe -m src.cli validate --alerts data/raw/GUIDE_Test.csv --rankings data/raw/GUIDE_Test_Queue_Rankings.csv --out data/derived/audit --chunk-rows 250000 --config configs/validation.yaml
```

## Validation work completed

- Checked both CSV schemas against the observed required headers, parsed the complete files, recorded row counts, file sizes and hashes, and profiled null rates, inferred value types, whitespace/leading-zero observations, and estimated per-field cardinalities.
- Used the composite `(OrgId, IncidentId)` key for joins, starting with distinct GUIDE incident keys so evidence row multiplicity could not replicate queue labels.
- Measured GUIDE identifier and alert-key integrity, including missing and repeated `Id` values, repeated evidence rows per composite alert key, and alert keys assigned to multiple incidents.
- Checked queue rank nulls, integer conversions, duplicate composite keys, ties, gaps, and whether numbering restarted at 1 within organizations.
- Counted organizations meeting the implemented numeric eligibility conditions: at least 50 GUIDE incidents, at least 10 detectors, and 20 observed rank values. No partition assignments were created.
- Reviewed fields for leakage and privacy. `IncidentId`, `QueueRank`, `IncidentGrade`, `ActionGrouped`, and `ActionGranular` remain evaluator-only. All fields remain denied or pending review; no model-visible allowlist was created.
- Added synthetic edge cases for repeated evidence, cross-organization incident-ID reuse, duplicate/missing ranks, ties/gaps, invalid timestamps, conflicting alert membership, and incomplete top-20 labels. The fixture validation completed successfully.

## Results

- GUIDE contained 4,147,992 evidence rows, 303,220 distinct `(OrgId, IncidentId)` keys, and 637,320 distinct `(OrgId, AlertId)` keys.
- `Id` had 0 missing rows. There were 291,595 duplicated `Id` values, accounting for 3,844,772 rows beyond the first occurrence. These counts establish that `Id` is not unique at the CSV row grain; the intended semantics of `Id` need source clarification before treating it as a stable citation key.
- There were 623,841 composite alert-key groups appearing on multiple evidence rows. This may be expected for evidence-row grain and is reported separately from conflicts.
- There were 70,702 composite alert keys with conflicting incident assignments. This blocks unambiguous alert-level correlation truth until the cause is understood.
- All 9,980 ranking keys matched distinct GUIDE incident keys on the composite key; 293,240 GUIDE incidents had no ranking row, and no ranking keys were unmatched. Unlabeled incidents are not assumed negative.
- No duplicate queue composite keys, null rank rows, integer conversion errors, ties, or rank gaps were detected. Rank numbering restarted at 1 within each organization.
- 499 organizations met the implemented numeric eligibility criteria, exceeding the proposed 50-organization split size. This does not establish that ranking labels are semantically complete or that the requested split is valid.
- The local files do not verify source release, license, download date, QueueRank direction/meaning, the ranking query universe, or completeness of expert top-20 labels. Candidate-pair recall ceiling was not computed because ambiguous alert membership blocks valid alert-level truth, and entity/technique provenance still requires review.

## Outputs produced

The full-data audit was written under `data/derived/audit/`:

- `validation.json` — detailed checks, counts, profiles, eligibility, and task gates.
- `validation.md` — human-readable findings, limitations, and next-step boundary.
- `schema.json` — observed headers and inferred value-type summaries.
- `field_disposition.csv` — null rates, estimated cardinalities, deny decisions, and rationale per field.
- `join_summary.csv` — anonymous per-organization aggregate counts and eligibility; contains no organization identifiers.
- `run_manifest.json` — command parameters, input/config hashes, Python/platform versions, encoding, timestamp, and unverified source metadata.

The audit artifacts are in `data/derived`, which is ignored by Git under the existing repository convention. No raw data was modified.

## Stage 1 decisions and handoff

- **Correlation:** no-go while conflicting alert-to-incident assignments remain unexplained.
- **Prioritization preprocessing development:** may proceed as leakage-safe Stage 2 work, with evaluator labels physically/logically separate and ambiguous alert mappings preserved for investigation.
- **Prioritization evaluation:** blocked until authoritative evidence confirms QueueRank meaning, rank direction, the query universe, and complete expert top-20 labels.
- **Joint evaluation:** no-go while both the alert mapping and ranking semantics remain unresolved.
- Do not generate final evaluation-ready alert pairs or ranking results before these blockers are resolved. Do not expose incident IDs or queue labels to model-visible inputs.

Evidence needed to clear the gate: authoritative dataset release/license citation and download record; documentation of QueueRank direction and scope; evidence that top-20 labels are complete for a defined query universe; source/timing provenance for candidate evidence fields; and explanation or resolution of duplicate `Id` values and conflicting alert memberships.

## Related project records

- Validation protocol: [`01_dataset_validation.md`](../01_dataset_validation.md)
- Overall project context and Phase 2 protocol: [`PROJECT_CONTEXT.md`](../PROJECT_CONTEXT.md)
- Validator and config: [`src/cli.py`](../src/cli.py), [`configs/validation.yaml`](../configs/validation.yaml)
