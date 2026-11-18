"""One trained pairwise score for baseline positions 11–30 only."""
import importlib.util
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P34_RANKER = ROOT / "experiments/PHASE34_FROZEN_RANK_GENERALIZATION/ranker.py"
spec = importlib.util.spec_from_file_location("phase34_frozen_features", P34_RANKER)
p34 = importlib.util.module_from_spec(spec); spec.loader.exec_module(p34)
p32 = p34.p32
FEATURE_ORDER = p34.FEATURE_ORDER


def score(group, lookup, accepted, params):
    values = p34.features(group, lookup, accepted)
    assert params["feature_order"] == list(FEATURE_ORDER)
    return sum(w * (x - mean) / scale for x, mean, scale, w in zip(
        values, params["mean"], params["scale"], params["coefficient"]))


def rerank(prediction, decisions, receiver_root, params):
    start = time.perf_counter()
    lookup, _ = p32.p31.visible_input(receiver_root, prediction["queue_id"], 100)
    assert sorted(lookup) == prediction["eligible_alert_ids"]
    groups = prediction["groups_ranked"]
    first_ten = groups[:10]
    window = sorted(groups[10:30], key=lambda g: (-score(g, lookup, decisions["accepted"], params), g[0]))
    ranked = first_ten + window + groups[30:]
    assert ranked[:10] == first_ten and ranked[30:] == groups[30:]
    assert sorted(map(tuple, ranked)) == sorted(map(tuple, groups))
    return dict(prediction, method="phase35_pairwise_boundary", ranker="top10_fixed_window11_30_pairwise",
                groups_ranked=ranked, runtime_seconds=prediction["runtime_seconds"] + time.perf_counter() - start)
