# Leakage and validity policy

This is an audit policy; no model was trained. A future C-only experiment must first prove source resolution and point-in-time feature availability.

| Field/source | Risk | Allowed use now |
| --- | --- | --- |
| Scenario name, ZIP member, run-specific source paths, host/IP, row order, Wazuh generated ID | Run fingerprint and attack schedule proxy | Audit and scenario-disjoint split only; no predictive input |
| `labels.csv` attack phase and interval endpoints, derived `window_phases`, precomputed event labels | Direct target leakage | Evaluation-only layer; never merge, threshold, or feature input |
| Detector name, Wazuh rule/category, AMiner component | Detector priors may reflect known attack steps | Audit-only until provenance and time-of-availability review |
| Raw log content and flow tuple | May be a valid observed input, but may include scripted strings and retrospective enrichment | Matching audit only until external original event and availability proof |
| Author `analyze.py` output | Event labels can be derived using external source labels and known schedule | Ground-truth construction only, isolated from inference |

If a later authorized pilot becomes feasible, split by complete scenario run, never randomly by alerts or time slices from the same run. With eight named runs, any held-out evaluation would be small and should report each run separately. Keep source matching and label construction in a separate evaluation-only process; freeze field allowlists and matching rules before evaluating held-out runs. Audit duplicate flow references and ambiguous matches explicitly. No GUIDE comparison, incident-level metric, or independent priority result follows from this dataset.
