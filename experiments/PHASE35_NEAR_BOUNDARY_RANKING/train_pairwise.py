"""Fit one pairwise model on fresh train, with predictions sealed before labels."""
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


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lines(path): return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x]


def main():
    ART.mkdir(exist_ok=True)
    manifest = json.loads((DATA / "train_manifest.json").read_text(encoding="utf-8"))
    visible = DATA / "receiver_visible/train"
    predictions = ART / "train_baseline_predictions.jsonl"
    decisions = ART / "train_baseline_decisions.jsonl"
    if predictions.exists() or decisions.exists(): raise FileExistsError(predictions)
    with predictions.open("w", encoding="utf-8", newline="\n") as f, decisions.open("w", encoding="utf-8", newline="\n") as a:
        for item in manifest["queues"]:
            row, audit = ranker.p32.predict_queue(visible, "train", item["queue_id"], 1)
            f.write(json.dumps(row, sort_keys=True) + "\n")
            a.write(json.dumps(audit, sort_keys=True) + "\n")
    seal = {"prediction_sha256": sha(predictions), "decision_sha256": sha(decisions),
        "phase34_feature_source_sha256": sha(ranker.P34_RANKER), "phase35_ranker_source_sha256": sha(HERE / "ranker.py")}
    (ART / "train_pre_label_seal.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
    # Only train truth is opened for pairwise fitting.
    group_features = []; pair_indices = []
    truth_root = DATA / "evaluator_only/train/ground_truth_private"
    for pred, audit in zip(lines(predictions), lines(decisions)):
        q = pred["queue_id"]
        lookup, _ = ranker.p32.p31.visible_input(visible, q, 100)
        truth = {x["alert_id"]: x["incident_id"] for x in lines(truth_root / f"{q}.jsonl")}
        oracle = lines(truth_root / f"{q}_priority.jsonl")
        top20 = {x["incident_id"] for x in oracle if x["priority_rank"] <= 20}
        sizes = Counter(truth[aid] for aid in pred["eligible_alert_ids"])
        start = len(group_features)
        positives = []; negatives = []
        for pos, group in enumerate(pred["groups_ranked"][10:30]):
            group_features.append(ranker.p34.features(group, lookup, audit["accepted"]))
            counts = Counter(truth[aid] for aid in group)
            qualifies = any(i in top20 and hits / sizes[i] >= .8 and hits / len(group) >= .8
                            for i, hits in counts.items())
            (positives if qualifies else negatives).append(start + pos)
        pair_indices.extend((p, n) for p in positives for n in negatives)
    X = np.asarray(group_features, dtype=float)
    scaler = StandardScaler().fit(X)
    normalized = scaler.transform(X)
    differences = np.asarray([normalized[p] - normalized[n] for p, n in pair_indices])
    training = np.vstack((differences, -differences))
    labels = np.r_[np.ones(len(differences)), np.zeros(len(differences))]
    model = LogisticRegression(fit_intercept=False, C=1.0, max_iter=1000, random_state=35).fit(training, labels)
    params = {"feature_order": list(ranker.FEATURE_ORDER), "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(), "coefficient": model.coef_[0].tolist(),
        "train_groups_in_window": len(group_features), "positive_negative_pairs": len(pair_indices),
        "fit_split": "phase35_train_only", "seed": 35101, "window": [11, 30]}
    (ART / "pairwise_params.json").write_text(json.dumps(params, indent=2), encoding="utf-8")
    print(json.dumps({"window_groups": len(group_features), "pairs": len(pair_indices)}))


if __name__ == "__main__": main()
