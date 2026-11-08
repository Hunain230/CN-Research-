# Phase 2 — Leakage-safe preprocessing and provenance

## Scope and source baseline

Phase 2 implemented preprocessing infrastructure only. No model, baseline, candidate-pair labels, pair metrics, incident ranking, priority scoring/calibration, or research evaluation was produced. GUIDE and queue files were read only; both raw hashes matched the Phase 1 baseline before and after the run.

The requested `phases_context/Phase1.md` was not present in this checkout. I used the existing verified record at `phases_outputs/Phase1.md`, together with `data/derived/audit/validation.json`, as the Phase 1 baseline.

| Input | Rows | SHA-256 before and after |
|---|---:|---|
| `data/raw/GUIDE_Test.csv` | 4,147,992 | `fdfd7523efd6e3c26bd0290ba6acbcb237196cf923dd56a28e96802035db35a3` |
| `data/raw/GUIDE_Test_Queue_Rankings.csv` | 9,980 | `e4ea9308f45821128a3cd446ab19e6559edfc50709e72034ce957b6f0e2e65d6` |

Run environment: project `.venv`, Python 3.12.10, Windows, seed 0, UTF-8/BOM-aware input parsing, standard library only. No dependency was installed. Normalizer version is `typed-v1`; parser version is `csv.reader-utf8-sig-v1`.

## Implementation and data boundaries

- Added `src/phase2.py` and `src/evaluator_store.py`, and extended `src/cli.py` with `preprocess`, `check-leakage`, `check-splits`, `inspect-ambiguity`, and `self-test-phase2` commands. Existing Stage 1 `validate` remains available.
- Streamed all GUIDE records and assigned source-row ordinals 1 through 4,147,992. `Id` was retained only as opaque source content; it was never used as a row identity or citation key.
- Wrote restricted source fields and typed normalization metadata to a SQLite evidence ledger. Original timestamps, normalized UTC values/statuses, normalized IP values/statuses, and parsed ATT&CK technique IDs/statuses are kept separately. Timezone-naive timestamps would remain unresolved; all observed timestamps parsed as timezone-aware UTC.
- Stored incident membership, queue labels, and exact-full-row digests in a separate evaluator SQLite database, with evaluator CSV exports. The evidence ledger schema has no `IncidentId`, `QueueRank`, incident grade, or action/outcome columns. No feature exporter reads evaluator data.
- Retained every alert-to-incident assignment with its source-row ordinal. Conflicting assignments are labeled ambiguous; none is selected, discarded, or treated as a positive/negative pair.
- Wrote the feature view as a schema-only, zero-row CSV because Phase 1 approved no model-visible fields. There are no approved features in `configs/field_policy.yaml`.
- Used typed, versioned normalization only for parseable timestamps, IP addresses, and ATT&CK technique identifiers. Other sensitive or temporally unverified values remain restricted and are not exported as features.
- Wrote a provisional organization split using SHA-256 of the versioned salt, a NUL delimiter, and the exact UTF-8 `OrgId`, sorted by digest and then exact ID. The first 10 eligible organizations are pilot, next 10 development, next 30 test. Every evidence row for selected organizations resolves to exactly one partition through the ledger partition view.

## Outputs

All preprocessing artifacts are under `data/derived/preprocessing/` (ignored by Git under the repository's existing `data/` rule):

- `evidence_ledger.sqlite` — restricted source-row ledger, ordinals, source hashes/parser version, and normalized values/statuses.
- `feature_view.csv` — intentionally empty/header-only; zero model-visible rows and zero approved fields.
- `evaluator/evaluator.sqlite` — separate evaluator-only membership, queue labels, and exact-row digest tables.
- `evaluator/incident_membership.csv` — composite membership assignments, mapping status, and source ordinals.
- `evaluator/queue_labels.csv` — ranking labels, evaluator-only.
- `review/ambiguous_alert_memberships.csv` — all ambiguous alert keys, all assigned incident IDs, and source ordinals for each assignment.
- `review/exact_duplicate_groups.csv` — digest groups and every source ordinal, distinct from repeated evidence rows and ambiguous mappings.
- `quarantine/invalid_rows.csv` — ordinal/reason only; no invalid or malformed rows were observed, so it contains only its header.
- `split_manifest.json` — restricted organization IDs and provisional partition assignments, hash algorithm/salt version, and assignment digest.
- `preprocessing.json`, `preprocessing_report.md` — counts, output status, split, and open research gates.
- `leakage_audit.json`, `leakage_audit.md` — deny-by-default checks and synthetic sentinel results.
- `run_manifest.json` — input-before/after hashes, config/field-policy/code hashes, output hashes, environment, command, seed, and timestamp.

## Results

- Processed 4,147,992 GUIDE data records with 4,147,992 unique source-row ordinals; zero malformed rows.
- Preserved 303,220 composite incident keys and 637,320 composite alert keys. Queue labels remain separate: 9,980 rows.
- Found and preserved 70,702 ambiguous composite alert keys. This matches the Phase 1 blocker. No final alert pairs or pair labels were produced.
- Found 104 exact full-row duplicate groups. These are separately reported and were not silently removed from the evidence ledger.
- Reconfirmed 499 eligible organizations using the specified numeric criteria; created a provisional 10/10/30 assignment. The assignment digest is `c0e6689f78d878237adb7689c0f5b39980bb547ab3bbd83efe4e7b4e639fe024`. Selected organizations contain 517,474 GUIDE evidence rows; all selected rows were confirmed partitioned.
- Leakage checks passed: no approved features, zero feature rows, no evaluator/lineage fields in the feature schema, and no synthetic incident/rank/outcome sentinel in the feature export. The sentinel check did not print the sentinel values.
- All 13 output hashes recorded in the run manifest matched the produced files. Raw before/after hashes matched the Phase 1 values.

## Commands run

Full preprocessing:

```powershell
.\.venv\Scripts\python.exe -m src.cli preprocess --alerts data/raw/GUIDE_Test.csv --rankings data/raw/GUIDE_Test_Queue_Rankings.csv --audit data/derived/audit --config configs/preprocessing.yaml --out data/derived/preprocessing --seed 0
```

Synthetic regression and boundary checks:

```powershell
.\.venv\Scripts\python.exe -m src.cli self-test-phase2
.\.venv\Scripts\python.exe -m src.cli check-leakage --features data/derived/preprocessing/feature_view.csv --policy configs/field_policy.yaml --audit <temporary-audit-path>
.\.venv\Scripts\python.exe -m src.cli check-splits --manifest data/derived/preprocessing/split_manifest.json --expected 10,10,30
.\.venv\Scripts\python.exe -m src.cli inspect-ambiguity --input data/derived/preprocessing/review/ambiguous_alert_memberships.csv --out <temporary-summary-path>
```

`self-test-phase2` passed all 16 synthetic assertions for stable ordinals despite repeated `Id`, exact duplicates, repeated evidence and conflicting mappings, organization-scoped identities, timestamps, typed normalization, rank edge cases, sentinel isolation, and deterministic disjoint split ordering. Leakage and split CLI checks passed; ambiguity inspection counted 70,702 keys.

## Current research gates and Stage 3 readiness

- **Correlation and joint evaluation: no-go.** Conflicting alert assignments remain unresolved; no final alert pairs or correlation metrics may be generated.
- **Prioritization preprocessing infrastructure: ready for continued development.** Evaluator labels remain isolated, but the current feature view is intentionally empty.
- **Priority evaluation/ranking: blocked.** QueueRank direction, semantics, query universe, and complete expert top-20 status remain unverified. Unlabeled incidents are not negatives.
- **Stage 3 modeling/baselines: not ready.** There are no approved model-visible fields, and label validity gates remain open. Do not train, calibrate, score, or evaluate priority, and do not treat provisional split assignment as permission to inspect test labels.

To clear these gates, obtain authoritative source/release/license/download metadata; verify the ranking direction, query universe, and top-20 completeness; document point-in-time and privacy approval for any candidate feature; and investigate the 70,702 conflicting alert assignments and the meaning of duplicated `Id` values.
