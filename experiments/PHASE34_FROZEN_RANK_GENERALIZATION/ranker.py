"""Visible-feature prioritization below the frozen top ten; C and V are unchanged."""
import importlib.util
import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P32_PATH = ROOT / "experiments/PHASE32_SAFE_EVIDENCE_RECOVERY/model.py"
spec = importlib.util.spec_from_file_location("frozen_phase32_model", P32_PATH)
p32 = importlib.util.module_from_spec(spec); spec.loader.exec_module(p32)

FEATURE_ORDER = ("frozen_score", "unique_sources", "max_severity", "mean_severity",
                 "max_criticality", "mean_criticality", "event_diversity",
                 "group_size", "time_span", "verified_unions")


def features(group, lookup, accepted):
    items = list({lookup[aid]["source_id"]: lookup[aid] for aid in group}.values())
    members = set(group)
    verified = sum(item["left_alert_id"] in members for item in accepted)
    severities = [a["severity"] for a in items]
    criticalities = [a["asset_criticality"] for a in items]
    span = max(a["event_minute"] for a in items) - min(a["event_minute"] for a in items)
    return [p32.p31.source_depth(group, lookup) + verified, len(items),
        max(severities), sum(severities) / len(severities),
        max(criticalities), sum(criticalities) / len(criticalities),
        len({a["event_type"] for a in items}), len(group), min(span, 60), verified]


def linear_score(feature_vector, params):
    assert params["feature_order"] == list(FEATURE_ORDER)
    return params["intercept"] + sum(
        w * (x - mean) / scale for x, mean, scale, w in zip(
            feature_vector, params["mean"], params["scale"], params["coefficient"]))


def rerank(prediction, decisions, receiver_root, params, name):
    if name not in ("top20_logistic", "priority_ridge"): raise ValueError(name)
    start = time.perf_counter()
    lookup, _ = p32.p31.visible_input(receiver_root, prediction["queue_id"], prediction["cutoff"])
    assert sorted(lookup) == prediction["eligible_alert_ids"]
    original = prediction["groups_ranked"]
    accepted = decisions["accepted"]
    first_ten = original[:10]
    remainder = sorted(original[10:], key=lambda g: (-linear_score(features(g, lookup, accepted), params), g[0]))
    ranked = first_ten + remainder
    assert ranked[:10] == first_ten
    assert sorted(map(tuple, ranked)) == sorted(map(tuple, original))
    output = dict(prediction, method=f"phase34_{name}", ranker=f"top10_fixed_{name}",
                  groups_ranked=ranked, runtime_seconds=prediction["runtime_seconds"] + time.perf_counter() - start)
    return output
