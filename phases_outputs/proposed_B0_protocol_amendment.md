# Adopted protocol amendment: B0 severity unavailable

**Status: ADOPTED as a project protocol assumption on 2026-11-08, following the user's direction to clear gates with explicit assumptions.** No empirical baseline has been run under this amendment.

The Phase 2 methodology defines B0 as deterministic entity/time clustering plus maximum detector severity. The observed local GUIDE schema has no severity field, and no authoritative severity value or `DetectorId`-to-severity crosswalk is available. Detector identifiers must not be sorted or treated as ordered severity. The source documentation describes timestamps as privacy-perturbed, so the original temporal windows are also not reproducible as written.

## Adopted change

Remove the unavailable maximum-severity component from B0. Because timestamps are privacy-perturbed and entity values remain denied under the adopted local policy, do not claim the original entity/time clusterer is reproducible. If a ranking-only comparator is needed, rank **gold-group oracle candidates** by distinct composite alert count and label it **count-only oracle-group ranking**. This is a separate heuristic diagnostic, not a reconstructed severity baseline.

Never substitute `QueueRank`, `IncidentGrade`, action/outcome labels, detector ID order, or inferred severity. Never expose `IncidentId` as a model-visible feature. Oracle grouping is evaluator-side only and must be named in every output.

## Rationale and impact

The severity and time components cannot be reproduced from verified public inputs. Count-only oracle-group ranking is conditional on correct gold grouping, so it measures neither correlation nor end-to-end performance. Cross-paper comparison to severity-based B0 would be invalid. Other baselines and the proposed system remain restricted to offline processing, evaluator isolation, and the adopted field policy in [the empirical protocol freeze](empirical_protocol_freeze.md).

## Future source clarification

If an authoritative severity field/crosswalk or timestamp semantics are later supplied, add a versioned amendment with source, provenance, and impact. Do not overwrite or silently reinterpret results produced under this amendment.
