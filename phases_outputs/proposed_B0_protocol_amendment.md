# Proposed protocol amendment: B0 severity unavailable

**Status: PROPOSED — NOT APPROVED.** No empirical baseline was run under this amendment.

The Phase 2 methodology defines B0 as deterministic entity/time clustering plus maximum detector severity. The local observed GUIDE schema has no severity field, and no authoritative severity value or `DetectorId`-to-severity crosswalk has been supplied for these files. Detector identifiers must not be sorted or treated as ordered severity.

## Proposed change

For this dataset, remove the maximum-severity component from B0. Define B0 only as deterministic entity/time clustering, and report that it has no prioritization score/ranking component. Do not substitute QueueRank, IncidentGrade, action/outcome labels, detector ID order, or inferred severity.

## Rationale and impact

The existing severity component cannot be reproduced from verified public inputs. The amended B0 would therefore be a correlation-only rule baseline and would no longer serve as a prioritization comparator. Cross-paper comparison to severity-based B0 would not be valid. B1–B3 and the proposed system remain subject to all existing feature, label, split, and evaluation gates.

## Approval required

The researcher must either approve this amendment before empirical comparison or provide an authoritative dataset field/crosswalk with provenance and version. Until then, the B0 severity gate remains closed and no empirical B0 result may be reported.
