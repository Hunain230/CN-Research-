# Phase 17 target status — NO-GO

The preregistered safety rule selected the transaction/process baseline on development because every calibrated cross-sensor C/V candidate increased false grouped pairs above that baseline. Only this frozen baseline was evaluated on the fresh 30-queue, 600-label locked test.

| Locked-test metric | Target | Selected baseline | Status |
| --- | ---: | ---: | --- |
| Incident Recall@20 | ≥80% | **0/600 = 0%** | Fail |
| Group recoverability | ≥85% | **0/600 = 0%** | Fail |
| P@10 | ≥63.88% | **0/300 = 0%** | Fail |
| Grouped-pair precision | ≥90% | **80,986/87,394 = 92.67%** | Pass |
| False grouped pairs | ≤ same-cohort baseline | **6,408** | Pass by definition |
| Mixed groups | ≤ same-cohort baseline | **457** | Pass by definition |

The baseline is deliberately limited and not a meaningful advance over Phase 16. On **development only**, calibrated threshold 0.80 with progression ranking reached 239/300 recoverability (79.67%), 187/300 Recall@20 (62.33%), 98/150 P@10 (65.33%) and 96.70% pair precision, but **4,197 false pairs versus 3,211 baseline**. It therefore failed the no-increase safety gate. No candidate locked-test metric is available or inferred. Synthetic results remain separate from GUIDE and real SOC data.
