"""Label-blind split of v2 groups at weak single-edge graph bridges."""
from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from collections import defaultdict
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from src.phase2 import sha256_file

CUT_BELOW = 0.80


def split_bridges(keys, groups, edges, scores, cut_below=CUT_BELOW):
    """Remove only graph bridges with score below cut_below; preserve every alert."""
    n = len(keys)
    group_of = {alert: i for i, group in enumerate(groups) for alert in group}
    adjacency = defaultdict(list)
    weak = set()
    for code, score in zip(edges, scores):
        if score < .75:
            continue
        a, b = divmod(int(code), n)
        if group_of[keys[a]] != group_of[keys[b]]:
            continue
        adjacency[a].append(b)
        adjacency[b].append(a)
        if score < cut_below:
            weak.add((min(a, b), max(a, b)))
    position = {alert: i for i, alert in enumerate(keys)}
    output, cuts = [], 0
    for group in groups:
        if len(group) <= 1:
            output.append(group)
            continue
        vertices = [position[a] for a in group]
        discovery, low, bridges = {}, {}, set()
        def dfs(u, parent):
            discovery[u] = low[u] = len(discovery)
            for v in adjacency[u]:
                if v == parent:
                    continue
                if v not in discovery:
                    dfs(v, u)
                    low[u] = min(low[u], low[v])
                    if low[v] > discovery[u]:
                        pair = (min(u, v), max(u, v))
                        if pair in weak:
                            bridges.add(pair)
                else:
                    low[u] = min(low[u], discovery[v])
        for vertex in vertices:
            if vertex not in discovery:
                dfs(vertex, -1)
        cuts += len(bridges)
        visited = set()
        for start in vertices:
            if start in visited:
                continue
            todo, part = [start], []
            visited.add(start)
            while todo:
                u = todo.pop()
                part.append(keys[u])
                for v in adjacency[u]:
                    pair = (min(u, v), max(u, v))
                    if pair not in bridges and v not in visited:
                        visited.add(v)
                        todo.append(v)
            output.append(sorted(part))
    output.sort(key=lambda group: group[0])
    if sorted(a for group in output for a in group) != sorted(keys):
        raise AssertionError("Bridge split changed alert scope")
    return output, cuts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-queues", type=int, default=0)
    args = parser.parse_args()
    source = HERE / "c_predictions"
    source_freeze = json.loads((source / "prediction_freeze.json").read_text())
    names = sorted(source_freeze["prediction_sha256"])
    if args.sample_queues:
        names = names[:args.sample_queues]
    target = HERE / ("bridge_sample" if args.sample_queues else "bridge_predictions")
    if target.exists():
        raise FileExistsError(f"Refusing overwrite: {target}")
    target.mkdir()
    started, process = time.perf_counter(), psutil.Process()
    hashes, cuts, peak = {}, 0, 0
    for i, name in enumerate(names, 1):
        path = source / f"{name}.pkl"
        if sha256_file(path) != source_freeze["prediction_sha256"][name]:
            raise ValueError("Frozen C prediction hash mismatch")
        with path.open("rb") as stream:
            row = pickle.load(stream)
        groups, count = split_bridges(row["keys"], row["groups"]["0.75"], row["edges"], row["probabilities"])
        cuts += count
        out = target / f"{name}.pkl"
        with out.open("wb") as stream:
            pickle.dump({"keys": row["keys"], "groups": groups, "bridges_cut": count}, stream, protocol=pickle.HIGHEST_PROTOCOL)
        hashes[name] = sha256_file(out)
        peak = max(peak, process.memory_info().rss)
        if i % 25 == 0 or args.sample_queues:
            print(f"Bridge split {i}/{len(names)}", flush=True)
    freeze = {"classification": "label_blind_retrospective_graph_split", "sample": bool(args.sample_queues),
              "cut_below": CUT_BELOW, "base_prediction_freeze_sha256": sha256_file(source / "prediction_freeze.json"),
              "code_sha256": sha256_file(Path(__file__)), "prediction_sha256": hashes,
              "bridges_cut": cuts, "resource": {"wall_seconds": time.perf_counter()-started,
                                                   "peak_process_rss_bytes": peak}, "evaluator_labels_read": False}
    (target / "prediction_freeze.json").write_text(json.dumps(freeze, indent=2), encoding="utf-8")
    print(json.dumps({"status": "frozen", "queues": len(names), "bridges_cut": cuts,
                      "resource": freeze["resource"]}))


if __name__ == "__main__":
    main()
