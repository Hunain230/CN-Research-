# Dataset and Preprocessing

## Datasets

### AUTHOR CLAIM

- **CICIDS2017:** labeled benign and malicious network traffic; Table 4 reports approximately 80 GB of raw traffic logs.
- **UNSW-NB15:** labeled normal traffic and modern blended attacks.
- The paper states that the datasets are combined and used to train/validate defender detection modules and inform attacker state representations.

[Agrawal, Abstract and “Cybersecurity datasets and validation challenges,” pp. 1, 4; “Dataset preparation and feature engineering,” p. 12]

## Preprocessing

### AUTHOR CLAIM

The pipeline extracts approximately 85 flow features, including packet counts, durations, flags, payload metadata, and temporal characteristics; removes or imputes missing values; normalizes data; performs dimensionality reduction; uses SMOTE for minority attack classes where applicable; and applies a stratified 80/20 train/test split. The summarized balanced dataset contains approximately 50,000 samples, with 40,000 training and 10,000 testing samples; fewer than 0.5% of rows are reported as affected by missing data. [Agrawal, “Dataset preparation and feature engineering,” Table 4, p. 12; Table 8, p. 15]

## Labels/classes and sources

### AUTHOR CLAIM

The paper describes supervised classification of known attack types and anomaly scoring for unknown behavior, but the exact final class list and class counts used after combining the datasets are **not clearly specified**. [Agrawal, “Multi-agent system architecture,” pp. 11-12]

The original dataset publications are cited, but the precise files, collection subsets, and join/merging procedure used in this study are **not clearly specified**. [Agrawal, references and dataset sections, pp. 4, 12, 19]

## Dataset limitations

### AUTHOR CLAIM

The authors acknowledge generally that CICIDS2017 and UNSW-NB15 have limitations for realistic agent training and that prior use in isolated/small-scale environments can limit generalization. They do not give a detailed limitation analysis of their final combined dataset. [Agrawal, “Cybersecurity datasets and validation challenges,” p. 4]

### OUR OBSERVATION

- Table 4 quantifies “~80 GB” only for CICIDS2017 even though the text says both datasets are combined; the per-dataset sample contribution is absent.
- The reduction from raw data to roughly 50,000 balanced samples is not documented sufficiently to reproduce sampling or preserve temporal structure.
- SMOTE can create synthetic minority samples but does not create new attack behaviors; its placement relative to train/test splitting is not clearly stated, leaving leakage risk unresolved.
- A stratified random split may not test temporal, campaign, or environment shift.
- Dataset age and curated benchmark conditions limit conclusions about present-day operational traffic and alert distributions.
- These are flow datasets, not SOC alert/case datasets with analyst dispositions, alert provenance, evidence links, or response outcomes.

