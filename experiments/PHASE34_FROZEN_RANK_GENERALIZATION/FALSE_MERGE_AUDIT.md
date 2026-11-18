# Group and queue-level safety audit

The new development baseline and both candidates use the **same frozen Phase 32 groups and verification decisions**. All three have 19,459 true grouped pairs, zero false grouped pairs, zero mixed groups, and 100% grouped-pair precision. Every candidate queue has the same eligible alert set, group partition and top ten as its baseline queue. No queue-level false-pair or mixed-group regression occurred. P@10 is also exactly equal queue by queue (110/150 aggregate), because the top ten groups and their order are frozen.

The candidates change only the ordering after position ten. Their measured recall changes are ranking effects, not new reconstructions. Prior Phase 33's 28/28 genuine fallback unions remain a frozen historical observation; Phase 34 did not accept any new union or weaken the three-root verifier. `QUEUE_LEVEL_AUDIT.csv` and `artifacts/post_evaluation_audit.json` contain the exact paired checks.
