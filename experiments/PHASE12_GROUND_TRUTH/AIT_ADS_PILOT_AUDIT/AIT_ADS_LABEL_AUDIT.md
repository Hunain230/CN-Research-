# Attack-phase label audit

The downloaded `labels.csv` contains 79 scripted attack intervals across eight named scenarios; phase counts: cracking 7, dirb 8, dnsteal 8, network_scans 8, privilege_escalation 8, reverse_shell 8, service_scans 8, service_stop 8, webshell 8, wpscan 8. No intervals overlap within or across scenario names in this file. File organization and author description support eight scenario runs, but do not establish multiple independent incidents per run or identify every original source observation. No per-alert ground-truth label appears in `labels.csv`.

| Association level | Evidence in small archive | Verdict |
| --- | --- | --- |
| A. Attack-window association | Compare an extracted alert time with a same-scenario scripted interval. | Descriptive only; measured below. |
| B. Event-level attack-phase association | Requires matching detector-carried raw text to original AIT-LDSv2 labeled log event, or Suricata flow to original AIT-NDS netflow, using the author workflow. | Zero independently verified within downloaded files. |
| C. Alert-to-incident membership | No complete incident ID or multi-incident mapping. | Unavailable. |

Mechanical half-open `[start,end)` window association, using the audit timestamp selection: 1,764,581/2,655,821 (66.4420%) in exactly one phase; 891,240/2,655,821 (33.5580%) outside all phases; 0/2,655,821 (0.0000%) in multiple phases; 0/2,655,821 (0.0000%) missing timestamp. Outside-window alerts are **not** proven benign; inside-window alerts are **not** proven true positives. Thus the small archive provides no validated positive/negative event-label counts and no known false-positive rate.

| Attack window phase | Window associated alerts | Share of all alerts |
| --- | ---: | ---: |
| cracking | 5,402 | 0.2034% |
| dirb | 1,691,090 | 63.6748% |
| dnsteal | 8,630 | 0.3249% |
| network_scans | 1,579 | 0.0595% |
| privilege_escalation | 371 | 0.0140% |
| reverse_shell | 82 | 0.0031% |
| service_scans | 2,354 | 0.0886% |
| service_stop | 21 | 0.0008% |
| webshell | 121 | 0.0046% |
| wpscan | 54,931 | 2.0683% |

Detector counts: AMiner 55,558, Wazuh 2,293,628, Suricata via Wazuh 306,635. Scenario counts: fox 473,104, harrison 593,948, russellmitchell 45,544, santos 130,779, shaw 70,782, wardbeck 91,257, wheeler 616,161, wilson 634,246. Each uses denominator 2,655,821 alerts and mutually exclusive bins, except phase counts reflect window matching. The author source code has `do_event_labeling = False` by default and requires external AIT-LDSv2 and AIT-NDS data when enabled. Its Wazuh/AMiner raw-line and Suricata flow matching is a *potential* event-level construction workflow, not a verified result of this audit. [Pinned `analyze.py`](https://github.com/ait-aecid/alert-data-set/blob/ce927ddaeaa674f6909e1de676fa7dc293e393bd/analyze.py).
