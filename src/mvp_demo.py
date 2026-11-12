"""End-to-end fictional MVP: offline C/P/V -> frozen predictions -> evaluator metrics.

This module is a software integration demo only. It never reads GUIDE data or makes
network/model calls. The evaluator truth file is opened only after predictions freeze.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from .agents.common import validate_request
from .agents.orchestrator import _run
from .evaluation.metrics import correlation, end_to_end_recall20, false_merge_split_components
from .evaluation.prediction_validation import strict_load_json, validate_predictions


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "mvp"
OUTPUT_ROOT = ROOT / "outputs" / "mvp"
CLASSIFICATION = "synthetic_end_to_end_demo_not_empirical"
PREDICTION_CLASSIFICATION = "synthetic_predictions_only_not_empirical"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _write_json(path: Path, value: object) -> None:
    path.write_bytes(_json_bytes(value))


def _load_scenario(fixture_dir: Path) -> dict:
    scenario = strict_load_json(fixture_dir / "scenario.json")
    expected = {"schema_version", "classification", "seed", "organizations", "requests", "truth_file"}
    if set(scenario) != expected or scenario["schema_version"] != "mvp-synthetic-scenario-v1":
        raise ValueError("MVP scenario schema mismatch")
    if scenario["classification"] != "fictional_software_demo_only":
        raise ValueError("MVP scenario must be explicitly fictional")
    if set(scenario["organizations"]) != set(scenario["requests"]):
        raise ValueError("every synthetic organization must have exactly one request")
    return scenario


def _safe_fixture_path(fixture_dir: Path, relative: str) -> Path:
    path = (fixture_dir / relative).resolve()
    if not path.is_relative_to(fixture_dir.resolve()) or not path.is_file():
        raise ValueError("MVP fixture path escaped its directory or is missing")
    return path


def build_predictions(fixture_dir: Path = FIXTURE_DIR) -> tuple[dict, list[dict], dict]:
    """Build model-facing output and a fictional UI event trace without reading truth."""
    fixture_dir = fixture_dir.resolve()
    scenario = _load_scenario(fixture_dir)
    cfg = strict_load_json(ROOT / "configs" / "agents.yaml")
    allowed = set(cfg["allowed_fields"])
    org_runs = []
    event_trace = []
    all_alerts: dict[str, dict] = {}
    pair_predictions = []
    prediction_rows = []
    components = []
    ranked_candidates = []
    top20_components = []
    step = 0

    for org_key in sorted(scenario["organizations"]):
        request_path = _safe_fixture_path(fixture_dir, scenario["requests"][org_key])
        request = strict_load_json(request_path)
        if request.get("org_key") != org_key:
            raise ValueError("request organization does not match scenario index")
        # Validate the exact model-facing object before invoking the same offline C/P/V path as Phase 4.
        validate_request(request, allowed)
        run_result = _run(ROOT, request_path, cfg)
        if run_result.get("live_model_calls") is not None:
            raise ValueError("unexpected provider-call field in C/P/V result")
        if run_result["summary"]["live_model_calls"] != 0:
            raise ValueError("synthetic MVP must not make live model calls")

        alert_org = {a["alert_key"]: a["org_key"] for a in request["alerts"]}
        all_alerts.update({a["alert_key"]: a for a in request["alerts"]})
        for alert in sorted(request["alerts"], key=lambda a: a["alert_key"]):
            step += 1
            event_trace.append({"step": step, "kind": "alert_received", "org_key": org_key,
                                "alert_key": alert["alert_key"], "evidence_count": len(alert["evidence"])})

        edges = run_result["correlation_edges"]
        for edge in edges:
            pair = edge["pair"]
            if alert_org[pair["left"]] != org_key or alert_org[pair["right"]] != org_key:
                raise ValueError("cross-organization pair escaped request validation")
            decision = edge["decision"]
            pair_predictions.append({
                "left": pair["left"], "right": pair["right"], "org_key": org_key,
                "left_org": org_key, "right_org": org_key, "decision": decision,
                "abstention": decision == "UNSURE", "failure": edge["status"] == "provider_failure",
            })
            step += 1
            event_trace.append({"step": step, "kind": "correlation_decision", "org_key": org_key,
                                "left": pair["left"], "right": pair["right"], "decision": decision,
                                "reason": edge["reason_code"],
                                "evidence_refs": sorted(set(edge["supporting_evidence_ids"] + edge["contradicting_evidence_ids"]))})

        # The C/P/V contract outputs one result per component. Any component touching an
        # UNSURE/failed edge is conservatively sent to review in this integration demo.
        review_alerts = set()
        for edge in edges:
            if edge["decision"] == "UNSURE" or edge["status"] == "provider_failure":
                review_alerts.update((edge["pair"]["left"], edge["pair"]["right"]))
        result_by_component = {r["component"]["component_key"]: r for r in run_result["component_results"]}
        priority_rows = []
        for component in run_result["components"]:
            result = result_by_component[component["component_key"]]
            priority = result["prioritization"]
            evidence_refs = sorted(set(priority["supporting_evidence_ids"] + priority["contradicting_evidence_ids"]))
            review = (result["final_status"] == "REVIEW" or
                      any(a in review_alerts for a in component["alert_keys"]))
            review_reason = result["verification"].get("review_reason")
            if review and not review_reason:
                review_reason = ("touches_unsure_or_failed_pair" if any(a in review_alerts for a in component["alert_keys"])
                                 else "prioritization_or_verification_requires_review")
            priority_rows.append({"component_key": component["component_key"], "org_key": org_key,
                                  "alert_keys": component["alert_keys"], "score": priority["score"],
                                  "verification": result["verification"]["decision"],
                                  "status": "REVIEW" if review else "PASS",
                                  "evidence_refs": evidence_refs,
                                  "review_reason": review_reason})
        priority_rows.sort(key=lambda row: (row["score"] is None, -(row["score"] or 0.0), row["component_key"]))

        for rank, row in enumerate(priority_rows, 1):
            components.append(row["alert_keys"])
            ranked_candidates.append(row["component_key"])
            top20_components.append(row["alert_keys"])
            prediction_rows.append({
                "method": "offline_cpv_synthetic_stub", "query_key": org_key, "org_key": org_key,
                "candidate_key": row["component_key"], "decision": "REVIEW" if row["status"] == "REVIEW" else "SCORE",
                "score": row["score"], "rank": rank, "abstention": row["status"] == "REVIEW",
                "failure": False, "evidence_refs": row["evidence_refs"], "latency_ms": None,
                "input_tokens": 0, "output_tokens": 0, "run_hash": "deterministic-offline-stub-no-tokenizer",
            })
            step += 1
            event_trace.append({"step": step, "kind": "component_ranked", "org_key": org_key,
                                "component_key": row["component_key"], "alert_keys": row["alert_keys"],
                                "score": row["score"], "rank": rank, "verification": row["verification"],
                                "status": row["status"], "evidence_refs": row["evidence_refs"],
                                "review_reason": row["review_reason"]})
        org_runs.append({"org_key": org_key, "agent_summary": run_result["summary"], "queue": priority_rows})

    prediction_document = {
        "schema_version": "evaluation-predictions-v1",
        "classification": PREDICTION_CLASSIFICATION,
        "run_id": "mvp-synthetic-fixture-v1",
        "predictions": prediction_rows,
        "pair_predictions": pair_predictions,
        "components": components,
        "ranked_candidates": ranked_candidates,
        "top20_components": top20_components,
    }
    validate_predictions(prediction_document)
    summary = {
        "classification": CLASSIFICATION,
        "organizations": org_runs,
        "alert_count": len(all_alerts),
        "candidate_pair_count": len(pair_predictions),
        "predicted_component_count": len(components),
        "review_component_count": sum(p["abstention"] for p in prediction_rows),
        "live_model_calls": 0,
        "resource_note": "No model tokens or provider latency were measured; token fields are zero and latency is null.",
    }
    return prediction_document, event_trace, summary


def _load_truth(path: Path, fixture_dir: Path) -> dict:
    path = path.resolve()
    if not path.is_relative_to(fixture_dir.resolve()):
        raise ValueError("evaluator truth must remain inside fixtures/mvp")
    truth = strict_load_json(path)
    if set(truth) != {"schema_version", "classification", "organizations"}:
        raise ValueError("MVP evaluator truth schema mismatch")
    if truth["schema_version"] != "mvp-evaluator-truth-v1" or truth["classification"] != "evaluator_only_fictional_labels":
        raise ValueError("MVP truth classification mismatch")
    return truth


def evaluate_frozen(prediction_document: dict, truth_path: Path, fixture_dir: Path = FIXTURE_DIR) -> dict:
    """Evaluator-only stage; called only after prediction JSON and freeze are written."""
    predictions = validate_predictions(prediction_document)
    truth = _load_truth(truth_path, fixture_dir)
    if set(truth["organizations"]) != {p["org_key"] for p in predictions["predictions"]}:
        raise ValueError("truth/prediction organization sets differ")

    pair_truth = []
    alert_truth = {}
    gold_groups = {}
    full_pair_universe = []
    for org_key, org_truth in truth["organizations"].items():
        labels = org_truth["alerts"]
        alert_truth.update(labels)
        groups: dict[str, list[str]] = {}
        for alert_key, group_key in labels.items():
            groups.setdefault(group_key, []).append(alert_key)
        for group_key, alerts in groups.items():
            if group_key in org_truth["expert_top20_groups"]:
                gold_groups[group_key] = sorted(alerts)
            for i, left in enumerate(sorted(alerts)):
                for right in sorted(alerts)[i + 1:]:
                    pair_truth.append([left, right])
        org_alerts = sorted(labels)
        full_pair_universe.extend([[left, right] for i, left in enumerate(org_alerts) for right in org_alerts[i + 1:]])

    candidate_universe = [[p["left"], p["right"]] for p in predictions["pair_predictions"]]
    correlation_metrics = correlation(pair_truth, predictions["pair_predictions"], candidate_universe, full_pair_universe)
    grouping_metrics = false_merge_split_components(alert_truth, predictions["components"])
    e2e = end_to_end_recall20(gold_groups, predictions["top20_components"], alert_truth)
    review_count = sum(bool(p["abstention"]) for p in predictions["predictions"])
    return {
        "classification": CLASSIFICATION,
        "interpretation": "Tiny hand-authored fixture metrics verify software wiring only; they do not estimate real-world performance.",
        "correlation": correlation_metrics,
        "grouping": grouping_metrics,
        "end_to_end_recall20": e2e,
        "priority_queue": {
            org_key: [{"rank": row["rank"], "candidate_key": row["candidate_key"],
                       "score": row["score"], "status": row["decision"]}
                      for row in sorted((p for p in predictions["predictions"] if p["org_key"] == org_key),
                                        key=lambda p: p["rank"])]
            for org_key in sorted({p["org_key"] for p in predictions["predictions"]})
        },
        "review": {"reviewed_components": review_count, "predicted_component_count": len(predictions["predictions"]),
                   "review_fraction": review_count / len(predictions["predictions"]) if predictions["predictions"] else 0.0,
                   "policy": "route components touching an UNSURE or failed pair to REVIEW"},
        "scope": {"organizations": len(truth["organizations"]), "alerts": len(alert_truth),
                  "candidate_pairs": len(candidate_universe), "full_pair_universe": len(full_pair_universe),
                  "expert_top20_groups": len(gold_groups), "live_model_calls": 0},
    }


def run(run_id: str, fixture_dir: Path = FIXTURE_DIR, output_root: Path = OUTPUT_ROOT) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", run_id):
        raise ValueError("run ID must use 1-80 letters, digits, dot, underscore, or dash")
    out = (output_root / run_id).resolve()
    if not out.is_relative_to(output_root.resolve()):
        raise ValueError("output path escaped MVP output root")
    if out.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {out}")
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    start_time = time.perf_counter()
    out.mkdir(parents=True)
    try:
        prediction_document, events, prediction_summary = build_predictions(fixture_dir)
        pred_path = out / "predictions.json"
        _write_json(pred_path, prediction_document)
        freeze = {"classification": CLASSIFICATION, "prediction_sha256": _sha(pred_path),
                  "prediction_frozen_before_truth_read": True,
                  "method": "Phase 4 deterministic offline provider plus conservative unsure-edge review routing"}
        _write_json(out / "prediction_freeze.json", freeze)
        _write_json(out / "dashboard_events.json", {"classification": CLASSIFICATION, "events": events})

        # The truth file is deliberately opened only after the prediction artifact and freeze exist.
        scenario = _load_scenario(fixture_dir)
        truth_path = _safe_fixture_path(fixture_dir, scenario["truth_file"])
        metrics_result = evaluate_frozen(prediction_document, truth_path, fixture_dir)
        _write_json(out / "metrics.json", metrics_result)
        (out / "report.md").write_text(render_report(prediction_summary, metrics_result), encoding="utf-8")

        inputs = [fixture_dir / "scenario.json", ROOT / "configs" / "agents.yaml"]
        inputs += [_safe_fixture_path(fixture_dir, name) for name in scenario["requests"].values()]
        inputs.append(truth_path)
        code_paths = [ROOT / "src" / "mvp_demo.py", ROOT / "src" / "agents" / "orchestrator.py",
                      ROOT / "src" / "agents" / "common.py", ROOT / "src" / "agents" / "correlation.py",
                      ROOT / "src" / "agents" / "prioritization.py", ROOT / "src" / "agents" / "verification.py",
                      ROOT / "src" / "agents" / "providers" / "offline_stub.py",
                      ROOT / "src" / "evaluation" / "metrics.py", ROOT / "src" / "evaluation" / "prediction_validation.py"]
        manifest = {
            "classification": CLASSIFICATION, "run_id": run_id, "mode": "synthetic", "seed": scenario["seed"],
            "command": f"python -m src.mvp_demo run --run-id {run_id}",
            "started_utc": started, "ended_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "runtime_ms": round((time.perf_counter() - start_time) * 1000, 3),
            "python": sys.version.split()[0], "provider": "deterministic-synthetic-agent-stub",
            "live_model_calls": 0, "external_network_calls": 0,
            "fixture_sha256": {str(p.relative_to(ROOT)): _sha(p) for p in sorted(inputs)},
            "evaluator_truth_sha256": _sha(truth_path),
            "code_sha256": {str(p.relative_to(ROOT)): _sha(p) for p in code_paths},
            "outputs_sha256": {name: _sha(out / name) for name in
                               ("predictions.json", "prediction_freeze.json", "dashboard_events.json", "metrics.json", "report.md")},
            "prediction_frozen_before_truth_read": True,
            "summary": prediction_summary,
        }
        _write_json(out / "run_manifest.json", manifest)
        return {"status": "synthetic_mvp_complete_not_empirical", "output": str(out),
                "metrics": metrics_result, "manifest": manifest}
    except Exception:
        # Keep failed run directories as a visible audit trace; never silently overwrite them.
        raise


def render_report(summary: dict, metrics_result: dict) -> str:
    c = metrics_result["correlation"]
    e = metrics_result["end_to_end_recall20"]
    g = metrics_result["grouping"]
    r = metrics_result["review"]
    lines = [
        "# Synthetic end-to-end MVP run", "",
        "> **Fictional software demonstration only. These metrics are not GUIDE results or empirical model performance.**", "",
        "## What ran", "",
        f"The deterministic offline C/P/V stub processed {summary['alert_count']} fictional alerts across {len(summary['organizations'])} organizations, compared {summary['candidate_pair_count']} supplied candidate pairs, formed {summary['predicted_component_count']} components, and made zero live model calls.", "",
        "Components touching an UNSURE or failed candidate pair were conservatively marked REVIEW. The synthetic prioritization scores are simple stub scores, not learned, calibrated, or operational risk estimates.", "",
        "Each fictional organization yields only four predicted components, so the top-20 recovery cutoff includes every available component. This fixture does not test competition among 20 or more incidents.", "",
        "## Fixture metrics", "",
        f"- Candidate-pair precision: {c['candidate_set']['precision']:.3f} ({c['candidate_set']['tp']} TP, {c['candidate_set']['fp']} FP).",
        f"- Candidate-pair recall: {c['candidate_set']['recall']:.3f} ({c['candidate_set']['tp']} TP, {c['candidate_set']['fn']} FN).",
        f"- Pair F1: {c['candidate_set']['f1']:.3f}.",
        f"- Candidate decision coverage: {c['decision_coverage']:.3f}; abstentions: {c['abstentions']}; failures: {c['failures']}.",
        f"- Full pair universe: {metrics_result['scope']['full_pair_universe']} pairs; candidate-generation coverage: {c['candidate_generation_coverage']['value']:.3f}.",
        f"- False merges: {g['false_merges']}; false splits: {g['false_splits']}.",
        f"- End-to-end fixture top-20 recovery: {e['recovered']}/{e['eligible_gold_top20']} = {e['recall_at_20']:.3f}.",
        f"- Components sent to review: {r['reviewed_components']}/{r['predicted_component_count']} = {r['review_fraction']:.3f}.", "",
        "These values are expected to reflect the hand-authored edge cases, including deliberate false links and uncertainty. The tiny fixture is designed to validate integration and evaluator wiring, not to estimate system effectiveness.", "",
        "## Reproduce", "",
        "```powershell", ".\\.venv\\Scripts\\python.exe -m src.mvp_demo self-test",
        ".\\.venv\\Scripts\\python.exe -m src.mvp_demo run --run-id <new-unique-id>", "```", "",
    ]
    return "\n".join(lines)


def self_test() -> dict:
    prediction_a, events_a, summary_a = build_predictions()
    prediction_b, events_b, summary_b = build_predictions()
    assert prediction_a == prediction_b
    assert events_a == events_b
    assert summary_a == summary_b
    decisions = {(p["left"], p["right"]): p["decision"] for p in prediction_a["pair_predictions"]}
    assert decisions[("org-mvp-01-a1", "org-mvp-01-a2")] == "LINK"
    assert decisions[("org-mvp-01-a1", "org-mvp-01-a3")] == "NO_LINK"
    assert decisions[("org-mvp-01-a1", "org-mvp-01-a4")] == "UNSURE"
    assert decisions[("org-mvp-01-a1", "org-mvp-01-a5")] == "UNSURE"
    assert decisions[("org-mvp-01-a1", "org-mvp-01-a6")] == "LINK"
    assert len({(p["org_key"], p["query_key"]) for p in prediction_a["predictions"]}) == 2
    assert all(p["org_key"] == p["left_org"] == p["right_org"] for p in prediction_a["pair_predictions"])
    truth_path = _safe_fixture_path(FIXTURE_DIR, _load_scenario(FIXTURE_DIR)["truth_file"])
    metrics_result = evaluate_frozen(prediction_a, truth_path)
    assert metrics_result["correlation"]["candidate_set"]["tp"] == 2
    assert metrics_result["correlation"]["candidate_set"]["fp"] == 2
    assert metrics_result["grouping"]["false_merges"] == 2
    assert metrics_result["grouping"]["false_splits"] == 0
    assert metrics_result["end_to_end_recall20"]["recovered"] == 6
    assert metrics_result["end_to_end_recall20"]["eligible_gold_top20"] == 10
    assert metrics_result["review"]["reviewed_components"] == 6
    return {"status": "pass", "assertions": 17, "classification": CLASSIFICATION,
            "pairwise_replay_deterministic": True, "live_model_calls": 0,
            "expected_fixture_metrics": {"pair_tp": 2, "pair_fp": 2, "false_merges": 2,
                                          "e2e_recovered": "6/10", "review_components": 6}}


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline fictional end-to-end C/P/V MVP demonstration")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test", help="check deterministic integration on fictional fixtures")
    run_parser = sub.add_parser("run", help="write a new synthetic MVP run")
    run_parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if args.command == "self-test":
        print(json.dumps(self_test(), indent=2))
    else:
        result = run(args.run_id)
        print(json.dumps({"status": result["status"], "output": result["output"],
                          "live_model_calls": result["manifest"]["live_model_calls"],
                          "metrics": result["metrics"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
