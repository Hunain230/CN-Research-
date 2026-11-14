"""Aggregate the frozen local-Qwen call audit without publishing prompts or rows.

These are batch inference diagnostics, not live alert-to-decision service levels.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from src.phase2 import sha256_file


ROOT = Path(__file__).resolve().parents[1]
RUN = "submission_qwen_v2_paper_20261113_v1"
PRIVATE_CALLS = ROOT / "data/derived" / RUN / "calls.json"
FREEZE = ROOT / "outputs" / RUN / "prediction_freeze.json"
METRICS = ROOT / "outputs" / RUN / "metrics.json"
OUT = ROOT / "outputs" / RUN / "operational_diagnostics.json"


def quantile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("No observations")
    position = (len(ordered) - 1) * p
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize(rows: list[dict]) -> dict:
    elapsed = [float(row["elapsed_seconds"]) for row in rows]
    return {
        "calls": len(rows),
        "failed_or_invalid_json_calls": sum(row["status"] != "ok" for row in rows),
        "call_latency_seconds_p50": round(quantile(elapsed, 0.5), 3),
        "call_latency_seconds_p95": round(quantile(elapsed, 0.95), 3),
        "call_latency_seconds_max": round(max(elapsed), 3),
        "sum_call_elapsed_seconds": round(sum(elapsed), 3),
        "prompt_tokens": sum(int(row["prompt_tokens"]) for row in rows),
        "output_tokens": sum(int(row["output_tokens"]) for row in rows),
    }


def main() -> None:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    if sha256_file(PRIVATE_CALLS) != freeze["calls_sha256"]:
        raise ValueError("Private call audit differs from frozen prediction")
    calls = json.loads(PRIVATE_CALLS.read_text(encoding="utf-8"))["calls"]
    all_calls = summarize(calls)
    for field in ("total", "failed", "prompt_tokens", "output_tokens"):
        target = {"total": "calls", "failed": "failed_or_invalid_json_calls"}.get(field, field)
        if all_calls[target] != freeze["call_summary"][field]:
            raise ValueError(f"Frozen call summary differs: {field}")
    if abs(all_calls["sum_call_elapsed_seconds"] - freeze["call_summary"]["elapsed_seconds"]) > 0.001:
        raise ValueError("Frozen elapsed time differs")
    roles: dict[str, list[dict]] = defaultdict(list)
    for row in calls:
        roles[row["role"]].append(row)
    if set(roles) != {"C", "P", "V", "B2"}:
        raise ValueError("Unexpected call roles")
    cpv = [row for row in calls if row["role"] != "B2"]
    cpv_seconds = sum(row["elapsed_seconds"] for row in cpv)
    pair_seconds = sum(row["elapsed_seconds"] for row in roles["C"])
    result = {
        "classification": "retrospective_local_batch_diagnostics_not_operational_soc_sla",
        "run": RUN,
        "provenance": {
            "private_call_audit_sha256": sha256_file(PRIVATE_CALLS),
            "prediction_freeze_sha256": sha256_file(FREEZE),
            "evaluation_metrics_sha256": sha256_file(METRICS),
            "model": freeze["model"],
            "model_digest": freeze["model_digest"],
            "localhost_only": freeze["localhost_only"],
        },
        "all_calls": all_calls,
        "by_role": {role: summarize(roles[role]) for role in ("C", "P", "V", "B2")},
        "observed_batch_work": {
            "selected_pairs": metrics["selected_pairs"],
            "selected_alerts": metrics["selected_alerts"],
            "predicted_groups": metrics["cpv"]["predicted_groups"],
            "organizations": metrics["organizations"],
            "cpv_sum_call_elapsed_seconds_excluding_paired_b2": round(cpv_seconds, 3),
            "cpv_selected_pairs_per_sum_call_hour": round(metrics["selected_pairs"] * 3600 / cpv_seconds, 3),
            "c_selected_pairs_per_sum_call_hour": round(metrics["selected_pairs"] * 3600 / pair_seconds, 3),
            "review_fraction_of_predicted_groups_macro": metrics["cpv"]["review_fraction_macro"],
            "c_abstention_fraction_of_selected_pairs": metrics["pair_metrics_on_selected_exact_match_candidates"]["C"]["abstentions"] / metrics["selected_pairs"],
        },
        "unmeasured": [
            "end-to-end alert-to-decision p50/p95 latency",
            "live arrival-rate and sustained throughput under concurrent load",
            "semantic invalid-output rate and independently adjudicated citation support",
            "analyst handling time, false-merge impact, and high-priority misses among auto-decided cases",
            "uptime, recovery from local-model failure, and production cost",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT.relative_to(ROOT)), "calls": all_calls["calls"], "cpv_sum_call_seconds": result["observed_batch_work"]["cpv_sum_call_elapsed_seconds_excluding_paired_b2"]}, sort_keys=True))


if __name__ == "__main__":
    main()
