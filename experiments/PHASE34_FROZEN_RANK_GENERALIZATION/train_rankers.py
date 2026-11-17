"""Fit two predeclared rank models from Phase 34 train truth only."""
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

import ranker

HERE = Path(__file__).resolve().parent
DATA = HERE / "dataset"
ART = HERE / "artifacts"


def lines(path): return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x]


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ART.mkdir(exist_ok=True)
    manifest = json.loads((DATA / "train_manifest.json").read_text(encoding="utf-8"))
    visible = DATA / "receiver_visible/train"
    predictions = ART / "train_frozen_predictions.jsonl"
    audits = ART / "train_frozen_decisions.jsonl"
    if predictions.exists() or audits.exists(): raise FileExistsError(predictions)
    with predictions.open("w", encoding="utf-8", newline="\n") as f, audits.open("w", encoding="utf-8", newline="\n") as a:
        for item in manifest["queues"]:
            pred, audit = ranker.p32.predict_queue(visible, "train", item["queue_id"], 1)
            f.write(json.dumps(pred, sort_keys=True) + "\n")
            a.write(json.dumps(audit, sort_keys=True) + "\n")
    seal = {"prediction_sha256": sha(predictions), "decision_sha256": sha(audits),
            "ranker_source_sha256": sha(HERE / "ranker.py"),
            "phase32_model_sha256": sha(ranker.P32_PATH)}
    (ART / "train_pre_label_seal.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
    # Train truth is read only after group predictions are sealed.
    X, y_binary, y_priority = [], [], []
    private = DATA / "evaluator_only/train/ground_truth_private"
    for pred, audit in zip(lines(predictions), lines(audits)):
        q = pred["queue_id"]
        lookup, _ = ranker.p32.p31.visible_input(visible, q, 100)
        truth = {x["alert_id"]: x["incident_id"] for x in lines(private / f"{q}.jsonl")}
        oracle = lines(private / f"{q}_priority.jsonl")
        top20 = {x["incident_id"]: x for x in oracle if x["priority_rank"] <= 20}
        sizes = Counter(truth[aid] for aid in pred["eligible_alert_ids"])
        for group in pred["groups_ranked"]:
            counts = Counter(truth[aid] for aid in group)
            matches = [i for i, hits in counts.items() if i in top20 and
                       hits / sizes[i] >= .8 and hits / len(group) >= .8]
            qualifying = min(matches, key=lambda i: top20[i]["priority_rank"]) if matches else None
            X.append(ranker.features(group, lookup, audit["accepted"]))
            y_binary.append(int(qualifying is not None))
            y_priority.append(top20[qualifying]["priority_score"] if qualifying else 0.0)
    X = np.asarray(X, dtype=float)
    scaler = StandardScaler().fit(X)
    standardized = scaler.transform(X)
    models = {
        "top20_logistic": LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=34).fit(standardized, y_binary),
        "priority_ridge": Ridge(alpha=10.0).fit(standardized, y_priority)}
    for name, fitted in models.items():
        coefficients = fitted.coef_[0] if name == "top20_logistic" else fitted.coef_
        intercept = fitted.intercept_[0] if name == "top20_logistic" else fitted.intercept_
        params = {"name": name, "feature_order": list(ranker.FEATURE_ORDER),
            "mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist(),
            "coefficient": np.asarray(coefficients).tolist(), "intercept": float(intercept),
            "train_groups": len(X), "top20_qualifying_groups": int(sum(y_binary)),
            "fit_split": "phase34_train_only", "training_seed": 34101}
        (ART / f"{name}_params.json").write_text(json.dumps(params, indent=2), encoding="utf-8")
    print(json.dumps({"train_groups": len(X), "qualifying": sum(y_binary), "models": list(models)}))


if __name__ == "__main__": main()
