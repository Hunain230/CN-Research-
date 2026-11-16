"""Export label-free, pseudonymous merge decisions from frozen predictions."""
import gzip
import hashlib
import json
import pickle
from pathlib import Path

HERE = Path(__file__).resolve().parent
freeze = json.loads((HERE / "predictions/prediction_freeze.json").read_text())
if freeze["evaluator_labels_read"] or len(freeze["prediction_sha256"]) != 499:
    raise ValueError("Full prediction freeze required")
target = HERE / "PHASE10_MERGE_PROVENANCE.jsonl.gz"
if target.exists():
    raise FileExistsError(target)

def digest(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:20]

with gzip.open(target, "wt", encoding="utf-8") as output:
    for name in sorted(freeze["prediction_sha256"]):
        with (HERE / "predictions" / f"{name}.pkl").open("rb") as stream:
            item = pickle.load(stream)
        for method, result in item["methods"].items():
            for decision in result["decisions"]:
                output.write(json.dumps({"queue": name, "method": method,
                    "fragments": decision["fragments"], "score": decision["score"],
                    "evidence": decision["evidence"], "decision": decision["decision"],
                    "reason": decision["reason"]}, sort_keys=True) + "\n")
            for group in result["groups"]:
                if len(group) > 1:
                    output.write(json.dumps({"queue": name, "method": method,
                        "record_type": "group_lineage", "alert_key_hashes": [digest(a) for a in group]},
                        sort_keys=True) + "\n")
print(json.dumps({"status": "exported", "bytes": target.stat().st_size}))
