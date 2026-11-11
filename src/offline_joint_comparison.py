"""Exploratory offline predicted-group comparison on complete small GUIDE queues.

This deliberately does not pretend that deterministic proxies are LLM agents.
Prediction never imports or reads label stores; evaluation is a separate command.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from .guide_rerun_v2 import ROOT, PRIVATE, FIELDS, features, key, labels, load, bootstrap, check_raw
from .phase2 import sha256_file

CONFIG = ROOT / "configs/offline_joint_v2.json"
OUT = ROOT / "outputs/offline_joint_v2"
HIDDEN = ROOT / "data/derived/offline_joint_v2"
PREDICTIONS = HIDDEN / "predictions.pkl"
METHODS = ("B0_rule_count", "B1_rule_bm25", "offline_CP_proxy", "offline_CPV_proxy")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def choose_cohort(data, maximum):
    counts = Counter(a["org"] for a in data["alerts"].values())
    return sorted(o for o, split in data["split"].items()
                  if split == "holdout" and 0 < counts[o] <= maximum)


def components(keys, edges, scores, docs, mode, cfg):
    """Use the same frozen retrieval edges for each method; never use truth."""
    n = len(keys)
    parent = np.arange(n)
    size = np.ones(n, dtype=np.int32)
    field_sets = [{f: set(docs[k]["fields"][f]) for f in ("Category", "MitreTechniques")}
                  for k in keys]
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return int(i)
    if mode == "rule":
        order = np.argsort(edges, kind="stable")
    else:
        order = np.lexsort((edges, -scores))
    accepted = rejected = 0
    for t in order:
        i, j = divmod(int(edges[t]), n)
        shared_category = bool(field_sets[i]["Category"] & field_sets[j]["Category"])
        shared_technique = bool(field_sets[i]["MitreTechniques"] & field_sets[j]["MitreTechniques"])
        if mode == "rule":
            link = shared_category and shared_technique
        elif mode == "cp":
            link = float(scores[t]) >= cfg["correlation_probability_threshold"]
        else:
            link = (float(scores[t]) >= cfg["verifier_proxy_probability_threshold"]
                    and (shared_category or shared_technique))
        if not link:
            continue
        ri, rj = root(i), root(j)
        if ri == rj:
            continue
        if size[ri] + size[rj] > cfg["max_predicted_component_size"]:
            rejected += 1
            continue
        if (size[ri], ri) < (size[rj], rj):
            ri, rj = rj, ri
        parent[rj] = ri
        size[ri] += size[rj]
        accepted += 1
    groups = defaultdict(list)
    for i, k in enumerate(keys):
        groups[root(i)].append(k)
    return sorted((sorted(v) for v in groups.values()), key=lambda v: v[0]), {
        "accepted_union_edges": accepted,
        "rejected_size_guard_edges": rejected,
    }


def rank_components(groups, alerts, fitted):
    """Aggregate permitted alert descriptors; score predicted groups only."""
    docs = []
    for group in groups:
        values = {f: set() for f in FIELDS}
        for alert_key in group:
            for f in FIELDS:
                values[f].update(alerts[alert_key]["fields"][f])
        docs.append({"fields": {f: sorted(v) for f, v in values.items()}})
    x = fitted["vec"].transform([features(d) for d in docs])
    z = fitted["tf"].transform(x)
    logistic = np.asarray(fitted["model"].decision_function(z)).ravel()
    dl = np.asarray(x.sum(axis=1)).ravel()
    # The query profile is built from this queue's model-visible descriptors only.
    # The prior v1 positive-label training profile was a supervised retrieval proxy.
    queue_profile = np.asarray(x.mean(axis=0)).ravel()
    bm25 = np.asarray(x @ (fitted["idf"] * queue_profile)).ravel()
    bm25 *= 2.2 / (1 + 1.2 * (.25 + .75 * dl / max(fitted["avgdl"], 1)))
    return {
        "count": [float(len(g)) for g in groups],
        "bm25": bm25.tolist(),
        "logistic": logistic.tolist(),
    }


def predict():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    if OUT.exists() or HIDDEN.exists():
        raise FileExistsError("offline_joint_v2 already exists; use a new version, never overwrite")
    source = PRIVATE / "prepared.pkl"
    model_path = PRIVATE / "fitted.pkl"
    correlation_path = PRIVATE / "correlation_model.pkl"
    for p in (source, model_path, correlation_path):
        if not p.exists():
            raise FileNotFoundError(p)
    check_raw()
    data = load()
    orgs = choose_cohort(data, cfg["max_alerts_per_org"])
    if not orgs:
        raise ValueError("empty complete-small-queue cohort")
    with model_path.open("rb") as stream:
        fitted = pickle.load(stream)
    by_org = defaultdict(dict)
    for k, doc in data["alerts"].items():
        if doc["org"] in orgs:
            by_org[doc["org"]][k] = doc
    outputs = {}
    frozen = json.loads((ROOT / "outputs/guide_rerun_v2/correlation_freeze.json").read_text())
    prior_prediction_freeze = ROOT / "outputs/guide_rerun_v2/correlation_prediction_freeze.json"
    expected_hashes = json.loads(prior_prediction_freeze.read_text())["hashes"]
    for o in orgs:
        path = PRIVATE / "correlation_predictions" / f"{key(o)}.npz"
        if sha256_file(path) != expected_hashes[key(o)]:
            raise ValueError("frozen correlation prediction hash mismatch")
        with np.load(path) as arr:
            keys = arr["keys"].tolist()
            edges = arr["edges"]
            scores = arr["probability"]
        if set(keys) != set(by_org[o]):
            raise ValueError(f"correlation prediction omitted alerts for organization {o}")
        if len(keys) > cfg["max_alerts_per_org"]:
            raise ValueError("sampled queue cannot enter full-small-queue comparison")
        rule, rule_trace = components(keys, edges, scores, by_org[o], "rule", cfg)
        cp, cp_trace = components(keys, edges, scores, by_org[o], "cp", cfg)
        cpv, cpv_trace = components(keys, edges, scores, by_org[o], "cpv", cfg)
        group_sets = {"rule": rule, "cp": cp, "cpv": cpv}
        scored = {mode: rank_components(groups, by_org[o], fitted)
                  for mode, groups in group_sets.items()}
        selection = {
            "B0_rule_count": ("rule", "count"),
            "B1_rule_bm25": ("rule", "bm25"),
            "offline_CP_proxy": ("cp", "logistic"),
            "offline_CPV_proxy": ("cpv", "logistic"),
        }
        outputs[o] = {
            "input_alert_keys": keys,
            "candidate_pair_count": len(edges),
            "methods": {
                method: {"groups": group_sets[mode], "scores": scored[mode][scorer],
                         "trace": {"rule": rule_trace, "cp": cp_trace, "cpv": cpv_trace}[mode]}
                for method, (mode, scorer) in selection.items()
            },
        }
        print("predicted", len(outputs), "/", len(orgs), "org", o, "alerts", len(keys), flush=True)
    HIDDEN.mkdir(parents=True)
    with PREDICTIONS.open("wb") as stream:
        pickle.dump(outputs, stream, protocol=pickle.HIGHEST_PROTOCOL)
    write_json(OUT / "prediction_freeze.json", {
        "classification": cfg["classification"],
        "organizations": len(orgs),
        "organization_hashes": [key(o) for o in orgs],
        "alert_counts": [len(outputs[o]["input_alert_keys"]) for o in orgs],
        "methods": list(METHODS),
        "labels_read_in_prediction_stage": False,
        "sha256": {str(p.relative_to(ROOT)): sha256_file(p)
                   for p in (CONFIG, Path(__file__), source, model_path, correlation_path,
                             ROOT / "outputs/guide_rerun_v2/correlation_freeze.json",
                             prior_prediction_freeze, PREDICTIONS)},
        "correlation_source_K": frozen["K"],
        "correlation_source_threshold": frozen["threshold"],
    })


def choose2(n):
    return n * (n - 1) // 2


def score_org(groups, scores, truth, ranks, expected_alerts, cfg):
    assert len(groups) == len(scores)
    flat = [a for group in groups for a in group]
    assert len(flat) == len(set(flat)) and set(flat) == set(expected_alerts)
    gold_counts = Counter(truth[a] for a in expected_alerts)
    positive = sum(choose2(n) for n in gold_counts.values())
    predicted_positive = sum(choose2(len(g)) for g in groups)
    intersection = [Counter(truth[a] for a in group) for group in groups]
    tp = sum(choose2(n) for counts in intersection for n in counts.values())
    fp = predicted_positive - tp
    fn = positive - tp
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
    order = sorted(range(len(groups)), key=lambda i: (-float(scores[i]), groups[i][0]))
    matched = []
    for i in order:
        counts = intersection[i]
        candidate = None
        if counts:
            gold, overlap = max(counts.items(), key=lambda kv: (kv[1], kv[0]))
            if (gold in ranks and overlap / gold_counts[gold] >= cfg["top20_recovery_min_completeness"]
                    and overlap / len(groups[i]) >= cfg["top20_recovery_min_purity"]):
                candidate = gold
        matched.append(candidate)
    recovered_top10 = len({g for g in matched[:10] if g is not None})
    recovered_top20 = len({g for g in matched[:20] if g is not None})
    def ndcg(reverse=False):
        def gain(g):
            if g is None:
                return 0
            r = 21 - ranks[g] if reverse else ranks[g]
            return 2 ** (21 - r) - 1
        dcg = sum(gain(g) / math.log2(i + 2) for i, g in enumerate(matched[:20]))
        ideal = sorted((gain(g) for g in ranks), reverse=True)
        idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
        return dcg / idcg if idcg else 0.0
    return {
        "pair_tp": tp, "pair_fp": fp, "pair_fn": fn,
        "pair_precision": precision, "pair_recall": recall, "pair_f1": f1,
        "precision_at_10": recovered_top10 / 10,
        "end_to_end_recall_at_20": recovered_top20 / 20,
        "ndcg_at_20_rank1_highest": ndcg(),
        "ndcg_at_20_rank20_highest": ndcg(reverse=True),
        "predicted_components": len(groups),
        "gold_groups_in_scope": len(gold_counts),
        "gold_top20_with_alerts_in_scope": sum(g in gold_counts for g in ranks),
        "zero_positive_pairs": positive == 0,
    }


def read_truth(orgs, all_alerts):
    truth = {}
    with (ROOT / "data/derived/preprocessing/evaluator/incident_membership.csv").open(
            encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["OrgId"] not in orgs or row["mapping_status"] != "unambiguous":
                continue
            a = key(row["OrgId"], row["AlertId"])
            if a in all_alerts:
                incident = key(row["OrgId"], row["IncidentId"])
                if a in truth and truth[a] != incident:
                    raise ValueError("unresolved conflicting truth")
                truth[a] = incident
    if set(truth) != set(all_alerts):
        raise ValueError("truth missing alert keys")
    return truth


def evaluate():
    if (OUT / "metrics.json").exists():
        raise FileExistsError("evaluation already exists; do not overwrite")
    freeze = json.loads((OUT / "prediction_freeze.json").read_text())
    if freeze["sha256"][str(PREDICTIONS.relative_to(ROOT))] != sha256_file(PREDICTIONS):
        raise ValueError("prediction freeze hash mismatch")
    check_raw()
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    with PREDICTIONS.open("rb") as stream:
        predicted = pickle.load(stream)
    orgs = set(predicted)
    all_alerts = {a for result in predicted.values() for a in result["input_alert_keys"]}
    truth = read_truth(orgs, all_alerts)
    ranks = labels(orgs)
    by_method = defaultdict(list)
    for o, result in sorted(predicted.items()):
        scope = result["input_alert_keys"]
        for method, item in result["methods"].items():
            scored = score_org(item["groups"], item["scores"], truth, ranks[o], scope, cfg)
            by_method[method].append(scored)
    metrics = {}
    for method, rows in sorted(by_method.items()):
        aggregate = {k: bootstrap([r[k] for r in rows if r[k] is not None])
                     for k in ("pair_precision", "pair_recall", "pair_f1", "precision_at_10",
                               "end_to_end_recall_at_20", "ndcg_at_20_rank1_highest",
                               "ndcg_at_20_rank20_highest")}
        tp, fp, fn = (sum(r[f"pair_{x}"] for r in rows) for x in ("tp", "fp", "fn"))
        aggregate["micro_pair"] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": tp / (tp + fp) if tp + fp else 0.0,
            "recall": tp / (tp + fn) if tp + fn else 0.0,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
        }
        aggregate["predicted_components_total"] = sum(r["predicted_components"] for r in rows)
        aggregate["gold_top20_with_alerts_total"] = sum(r["gold_top20_with_alerts_in_scope"] for r in rows)
        metrics[method] = aggregate
    report = {
        "classification": cfg["classification"],
        "organizations": len(predicted),
        "alerts": len(all_alerts),
        "candidate_pairs": sum(r["candidate_pair_count"] for r in predicted.values()),
        "label_count": 20 * len(predicted),
        "methods": metrics,
        "unavailable": {
            "B2_single_LLM": "offline-only selection; no live LLM provider or empirical predictions",
            "B3_repeated_single_LLM": "offline-only selection; no live LLM provider or empirical predictions",
            "B4_C_plus_P_LLM": "offline CP proxy is not an LLM role comparison",
            "proposed_C_P_V_LLM": "offline CPV proxy is not an LLM role comparison",
        },
        "prediction_freeze_sha256": sha256_file(OUT / "prediction_freeze.json"),
        "limitations": [
            "exploratory holdout previously accessed",
            "complete small-queue subset selected by alert count; not all 68 holdout organizations",
            "ambiguous alert keys excluded",
            "rank direction and local active-queue snapshot unverified",
            "offline proxy verifier checks descriptor agreement only, not citation truth",
            "priority scorer trained on oracle incident documents; inference uses predicted components",
        ],
    }
    write_json(OUT / "metrics.json", report)
    lines = ["# Offline predicted-group comparison", "",
             "**Exploratory, not a complete LLM-agent comparison.** All four runnable methods use the same small complete GUIDE_Test organization queues and frozen correlation candidate edges. Ranking consumes predicted groups, never oracle incident groups. B1 uses a label-free queue descriptor profile with training-corpus IDF. The offline CP/CPV rows are deterministic proxies, not the proposed LLM agents.", "",
             f"Organizations: {report['organizations']}; alerts: {report['alerts']}; candidate pairs: {report['candidate_pairs']}; expert top-20 labels: {report['label_count']}.", "",
             "| Method | Pair F1 micro | Pair F1 macro | P@10 macro | End-to-end Recall@20 macro | nDCG@20 rank 1 high |",
             "|---|---:|---:|---:|---:|---:|"]
    for method in METHODS:
        m = metrics[method]
        lines.append(f"| {method} | {m['micro_pair']['f1']:.4f} | {m['pair_f1']['mean']:.4f} | {m['precision_at_10']['mean']:.4f} | {m['end_to_end_recall_at_20']['mean']:.4f} | {m['ndcg_at_20_rank1_highest']['mean']:.4f} |")
    lines += ["", "B2, B3, B4, and the proposed LLM C/P/V have no empirical scores in this offline run. Do not substitute synthetic stubs or deterministic proxies for them.", "",
              "Pair F1 is computed from all within-queue alert pairs implied by predicted components. End-to-end recovery requires a predicted top-20 component to contain at least 80% of a gold incident's in-scope alerts and at least 80% of its own alerts to belong to that incident. A missing gold incident has zero recovery. Precision@10 counts recovered expert incidents in the first ten predicted components divided by ten. nDCG uses the implemented exponential gain; reverse direction is in metrics.json.", "",
              "The original 30 organizations were excluded; the 68 rerun holdout organizations have already been evaluated and are exploratory. This comparison restricts further to complete queues with at most 500 unambiguous alerts, selected without outcome labels. It cannot establish performance on larger queues or a confirmatory holdout.", "",
              "The v1 prototype used a training-positive BM25 profile and must not be described as the plain B1 baseline. This v2 run corrects that definition without altering v1 artifacts. The two exploratory runs are not independent tests.", "",
              "Source artifacts and their hashes are in prediction_freeze.json. Private predictions remain under ignored data/derived/offline_joint_v2/; only aggregate results are under outputs/offline_joint_v2/.", ""]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    write_json(OUT / "run_manifest.json", {
        "classification": cfg["classification"],
        "source_raw_hashes": json.loads((ROOT / "outputs/guide_rerun_v2/run_manifest.json").read_text())["raw_hashes"],
        "sha256": {str(p.relative_to(ROOT)): sha256_file(p)
                   for p in (CONFIG, Path(__file__), PREDICTIONS, OUT / "prediction_freeze.json",
                             OUT / "metrics.json", OUT / "report.md")},
    })


def self_test():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    a, b, c = "a", "b", "c"
    truth = {a: "x", b: "x", c: "y"}
    ranks = {"x": 1, "y": 2, **{str(i): i for i in range(3, 21)}}
    good = score_org([[a, b], [c]], [2, 1], truth, ranks, [a, b, c], cfg)
    assert good["pair_tp"] == 1 and good["pair_fp"] == 0 and good["pair_fn"] == 0
    assert good["end_to_end_recall_at_20"] == .1
    bad = score_org([[a, c], [b]], [2, 1], truth, ranks, [a, b, c], cfg)
    assert bad["pair_tp"] == 0 and bad["pair_fp"] == 1 and bad["pair_fn"] == 1
    assert bad["end_to_end_recall_at_20"] == 0
    print("offline joint self-test: 7 assertions passed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("self-test", "predict", "evaluate"))
    args = parser.parse_args()
    {"self-test": self_test, "predict": predict, "evaluate": evaluate}[args.stage]()


if __name__ == "__main__":
    main()
