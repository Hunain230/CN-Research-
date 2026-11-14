"""Development-only candidate expansion cost and oracle-connectivity sensitivity."""

from __future__ import annotations

import json
import pickle
import time
from collections import Counter, defaultdict
from pathlib import Path

from src.guide_rerun_v2 import labels
from src.offline_joint_comparison import read_truth
from src.phase2 import sha256_file
from src.submission_full_guide import ROOT, write_json
from src.submission_full_entity_time import (PARENT, SPLIT, ENTITY_FIELDS,
                                             MAX_TOKEN_FREQUENCY, RARE_TOKEN_FREQUENCY,
                                             read_docs)
from src.submission_entity_time_pair_v2 import shard_map
from submission.audit_entity_time_fields_v3 import detect_modal_sentinels


OUT = ROOT / "outputs/submission_development_candidate_expansion_20261114_v1.json"
CONFIGS = (("current_5_48h_1h", 5, 48, 1),
           ("moderate_10_72h_2h", 10, 72, 2),
           ("wide_20_96h_4h", 20, 96, 4))


def propose(keys: list[str], docs: dict, baseline: list[tuple[str, str]],
            neighbors: int, entity_hours: int, technique_hours: int) -> set[int]:
    n = len(keys)
    index = {a: i for i, a in enumerate(keys)}
    stamps = [docs[a]["stamp"] for a in keys]
    edges = set()
    for a, b in baseline:
        i, j = sorted((index[a], index[b]))
        edges.add(i * n + j)
    posting = defaultdict(list)
    technique = defaultdict(list)
    for i, alert in enumerate(keys):
        for token in docs[alert]["entities"]:
            posting[token].append(i)
        for token in docs[alert]["fields"]["MitreTechniques"]:
            technique[token].append(i)
    for mapping, hours in ((posting, entity_hours), (technique, technique_hours)):
        for members in mapping.values():
            if not 2 <= len(members) <= MAX_TOKEN_FREQUENCY:
                continue
            ordered = sorted(members, key=lambda i: (stamps[i], i))
            for pos, a in enumerate(ordered):
                for b in ordered[pos + 1:pos + 1 + neighbors]:
                    if stamps[b] - stamps[a] > hours * 3600:
                        break
                    i, j = sorted((a, b))
                    edges.add(i * n + j)
    return edges


def oracle_connected(keys: list[str], edges: set[int], truth: dict, top20: dict) -> int:
    n = len(keys)
    parent = list(range(n))
    sizes = [1] * n

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for edge in edges:
        i, j = divmod(int(edge), n)
        if truth[keys[i]] != truth[keys[j]]:
            continue
        a, b = root(i), root(j)
        if a != b:
            if sizes[a] < sizes[b]:
                a, b = b, a
            parent[b] = a
            sizes[a] += sizes[b]
    counts = Counter(truth[a] for a in keys)
    parts = defaultdict(Counter)
    for i, alert in enumerate(keys):
        parts[truth[alert]][root(i)] += 1
    return sum(bool(counts[gold]) and max(parts[gold].values(), default=0) / counts[gold] >= .8
               for gold in top20)


def main() -> None:
    if OUT.exists():
        raise FileExistsError("Candidate sensitivity already frozen")
    with PARENT.open("rb") as stream:
        parent = pickle.load(stream)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    chosen = sorted(o for o in parent if split.get(o) == "validation" and len(parent[o]["input_alert_keys"]) <= 500)
    if len(chosen) != 42:
        raise ValueError("Development cohort changed")
    truth = read_truth(set(chosen), {a for o in chosen for a in parent[o]["input_alert_keys"]})
    ranks = labels(set(chosen))
    sentinels, _ = detect_modal_sentinels()
    paths, manifest = shard_map()
    totals = defaultdict(Counter)
    started = time.perf_counter()
    for index, org in enumerate(chosen, 1):
        path = paths[org]
        if sha256_file(path) != manifest["parquet_sha256"][str(path.relative_to(ROOT))]:
            raise ValueError("Projection changed")
        keys = parent[org]["input_alert_keys"]
        docs = read_docs(org, path, sentinels, set(keys))
        n = len(keys)
        for name, neighbors, entity_hours, technique_hours in CONFIGS:
            tic = time.perf_counter()
            edges = propose(keys, docs, parent[org]["candidate_edges"],
                            neighbors, entity_hours, technique_hours)
            positive = sum(truth[keys[e // n]] == truth[keys[e % n]] for e in edges)
            totals[name].update({"candidate_pairs": len(edges), "positive_candidate_pairs": positive,
                                 "oracle_connected_top20_labels": oracle_connected(keys, edges, truth, ranks[org]),
                                 "expert_top20_labels": 20,
                                 "generation_ms": round((time.perf_counter() - tic) * 1000)})
        if index % 10 == 0:
            print(f"Candidate expansion {index}/42 development queues", flush=True)
    output = {name: {**dict(counts),
                     "candidate_oracle_connectivity_recall20": counts["oracle_connected_top20_labels"] / counts["expert_top20_labels"]}
              for name, counts in totals.items()}
    result = {"classification": "development_only_candidate_expansion_oracle_bound_not_model_performance",
              "organizations": len(chosen), "configs": output,
              "analysis_code_sha256": sha256_file(Path(__file__)),
              "source_projection_manifest_sha256": sha256_file(ROOT / "outputs/submission_entity_time_shards_20261114_v1.json"),
              "wall_seconds": time.perf_counter() - started,
              "notes": ["Oracle connectivity ignores group purity and ranking", "No holdout labels read", "Generation times exclude parquet loading and model scoring"]}
    write_json(OUT, result)
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
