"""Bounded, exploratory local Qwen C/P/V comparison on frozen GUIDE candidates.

Only five local-assumption descriptors enter localhost Ollama prompts. All model
responses and prediction rows stay under ignored data/derived. Evaluator truth
is opened only by the separate evaluate stage, after the prediction freeze.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pickle
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from .guide_rerun_v2 import FIELDS, INPUT_HASHES, key, labels
from .offline_joint_comparison import choose_cohort, read_truth, score_org
from .phase2 import sha256_file
from .empirical_priority_tie_eval import _expected_metrics


ROOT = Path(__file__).resolve().parents[1]
PREPARED = ROOT / "data/derived/guide_rerun_v2/prepared.pkl"
PRIOR_FREEZE = ROOT / "outputs/guide_rerun_v2/correlation_prediction_freeze.json"
PRIOR_CANDIDATES = ROOT / "data/derived/guide_rerun_v2/correlation_predictions"
POLICY = ROOT / "configs/empirical_field_policy.yaml"
MODEL = "qwen2.5:3b"
API = "http://127.0.0.1:11434/api"
RUN_PREFIX = "submission_qwen_"
PAIRS_PER_ORG = 15
BATCH = 5


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_json(path: str, payload: dict | None = None, timeout: int = 180) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(API + path, data=data, headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def model_digest() -> str:
    for model in fetch_json("/tags")["models"]:
        if model["name"] == MODEL:
            return model["digest"]
    raise ValueError("Required local model is not installed")


def call(prompt: str, role: str, seed: int, calls: list[dict]) -> dict:
    request = {
        "model": MODEL,
        "system": "You are a careful offline security research assistant. Use only supplied fictional aliases and local descriptors. Do not invent evidence or incident identities. Return one JSON object only.",
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "keep_alive": "30m",
        "options": {"temperature": 0 if role != "B3" else 0.2, "seed": seed, "num_predict": 700},
    }
    started = time.monotonic()
    try:
        response = fetch_json("/generate", request, timeout=240)
        parsed = json.loads(response["response"])
        if not isinstance(parsed, dict):
            raise ValueError("non-object JSON response")
        status = "ok"
        error = None
    except (ValueError, KeyError, OSError) as exc:
        response = {}
        parsed = {}
        status = "invalid_or_failed"
        error = type(exc).__name__
    calls.append({
        "role": role,
        "seed": seed,
        "request_sha256": hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest(),
        "status": status,
        "error_class": error,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "prompt_tokens": response.get("prompt_eval_count", 0),
        "output_tokens": response.get("eval_count", 0),
    })
    return parsed


def descriptor(fields: dict[str, list[str]]) -> str:
    return "; ".join(f"{field}: {', '.join(fields[field][:5]) or '(missing)'}" for field in FIELDS)


def pairs_prompt(pairs: list[dict], aliases: dict[str, str], docs: dict[str, dict], role: str) -> str:
    used = sorted({k for pair in pairs for k in (pair["left"], pair["right"])}, key=lambda k: aliases[k])
    evidence = "\n".join(f"{aliases[k]} / evidence E-{aliases[k]}: {descriptor(docs[k]['fields'])}" for k in used)
    pair_lines = "\n".join(f"{pair['id']}: {aliases[pair['left']]} vs {aliases[pair['right']]}" for pair in pairs)
    return (
        f"Role {role}. Decide whether each candidate pair is the same security incident based only on these descriptors. "
        "Shared generic fields alone may be weak. Choose LINK, NO_LINK, or UNSURE. "
        "If evidence is insufficient or conflicting, choose UNSURE. Return JSON: "
        '{"pairs":[{"id":"P01","decision":"LINK","reason":"short reason","refs":["E-A01","E-A02"]}]}. '
        "Use only listed pair IDs and evidence refs; include one result per pair.\n"
        f"Evidence:\n{evidence}\nCandidate pairs:\n{pair_lines}"
    )


def normalize_decisions(response: dict, pairs: list[dict], aliases: dict[str, str]) -> dict[str, dict]:
    rows = response.get("pairs", [])
    if not isinstance(rows, list):
        rows = []
    by_id = {row.get("id"): row for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str)}
    out = {}
    for pair in pairs:
        row = by_id.get(pair["id"], {})
        valid_refs = {f"E-{aliases[pair['left']]}", f"E-{aliases[pair['right']]}"}
        decision = row.get("decision") if row.get("decision") in {"LINK", "NO_LINK", "UNSURE"} else "UNSURE"
        refs = row.get("refs", [])
        if not isinstance(refs, list) or any(ref not in valid_refs for ref in refs):
            decision, refs = "UNSURE", []
        if decision == "LINK" and not refs:
            decision = "UNSURE"
        out[pair["id"]] = {"decision": decision, "refs": refs, "reason": str(row.get("reason", "unavailable"))[:240]}
    return out


def groups_from_links(alerts: list[str], pairs: list[dict], decisions: dict[str, dict]) -> list[list[str]]:
    parent = {a: a for a in alerts}

    def root(a: str) -> str:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for pair in pairs:
        if decisions[pair["id"]]["decision"] == "LINK":
            a, b = root(pair["left"]), root(pair["right"])
            if a != b:
                parent[b] = a
    grouped = defaultdict(list)
    for alert in alerts:
        grouped[root(alert)].append(alert)
    return sorted((sorted(group) for group in grouped.values()), key=lambda group: group[0])


def group_prompt(groups: list[list[str]], aliases: dict[str, str], docs: dict[str, dict], role: str, prior: dict | None = None) -> str:
    lines = []
    for i, group in enumerate(groups, 1):
        line = f"G{i:02d}: " + " | ".join(f"{aliases[a]} E-{aliases[a]} [{descriptor(docs[a]['fields'])}]" for a in group)
        if prior:
            line += f" | proposed score {prior.get(f'G{i:02d}', {}).get('score')}"
        lines.append(line)
    if role == "P":
        instruction = 'Score every group from 0 to 1 as a relative review priority, without using a gold rank. Return {"groups":[{"id":"G01","score":0.5,"refs":["E-A01"],"reason":"short"}]}. Include every group.'
    else:
        instruction = 'Check whether each proposed score has support in its listed evidence. Return {"groups":[{"id":"G01","decision":"PASS","refs":["E-A01"],"reason":"short"}]}. Use PASS, REVISE, or REVIEW. Unsupported, missing, or conflicting claims require REVIEW or REVISE. Include every group.'
    return f"Role {role}. {instruction}\nGroups:\n" + "\n".join(lines)


def normalize_priority(response: dict, groups: list[list[str]], aliases: dict[str, str]) -> dict[str, dict]:
    rows = response.get("groups", [])
    if not isinstance(rows, list):
        rows = []
    by_id = {row.get("id"): row for row in rows if isinstance(row, dict)}
    out = {}
    for i, group in enumerate(groups, 1):
        gid = f"G{i:02d}"
        row = by_id.get(gid, {})
        refs = row.get("refs", [])
        allowed = {f"E-{aliases[a]}" for a in group}
        score = row.get("score")
        if not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1:
            score = None
        if not isinstance(refs, list) or any(ref not in allowed for ref in refs):
            refs = []
            score = None
        out[gid] = {"score": score, "refs": refs, "reason": str(row.get("reason", "unavailable"))[:240]}
    return out


def normalize_verification(response: dict, groups: list[list[str]], aliases: dict[str, str]) -> dict[str, dict]:
    rows = response.get("groups", [])
    if not isinstance(rows, list):
        rows = []
    by_id = {row.get("id"): row for row in rows if isinstance(row, dict)}
    out = {}
    for i, group in enumerate(groups, 1):
        gid = f"G{i:02d}"
        row = by_id.get(gid, {})
        refs = row.get("refs", [])
        allowed = {f"E-{aliases[a]}" for a in group}
        decision = row.get("decision") if row.get("decision") in {"PASS", "REVISE", "REVIEW"} else "REVIEW"
        if not isinstance(refs, list) or any(ref not in allowed for ref in refs):
            refs, decision = [], "REVIEW"
        out[gid] = {"decision": decision, "refs": refs, "reason": str(row.get("reason", "unavailable"))[:240]}
    return out


def choose_inputs() -> tuple[dict, list[str], dict, dict]:
    with PREPARED.open("rb") as stream:
        data = pickle.load(stream)
    cohort = choose_cohort(data, 500)
    selected = sorted(cohort, key=lambda org: key("submission-qwen-v1", org))[:2]
    if len(selected) != 2:
        raise ValueError("Not enough bounded organizations")
    prior = json.loads(PRIOR_FREEZE.read_text(encoding="utf-8"))["hashes"]
    inputs = {}
    for org in selected:
        path = PRIOR_CANDIDATES / f"{key(org)}.npz"
        if sha256_file(path) != prior[key(org)]:
            raise ValueError("Upstream frozen candidate hash mismatch")
        with np.load(path) as array:
            keys = array["keys"].tolist()
            edge_codes = array["edges"].tolist()
            probabilities = array["probability"].tolist()
        n = len(keys)
        order = sorted(range(len(edge_codes)), key=lambda i: (-probabilities[i], edge_codes[i]))
        chosen = order[:10] + list(reversed(order[-5:]))
        if len(set(chosen)) != PAIRS_PER_ORG:
            raise ValueError("Insufficient distinct candidate pairs")
        pairs = []
        for i, index in enumerate(chosen, 1):
            code = int(edge_codes[index])
            pairs.append({"id": f"P{i:02d}", "left": keys[code // n], "right": keys[code % n]})
        alerts = sorted({a for pair in pairs for a in (pair["left"], pair["right"])})
        docs = {a: data["alerts"][a] for a in alerts}
        aliases = {a: f"A{i:02d}" for i, a in enumerate(alerts, 1)}
        inputs[org] = {"pairs": pairs, "alerts": alerts, "docs": docs, "aliases": aliases, "upstream_candidate_sha256": prior[key(org)]}
    return data, selected, inputs, prior


def predict(run_id: str) -> None:
    if not run_id.startswith(RUN_PREFIX):
        raise ValueError(f"Run ID must start with {RUN_PREFIX}")
    out = ROOT / "outputs" / run_id
    private = ROOT / "data/derived" / run_id
    if out.exists() or private.exists():
        raise FileExistsError("Run path exists; choose a new versioned ID")
    if "no_external_transmission: true" not in POLICY.read_text(encoding="utf-8"):
        raise ValueError("Local-only policy changed")
    digest = model_digest()
    data, selected, inputs, _ = choose_inputs()
    calls = []
    predictions = {}
    for position, org in enumerate(selected, 1):
        item = inputs[org]
        pairs, aliases, docs = item["pairs"], item["aliases"], item["docs"]
        c = {}
        b2 = {}
        votes = defaultdict(list)
        for offset in range(0, len(pairs), BATCH):
            batch = pairs[offset:offset + BATCH]
            c.update(normalize_decisions(call(pairs_prompt(batch, aliases, docs, "C"), "C", 0, calls), batch, aliases))
            b2.update(normalize_decisions(call(pairs_prompt(batch, aliases, docs, "B2 single model"), "B2", 0, calls), batch, aliases))
            for seed in (41, 42, 43):
                batch_votes = normalize_decisions(call(pairs_prompt(batch, aliases, docs, "B3 repeated single model"), "B3", seed, calls), batch, aliases)
                for pair_id, decision in batch_votes.items():
                    votes[pair_id].append(decision["decision"])
        b3 = {}
        for pair in pairs:
            tally = Counter(votes[pair["id"]])
            winning, count = tally.most_common(1)[0]
            b3[pair["id"]] = {"decision": winning if count >= 2 and winning != "UNSURE" else "UNSURE", "refs": [], "reason": "majority of three local calls"}
        groups = groups_from_links(item["alerts"], pairs, c)
        p = normalize_priority(call(group_prompt(groups, aliases, docs, "P"), "P", 0, calls), groups, aliases)
        v = normalize_verification(call(group_prompt(groups, aliases, docs, "V", p), "V", 0, calls), groups, aliases)
        scores = []
        review = []
        for i, group in enumerate(groups, 1):
            gid = f"G{i:02d}"
            score = p[gid]["score"]
            unsafe = score is None or not p[gid]["refs"] or v[gid]["decision"] != "PASS" or any(c[pair["id"]]["decision"] == "UNSURE" and (pair["left"] in group or pair["right"] in group) for pair in pairs)
            scores.append(float(score) if score is not None else 0.0)
            review.append(bool(unsafe))
        predictions[org] = {"alerts": item["alerts"], "pairs": pairs, "c": c, "b2": b2, "b3": b3, "groups": groups, "p": p, "v": v, "scores": scores, "review": review, "upstream_candidate_sha256": item["upstream_candidate_sha256"]}
        print(f"Local Qwen predicted organization {position}/2: {len(pairs)} pairs, {len(groups)} groups", flush=True)
    private.mkdir(parents=True)
    prediction_path = private / "predictions.pkl"
    with prediction_path.open("wb") as stream:
        pickle.dump(predictions, stream, protocol=pickle.HIGHEST_PROTOCOL)
    write_json(private / "calls.json", {"calls": calls, "model": MODEL, "model_digest": digest})
    out.mkdir(parents=True)
    freeze = {
        "classification": "exploratory_bounded_local_qwen_hybrid_not_full_llm_study",
        "model": MODEL,
        "model_digest": digest,
        "organizations": 2,
        "pairs_per_organization": PAIRS_PER_ORG,
        "selection": "first two complete <=500-alert holdout organizations by SHA-256(submission-qwen-v1, OrgId); each takes 10 highest and 5 lowest frozen correlation scores, label-blind",
        "source_sha256": {str(path.relative_to(ROOT)): sha256_file(path) for path in (Path(__file__), POLICY, PREPARED, PRIOR_FREEZE)},
        "upstream_candidate_sha256": sorted(item["upstream_candidate_sha256"] for item in inputs.values()),
        "prediction_sha256": sha256_file(prediction_path),
        "calls_sha256": sha256_file(private / "calls.json"),
        "labels_read_in_prediction_stage": False,
        "localhost_only": True,
        "seeds": {"C": 0, "B2": 0, "B3": [41, 42, 43], "P": 0, "V": 0},
        "call_summary": {"total": len(calls), "failed": sum(call["status"] != "ok" for call in calls), "prompt_tokens": sum(call["prompt_tokens"] for call in calls), "output_tokens": sum(call["output_tokens"] for call in calls)},
    }
    write_json(out / "prediction_freeze.json", freeze)
    print(json.dumps({"status": "local_qwen_predictions_frozen", "run": run_id, "calls": len(calls), "failed": freeze["call_summary"]["failed"]}, sort_keys=True))


def tie_aware(groups: list[list[str]], scores: list[float], truth: dict[str, str], ranks: dict[str, int]) -> dict:
    counts = Counter(truth[a] for group in groups for a in group)
    recovered = {}
    for group in groups:
        members = Counter(truth[a] for a in group)
        gold, overlap = max(members.items(), key=lambda row: (row[1], row[0]))
        if gold in ranks and overlap / counts[gold] >= 0.8 and overlap / len(group) >= 0.8:
            recovered[group[0]] = ranks[gold]
    ordered = sorted(zip(groups, scores), key=lambda row: (-row[1], row[0][0]))
    blocks = []
    for group, score in ordered:
        if not blocks or blocks[-1][0][1] != score:
            blocks.append([])
        blocks[-1].append((group[0], score))
    labels_map = recovered | {f"unrecovered-{gold}": rank for gold, rank in ranks.items() if rank not in recovered.values()}
    return _expected_metrics(blocks, labels_map)


def evaluate(run_id: str) -> None:
    out = ROOT / "outputs" / run_id
    private = ROOT / "data/derived" / run_id
    if (out / "metrics.json").exists():
        raise FileExistsError("Evaluation already exists")
    freeze = json.loads((out / "prediction_freeze.json").read_text(encoding="utf-8"))
    path = private / "predictions.pkl"
    if sha256_file(path) != freeze["prediction_sha256"]:
        raise ValueError("Prediction freeze mismatch")
    with path.open("rb") as stream:
        predictions = pickle.load(stream)
    orgs = set(predictions)
    all_alerts = {a for item in predictions.values() for a in item["alerts"]}
    truth = read_truth(orgs, all_alerts)
    ranks = labels(orgs)
    methods = {name: Counter() for name in ("C_local_qwen", "B2_pair_only", "B3_pair_only")}
    per_org = []
    for org, item in predictions.items():
        for method, field in (("C_local_qwen", "c"), ("B2_pair_only", "b2"), ("B3_pair_only", "b3")):
            counts = methods[method]
            for pair in item["pairs"]:
                positive = truth[pair["left"]] == truth[pair["right"]]
                decision = item[field][pair["id"]]["decision"]
                counts["positive_pairs"] += positive
                counts["candidate_pairs"] += 1
                counts["abstentions"] += decision == "UNSURE"
                counts["tp"] += positive and decision == "LINK"
                counts["fp"] += not positive and decision == "LINK"
                counts["fn"] += positive and decision != "LINK"
        groups = item["groups"]
        scored = score_org(groups, item["scores"], truth, ranks[org], item["alerts"], {"top20_recovery_min_completeness": 0.8, "top20_recovery_min_purity": 0.8})
        ranking = tie_aware(groups, item["scores"], truth, ranks[org])
        per_org.append({"pair_f1": scored["pair_f1"], "recall20": ranking["recall_at_20"], "p10": ranking["precision_at_10"], "ndcg1": ranking["ndcg_at_20_rank1_highest"], "ndcg20": ranking["ndcg_at_20_rank20_highest_sensitivity"], "review_fraction": sum(item["review"]) / len(groups), "groups": len(groups), "alerts": len(item["alerts"]), "candidate_positive": sum(truth[p["left"]] == truth[p["right"]] for p in item["pairs"])})
    pair_metrics = {}
    for method, counts in methods.items():
        tp, fp, fn = (counts[key] for key in ("tp", "fp", "fn"))
        pair_metrics[method] = dict(counts) | {"precision": tp / (tp + fp) if tp + fp else 0.0, "recall_on_selected_candidates": tp / (tp + fn) if tp + fn else None, "f1_on_selected_candidates": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0}
    metrics = {
        "classification": freeze["classification"],
        "organizations": 2,
        "selected_pairs": 2 * PAIRS_PER_ORG,
        "alerts": len(all_alerts),
        "expert_top20_denominator": 40,
        "candidate_pair_metrics": pair_metrics,
        "cpv_batched_local_qwen": {"end_to_end_recall_at_20_macro": sum(row["recall20"] for row in per_org) / 2, "precision_at_10_macro": sum(row["p10"] for row in per_org) / 2, "ndcg_at_20_rank1_high_macro": sum(row["ndcg1"] for row in per_org) / 2, "ndcg_at_20_rank20_high_macro": sum(row["ndcg20"] for row in per_org) / 2, "pair_f1_full_subset_macro": sum(row["pair_f1"] for row in per_org) / 2, "review_fraction_macro": sum(row["review_fraction"] for row in per_org) / 2, "predicted_groups": sum(row["groups"] for row in per_org)},
        "selected_candidate_positive_pairs": sum(row["candidate_positive"] for row in per_org),
        "call_summary": freeze["call_summary"],
        "prediction_freeze_sha256": sha256_file(out / "prediction_freeze.json"),
        "limits": ["two previously accessed organizations; no confidence interval", "15 deliberately score-stratified frozen candidate pairs per organization, not full pair universe", "C/B2/B3 pair scores only; B2/B3 do not rank components", "C/P/V roles are batched by organization, rather than one call per pair/component", "V checks model-provided citations over local descriptors; no independent analyst review or revision loop", "priority scores are uncalibrated", "all 20 expert labels per organization stay in end-to-end denominator", "local-only assumed fields; no hosted transmission", "model outputs are exploratory and not a full-scale C/P/V result"],
    }
    write_json(out / "metrics.json", metrics)
    write_json(out / "run_manifest.json", {"classification": metrics["classification"], "command_predict": f"python -m src.submission_local_qwen predict --run-id {run_id}", "command_evaluate": f"python -m src.submission_local_qwen evaluate --run-id {run_id}", "model": MODEL, "model_digest": freeze["model_digest"], "sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in (Path(__file__), POLICY, path, private / "calls.json", out / "prediction_freeze.json", out / "metrics.json")}, "raw_sha256": INPUT_HASHES, "external_calls": 0})
    print(json.dumps({"status": "exploratory_qwen_evaluation_complete", "run": run_id, "pair_metrics": pair_metrics, "cpv": metrics["cpv_batched_local_qwen"]}, sort_keys=True))


def self_test() -> None:
    aliases = {"x": "A01", "y": "A02"}
    pair = [{"id": "P01", "left": "x", "right": "y"}]
    assert normalize_decisions({"pairs": [{"id": "P01", "decision": "LINK", "refs": ["E-A01"]}]}, pair, aliases)["P01"]["decision"] == "LINK"
    assert normalize_decisions({"pairs": [{"id": "P01", "decision": "LINK", "refs": ["fabricated"]}]}, pair, aliases)["P01"]["decision"] == "UNSURE"
    assert groups_from_links(["x", "y"], pair, {"P01": {"decision": "LINK"}}) == [["x", "y"]]
    assert normalize_priority({"groups": [{"id": "G01", "score": 0.7, "refs": ["E-A01"]}]}, [["x", "y"]], aliases)["G01"]["score"] == 0.7
    assert normalize_verification({"groups": [{"id": "G01", "decision": "PASS", "refs": ["fake"]}]}, [["x", "y"]], aliases)["G01"]["decision"] == "REVIEW"
    print("local Qwen adapter self-test: 5 assertions passed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test", "predict", "evaluate"))
    parser.add_argument("--run-id", default="submission_qwen_20261112_v1")
    args = parser.parse_args()
    {"self-test": self_test, "predict": predict, "evaluate": evaluate}[args.stage](**({} if args.stage == "self-test" else {"run_id": args.run_id}))


if __name__ == "__main__":
    main()
