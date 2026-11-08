# Stage 1 synthetic fixtures

`edge_cases.py` generates throwaway CSVs containing duplicate evidence rows, an
IncidentId reused across organizations, duplicate/missing/tied/gapped ranks,
invalid timestamps, an alert assigned to two incidents, and an incomplete
top-20 list. All values are synthetic. Run it with `python fixtures/stage1/edge_cases.py
<directory>`; generated CSVs are not committed as data inputs.
