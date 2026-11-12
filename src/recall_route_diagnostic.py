"""Post-hoc descriptor-overlap diagnostic on the prior small-queue cohort.

This reads evaluator truth and is not a frozen candidate-generation experiment.
It can guide a future protocol, but its routes must not be reported as a new
held-out candidate benchmark or a model result.
"""

from __future__ import annotations

import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

from .offline_joint_comparison import choose_cohort, read_truth
from .phase2 import sha256_file


ROOT = Path(__file__).resolve().parents[1]
PREPARED = ROOT / "data/derived/guide_rerun_v2/prepared.pkl"
OUT = ROOT / "outputs/recall_route_diagnostic_20261113_v1"
FIELDS = ("Category", "MitreTechniques", "DetectorId")
ROUTES = ("category_and_technique", "category", "technique", "detector", "any_three")


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Diagnostic output exists")
    with PREPARED.open("rb") as stream:
        data = pickle.load(stream)
    cohort = choose_cohort(data, 500)
    if len(cohort) != 57:
        raise ValueError("Unexpected small-queue cohort")
    by_org = defaultdict(list)
    for alert, doc in data["alerts"].items():
        if doc["org"] in cohort:
            by_org[doc["org"]].append(alert)
    all_alerts = {alert for alerts in by_org.values() for alert in alerts}
    truth = read_truth(set(cohort), all_alerts)
    totals = Counter()
    for org in cohort:
        alerts = sorted(by_org[org])
        vectors = [tuple(set(data["alerts"][alert]["fields"][field]) for field in FIELDS) for alert in alerts]
        for i, left in enumerate(alerts):
            lf = vectors[i]
            for j in range(i + 1, len(alerts)):
                matched = [bool(lf[k] & vectors[j][k]) for k in range(3)]
                route_flags = (
                    matched[0] and matched[1],
                    matched[0], matched[1], matched[2], any(matched),
                )
                positive = truth[left] == truth[alerts[j]]
                totals["pairs"] += 1
                totals["positive_pairs"] += positive
                for route, active in zip(ROUTES, route_flags):
                    if active:
                        totals[route + "_pairs"] += 1
                        totals[route + "_positive"] += positive
    result = {
        "classification": "exploratory_posthoc_truth_informed_route_diagnostic_not_frozen_candidate_benchmark",
        "organizations": len(cohort),
        "alerts": len(all_alerts),
        "possible_pairs": totals["pairs"],
        "positive_pairs": totals["positive_pairs"],
        "routes": {route: {
            "pair_coverage": totals[route + "_pairs"] / totals["pairs"],
            "positive_pair_overlap": totals[route + "_positive"] / totals["positive_pairs"],
            "pairs": totals[route + "_pairs"],
            "positive_pairs": totals[route + "_positive"],
        } for route in ROUTES},
        "limits": ["previously exposed 57 small queues", "truth read in same diagnostic process; not a frozen candidate run", "overlap is an upper bound for exact-field retrieval before any cap or classifier", "does not measure end-to-end Recall@20", "field use remains local-only assumption"],
        "source_sha256": {"data/derived/guide_rerun_v2/prepared.pkl": sha256_file(PREPARED), "src/recall_route_diagnostic.py": sha256_file(Path(__file__))},
    }
    OUT.mkdir(parents=True)
    (OUT / "aggregate.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "posthoc_diagnostic_complete", "routes": result["routes"]}, sort_keys=True))


if __name__ == "__main__":
    main()
