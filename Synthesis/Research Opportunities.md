# Research Opportunities

## Evidence boundary

These directions are derived only from the three reviewed papers. They are candidate opportunities, not claims of novelty in the wider literature. A broader literature review would be required before claiming that any direction is new.

## 1. Evidence-specialized critic for alert disposition

### RESEARCH OPPORTUNITY

- **Direction:** Compare a single-agent RAG triager with a proposer-critic-adjudicator workflow for true-positive/false-positive disposition plus abstention.
- **Supporting evidence:** Zhang's Red policy and Debapt's CritEn/JdgEn ablations show value from challenge/review in their tasks; neither tests alert disposition. Agrawal supplies realistic attack scenarios but no evidence review.
- **Novelty risk:** Medium. Multi-agent critique is common; novelty must come from triage-specific evidence roles and rigorous matched-budget evaluation.
- **Methodological difficulty:** Medium.
- **Dataset requirements:** Alert cases with ground-truth disposition and linked telemetry/CTI; ideally time-separated cases.
- **3-4 month feasibility:** High if limited to one alert type or a curated case set.
- **Expected contribution:** Evidence on whether critic/adjudicator roles reduce unsupported dispositions and improve calibrated abstention.
- **Major risks:** label leakage, weak ground truth, and unfair compute budgets.

## 2. Provenance-preserving CTI enrichment for triage

### RESEARCH OPPORTUNITY

- **Direction:** Test whether CTI facts with explicit source spans and conflict markers improve alert severity/disposition compared with ungrounded CTI summaries.
- **Supporting evidence:** Debapt grounds and aggregates CTI facts; Zhang uses evidence sufficiency for escalation; neither connects CTI provenance to alert decisions.
- **Novelty risk:** Medium-high until wider literature is checked.
- **Methodological difficulty:** Medium-high.
- **Dataset requirements:** Alerts linked to indicators/entities plus time-valid CTI documents and outcome labels.
- **3-4 month feasibility:** Medium if restricted to one threat/alert family.
- **Expected contribution:** A measured relationship between provenance quality, conflict handling, and triage performance.
- **Major risks:** temporal leakage from post-incident CTI and unreliable indicator matching.

## 3. Disagreement-calibrated escalation

### RESEARCH OPPORTUNITY

- **Direction:** Determine whether agent disagreement predicts triage error and can set an abstention/escalation threshold better than single-model confidence.
- **Supporting evidence:** Zhang exposes policy divergence and ETS but lacks analyst validation; Debapt uses adjudication without calibration; Agrawal lacks an uncertainty mechanism.
- **Novelty risk:** Medium.
- **Methodological difficulty:** Medium.
- **Dataset requirements:** Labeled alert decisions with confidence/error analysis; analyst review on a subset is desirable.
- **3-4 month feasibility:** High with offline experiments.
- **Expected contribution:** Calibration curves and a risk-coverage trade-off for human escalation.
- **Major risks:** disagreement may measure prompt randomness rather than epistemic uncertainty.

## 4. Robust triage under conflicting or missing evidence

### RESEARCH OPPORTUNITY

- **Direction:** Inject controlled evidence deletion, contradiction, stale CTI, or benign look-alikes and test whether a structured critic reduces confident errors.
- **Supporting evidence:** Zhang models adversarial telemetry perturbation; Debapt checks conflict and hallucination; neither evaluates alert triage under evidence corruption.
- **Novelty risk:** Medium-low as a three-paper-derived question, but wider-literature novelty remains unknown.
- **Methodological difficulty:** Medium.
- **Dataset requirements:** Complete alert cases from which evidence can be systematically removed or altered.
- **3-4 month feasibility:** High if perturbations are carefully bounded.
- **Expected contribution:** Robustness evidence and a taxonomy of failure modes.
- **Major risks:** synthetic perturbations may not represent operational missingness or adversarial behavior.

## 5. Quality-cost frontier of multi-agent triage

### RESEARCH OPPORTUNITY

- **Direction:** Measure the marginal benefit of critics and debate rounds under fixed token, latency, and evidence budgets.
- **Supporting evidence:** Zhang acknowledges deliberation overhead; Agrawal demonstrates why latency matters; Debapt caps rounds but does not report cost/latency.
- **Novelty risk:** Medium-high unless paired with a substantive triage hypothesis.
- **Methodological difficulty:** Low-medium.
- **Dataset requirements:** A modest labeled alert-case set and reproducible inference logging.
- **3-4 month feasibility:** High.
- **Expected contribution:** A practical accuracy/grounding/calibration versus cost curve.
- **Major risks:** results may be model/provider-specific and become an engineering benchmark rather than a research contribution.

## Comparative recommendation without selecting a final methodology

### OUR OBSERVATION

Directions 1, 3, and 4 are the strongest semester-scale candidates because they isolate testable mechanisms. Direction 2 is conceptually strong but dataset-intensive. Direction 5 is feasible but weak alone; it is better used as a secondary analysis. No final methodology is selected at Phase 1.

