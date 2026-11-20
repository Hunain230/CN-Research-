"""Paired descriptive bootstrap for the frozen 15-queue synthetic holdout.

Run from this directory: python paired_queue_bootstrap.py
The queue is the resampling unit; intervals are conditional on this generator.
"""
import csv
import random
from pathlib import Path

ROWS = list(csv.DictReader((Path(__file__).parent / "holdout_queue_results.csv").open(newline="", encoding="utf-8")))
RNG = random.Random(31103)
B = 10000

for title, base, cand, denominator in (
    ("Recall@20", "baseline_recall", "candidate_recall", 20),
    ("Recoverability", "baseline_recoverable", "candidate_recoverable", 20),
    ("P@10", "baseline_p10", "candidate_p10", 10),
):
    differences = [(int(row[cand]) - int(row[base])) * 100 / denominator for row in ROWS]
    replicates = sorted(sum(RNG.choice(differences) for _ in differences) / len(differences) for _ in range(B))
    mean = sum(differences) / len(differences)
    print(f"{title}: {mean:.2f} pp; paired queue bootstrap percentile 95% interval "
          f"[{replicates[249]:.2f}, {replicates[9749]:.2f}] pp")
