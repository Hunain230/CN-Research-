"""Label-blind C/P/V inference over model-visible alerts and availability ledger."""
import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ALLOWED = {"alert_id", "source_id", "queue_id", "event_minute", "host", "account",
           "indicator", "trace", "event_type", "severity", "asset_criticality",
           "evidence_available_minute"}
FORBIDDEN = {"incident_id", "scenario_id", "template_id", "priority_score", "priority_rank",
             "malicious", "attack_stage", "impact", "urgency"}


def read_lines(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def load_visible(data_root, split, queue, cutoff):
    base = Path(data_root) / split
    alerts = read_lines(base / "generated_alerts" / f"{queue}.jsonl")
    ledger = read_lines(base / "evidence_ledger" / f"{queue}.jsonl")
    assert all(set(a) <= ALLOWED and not set(a) & FORBIDDEN for a in alerts)
    assert [x["sequence"] for x in ledger] == list(range(1, len(ledger)+1))
    availability = {x["artifact_id"]: x["evidence_available_minute"] for x in ledger}
    assert len(availability) == len(ledger) == len(alerts)
    visible = [a for a in alerts if availability[a["alert_id"]] <= cutoff]
    assert all(a["evidence_available_minute"] == availability[a["alert_id"]] for a in alerts)
    assert all(a["evidence_available_minute"] <= cutoff for a in visible)
    return sorted(visible, key=lambda a: a["alert_id"])


def groups_for(alerts, method, cap=100):
    ids = [a["alert_id"] for a in alerts]
    n = len(ids)
    parent = list(range(n))
    size = [1] * n
    decisions = Counter()
    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def merge(i, j):
        a, b = root(i), root(j)
        if a == b:
            return
        if size[a]+size[b] > cap:
            decisions["cap_rejected"] += 1
            return
        if method.endswith("_v"):
            traces_a = {alerts[k]["trace"] for k in range(n) if root(k) == a and alerts[k]["trace"]}
            traces_b = {alerts[k]["trace"] for k in range(n) if root(k) == b and alerts[k]["trace"]}
            if traces_a and traces_b and traces_a != traces_b:
                decisions["contradiction_rejected"] += 1
                return
        parent[b] = a
        size[a] += size[b]
        decisions["accepted"] += 1
    # Same source is one provenance witness and can produce duplicate alerts.
    by_source = defaultdict(list)
    by_trace = defaultdict(list)
    for i, a in enumerate(alerts):
        by_source[a["source_id"]].append(i)
        if a["trace"]:
            by_trace[a["trace"]].append(i)
    for indices in by_source.values():
        for j in indices[1:]:
            merge(indices[0], j)
    for indices in by_trace.values():
        for j in indices[1:]:
            merge(indices[0], j)
    candidates = set()
    if method.startswith("multi"):
        buckets = defaultdict(list)
        for i,a in enumerate(alerts):
            if a["host"] and a["account"]:
                buckets[(a["host"], a["account"])].append(i)
        for indices in buckets.values():
            indices.sort(key=lambda i: alerts[i]["event_minute"])
            for pos, i in enumerate(indices):
                for j in indices[pos+1:]:
                    if alerts[j]["event_minute"]-alerts[i]["event_minute"] > 18:
                        break
                    if alerts[i]["source_id"] == alerts[j]["source_id"]:
                        continue
                    if alerts[i]["indicator"] and alerts[i]["indicator"] == alerts[j]["indicator"]:
                        candidates.add((i,j))
                    elif alerts[i]["event_type"] != alerts[j]["event_type"]:
                        candidates.add((i,j))
        # Boundary needs two distinct source observations on at least one side;
        # exact indicator is a stronger singleton-to-singleton route.
        boundary = defaultdict(list)
        for i,j in sorted(candidates):
            a,b = root(i),root(j)
            if a != b:
                boundary[tuple(sorted((a,b)))].append((i,j))
        proposals = []
        for pair, links in boundary.items():
            witnesses = {alerts[i]["source_id"] for i,j in links} | {alerts[j]["source_id"] for i,j in links}
            exact = any(alerts[i]["indicator"] and alerts[i]["indicator"] == alerts[j]["indicator"] for i,j in links)
            if len(witnesses) >= 3 or exact:
                proposals.append((len(links),len(witnesses),pair))
            else:
                decisions["weak_abstained"] += 1
        for _,__,(i,j) in sorted(proposals, reverse=True):
            merge(i,j)
    groups = defaultdict(list)
    for i,a in enumerate(alerts):
        groups[root(i)].append(a["alert_id"])
    result = sorted((sorted(g) for g in groups.values()), key=lambda g:g[0])
    assert sum(map(len,result)) == n and max(map(len,result),default=0) <= cap
    return result, len(candidates), dict(decisions)


def rank_groups(groups, alerts, ranker):
    lookup = {a["alert_id"]: a for a in alerts}
    scores = {}
    for group in groups:
        items = [lookup[x] for x in group]
        unique = {a["source_id"]: a for a in items}
        items = list(unique.values())
        maxsev = max(a["severity"] for a in items)
        critical = max(a["asset_criticality"] for a in items)
        diversity = len({a["event_type"] for a in items})
        if ranker == "simple":
            score = maxsev + .1*critical + .01*len(items)
        elif ranker == "progression":
            score = 1.2*maxsev + .7*critical + .55*diversity + .1*min(len(items),10)
        else:
            raise ValueError(ranker)
        scores[group[0]] = score
    return sorted(groups, key=lambda g:(-scores[g[0]],g[0]))


def predict(data_root, split, queue, method, ranker, cutoff, cap=100):
    start = time.perf_counter()
    alerts = load_visible(data_root, split, queue, cutoff)
    groups, candidates, decisions = groups_for(alerts, method, cap)
    ranked = rank_groups(groups, alerts, ranker)
    return {"queue_id":queue,"split":split,"method":method,"ranker":ranker,
            "cutoff":cutoff,"eligible_alert_ids":[a["alert_id"] for a in alerts],
            "groups_ranked":ranked,"candidate_pairs":candidates,"decisions":decisions,
            "runtime_seconds":time.perf_counter()-start}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data-root",default=str(HERE/"datasets"))
    p.add_argument("--split",required=True)
    p.add_argument("--method",choices=("exact","multi","multi_v"),required=True)
    p.add_argument("--ranker",choices=("simple","progression"),required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    config=json.loads((HERE/"configs/study.json").read_text())
    queues=[x["queue_id"] for x in json.loads((Path(a.data_root)/"manifest.json").read_text())["splits"][a.split]]
    out=Path(a.out)
    if out.exists():
        raise FileExistsError(out)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8") as stream:
        for queue in queues:
            stream.write(json.dumps(predict(a.data_root,a.split,queue,a.method,a.ranker,config["decision_minute"],config["component_cap"]),sort_keys=True)+"\n")
    print(json.dumps({"predictions":str(out),"queues":len(queues)}))


if __name__=="__main__":
    main()
