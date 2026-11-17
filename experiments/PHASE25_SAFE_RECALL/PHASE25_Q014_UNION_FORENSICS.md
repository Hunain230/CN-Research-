# Phase 24 Q014 union forensics (opened development data)

The five Phase 24 `coherent_rare` unions occur at decision orders 223–227. The [member audit](PHASE25_Q014_UNION_MEMBERS.csv) lists every premerge alert on both sides, its source-event ID, initial component, visible host/account/process/auth/flow fields, event and arrival times, field availability, and evaluator-only incident membership. Phase 24 did **not** record a sensor-origin field or a direct physical parent relationship for these alerts; those facts cannot be reconstructed from source IDs. The source IDs are provenance roots, not incident features.

| Order | Premerge sizes | Reference | Initial reference frequency | Event ranges (minutes) | New false pairs | Cumulative |
| ---: | ---: | --- | ---: | --- | ---: | ---: |
| 223 | 7 + 6 | auth | 2 components | 5–20 / 18–28 | 42 | 42 |
| 224 | 13 + 2 | flow | 2 | 5–28 / 24–26 | 12 | 54 |
| 225 | 1 + 15 | auth | 2 | 23 / 5–28 | 6 | 60 |
| 226 | 4 + 16 | flow | 2 | 13–16 / 5–28 | 40 | 100 |
| 227 | 20 + 2 | auth | 2 | 5–28 / 31–32 | 20 | 120 |

All five have visible host and account agreement. The first union joins two pure, different incidents with one rare auth reference and overlapping time ranges. Its linking alerts each have a visible but **different** flow reference. Later unions are contaminated by that first component merge: several add false pairs despite adding a fragment from an incident already present in the group. Reference rarity and group context are therefore insufficient causal proof.

Across the other accepted Phase 24 rare-context unions, **786** add no false pairs; **261/786** also have disjoint orthogonal references, and **98/786** have overlapping time ranges. Among the five false-pair-creating unions, three have disjoint orthogonal references and four have overlapping times. Neither feature perfectly separates truth. The Phase 25 `orthogonal_veto` diagnostic blocks one Q014 cross-incident union and reduces Q014 false pairs from 120 to zero when replayed retrospectively. That retrospective result is design-set evidence, not validation. On fresh Phase 25 development data, `orthogonal_veto` and unvetoed `coherent_rare` make identical predictions; the veto's independent benefit remains unproven.

The failure may combine a false but plausible rare reference, shared upstream generation, and missing independent contradiction. Phase 24 has no authenticated sensor or causal receipt stream to distinguish these possibilities. The Phase 25 synthetic receipt stream tests separate failure modes, but the selected Phase 25 rule did not depend on those receipts. The [structured forensic record](q014_forensic.json) preserves the five union details and [comparison counts](q014_comparison.json) preserve the true-union comparison.
