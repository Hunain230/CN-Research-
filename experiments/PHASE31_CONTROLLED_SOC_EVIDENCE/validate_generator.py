"""Independent pre-evaluation generator and leakage validation."""
import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "dataset"
PRIVATE_WORDS = {"incident_id", "scenario_id", "template_id", "true_relation", "malicious",
                 "attack_stage", "priority_rank", "priority_score", "condition"}


def lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def validate(splits):
    summary = {}
    all_incidents = set()
    all_templates = set()
    for split in splits:
        manifest = json.loads((DATA / f"{split}_manifest.json").read_text(encoding="utf-8"))
        visible = DATA / "receiver_visible" / split
        private = DATA / "evaluator_only" / split
        assert visible.resolve() != private.resolve()
        counts = Counter()
        ids = set()
        split_incidents = set()
        templates = set()
        for item in manifest["queues"]:
            q = item["queue_id"]
            alerts = lines(visible / "alerts" / f"{q}.jsonl")
            ledger = lines(visible / "evidence_ledger" / f"{q}.jsonl")
            claims = lines(visible / "claims" / f"{q}.jsonl")
            truth = lines(private / "ground_truth_private" / f"{q}.jsonl")
            priority = lines(private / "ground_truth_private" / f"{q}_priority.jsonl")
            relation_truth = lines(private / "relationship_truth" / f"{q}.jsonl")
            assert len(alerts) == len(ledger) == len(truth) == item["alerts"]
            assert len(claims) == item["claims"]
            assert len(priority) == item["incidents"] == 25
            assert set(x["alert_id"] for x in alerts) == set(x["alert_id"] for x in truth)
            assert len({x["alert_id"] for x in alerts}) == len(alerts)
            assert len({x["observation_id"] for x in alerts}) == len(alerts)
            assert len({x["observation_id"] for x in claims}) == len(claims)
            assert [x["sequence"] for x in ledger] == list(range(1, len(ledger) + 1))
            assert {x["artifact_id"]: x["evidence_available_minute"] for x in ledger} == {
                x["alert_id"]: x["evidence_available_minute"] for x in alerts}
            assert set().union(*(set(x) & PRIVATE_WORDS for x in alerts + ledger + claims)) == set()
            assert all(re.fullmatch(r"[0-9a-f]{24}", x["alert_id"]) for x in alerts)
            assert all(x["event_minute"] <= x["evidence_available_minute"] for x in alerts)
            assert all(x["observed_minute"] <= x["evidence_available_minute"] for x in claims)
            assert all(x["family"] in ("process", "authentication", "network_flow") for x in claims)
            assert all(x["left_alert_id"] in {a["alert_id"] for a in alerts} and
                       x["right_alert_id"] in {a["alert_id"] for a in alerts} for x in claims)
            assert set(range(1, 26)) == {x["priority_rank"] for x in priority}
            incident_ids = {x["incident_id"] for x in priority}
            assert all(any(t["incident_id"] == i for t in truth) for i in incident_ids)
            incident_of = {t["alert_id"]: t["incident_id"] for t in truth}
            for field in ("process_id", "auth_session_id", "flow_id"):
                users = defaultdict(set)
                for a in alerts: users[a[field]].add(incident_of[a["alert_id"]])
                counts[f"cross_incident_reused_{field}"] += sum(len(v) > 1 for v in users.values())
            assert not incident_ids & split_incidents
            split_incidents.update(incident_ids)
            templates.update(x["template_id"] for x in priority)
            visible_text = "".join((visible / kind / f"{q}.jsonl").read_text(encoding="utf-8")
                                   for kind in ("alerts", "claims", "evidence_ledger"))
            assert not any(i in visible_text for i in incident_ids)
            by_obs = {x["observation_id"]: x for x in claims}
            by_alert = {x["alert_id"]: x for x in alerts}
            false_same_context = set()
            for c in claims:
                if c["derived_from"]:
                    parent = by_obs[c["derived_from"]]
                    assert c["upstream_root_id"] == parent["upstream_root_id"]
                    assert c["relationship_token"] == parent["relationship_token"]
                    counts["derived_claims"] += 1
                if c["evidence_available_minute"] > 100: counts["late_claims"] += 1
            for t in relation_truth:
                counts[t["condition"]] += 1
                if t["condition"] == "false_independent_looking_claim":
                    c = by_obs[t["observation_id"]]
                    left, right = by_alert[c["left_alert_id"]], by_alert[c["right_alert_id"]]
                    if left["host"] == right["host"] and left["account"] == right["account"]:
                        false_same_context.add(t["relationship_token"])
                if t["condition"] == "genuine":
                    c = by_obs[t["observation_id"]]
                    left, right = by_alert[c["left_alert_id"]], by_alert[c["right_alert_id"]]
                    assert right["event_minute"] >= left["event_minute"] - 3
            assert len(false_same_context) >= 3, (q, len(false_same_context))
            counts["false_same_context_relationships"] += len(false_same_context)
            counts["late_alerts"] += sum(x["evidence_available_minute"] > 100 for x in alerts)
            counts["duplicate_alerts"] += sum(x["duplicate_of"] is not None for x in alerts)
            counts["process_events"] += sum(x["event_type"] == "process" for x in alerts)
            counts["authentication_events"] += sum(x["event_type"] == "authentication" for x in alerts)
            counts["network_flow_events"] += sum(x["event_type"] == "network_flow" for x in alerts)
            counts["queues"] += 1; counts["alerts"] += len(alerts); counts["claims"] += len(claims)
            ids.update(x["alert_id"] for x in alerts)
        assert not split_incidents & all_incidents
        assert not templates & all_templates
        all_incidents.update(split_incidents); all_templates.update(templates)
        assert len(templates) >= 8
        assert all(counts[k] > 0 for k in ("genuine", "false_independent_looking_claim", "derived_claims",
            "missing", "late_claims", "late_alerts", "duplicate_alerts", "process_events",
            "authentication_events", "network_flow_events", "delayed_contradiction",
            "cross_incident_reused_process_id", "cross_incident_reused_auth_session_id",
            "cross_incident_reused_flow_id", "false_same_context_relationships"))
        summary[split] = dict(counts)
    (HERE / "artifacts/generator_validation.json").parent.mkdir(exist_ok=True)
    (HERE / "artifacts/generator_validation.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("splits", nargs="+", choices=("train", "development", "locked_test"))
    validate(p.parse_args().splits)
