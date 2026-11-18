"""One evidence-aware, ranking-only candidate on frozen Phase 32 groups."""
import importlib.util
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P34_PATH = ROOT / "experiments/PHASE34_FROZEN_RANK_GENERALIZATION/ranker.py"
spec = importlib.util.spec_from_file_location("phase34_visible_features", P34_PATH)
p34 = importlib.util.module_from_spec(spec); spec.loader.exec_module(p34)
p32 = p34.p32
FEATURE_ORDER = p34.FEATURE_ORDER + (
    "accepted_original_observations", "accepted_independent_roots", "accepted_family_coverage",
    "verified_coverage_fraction", "mean_claim_delay")


def features(group, lookup, claims, accepted):
    base = p34.features(group, lookup, accepted)
    members = set(group)
    accepted_inside = [x for x in accepted if x["left_alert_id"] in members and x["right_alert_id"] in members]
    tokens = {x["relationship_token"] for x in accepted_inside}
    originals = [c for c in claims if c["relationship_token"] in tokens and c["derived_from"] is None
                 and c["left_alert_id"] in members and c["right_alert_id"] in members]
    unique = {c["observation_id"]: c for c in originals}
    originals = list(unique.values())
    roots = {c["upstream_root_id"] for c in originals}
    families = {c["family"] for c in originals}
    covered = {a for x in accepted_inside for a in (x["left_alert_id"], x["right_alert_id"])}
    delay = sum(c["evidence_available_minute"] - c["observed_minute"] for c in originals) / len(originals) if originals else 0.0
    return base + [len(originals), len(roots), len(families), len(covered) / len(group), delay]


def linear_score(values, params):
    assert params["feature_order"] == list(FEATURE_ORDER)
    return params["intercept"] + sum(w * (x - mean) / scale for x, mean, scale, w in zip(
        values, params["mean"], params["scale"], params["coefficient"]))


def rerank(prediction, decisions, receiver_root, params):
    start = time.perf_counter()
    lookup, claims = p32.p31.visible_input(receiver_root, prediction["queue_id"], prediction["cutoff"])
    assert sorted(lookup) == prediction["eligible_alert_ids"]
    original = prediction["groups_ranked"]
    first_ten = original[:10]
    rest = sorted(original[10:], key=lambda g: (-linear_score(features(g, lookup, claims, decisions["accepted"]), params), g[0]))
    ranked = first_ten + rest
    assert ranked[:10] == first_ten
    assert sorted(map(tuple, ranked)) == sorted(map(tuple, original))
    return dict(prediction, method="phase36_evidence_aware_rank", ranker="top10_fixed_evidence_aware_logistic",
                groups_ranked=ranked, runtime_seconds=prediction["runtime_seconds"] + time.perf_counter() - start)
