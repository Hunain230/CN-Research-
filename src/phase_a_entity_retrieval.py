"""Local-only, exploratory entity-link candidate audit on train/validation orgs.

Generation never reads labels. Evaluation is a separate command. No entity value is
written to disk or exported to a model provider. Raw entity timing is unverified.
"""
from __future__ import annotations

import argparse
import csv
import json
import pickle
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from .guide_correlation_v2 import edges
from .guide_rerun_v2 import ROOT, PRIVATE, OUT, check_raw, key, load, bootstrap
from .phase2 import sha256_file

ENTITY_FIELDS = (
    "DeviceId", "AccountSid", "AccountObjectId", "AccountUpn", "Sha256",
    "NetworkMessageId", "EmailClusterId", "IpAddress", "Url",
    "OAuthApplicationId", "ApplicationId", "ResourceIdName",
)
CAP = 20  # Fixed before evaluation; overly common tokens generate no pairs.
LIMIT = 500  # Existing correlation diagnostic population.
DEST = ROOT / "data/derived/phase_a_entity_retrieval"
REPORT = ROOT / "outputs/phase_a/entity_retrieval_v1.json"


def selected(data):
    training_orgs = sorted((org for org, split in data["split"].items() if split == "train"),
                           key=lambda org: key("phase-a-entity-train-v1", org))[:20]
    training_orgs = set(training_orgs)
    by = defaultdict(dict)
    for alert, doc in data["alerts"].items():
        if doc["org"] in training_orgs or data["split"][doc["org"]] == "validation":
            by[doc["org"]][alert] = doc
    return {org: dict(sorted(docs.items())[:LIMIT]) for org, docs in by.items()}


def generate():
    if DEST.exists():
        raise FileExistsError(f"generation exists: {DEST}")
    check_raw()
    data = load()
    by = selected(data)
    # Fit descriptor vocabulary exclusively on training organizations.
    with (PRIVATE / "correlation_model.pkl").open("rb") as stream:
        _, vec = pickle.load(stream)
    chosen = {alert for docs in by.values() for alert in docs}
    tokens = defaultdict(set)
    started = time.perf_counter()
    with (ROOT / "data/raw/GUIDE_Test.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            alert = key(row["OrgId"], row["AlertId"])
            if alert not in chosen:
                continue
            # Equality is scoped by organization when pairs are built below.
            for field in ENTITY_FIELDS:
                value = row[field].strip().lower()
                if value and value not in {"nan", "none", "null", "unknown", "-"}:
                    tokens[alert].add((field, value))
    DEST.mkdir(parents=True)
    hashes = {}
    aggregate = Counter()
    for index, (org, docs) in enumerate(sorted(by.items()), 1):
        keys, base = edges(docs, vec, [200])
        n = len(keys)
        postings = defaultdict(list)
        for i, alert in enumerate(keys):
            for token in tokens[alert]:
                postings[token].append(i)
        entity = set()
        for members in postings.values():
            if 2 <= len(members) <= CAP:
                for i in range(len(members)):
                    for j in range(i + 1, len(members)):
                        entity.add(members[i] * n + members[j])
        original = base[200]
        extra = np.fromiter(sorted(entity), dtype=np.int64)
        union = np.union1d(original, extra)
        path = DEST / f"{key(org)}.npz"
        np.savez_compressed(path, keys=np.array(keys), baseline=original, entity=extra, union=union)
        hashes[key(org)] = sha256_file(path)
        aggregate.update({"organizations": 1, "alerts": n, "possible_pairs": n * (n - 1) // 2,
                          "baseline_pairs": len(original), "entity_pairs": len(extra),
                          "union_pairs": len(union), "tokens": sum(map(len, postings.values())),
                          "eligible_tokens": sum(2 <= len(v) <= CAP for v in postings.values())})
        if index % 20 == 0:
            print("generated", index, "/", len(by), "organizations", flush=True)
    (DEST / "manifest.json").write_text(json.dumps({
        "classification": "exploratory_local_only_timing_unverified",
        "cohort_counts": dict(Counter(data["split"][o] for o in by)),
        "entity_fields": ENTITY_FIELDS, "max_token_document_frequency": CAP,
        "max_alerts_per_org": LIMIT, "candidate_sha256": hashes,
        "train_sample_orgs": 20,
        "aggregate": dict(aggregate), "seconds": time.perf_counter() - started,
        "source_sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in
                          (Path(__file__), PRIVATE / "prepared.pkl", PRIVATE / "correlation_model.pkl",
                           PRIVATE / "split.json")},
        "notes": ["No source entity value or incident label persisted in this artifact.",
                  "This assumption-only route is not approved for hosted model calls.",
                  "No holdout organization was used."],
    }, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(dict(aggregate), indent=2))


def evaluate():
    if REPORT.exists():
        raise FileExistsError(REPORT)
    check_raw()
    manifest_path = DEST / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data = load()
    by = selected(data)
    # Membership truth is opened only after all candidate files were frozen.
    from .guide_correlation_v2 import truth
    gold = truth(set(by), data["alerts"])
    totals = Counter()
    results = {"train": [], "validation": []}
    for org, docs in sorted(by.items()):
        path = DEST / f"{key(org)}.npz"
        if sha256_file(path) != manifest["candidate_sha256"][key(org)]:
            raise ValueError("candidate freeze hash mismatch")
        with np.load(path) as arrays:
            keys = arrays["keys"].tolist()
            if set(keys) != set(docs):
                raise ValueError("alert population mismatch")
            sizes = Counter(gold[k] for k in keys)
            positive = sum(v * (v - 1) // 2 for v in sizes.values())
            n = len(keys)
            row = {"positive": positive, "possible_pairs": n * (n - 1) // 2}
            for name in ("baseline", "entity", "union"):
                edge = arrays[name]
                retrieved = sum(gold[keys[int(v // n)]] == gold[keys[int(v % n)]] for v in edge)
                row[name + "_positive"] = retrieved
                row[name + "_pairs"] = len(edge)
            results[data["split"][org]].append(row)
    summary = {}
    for split, rows in results.items():
        sums = {k: sum(r[k] for r in rows) for k in rows[0]}
        summary[split] = {"organizations": len(rows), "totals": sums,
                          "routes": {name: {
                              "micro_candidate_recall": sums[name + "_positive"] / sums["positive"] if sums["positive"] else None,
                              "pair_coverage": sums[name + "_pairs"] / sums["possible_pairs"] if sums["possible_pairs"] else None,
                              "macro_candidate_recall": bootstrap([r[name + "_positive"] / r["positive"] for r in rows if r["positive"]]),
                          } for name in ("baseline", "entity", "union")}}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"classification": "exploratory_train_validation_only",
                                  "manifest_sha256": sha256_file(manifest_path),
                                  "cohorts": summary,
                                  "target_micro_candidate_recall": .99,
                                  "target_met_on_validation": summary["validation"]["routes"]["union"]["micro_candidate_recall"] >= .99,
                                  "timing_approval": False,
                                  "privacy_approval_for_external_calls": False,
                                  "labels_in_generation": False,
                                  "test_cohort_used": False}, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: {n: v["routes"][n] for n in ("baseline", "entity", "union")}
                      for k, v in summary.items()}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("generate", "evaluate"))
    globals()[parser.parse_args().stage]()
