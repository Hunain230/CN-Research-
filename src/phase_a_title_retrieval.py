"""Experimental local-only alert-title retrieval, frozen before truth access."""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from .guide_rerun_v2 import ROOT, PRIVATE, check_raw, key, load, bootstrap
from .phase2 import sha256_file
from .phase_a_entity_retrieval import DEST as ENTITY_DEST, selected

DEST = ROOT / "data/derived/phase_a_title_retrieval"
REPORT = ROOT / "outputs/phase_a/title_retrieval_v1.json"
STOP = {"the", "and", "for", "from", "with", "this", "that", "was", "are",
        "has", "have", "been", "user", "alert", "detected", "suspicious"}


def generate():
    if DEST.exists():
        raise FileExistsError(DEST)
    check_raw()
    entity_manifest = ENTITY_DEST / "manifest.json"
    frozen = json.loads(entity_manifest.read_text(encoding="utf-8"))
    by = selected(load())
    chosen = {alert for docs in by.values() for alert in docs}
    titles = defaultdict(set)
    with (ROOT / "data/raw/GUIDE_Test.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["OrgId"] not in by:
                continue
            alert = key(row["OrgId"], row["AlertId"])
            if alert not in chosen:
                continue
            title = row["AlertTitle"].strip().lower()
            if not title:
                continue
            titles[alert].add(("exact", title))
            titles[alert].update(("word", word) for word in set(re.findall(r"[a-z0-9]{4,}", title))
                                 if word not in STOP and not word.isdigit())
    DEST.mkdir(parents=True)
    hashes = {}
    total = Counter()
    for org, docs in sorted(by.items()):
        source = ENTITY_DEST / f"{key(org)}.npz"
        if sha256_file(source) != frozen["candidate_sha256"][key(org)]:
            raise ValueError("entity candidate freeze mismatch")
        with np.load(source) as arr:
            keys = arr["keys"].tolist()
            prior = arr["union"].copy()
        n = len(keys)
        posts = defaultdict(list)
        for i, alert in enumerate(keys):
            for token in titles[alert]:
                posts[token].append(i)
        added = set()
        for token, members in posts.items():
            cap = 100 if token[0] == "exact" else 20
            if 2 <= len(members) <= cap:
                for a in range(len(members)):
                    for b in range(a + 1, len(members)):
                        added.add(members[a] * n + members[b])
        title_edge = np.fromiter(sorted(added), dtype=np.int64)
        union = np.union1d(prior, title_edge)
        path = DEST / f"{key(org)}.npz"
        np.savez_compressed(path, keys=np.array(keys), prior=prior, title=title_edge, union=union)
        hashes[key(org)] = sha256_file(path)
        total.update({"organizations": 1, "possible_pairs": n * (n - 1) // 2,
                      "prior_pairs": len(prior), "title_pairs": len(title_edge),
                      "union_pairs": len(union)})
    (DEST / "manifest.json").write_text(json.dumps({
        "classification": "exploratory_local_only_timing_unverified",
        "candidate_sha256": hashes, "aggregate": dict(total),
        "exact_title_document_frequency_cap": 100, "word_document_frequency_cap": 20,
        "token_minimum_length": 4, "stopwords": sorted(STOP),
        "entity_manifest_sha256": sha256_file(entity_manifest),
        "source_sha256": {"code": sha256_file(Path(__file__)),
                          "raw": sha256_file(ROOT / "data/raw/GUIDE_Test.csv")},
        "no_title_or_token_values_persisted": True,
    }, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(dict(total), indent=2))


def evaluate():
    if REPORT.exists():
        raise FileExistsError(REPORT)
    check_raw()
    manifest_path = DEST / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data = load()
    by = selected(data)
    from .guide_correlation_v2 import truth
    gold = truth(set(by), data["alerts"])
    results = {"train": [], "validation": []}
    for org, docs in sorted(by.items()):
        path = DEST / f"{key(org)}.npz"
        if sha256_file(path) != manifest["candidate_sha256"][key(org)]:
            raise ValueError("title candidate freeze mismatch")
        with np.load(path) as arr:
            keys = arr["keys"].tolist()
            if set(keys) != set(docs):
                raise ValueError("alert population mismatch")
            n = len(keys)
            sizes = Counter(gold[k] for k in keys)
            row = {"positive": sum(v * (v - 1) // 2 for v in sizes.values()),
                   "possible_pairs": n * (n - 1) // 2}
            for name in ("prior", "title", "union"):
                edge = arr[name]
                row[name + "_positive"] = sum(gold[keys[int(v // n)]] == gold[keys[int(v % n)]] for v in edge)
                row[name + "_pairs"] = len(edge)
            results[data["split"][org]].append(row)
    summary = {}
    for split, rows in results.items():
        total = {name: sum(r[name] for r in rows) for name in rows[0]}
        summary[split] = {"organizations": len(rows), "totals": total,
                          "routes": {name: {
                              "micro_candidate_recall": total[name + "_positive"] / total["positive"],
                              "pair_coverage": total[name + "_pairs"] / total["possible_pairs"],
                              "macro_candidate_recall": bootstrap([r[name + "_positive"] / r["positive"] for r in rows if r["positive"]]),
                          } for name in ("prior", "title", "union")}}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"classification": "exploratory_train_validation_only",
                                  "cohorts": summary, "manifest_sha256": sha256_file(manifest_path),
                                  "target_met_on_validation": summary["validation"]["routes"]["union"]["micro_candidate_recall"] >= .99,
                                  "point_in_time_provenance_confirmed": False,
                                  "external_transfer_approved": False,
                                  "test_cohort_used": False,
                                  "labels_in_generation": False}, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({s: {n: r["routes"][n] for n in ("prior", "title", "union")}
                      for s, r in summary.items()}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("generate", "evaluate"))
    globals()[parser.parse_args().stage]()
