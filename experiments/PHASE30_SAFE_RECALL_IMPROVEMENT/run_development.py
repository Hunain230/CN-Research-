"""Three predeclared Phase 30 candidates on Phase 16 development only."""
import csv
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V4 = ROOT / "experiments/PHASE16_PROVENANCE_RECONSTRUCTION/v4"
PREV = ROOT / "experiments/RECALL_ONLY_IMPROVEMENT"
ART = HERE / "artifacts"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


PREDICT = module("phase16_predict", V4 / "predict.py")
EVAL = module("phase15_eval", ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py")
OLD_RANK = module("recall_only_rank", PREV / "run_development.py")


def lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def features(group, lookup):
    items = list({lookup[a]["source_id"]: lookup[a] for a in group}.values())
    span = max(a["event_minute"] for a in items) - min(a["event_minute"] for a in items)
    return [OLD_RANK.score(group, lookup, "source_depth"),
            max(a["severity"] for a in items), max(a["asset_criticality"] for a in items),
            len({a["event_type"] for a in items}), min(len(items), 10), min(span, 50) / 10]


def train_ranker():
    manifest = json.loads((V4 / "datasets/manifest.json").read_text(encoding="utf-8"))
    X, y = [], []
    for item in manifest["queues"]["train"]:
        q = item["queue_id"]
        alerts = PREDICT.visible(V4 / "datasets", "train", q, 100)
        lookup = {a["alert_id"]: a for a in alerts}
        groups, _, _, _ = PREDICT.correlate(alerts, "lineage_one_context_v", 100)
        truth = {a["alert_id"]: a["incident_id"] for a in lines(V4 / "datasets/train/ground_truth_private" / f"{q}.jsonl")}
        priority = lines(V4 / "datasets/train/ground_truth_private" / f"{q}_priority.jsonl")
        top10 = {a["incident_id"] for a in priority if a["priority_rank"] <= 10}
        sizes = Counter(truth[a["alert_id"]] for a in alerts)
        for group in groups:
            counts = Counter(truth[a] for a in group)
            label = any(i in top10 and n / sizes[i] >= .8 and n / len(group) >= .8 for i, n in counts.items())
            X.append(features(group, lookup)); y.append(int(label))
    model = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=30)
    model.fit(np.array(X), np.array(y))
    (ART / "train_ranker.json").write_text(json.dumps({"feature_order": ["source_depth", "severity", "criticality", "event_diversity", "source_count", "time_span"],
        "coefficient": model.coef_[0].tolist(), "intercept": model.intercept_.tolist(),
        "train_groups": len(y), "positive": sum(y)}, indent=2), encoding="utf-8")
    return model


def strict_union(groups, lookup):
    """Direct dual-reference proposal; source IDs are witnesses, not trust roots."""
    refs = []
    for group in groups:
        values = {}
        for field in ("auth_session_ref", "network_flow_ref"):
            values[field] = defaultdict(set)
            for aid in group:
                a = lookup[aid]
                if a[field]: values[field][a[field]].add(a["source_id"])
        refs.append(values)
    usage = {field: Counter() for field in ("auth_session_ref", "network_flow_ref")}
    for group_ref in refs:
        for field in usage:
            usage[field].update(group_ref[field].keys())
    proposals = []
    diagnostics = Counter()
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            shared = {f: set(refs[i][f]) & set(refs[j][f]) for f in usage}
            if not all(shared.values()): continue
            diagnostics["dual_reference_pairs"] += 1
            if any(usage[f][token] != 2 for f in usage for token in shared[f]):
                diagnostics["nonunique_reference_reject"] += 1; continue
            witnesses = set().union(*(refs[k][f][t] for k in (i, j) for f in usage for t in shared[f]))
            if len(witnesses) < 4:
                diagnostics["source_diversity_reject"] += 1; continue
            left, right = [lookup[a] for a in groups[i]], [lookup[a] for a in groups[j]]
            hosts = [{a["host"] for a in side if a["host"]} for side in (left, right)]
            accounts = [{a["account"] for a in side if a["account"]} for side in (left, right)]
            if not (hosts[0] & hosts[1] and accounts[0] & accounts[1]):
                diagnostics["context_reject"] += 1; continue
            if len(groups[i]) + len(groups[j]) > 100:
                diagnostics["cap_reject"] += 1; continue
            if not all(any(abs(a["event_minute"] - b["event_minute"]) <= 25 and
                    a[f] and a[f] == b[f] for a in left for b in right) for f in usage):
                diagnostics["time_reject"] += 1; continue
            proposals.append((i, j))
    # Noncascading: original fragments can join at most once.
    used = set(); accepted = []
    for i, j in proposals:
        if i in used or j in used: continue
        used.update((i, j)); accepted.append((i, j))
    diagnostics["accepted_unions"] = len(accepted)
    result = [groups[i] + groups[j] for i, j in accepted]
    result.extend(group for i, group in enumerate(groups) if i not in used)
    return result, dict(diagnostics)


def rank(groups, lookup, candidate, model):
    if candidate == "recovery_source_depth":
        return sorted(groups, key=lambda g: (-OLD_RANK.score(g, lookup, "source_depth"), min(g)))
    def score(g):
        f = features(g, lookup)
        logit = float(model.decision_function(np.array([f]))[0])
        return f[0] + logit
    return sorted(groups, key=lambda g: (-score(g), min(g)))


def main():
    ART.mkdir(exist_ok=True)
    model = train_ranker()
    baseline = lines(PREV / "artifacts/development_source_depth.jsonl")
    reference = json.loads((PREV / "artifacts/development_source_depth_evaluation.json").read_text(encoding="utf-8"))
    outputs = []
    for candidate in ("trained_rank", "recovery_source_depth", "hybrid"):
        path = ART / f"development_{candidate}.jsonl"
        eval_path = ART / f"development_{candidate}_evaluation.json"
        diagnostics = Counter()
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            for row in baseline:
                q = row["queue_id"]
                visible = PREDICT.visible(V4 / "datasets", "development", q, 100)
                lookup = {a["alert_id"]: a for a in visible}
                groups = row["groups_ranked"]
                if candidate != "trained_rank":
                    groups, detail = strict_union(groups, lookup)
                    diagnostics.update(detail)
                ranked = rank(groups, lookup, candidate, model)
                output = dict(row, groups_ranked=ranked, ranker=candidate)
                stream.write(json.dumps(output, sort_keys=True) + "\n")
        if not eval_path.exists():
            EVAL.evaluate(path, V4 / "datasets/development/ground_truth_private", eval_path)
        result = json.loads(eval_path.read_text(encoding="utf-8"))
        s, b = result["summary"], reference["summary"]
        regressions = [x["queue_id"] for x, y in zip(reference["queues"], result["queues"])
                       if y["false_grouped_pairs"] > x["false_grouped_pairs"] or
                       y["mixed_predicted_groups"] > x["mixed_predicted_groups"]]
        gate = (s["recall20_count"] > b["recall20_count"] and s["p10_count"] >= 97 and
                s["recoverable"] >= b["recoverable"] and s["grouped_pair_precision"] >= b["grouped_pair_precision"] and
                s["false_grouped_pairs"] <= b["false_grouped_pairs"] and
                s["mixed_predicted_groups"] <= b["mixed_predicted_groups"] and not regressions)
        outputs.append({"candidate": candidate, "recall20": s["recall20_count"], "recall_denominator": s["expert_top20"],
            "recoverable": s["recoverable"], "p10": s["p10_count"], "p10_denominator": 150,
            "pair_precision": s["grouped_pair_precision"], "false_pairs": s["false_grouped_pairs"],
            "mixed_groups": s["mixed_predicted_groups"], "new_relationships": diagnostics["accepted_unions"],
            "queue_safety_regressions": len(regressions), "development_gate": gate,
            "prediction_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        (ART / f"{candidate}_proposal_diagnostics.json").write_text(json.dumps(dict(diagnostics), indent=2), encoding="utf-8")
    for name in ("DEVELOPMENT_RESULTS.csv", "CANDIDATE_COMPARISON.csv"):
        with (HERE / name).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(outputs[0])); writer.writeheader(); writer.writerows(outputs)
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()
