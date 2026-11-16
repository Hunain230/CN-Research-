# Track A — authorized SOC export

## Acquisition request and governance

Request a scoped export from an organization that can authorize use of its SOC data. Obtain written data-owner approval, research purpose, permitted retention and transfer, privacy review, analyst time allocation, and a list of systems/tenants covered **before** access. This document is a specification; no person or organization has been contacted. Prefer an on-site or remote enclave to copying raw security logs to local hardware. If policy prevents raw payload export, export opaque IDs, keyed hashes, timestamps, normalized minimal features, and a controlled re-query channel for adjudication. Never include credentials, secrets, or unrestricted personal data in the research repository.

## Minimum data extract

1. **Original observations:** source-native ID/offset, source system and tenant, raw-event hash, event time, collector receipt time, clock metadata, and a reversible internal locator held by the data owner.
2. **Detector alerts:** stable native alert ID, detector/version, generation time, receipt/availability time, immutable payload hash, and source-native derivation references. Keep alert revisions and suppressions.
3. **Availability ledger:** receiver-side append-only record of when each observation, alert, enrichment, and corrected version became readable to C/P/V. Log query-result snapshots or index commit times where direct receipt is insufficient.
4. **Independent incident truth:** case IDs, case creation/closure timeline, explicit alert/source memberships and exclusions, duplicate-case reconciliation, conflicting/mixed cases, and analyst evidence citations. A case-system grouping alone is provisional until reviewed independently of the experimental C/P/V predictions.
5. **Expert priority:** two or more analysts rank complete, blinded incident queues at a declared cutoff using a fixed rubric (expected harm, urgency, confidence), with disagreement and adjudication retained. Rankings made after seeing C/P/V outputs are invalid as independent truth.
6. **Negative and unknown population:** retain benign alerts, unrelated alerts, false-positive dispositions, unresolved references, and unjudged cases. Do not construct a benchmark solely from resolved positives.

## Sampling and quality control

Choose a prospective time span and all eligible alert sources before inspecting outcome distributions. Preserve the full queue and inclusion/exclusion ledger. Sample across shifts, weekdays, high/low volume, detector families, incident sizes, and overlapping incidents. Do not filter difficult alerts to improve reconstruction metrics. Record outages, missing logs, retention gaps, clock shifts, and case merges/splits. Reconcile source IDs to originals inside the owner environment; record match method and multiplicity. Pilot a small, independently chosen sample to confirm that provenance and timing are obtainable before export expansion.

## Adjudication and release

Reviewers receive original observations and case evidence, but not C/P/V predictions or GUIDE labels. Two blinded reviews produce membership and priority records; disagreement is preserved and escalated. A data steward freezes the truth package, hashes it, and releases only development labels. Test labels stay sealed until predictions and code are frozen. If independent case membership or receipt-time evidence cannot be recovered, classify the extract as C-only/descriptive or NO-GO; never substitute case creation time for evidence availability.
