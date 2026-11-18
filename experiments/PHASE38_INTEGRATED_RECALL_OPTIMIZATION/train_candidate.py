"""Seal Phase 38 train predictions, then fit one hard-negative pairwise model."""
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
    assert manifest["seed"] == 38101 and len(manifest["queues"]) == 8
    visible = DATA / "receiver_visible/train"
    pred_path = ART / "train_baseline_predictions.jsonl"
    decision_path = ART / "train_baseline_decisions.jsonl"
    assert not pred_path.exists() and not decision_path.exists()
    with pred_path.open("w", encoding="utf-8", newline="\n") as f, decision_path.open("w", encoding="utf-8", newline="\n") as a:
        for item in manifest["queues"]:
            p, d = ranker.p32.predict_queue(visible, "train", item["queue_id"], 1)
            f.write(json.dumps(p, sort_keys=True) + "\n")
            a.write(json.dumps(d, sort_keys=True) + "\n")
    seal = {"predictions_sha256": sha(pred_path), "decisions_sha256": sha(decision_path),
            "ranker_sha256": sha(HERE / "ranker.py"),
            "phase32_model_sha256": sha(ranker.p36.p34.P32_PATH)}
    (ART / "train_pre_label_seal.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
    # Training truth opens only after the baseline prediction seal is written.
    X, pairs = [], []
    truth_root = DATA / "evaluator_only/train/ground_truth_private"
    for pred, decision in zip(lines(pred_path), lines(decision_path)):
        q = pred["queue_id"]
        lookup, claims = ranker.p32.p31.visible_input(visible, q, 100)
        truth = {x["alert_id"]: x["incident_id"] for x in lines(truth_root / f"{q}.jsonl")}
        oracle = lines(truth_root / f"{q}_priority.jsonl")
        top20 = {x["incident_id"] for x in oracle if x["priority_rank"] <= 20}
        sizes = Counter(truth[a] for a in pred["eligible_alert_ids"])
        positives, negatives = [], []
        for group in pred["groups_ranked"][10:30]:
            index = len(X)
            X.append(ranker.p36.features(group, lookup, claims, decision["accepted"]))
            counts = Counter(truth[a] for a in group)
            qualifies = any(i in top20 and n / sizes[i] >= .8 and n / len(group) >= .8 for i, n in counts.items())
            (positives if qualifies else negatives).append(index)
        pairs.extend((p, n) for p in positives for n in negatives)
    X = np.asarray(X, dtype=float)
    scaler = StandardScaler().fit(X)
    normalized = scaler.transform(X)
    differences = np.asarray([normalized[p] - normalized[n] for p, n in pairs])
    training = np.vstack((differences, -differences))
    labels = np.r_[np.ones(len(differences)), np.zeros(len(differences))]
    model = LogisticRegression(fit_intercept=False, C=1.0, max_iter=1000, random_state=38).fit(training, labels)
    params = {"feature_order": list(ranker.FEATURE_ORDER), "mean": scaler.mean_.tolist(),
              "scale": scaler.scale_.tolist(), "coefficient": model.coef_[0].tolist(),
              "train_window_groups": len(X), "positive_negative_pairs": len(pairs),
              "fit_split": "phase38_train_only", "seed": 38101, "window": [11, 30]}
    (ART / "candidate_params.json").write_text(json.dumps(params, indent=2), encoding="utf-8")
    print(json.dumps({"train_window_groups": len(X), "pairs": len(pairs)}))


if __name__ == "__main__": main()
