# Phase 10 error analysis

All counts use the same 499 queues and 9,980 expert top-20 labels. These are retrospective exploratory outcomes on previously accessed GUIDE_Test labels.

| Cascade state | E0/E1 frozen groups | E2 mutual fragments | E3 hierarchy | E4/E5 hierarchy + verification |
|---|---:|---:|---:|---:|
| Outside unambiguous alert scope | 855 | 855 | 855 | 855 |
| Candidate-disconnected | 487 | 487 | 487 | 487 |
| Candidate-connected, incompletely grouped | 1,451 | 1,435 | 1,411 | 1,440 |
| Complete but impure | 218 | 259 | 289 | 259 |
| Recoverable, ranked below 20 | 1,997 / 1,903 | 1,976 | 1,979 | 1,978 / 1,888 |
| Successfully recovered | 4,972 / 5,066 | 4,968 | 4,959 | 4,961 / 5,051 |

The slash in E0/E1 and E4/E5 shows v7 / blend ordering on identical groups. Each column totals 9,980. The main reconstruction failure is conversion of incomplete fragments into impure groups: E3 reduces the incomplete category by 40 labels but increases the impure category by 71. Net recoverability **falls by 31**. E4 reduces incomplete by 11 but increases impure by 41; net recoverability **falls by 30**. E2 follows the same pattern, net **−25**. The 487 candidate-disconnected and 855 out-of-scope labels are unaffected by a frozen-graph merge method.

E2 accepts 593 fragment merges, of which 364 cross expert incidents; false grouped pairs rise by 3,880 to 32,486 and mixed groups rise by 16. E3 accepts 1,793, of which 1,043 cross incidents; false pairs rise by 7,602 to 36,208 and mixed groups rise by 195. E4's verification veto cuts accepted merges to 365 and reduces false merges to 217, but still adds 3,099 false pairs. Its mixed-group count falls by nine even though many wrong merges occur; this count can decrease when two already mixed groups become one. Pair precision drops from 90.4148% to 89.6642% in E4/E5. The verification criteria are insufficient to distinguish shared infrastructure, repeated detector observations, and true incident continuity.

Gross additional alerts in newly recoverable expert incidents are 74 (E2), 159 (E3), and 57 (E4/E5); these figures do **not** subtract alerts from incidents that lost recoverability. Net recoverable incident counts are lower in every reconstruction policy. The >100-alert cap remains active and no produced component is oversized. Phase 9F's 1,445 low-score incomplete incidents and the 62 >125-alert labels remain structural limits; the current score has not overcome them safely.

The current local provenance cannot establish independent evidence or field availability at queue entry. Two touched endpoints, a shared entity, and a short alert-creation gap are correlated proxies. The next experiment should obtain authoritative source-observation IDs and evidence-arrival timestamps, construct provenance-independent fragment witnesses, and test a learned incident-level purity objective on a newly authorized development cohort before sealed evaluation.
