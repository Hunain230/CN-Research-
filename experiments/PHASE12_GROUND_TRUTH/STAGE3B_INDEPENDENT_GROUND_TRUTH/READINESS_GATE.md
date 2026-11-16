# Ground-truth readiness gate

| Gate | Acceptance evidence | Failure consequence |
| --- | --- | --- |
| Authorization | Signed owner scope, retention, privacy/access controls | No SOC acquisition |
| Source identity | Native observation ID/offset resolves to immutable original plus hash | No event-level C truth for affected alerts |
| Derivation | Alert-to-source links independently verified; multiplicity and ambiguity retained | Exclude from scored subset only with coverage disclosed; no inferred link |
| Availability | Receiver-side timestamp/version ledger and clock quality, including corrections | No point-in-time claim |
| Membership | Independent positive, explicit negative, ambiguous judgments with evidence; no detector-derived truth | No full C evaluation |
| Priority | Complete blind expert judgments for eligible queues, disagreement resolution | C-only; no P@10/nDCG@20/Recall@20 claim |
| Population | Prospective inclusion rules preserve negatives, missed and difficult alerts | No unbiased benchmark |
| Split/seal | Whole incident/run/family held out, test truth sealed, code/predictions hashed | Retrospective exploratory only |
| Privacy | Pseudonymization, least privilege, approved storage and deletion | No export into research workspace |

**Possible outcomes:** `READY_FOR_C_ONLY`, `READY_FOR_FULL_CPV`, `RESEARCH_ONLY_DESCRIPTIVE`, or `NO_GO`. The validator is a necessary format/integrity gate, not sufficient proof of authorization, truthful labels, human independence, or operational availability. Reviewers must inspect those records manually. The included synthetic fixture is `RESEARCH_ONLY_DESCRIPTIVE` by construction.

**Next concrete action:** approach an authorized SOC data owner with `SOC_EXPORT_PROTOCOL.md` and a small provenance/availability feasibility sample. In parallel, specify instrumentation and budget for the lab dry run. Do not collect real data or execute attacks until separate authorizations are in place.
