"""Generate synthetic edge-case CSVs for manual Stage 1 CLI runs."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.cli import GUIDE, RANK

out=Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=True)
def row(**kw):
    return {c: str(kw.get(c,"")) for c in GUIDE}
rows=[row(Id="e1",OrgId="orgA",IncidentId="shared",AlertId="alert1",Timestamp="2025-01-01T00:00:00Z",DetectorId="d1",MitreTechniques="T1001"),
      row(Id="e1",OrgId="orgA",IncidentId="shared",AlertId="alert1",Timestamp="2025-01-01T00:00:00Z",DetectorId="d1",MitreTechniques="T1001"),
      row(Id="e2",OrgId="orgA",IncidentId="other",AlertId="alert1",Timestamp="not-a-time",DetectorId="d2"),
      row(Id="e3",OrgId="orgB",IncidentId="shared",AlertId="alert2",Timestamp="2025-01-01T01:00:00Z",DetectorId="d3")]
with (out/"GUIDE_Test.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=GUIDE); w.writeheader(); w.writerows(rows)
labels=[{"OrgId":"orgA","IncidentId":"shared","QueueRank":"1"},{"OrgId":"orgA","IncidentId":"shared","QueueRank":"1"},{"OrgId":"orgA","IncidentId":"other","QueueRank":"3"},{"OrgId":"orgB","IncidentId":"shared","QueueRank":""}]
with (out/"GUIDE_Test_Queue_Rankings.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=RANK); w.writeheader(); w.writerows(labels)
