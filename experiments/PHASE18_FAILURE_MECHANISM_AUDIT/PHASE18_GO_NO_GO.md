# Phase 18 decision: AUDIT COMPLETE; NO-GO for a new candidate

The zero-recovery Phase 17 baseline is structurally incapable of meeting the 80% completeness requirement on its nine-action incidents. It behaves the same on train, development and locked test; no test-only distribution shift or schema mismatch was found. The candidate's 986 additional development false pairs are exactly reconciled to 12 accepted unions, dominated by non-rare single-type references and amplified group sizes. No algorithm was changed or evaluated on an opened locked test in Phase 18.

**Phase 16 v4 remains the selected best safe synthetic result.** Phase 17's candidate remains rejected. Advance only after a strong comparator and the criteria in `PHASE18_DEVELOPMENT_ACCEPTANCE_CRITERIA.md` are fixed on new development data, with another fresh holdout reserved.
