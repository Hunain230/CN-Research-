"""One hard-negative pairwise ranker; frozen Phase 32 groups and top ten."""
import importlib.util
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P36_PATH = ROOT / "experiments/PHASE36_EVIDENCE_AWARE_RECALL/ranker.py"
spec = importlib.util.spec_from_file_location("phase36_visible_features", P36_PATH)
p36 = importlib.util.module_from_spec(spec); spec.loader.exec_module(p36)
p32 = p36.p32
FEATURE_ORDER = p36.FEATURE_ORDER


def score(group, lookup, claims, accepted, params):
    values = p36.features(group, lookup, claims, accepted)
    assert params["feature_order"] == list(FEATURE_ORDER)
    return sum(w * (x - mean) / scale for x, mean, scale, w in zip(
        values, params["mean"], params["scale"], params["coefficient"]))


def rerank(prediction, decisions, receiver_root, params):
    start = time.perf_counter()
    lookup, claims = p32.p31.visible_input(receiver_root, prediction["queue_id"], prediction["cutoff"])
    assert sorted(lookup) == prediction["eligible_alert_ids"]
    groups = prediction["groups_ranked"]
    first_ten = groups[:10]
    rest = sorted(groups[10:], key=lambda g: (-score(g, lookup, claims, decisions["accepted"], params), g[0]))
    ranked = first_ten + rest
    assert ranked[:10] == first_ten
    assert sorted(map(tuple, ranked)) == sorted(map(tuple, groups))
    return dict(prediction, method="phase38_hard_negative_rank", ranker="top10_fixed_pairwise_evidence",
                groups_ranked=ranked, runtime_seconds=prediction["runtime_seconds"] + time.perf_counter() - start)
