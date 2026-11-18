"""Train one logistic candidate on Phase 36 train after sealing predictions."""
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

import ranker

HERE = Path(__file__).resolve().parent
DATA = HERE / "dataset"
ART = HERE / "artifacts"


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def lines(path): return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]


def main():
    assert not (ART / "candidate_params.json").exists()
    manifest = json.loads((DATA / "train_manifest.json").read_text(encoding="utf-8"))
    assert manifest["seed"] == 36101 and len(manifest["queues"]) == 8
    visible = DATA / "receiver_visible/train"
    preds = ART / "train_baseline_predictions.jsonl"
    audits = ART / "train_baseline_decisions.jsonl"
    assert not preds.exists() and not audits.exists()
    with preds.open("w", encoding="utf-8", newline="\n") as f, audits.open("w", encoding="utf-8", newline="\n") as a:
        for item in manifest["queues"]:
            p, d = ranker.p32.predict_queue(visible, "train", item["queue_id"], 1)
            f.write(json.dumps(p, sort_keys=True) + "\n")
            a.write(json.dumps(d, sort_keys=True) + "\n")
    seal = {"predictions_sha256": sha(preds), "decisions_sha256": sha(audits),
            "ranker_sha256": sha(HERE / "ranker.py"),
            "phase32_model_sha256": sha(ranker.p34.P32_PATH)}
    (ART / "train_pre_label_seal.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
    # Only the train truth is opened, after the baseline prediction seal exists.
    X, y = [], []
    truth_root = DATA / "evaluator_only/train/ground_truth_private"
    for pred, audit in zip(lines(preds), lines(audits)):
        q = pred["queue_id"]
        lookup, claims = ranker.p32.p31.visible_input(visible, q, 100)
        truth = {x["alert_id"]: x["incident_id"] for x in lines(truth_root / f"{q}.jsonl")}
        oracle = lines(truth_root / f"{q}_priority.jsonl")
        top20 = {x["incident_id"] for x in oracle if x["priority_rank"] <= 20}
        sizes = Counter(truth[a] for a in pred["eligible_alert_ids"])
        for group in pred["groups_ranked"]:
            counts = Counter(truth[a] for a in group)
            qualifies = any(i in top20 and n / sizes[i] >= .8 and n / len(group) >= .8 for i, n in counts.items())
            X.append(ranker.features(group, lookup, claims, audit["accepted"]))
            y.append(int(qualifies))
    X = np.asarray(X, dtype=float)
    scaler = StandardScaler().fit(X)
    model = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=36).fit(scaler.transform(X), y)
    params = {"name": "evidence_aware_logistic", "feature_order": list(ranker.FEATURE_ORDER),
              "mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist(),
              "coefficient": model.coef_[0].tolist(), "intercept": float(model.intercept_[0]),
              "train_groups": len(X), "qualifying_groups": int(sum(y)), "fit_split": "phase36_train_only",
              "training_seed": 36101}
    (ART / "candidate_params.json").write_text(json.dumps(params, indent=2), encoding="utf-8")
    print(json.dumps({"train_groups": len(X), "qualifying_groups": int(sum(y))}))


if __name__ == "__main__": main()
