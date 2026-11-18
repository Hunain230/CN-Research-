"""Frozen Phase 32 C/V under controlled receiver-visible telemetry conditions."""
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = HERE / "dataset"
ART = HERE / "artifacts"
SOURCE = DATA / "receiver_visible/development"
VARIANTS = DATA / "telemetry_conditions"
P32_PATH = ROOT / "experiments/PHASE32_SAFE_EVIDENCE_RECOVERY/model.py"
spec = importlib.util.spec_from_file_location("phase32_frozen_37", P32_PATH)
p32 = importlib.util.module_from_spec(spec); spec.loader.exec_module(p32)
CONDITIONS = ("original", "claim_delay20", "snapshot_minute80", "drop_process",
              "drop_authentication", "drop_network_flow", "derived_copies", "collapsed_roots",
              "contradictory_process")


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def lines(path): return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]
def write_lines(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in rows), encoding="utf-8")
def selected(token): return int(hashlib.sha256(token.encode()).hexdigest()[:8], 16) % 4 == 0


def transform(condition, alerts, claims, ledger):
    alerts = [dict(x) for x in alerts]; claims = [dict(x) for x in claims]; ledger = [dict(x) for x in ledger]
    if condition == "claim_delay20":
        for c in claims: c["evidence_available_minute"] += 20
    elif condition == "snapshot_minute80":
        for a in alerts: a["evidence_available_minute"] += 20
        for c in claims: c["evidence_available_minute"] += 20
        for l in ledger: l["evidence_available_minute"] += 20
    elif condition.startswith("drop_"):
        family = condition.removeprefix("drop_")
        claims = [c for c in claims if c["family"] != family]
    elif condition == "derived_copies":
        copies = []
        for c in claims:
            if c["derived_from"] is None:
                copy = dict(c)
                copy["observation_id"] = hashlib.sha256(("derived:" + c["observation_id"]).encode()).hexdigest()[:24]
                copy["derived_from"] = c["observation_id"]
                copy["evidence_available_minute"] += 1
                copies.append(copy)
        claims.extend(copies)
    elif condition == "collapsed_roots":
        by_token = defaultdict(list)
        for c in claims: by_token[c["relationship_token"]].append(c)
        for token, bundle in by_token.items():
            if selected(token):
                root = bundle[0]["upstream_root_id"]
                for c in bundle: c["upstream_root_id"] = root
    elif condition == "contradictory_process":
        for c in claims:
            if selected(c["relationship_token"]) and c["family"] == "process" and c["derived_from"] is None:
                c["right_parent_process_id"] = "contradiction_" + c["observation_id"]
    elif condition != "original": raise ValueError(condition)
    return alerts, claims, ledger


def main():
    manifest_path = DATA / "development_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["seed"] == 37102 and len(manifest["queues"]) == 15
    assert not VARIANTS.exists() and not (ART / "pre_evaluation_seal.json").exists()
    evaluator = ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py"
    outputs = {}
    for condition in CONDITIONS:
        root = VARIANTS / condition
        pred_path = ART / f"{condition}_predictions.jsonl"
        decision_path = ART / f"{condition}_decisions.jsonl"
        with pred_path.open("w", encoding="utf-8", newline="\n") as f, decision_path.open("w", encoding="utf-8", newline="\n") as a:
            for item in manifest["queues"]:
                q = item["queue_id"]
                transformed = transform(condition, *(lines(SOURCE / kind / f"{q}.jsonl")
                    for kind in ("alerts", "claims", "evidence_ledger")))
                for kind, rows in zip(("alerts", "claims", "evidence_ledger"), transformed):
                    write_lines(root / kind / f"{q}.jsonl", rows)
                pred, decision = p32.predict_queue(root, "development", q, 1)
                f.write(json.dumps(pred, sort_keys=True) + "\n")
                a.write(json.dumps(decision, sort_keys=True) + "\n")
        outputs[condition] = (pred_path, decision_path)
    seal = {"manifest_sha256": sha(manifest_path), "model_sha256": sha(P32_PATH),
            "evaluator_sha256": sha(evaluator), "runner_sha256": sha(HERE / "run_telemetry.py"),
            "predictions_sha256": {name: sha(p) for name, (p, _) in outputs.items()},
            "decisions_sha256": {name: sha(d) for name, (_, d) in outputs.items()},
            "visible_sha256": {p.relative_to(HERE).as_posix(): sha(p) for p in sorted(VARIANTS.rglob("*.jsonl"))}}
    (ART / "pre_evaluation_seal.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
    truth = DATA / "evaluator_only/development/ground_truth_private"
    evaluations = {}
    for name, (pred, _) in outputs.items():
        out = ART / f"{name}_evaluation.json"
        subprocess.run([sys.executable, str(evaluator), "--predictions", str(pred),
                        "--truth-root", str(truth), "--out", str(out)], check=True, capture_output=True, text=True)
        evaluations[name] = json.loads(out.read_text(encoding="utf-8"))
    relation_root = DATA / "evaluator_only/development/relationship_truth"
    rows = []
    queue_rows = []
    original = evaluations["original"]
    for name, (_, decisions_path) in outputs.items():
        result = evaluations[name]
        true_tokens = {}
        for item in manifest["queues"]:
            q = item["queue_id"]
            for x in lines(relation_root / f"{q}.jsonl"):
                if x.get("relationship_token") and x.get("observation_id"):
                    true_tokens[(q, x["relationship_token"])] = x["true_relation"]
        correct = incorrect = abstentions = 0
        for d in lines(decisions_path):
            q = d["queue_id"]
            for x in d["accepted"]:
                if true_tokens.get((q, x["relationship_token"])) is True: correct += 1
                else: incorrect += 1
            abstentions += len(d["rejected"])
        s = result["summary"]
        rows.append({"condition": name, "status": "evaluated", "recall20": s["recall20_count"],
                     "recoverable": s["recoverable"], "p10": s["p10_count"],
                     "pair_precision": s["grouped_pair_precision"], "false_pairs": s["false_grouped_pairs"],
                     "mixed_groups": s["mixed_predicted_groups"], "accepted_unions": s["accepted_merges"],
                     "correctly_accepted_unions": correct, "incorrectly_accepted_unions": incorrect,
                     "rejected_or_abstained_bundles": abstentions})
        for b, c in zip(original["queues"], result["queues"]):
            assert b["queue_id"] == c["queue_id"]
            queue_rows.append({"condition": name, "queue_id": b["queue_id"],
                               "baseline_recall": b["recall20_count"], "condition_recall": c["recall20_count"],
                               "baseline_recoverable": b["recoverable"], "condition_recoverable": c["recoverable"],
                               "baseline_p10": b["p10_count"], "condition_p10": c["p10_count"],
                               "condition_false_pairs": c["false_grouped_pairs"],
                               "condition_mixed_groups": c["mixed_predicted_groups"]})
    rows.append({"condition": "additional_independent_capture", "status": "unavailable_no_independent_source",
                 **{k: "" for k in rows[0] if k not in ("condition", "status")}})
    for path, data in ((HERE / "RECONSTRUCTION_EXPERIMENTS.csv", rows),
                       (HERE / "QUEUE_LEVEL_AUDIT.csv", queue_rows)):
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0])); w.writeheader(); w.writerows(data)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__": main()
