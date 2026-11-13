"""Frozen, label-blind local Qwen C/P/V evaluation on 20 GUIDE small queues.

This is an exploratory bounded model study, paired for C and B2 on selected
candidate pairs. Prediction and truth evaluation are separate commands.
"""

from __future__ import annotations

import argparse
import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

from .empirical_priority_tie_eval import _expected_metrics
from .guide_rerun_v2 import INPUT_HASHES, key, labels
from .offline_joint_comparison import bootstrap, choose_cohort, read_truth
from .phase2 import sha256_file
from .submission_local_qwen import (
    POLICY, PREPARED, ROOT, call, group_prompt, groups_from_links, model_digest,
    normalize_decisions, normalize_priority, normalize_verification, pairs_prompt,
)


MODEL = "qwen2.5:3b"
PREFIX = "submission_qwen_v2_"
ORGANIZATIONS = 20
PAIRS_PER_ORG = 12
PAIR_BATCH = 6
GROUP_BATCH = 8


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_raw() -> None:
    for name, expected in INPUT_HASHES.items():
        if sha256_file(ROOT / "data/raw" / name) != expected:
            raise ValueError(f"Raw input hash mismatch: {name}")


def choose_inputs(data: dict) -> dict[str, dict]:
    """Choose exact descriptor matches with no evaluator truth or scores."""
    eligible = choose_cohort(data, 500)
    by_org = defaultdict(dict)
    for alert, doc in data["alerts"].items():
        if doc["org"] in eligible:
            by_org[doc["org"]][alert] = doc
    candidates = []
    for org in eligible:
        docs = by_org[org]
        buckets = defaultdict(list)
        for alert, doc in docs.items():
            for category in doc["fields"]["Category"]:
                for technique in doc["fields"]["MitreTechniques"]:
                    buckets[(category, technique)].append(alert)
        pairs = set()
        for members in buckets.values():
            members = sorted(set(members))
            for i, left in enumerate(members):
                for right in members[i + 1:]:
                    pairs.add((left, right))
        if len(pairs) >= PAIRS_PER_ORG:
            candidates.append((org, docs, pairs))
    chosen = sorted(candidates, key=lambda row: key("submission-qwen-v2-org", row[0]))[:ORGANIZATIONS]
    if len(chosen) != ORGANIZATIONS:
        raise ValueError("Insufficient label-blind eligible queues")
    out = {}
    for org, docs, all_pairs in chosen:
        selected = sorted(all_pairs, key=lambda pair: key("submission-qwen-v2-pair", *pair))[:PAIRS_PER_ORG]
        pairs = [{"id": f"P{i:02d}", "left": a, "right": b} for i, (a, b) in enumerate(selected, 1)]
        alerts = sorted({a for pair in pairs for a in (pair["left"], pair["right"])})
        aliases = {alert: f"A{i:02d}" for i, alert in enumerate(alerts, 1)}
        out[org] = {"pairs": pairs, "alerts": alerts, "docs": {a: docs[a] for a in alerts}, "aliases": aliases, "available_exact_pairs": len(all_pairs)}
    return out


def predict(run_id: str) -> None:
    if not run_id.startswith(PREFIX):
        raise ValueError(f"Run ID must start with {PREFIX}")
    public = ROOT / "outputs" / run_id
    private = ROOT / "data/derived" / run_id
    if public.exists() or private.exists():
        raise FileExistsError("Run path exists; choose a new versioned ID")
    if "no_external_transmission: true" not in POLICY.read_text(encoding="utf-8"):
        raise ValueError("Local-only field policy changed")
    check_raw()
    digest = model_digest()
    with PREPARED.open("rb") as stream:
        data = pickle.load(stream)
    inputs = choose_inputs(data)
    calls = []
    predictions = {}
    for position, (org, item) in enumerate(sorted(inputs.items()), 1):
        pairs, docs, aliases = item["pairs"], item["docs"], item["aliases"]
        c, b2 = {}, {}
        for offset in range(0, len(pairs), PAIR_BATCH):
            batch = pairs[offset:offset + PAIR_BATCH]
            c.update(normalize_decisions(call(pairs_prompt(batch, aliases, docs, "C"), "C", 0, calls), batch, aliases))
            b2.update(normalize_decisions(call(pairs_prompt(batch, aliases, docs, "B2 single model"), "B2", 0, calls), batch, aliases))
        groups = groups_from_links(item["alerts"], pairs, c)
        scores, review = [], []
        for offset in range(0, len(groups), GROUP_BATCH):
            chunk = groups[offset:offset + GROUP_BATCH]
            priority = normalize_priority(call(group_prompt(chunk, aliases, docs, "P"), "P", 0, calls), chunk, aliases)
            verification = normalize_verification(call(group_prompt(chunk, aliases, docs, "V", priority), "V", 0, calls), chunk, aliases)
            for i, group in enumerate(chunk, 1):
                gid = f"G{i:02d}"
                score = priority[gid]["score"]
                uncertain = any(row["decision"] == "UNSURE" and (pair["left"] in group or pair["right"] in group) for pair in pairs for row in [c[pair["id"]]])
                scores.append(float(score) if score is not None else 0.0)
                review.append(bool(score is None or not priority[gid]["refs"] or verification[gid]["decision"] != "PASS" or uncertain))
        predictions[org] = {"alerts": item["alerts"], "pairs": pairs, "c": c, "b2": b2, "groups": groups, "scores": scores, "review": review, "available_exact_pairs": item["available_exact_pairs"]}
        print(f"Local Qwen v2 predicted organization {position}/{ORGANIZATIONS}: {len(pairs)} pairs, {len(groups)} groups", flush=True)
    private.mkdir(parents=True)
    prediction_path = private / "predictions.pkl"
    with prediction_path.open("wb") as stream:
        pickle.dump(predictions, stream, protocol=pickle.HIGHEST_PROTOCOL)
    write_json(private / "calls.json", {"calls": calls, "model": MODEL, "model_digest": digest})
    public.mkdir(parents=True)
    freeze = {
        "classification": "exploratory_bounded_local_qwen_v2_not_full_model_study",
        "model": MODEL, "model_digest": digest,
        "selection": "first 20 <=500-alert holdout organizations with >=12 exact Category+MitreTechniques pairs, SHA-256(org) order; 12 SHA-256(pair)-ordered pairs per org; no labels or scores read",
        "organizations": ORGANIZATIONS, "pairs_per_organization": PAIRS_PER_ORG,
        "prediction_sha256": sha256_file(prediction_path), "calls_sha256": sha256_file(private / "calls.json"),
        "source_sha256": {str(path.relative_to(ROOT)): sha256_file(path) for path in (Path(__file__), ROOT / "src/submission_local_qwen.py", POLICY, PREPARED)},
        "raw_sha256": INPUT_HASHES,
        "labels_read_in_prediction_stage": False, "localhost_only": True,
        "call_summary": {"total": len(calls), "failed": sum(row["status"] != "ok" for row in calls), "prompt_tokens": sum(row["prompt_tokens"] for row in calls), "output_tokens": sum(row["output_tokens"] for row in calls), "elapsed_seconds": round(sum(row["elapsed_seconds"] for row in calls), 3)},
    }
    write_json(public / "prediction_freeze.json", freeze)
    print(json.dumps({"status": "frozen", "run": run_id, "calls": len(calls), "failures": freeze["call_summary"]["failed"]}, sort_keys=True))


def rank_metrics(groups: list[list[str]], scores: list[float], truth: dict, ranks: dict, full_counts: Counter) -> tuple[dict, int]:
    recovered = {}
    for group in groups:
        members = Counter(truth[a] for a in group)
        gold, overlap = max(members.items(), key=lambda row: (row[1], row[0]))
        if gold in ranks and overlap / full_counts[gold] >= 0.8 and overlap / len(group) >= 0.8:
            recovered[group[0]] = ranks[gold]
    ordered = sorted(zip(groups, scores), key=lambda row: (-row[1], row[0][0]))
    blocks = []
    for group, score in ordered:
        if not blocks or blocks[-1][0][1] != score:
            blocks.append([])
        blocks[-1].append((group[0], score))
    label_map = recovered | {f"unrecovered-{gold}": rank for gold, rank in ranks.items() if rank not in recovered.values()}
    return _expected_metrics(blocks, label_map), len(set(recovered.values()))


def evaluate(run_id: str) -> None:
    public = ROOT / "outputs" / run_id
    private = ROOT / "data/derived" / run_id
    if (public / "metrics.json").exists():
        raise FileExistsError("Evaluation already exists")
    freeze_path = public / "prediction_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    prediction_path = private / "predictions.pkl"
    if sha256_file(prediction_path) != freeze["prediction_sha256"]:
        raise ValueError("Prediction freeze mismatch")
    if sha256_file(PREPARED) != freeze["source_sha256"][r"data\derived\guide_rerun_v2\prepared.pkl"]:
        raise ValueError("Prepared input hash mismatch")
    check_raw()
    with prediction_path.open("rb") as stream:
        predictions = pickle.load(stream)
    with PREPARED.open("rb") as stream:
        data = pickle.load(stream)
    orgs = set(predictions)
    all_alerts = {a for a, doc in data["alerts"].items() if doc["org"] in orgs}
    truth = read_truth(orgs, all_alerts)
    ranks = labels(orgs)
    by_org = defaultdict(list)
    for alert in all_alerts:
        by_org[data["alerts"][alert]["org"]].append(alert)
    counts = {method: Counter() for method in ("C", "B2")}
    ranked = []
    for org, item in sorted(predictions.items()):
        for method, field in (("C", "c"), ("B2", "b2")):
            tally = counts[method]
            for pair in item["pairs"]:
                positive = truth[pair["left"]] == truth[pair["right"]]
                decision = item[field][pair["id"]]["decision"]
                tally["pairs"] += 1
                tally["positive_pairs"] += positive
                tally["abstentions"] += decision == "UNSURE"
                tally["tp"] += positive and decision == "LINK"
                tally["fp"] += not positive and decision == "LINK"
                tally["fn"] += positive and decision != "LINK"
        gold_counts = Counter(truth[a] for a in by_org[org])
        ranking, recovered = rank_metrics(item["groups"], item["scores"], truth, ranks[org], gold_counts)
        ranked.append({"recall20": ranking["recall_at_20"], "p10": ranking["precision_at_10"], "ndcg1": ranking["ndcg_at_20_rank1_highest"], "ndcg20": ranking["ndcg_at_20_rank20_highest_sensitivity"], "recovered": recovered, "alerts": len(by_org[org]), "selected_alerts": len(item["alerts"]), "groups": len(item["groups"]), "review_fraction": sum(item["review"]) / len(item["review"]), "top20_with_alerts": sum(g in gold_counts for g in ranks[org])})
    pair_metrics = {}
    for method, tally in counts.items():
        tp, fp, fn = tally["tp"], tally["fp"], tally["fn"]
        pair_metrics[method] = dict(tally) | {"precision": tp / (tp + fp) if tp + fp else 0.0, "recall": tp / (tp + fn) if tp + fn else None, "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0}
    metrics = {
        "classification": freeze["classification"], "organizations": ORGANIZATIONS,
        "selected_pairs": sum(len(item["pairs"]) for item in predictions.values()),
        "selected_alerts": sum(row["selected_alerts"] for row in ranked),
        "full_unambiguous_alerts_in_selected_orgs": sum(row["alerts"] for row in ranked),
        "expert_top20_denominator": ORGANIZATIONS * 20,
        "top20_with_unambiguous_alerts": sum(row["top20_with_alerts"] for row in ranked),
        "pair_metrics_on_selected_exact_match_candidates": pair_metrics,
        "cpv": {"recovered_labels": sum(row["recovered"] for row in ranked), "end_to_end_recall_at_20_macro": bootstrap([row["recall20"] for row in ranked]), "precision_at_10_macro": bootstrap([row["p10"] for row in ranked]), "ndcg_at_20_rank1_high_macro": bootstrap([row["ndcg1"] for row in ranked]), "predicted_groups": sum(row["groups"] for row in ranked), "review_fraction_macro": sum(row["review_fraction"] for row in ranked) / ORGANIZATIONS},
        "call_summary": freeze["call_summary"], "prediction_freeze_sha256": sha256_file(freeze_path),
        "limits": ["20 previously exposed small holdout organizations; descriptive bootstrap only", "12 exact-match candidate pairs per organization, not full pair universe", "C and B2 share candidate/evidence budget; B2 has pair diagnostics only", "P/V applied to selected C groups with local evidence; no independent analyst review or revision loop", "Qwen calls are local, model-visible fields remain unapproved for external use", "unselected alerts retained in full-organization completeness counts and all 400 expert labels in ranking denominator", "not a full-dataset model or matched B0-B4 comparison"],
    }
    write_json(public / "metrics.json", metrics)
    write_json(public / "run_manifest.json", {"classification": metrics["classification"], "model": MODEL, "model_digest": freeze["model_digest"], "external_calls": 0, "command_predict": f"python -m src.submission_local_qwen_v2 predict --run-id {run_id}", "command_evaluate": f"python -m src.submission_local_qwen_v2 evaluate --run-id {run_id}", "sha256": {str(path.relative_to(ROOT)): sha256_file(path) for path in (Path(__file__), ROOT / "src/submission_local_qwen.py", POLICY, PREPARED, prediction_path, private / "calls.json", freeze_path, public / "metrics.json")}, "raw_sha256": INPUT_HASHES})
    print(json.dumps({"status": "evaluated", "run": run_id, "selected_positive_pairs": counts["C"]["positive_pairs"], "C": pair_metrics["C"], "B2": pair_metrics["B2"], "cpv_recovered": metrics["cpv"]["recovered_labels"]}, sort_keys=True))


def self_test() -> None:
    truth = {"a": "x", "b": "x", "c": "y"}
    ranks = {"x": 1, "y": 2}
    scores, recovered = rank_metrics([["a", "b"], ["c"]], [0.8, 0.2], truth, ranks, Counter({"x": 2, "y": 1}))
    assert recovered == 2 and scores["recall_at_20"] == 1.0
    scores, recovered = rank_metrics([["a"], ["b"], ["c"]], [0.8, 0.5, 0.2], truth, ranks, Counter({"x": 2, "y": 1}))
    assert recovered == 1 and scores["recall_at_20"] == 0.5
    print("Qwen v2 evaluator self-test: 2 assertions passed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test", "plan", "predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_qwen_v2_20261113_v1")
    args = parser.parse_args()
    if args.stage == "self-test":
        self_test()
    elif args.stage == "plan":
        with PREPARED.open("rb") as stream:
            data = pickle.load(stream)
        inputs = choose_inputs(data)
        print(json.dumps({"organizations": len(inputs), "selected_pairs": sum(len(item["pairs"]) for item in inputs.values()), "selected_alerts": sum(len(item["alerts"]) for item in inputs.values()), "min_available_exact_pairs": min(item["available_exact_pairs"] for item in inputs.values())}, sort_keys=True))
    elif args.stage == "predict":
        predict(args.run_id)
    else:
        evaluate(args.run_id)


if __name__ == "__main__":
    main()
