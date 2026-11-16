# Track B — controlled SOC lab

## Testbed and independent oracle

Use an isolated, authorized lab with fixed infrastructure images, host/network clock synchronization, versioned sensors, and a controller that records actions independently of the detectors. The lab controller writes signed action IDs, incident IDs, start/end times, source target IDs, and expected observable effects to an oracle store unavailable to C/P/V. A separate collector records original source observations and an append-only receiver-side availability ledger. Detector output is never the source of attack truth.

## Scenario matrix

Construct multiple incident chains per run, with overlapping steps and shared hosts/users/services in controlled ways. Include unrelated benign operations, routine maintenance, noisy scans, failed attack steps, detector false positives, duplicate alerts, alert loss, delayed ingestion, source retractions, and clock uncertainty. Vary incident size, duration, detector coverage, and entity overlap. At least one run should contain more simultaneous incidents than the top-20 queue capacity, so ranking is meaningful; exact run counts and power targets are set from pilot variance and available resources before any confirmatory test. Do not use a single attack per run as a substitute for interleaved reconstruction pressure.

Each scripted action has a unique controller ID and is linked to actual source observation IDs through instrumented system logs, transaction IDs, or packet/flow capture references. If an action leaves no observable source record, mark it unobservable. If a benign action overlaps an attack phase, keep it benign unless its own source provenance supports membership. Preserve failed steps and unattributed alerts. Attach ground-truth incident membership to observations/actions first, then adjudicate alert membership through verified derivation edges; never label alerts by time-window overlap alone.

## Evidence-availability capture

At the correlator ingress, emit a ledger event when each immutable artifact version becomes queryable. Include receiver monotonic sequence, wall-clock UTC, clock quality, payload hash, source/alert ID, and supersession/retraction events. Replay tests must preserve original arrival order and delay, with a separate replay clock mapping recorded. Validate delayed and out-of-order arrivals in a small dry run. A time-based evaluation only sees versions available at its cutoff; later forensic knowledge remains evaluator-only.

## Trial progression

1. Instrumentation dry run: one incident plus benign activity; validate every source-to-alert link and availability clock without assessing model quality.
2. Interleaving pilot: at least two incidents with shared entities and staggered arrivals; measure missingness, ambiguous truth, and clock error. Fix instrumentation before freezing the final protocol.
3. Confirmatory design freeze: predeclare scenario families, random seeds, run allocation, detector versions, metric definitions, abstention policy, and power analysis. Reserve whole runs and incident families for sealed test.
4. Execute, seal, and hash source/oracle/ledger packages independently. External reviewers adjudicate uncertainty and expert priority without seeing C/P/V predictions.

All target systems are nonproduction; no attack execution is authorized by this design document. The stage ends at design and validation tooling.
