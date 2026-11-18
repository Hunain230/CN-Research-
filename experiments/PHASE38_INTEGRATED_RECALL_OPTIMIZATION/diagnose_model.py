"""Post-evaluation diagnostics; never select or retune the sealed candidate."""
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

import ranker

HERE = Path(__file__).resolve().parent
DATA = HERE / "dataset"
ART = HERE / "artifacts"


def lines(path): return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]
def csv_write(path, rows, columns):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns); w.writeheader(); w.writerows(rows)


def incident_status(pred, truth, oracle):
    top20 = {x["incident_id"]: x for x in oracle if x["priority_rank"] <= 20}
    sizes = Counter(truth[a] for a in pred["eligible_alert_ids"])
    positions = defaultdict(list); fragments = defaultdict(list)
    for pos, group in enumerate(pred["groups_ranked"], 1):
        counts = Counter(truth[a] for a in group)
        for i, n in counts.items():
            if i not in top20: continue
            fragments[i].append((n, pos, len(group)))
            if n / sizes[i] >= .8 and n / len(group) >= .8: positions[i].append(pos)
    return {i: {"status": "recalled" if positions[i] and min(positions[i]) <= 20 else
                    "recoverable_unranked" if positions[i] else "unrecoverable",
                "rank": min(positions[i]) if positions[i] else None,
                "largest_fragment": max(fragments[i], default=(0, 0, 0)),
                "eligible_alerts": sizes[i]} for i in top20}


def pair_data(split):
    visible = DATA / "receiver_visible" / split
    truth_root = DATA / "evaluator_only" / split / "ground_truth_private"
    pred_path = ART / ("train_baseline_predictions.jsonl" if split == "train" else "development_baseline_predictions.jsonl")
    decision_path = ART / ("train_baseline_decisions.jsonl" if split == "train" else "development_baseline_decisions.jsonl")
    result = []
    for pred, decision in zip(lines(pred_path), lines(decision_path)):
        q = pred["queue_id"]
        lookup, claims = ranker.p32.p31.visible_input(visible, q, 100)
        truth = {x["alert_id"]: x["incident_id"] for x in lines(truth_root / f"{q}.jsonl")}
        oracle = lines(truth_root / f"{q}_priority.jsonl")
        top20 = {x["incident_id"] for x in oracle if x["priority_rank"] <= 20}
        sizes = Counter(truth[a] for a in pred["eligible_alert_ids"])
        features = []; positives = []; negatives = []
        for group in pred["groups_ranked"][10:30]:
            index = len(features)
            features.append(ranker.p36.features(group, lookup, claims, decision["accepted"]))
            counts = Counter(truth[a] for a in group)
            qualifies = any(i in top20 and n / sizes[i] >= .8 and n / len(group) >= .8 for i, n in counts.items())
            (positives if qualifies else negatives).append(index)
        result.append((np.asarray(features, dtype=float), [(p, n) for p in positives for n in negatives]))
    return result


def loss(differences, weights):
    z = differences @ weights
    return float(np.logaddexp(0, -z).mean()), float((z > 0).mean())


def main():
    params = json.loads((ART / "candidate_params.json").read_text(encoding="utf-8"))
    mean = np.asarray(params["mean"]); scale = np.asarray(params["scale"])
    weights = np.asarray(params["coefficient"])
    datasets = {}
    for split in ("train", "development"):
        rows = pair_data(split)
        differences = np.vstack([((X - mean) / scale)[[p for p, _ in pairs]] -
                                  ((X - mean) / scale)[[n for _, n in pairs]]
                                  for X, pairs in rows if pairs])
        datasets[split] = (rows, differences)
    train_loss, train_accuracy = loss(datasets["train"][1], weights)
    dev_loss, dev_accuracy = loss(datasets["development"][1], weights)
    ablation = []
    for j, name in enumerate(params["feature_order"]):
        w = weights.copy(); w[j] = 0
        tl, _ = loss(datasets["train"][1], w)
        dl, _ = loss(datasets["development"][1], w)
        ablation.append({"feature": name, "sealed_coefficient": float(weights[j]),
                         "train_loss_without": tl, "development_loss_without": dl,
                         "train_loss_delta": tl - train_loss, "development_loss_delta": dl - dev_loss,
                         "note": "posthoc_coefficient_zeroing_no_refit_no_selection"})
    csv_write(HERE / "FEATURE_ABLATION.csv", ablation, list(ablation[0]))
    # Diagnostic learning curve: fixed 2/4/8 train-queue prefixes, never a candidate search.
    curve = []
    for n in (2, 4, 8):
        subset = datasets["train"][0][:n]
        X = np.vstack([x for x, _ in subset])
        scaler = StandardScaler().fit(X)
        differences = np.vstack([(scaler.transform(x)[[p for p, _ in pairs]] -
                                   scaler.transform(x)[[m for _, m in pairs]])
                                  for x, pairs in subset if pairs])
        symmetric = np.vstack((differences, -differences))
        labels = np.r_[np.ones(len(differences)), np.zeros(len(differences))]
        model = LogisticRegression(fit_intercept=False, C=1.0, max_iter=1000, random_state=38).fit(symmetric, labels)
        fitted = model.coef_[0]
        # Recompute pair differences in each diagnostic model's scale; means cancel in differences.
        dtrain = datasets["train"][1] * (scale / scaler.scale_)
        ddev = datasets["development"][1] * (scale / scaler.scale_)
        tl, ta = loss(dtrain, fitted); dl, da = loss(ddev, fitted)
        curve.append({"train_queues": n, "train_pair_loss": tl, "development_pair_loss": dl,
                      "train_pair_accuracy": ta, "development_pair_accuracy": da,
                      "diagnostic_only": True})
    csv_write(HERE / "LEARNING_CURVE.csv", curve, list(curve[0]))
    base = lines(ART / "development_baseline_predictions.jsonl")
    cand = lines(ART / "development_candidate_predictions.jsonl")
    truth_root = DATA / "evaluator_only/development/ground_truth_private"
    rank_rows = []; recon_rows = []; scenarios = defaultdict(Counter)
    for b, c in zip(base, cand):
        q = b["queue_id"]
        truth = {x["alert_id"]: x["incident_id"] for x in lines(truth_root / f"{q}.jsonl")}
        oracle = lines(truth_root / f"{q}_priority.jsonl")
        before, after = incident_status(b, truth, oracle), incident_status(c, truth, oracle)
        for item in oracle:
            if item["priority_rank"] > 20: continue
            i = item["incident_id"]
            scenarios[item["template_id"]]["opportunities"] += 1
            scenarios[item["template_id"]]["baseline_recalled"] += before[i]["status"] == "recalled"
            scenarios[item["template_id"]]["candidate_recalled"] += after[i]["status"] == "recalled"
            if after[i]["status"] != "recalled":
                row = {"queue_id": q, "incident_id_offline_only": i, "template_id_offline_only": item["template_id"],
                       "oracle_rank_offline_only": item["priority_rank"],
                       "baseline_status": before[i]["status"], "candidate_status": after[i]["status"],
                       "baseline_group_rank": before[i]["rank"] or "", "candidate_group_rank": after[i]["rank"] or "",
                       "eligible_alerts": after[i]["eligible_alerts"],
                       "largest_fragment_hits": after[i]["largest_fragment"][0],
                       "largest_fragment_position": after[i]["largest_fragment"][1]}
                rank_rows.append(row)
                if after[i]["status"] == "unrecoverable": recon_rows.append(row)
    csv_write(HERE / "RANKING_ERROR_ANALYSIS.csv", rank_rows, list(rank_rows[0]))
    csv_write(HERE / "RECONSTRUCTION_ERROR_ANALYSIS.csv", recon_rows, list(recon_rows[0]))
    scenario_rows = [{"template_id_offline_only": k, **dict(v)} for k, v in sorted(scenarios.items())]
    csv_write(HERE / "SCENARIO_DIAGNOSTICS.csv", scenario_rows,
              ["template_id_offline_only", "opportunities", "baseline_recalled", "candidate_recalled"])
    report = {"train_pair_loss": train_loss, "development_pair_loss": dev_loss,
              "train_pair_accuracy": train_accuracy, "development_pair_accuracy": dev_accuracy,
              "pair_loss_gap": dev_loss - train_loss, "train_pairs": len(datasets["train"][1]),
              "development_pairs": len(datasets["development"][1]),
              "candidate_misses": len(rank_rows), "candidate_unrecoverable": len(recon_rows),
              "candidate_recoverable_unranked": len(rank_rows) - len(recon_rows),
              "posthoc_no_candidate_selection": True}
    (ART / "model_diagnostics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__": main()
