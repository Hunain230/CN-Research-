"""One controlled SOC generator. Private truth is written to a separate tree."""
import argparse
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
FAMILIES = ("process", "authentication", "network_flow")
TEMPLATES = (
    "credential_access", "lateral_activity", "persistence", "data_staging",
    "command_activity", "privilege_change", "service_abuse", "remote_execution",
    "exfiltration", "account_takeover")


def token(rng):
    return f"{rng.getrandbits(96):024x}"


def write_lines(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def make_alert(rng, queue, host, account, indicator, minute, family, tree, severity, criticality,
               process_id=None, parent_process_id=None, auth_session_id=None, flow_id=None,
               upstream_root=None, duplicate_of=None):
    event_id = token(rng) if duplicate_of is None else duplicate_of["event_id"]
    source_id = token(rng) if duplicate_of is None else duplicate_of["source_id"]
    availability = (minute + rng.randrange(1, 6) + (rng.randrange(24, 46) if rng.random() < .025 else 0)
                    if duplicate_of is None else duplicate_of["evidence_available_minute"] + 1)
    return {"alert_id": token(rng), "event_id": event_id, "source_id": source_id,
        "queue_id": queue, "event_minute": minute, "evidence_available_minute": availability,
        "host": host, "account": account, "indicator": indicator,
        "process_tree_ref": tree, "auth_session_ref": None, "network_flow_ref": None,
        "event_type": family, "severity": severity, "asset_criticality": criticality,
        "process_id": process_id or (f"pid_{rng.randrange(30)}" if rng.random() < .08 else token(rng)),
        "parent_process_id": parent_process_id or token(rng),
        "executable_hash": token(rng), "user_session_id": token(rng),
        "auth_session_id": auth_session_id or (f"session_{rng.randrange(24)}" if rng.random() < .08 else token(rng)),
        "auth_provider": f"idp_{rng.randrange(3)}",
        "source_host": host, "destination_host": f"host_{rng.randrange(10)}",
        "flow_id": flow_id or (f"flow_{rng.randrange(24)}" if rng.random() < .08 else token(rng)),
        "port": rng.choice((22, 80, 443, 445, 3389)), "direction": rng.choice(("in", "out")),
        "duration_seconds": rng.randrange(1, 180),
        "endpoint_origin": upstream_root or f"endpoint_{host}",
        "observation_id": token(rng), "duplicate_of": None if duplicate_of is None else duplicate_of["observation_id"]}


def claim(rng, queue, left, right, rel_token, family, *, derived_from=None, upstream_root=None,
          available_minute=None, corrupt=False):
    origin = upstream_root or {"process": f"endpoint_{left['host']}",
        "authentication": f"idp_{left['auth_provider']}",
        "network_flow": f"network_tap_{left['host']}"}[family]
    mechanism = {"process": "endpoint_parent_child_event", "authentication": "identity_provider_session_event",
        "network_flow": "network_tap_connection_event"}[family]
    record = {"observation_id": token(rng), "queue_id": queue, "relationship_token": rel_token,
        "left_alert_id": left["alert_id"], "right_alert_id": right["alert_id"],
        "left_event_id": left["event_id"], "right_event_id": right["event_id"],
        "family": family, "upstream_root_id": origin, "collection_mechanism": mechanism,
        "derived_from": derived_from, "observed_minute": max(left["event_minute"], right["event_minute"]),
        "sensor_clock_minute": max(left["event_minute"], right["event_minute"]) + rng.randrange(-3, 4),
        "evidence_available_minute": available_minute if available_minute is not None else
            max(left["event_minute"], right["event_minute"]) + rng.randrange(2, 7),
        "left_host": left["host"], "right_host": right["host"], "account": left["account"],
        "left_process_id": left["process_id"],
        "right_parent_process_id": right["parent_process_id"] if not corrupt else token(rng),
        "auth_session_id": left["auth_session_id"], "flow_id": left["flow_id"]}
    return record


def generate_split(split):
    if split not in CONFIG["splits"]: raise ValueError(split)
    spec = CONFIG["splits"][split]
    root = HERE / "dataset"
    visible = root / "receiver_visible" / split
    private = root / "evaluator_only" / split
    manifest_path = root / f"{split}_manifest.json"
    if manifest_path.exists() or visible.exists() or private.exists():
        raise FileExistsError(f"split already exists: {split}")
    rng = random.Random(spec["seed"])
    manifest = {"schema": CONFIG["schema"], "split": split, "seed": spec["seed"],
        "template_variant": spec["template_variant"], "queues": [], "decision_minute": CONFIG["decision_minute"]}
    for qi in range(spec["queues"]):
        queue = f"p31_{split}_q{qi:03d}"
        alerts, claims, truth, priority, relation_truth = [], [], [], [], []
        incident_fragments = []
        for ii in range(CONFIG["incidents_per_queue"]):
            incident_id = token(rng)
            template = TEMPLATES[(ii * 3 + qi + spec["template_variant"]) % len(TEMPLATES)]
            host = f"host_{rng.randrange(5)}"
            account = f"account_{rng.randrange(6)}"
            indicator = f"service_{rng.randrange(7)}"
            criticality = rng.randrange(1, 6)
            impact = rng.randrange(1, 6)
            urgency = rng.randrange(1, 6)
            priority.append({"incident_id": incident_id, "scenario_id": token(rng),
                "template_id": f"{template}:v{spec['template_variant']}",
                "priority_score": 4 * impact + 3 * criticality + 2 * urgency + rng.randrange(1, 5)})
            count = rng.randrange(9, 13)
            start = rng.randrange(5, 50)
            family_shift = rng.randrange(3)
            fragment_trees = [token(rng) for _ in range(3)]
            scenario_alerts = []
            for j in range(count):
                family = FAMILIES[(j + family_shift + spec["template_variant"]) % 3]
                minute = min(94, start + 3 * j + rng.randrange(-1, 2))
                a = make_alert(rng, queue, host, account, indicator, minute, family,
                    fragment_trees[min(j // 4, 2)],
                    max(1, min(5, impact + rng.choice((-2, -1, 0, 0, 1)))), criticality)
                alerts.append(a); scenario_alerts.append(a)
                truth.append({"alert_id": a["alert_id"], "incident_id": incident_id,
                    "scenario_id": priority[-1]["scenario_id"], "malicious": True,
                    "attack_stage": template})
                if rng.random() < .045:
                    duplicate = make_alert(rng, queue, host, account, indicator, minute, family,
                        a["process_tree_ref"], a["severity"], criticality, duplicate_of=a,
                        process_id=a["process_id"], parent_process_id=a["parent_process_id"],
                        auth_session_id=a["auth_session_id"], flow_id=a["flow_id"])
                    duplicate.update({k: v for k, v in a.items() if k not in (
                        "alert_id", "observation_id", "evidence_available_minute", "duplicate_of")})
                    alerts.append(duplicate)
                    truth.append({"alert_id": duplicate["alert_id"], "incident_id": incident_id,
                        "scenario_id": priority[-1]["scenario_id"], "malicious": True,
                        "attack_stage": template})
            incident_fragments.append(scenario_alerts)
            for boundary in (3, 7):
                left, right = scenario_alerts[boundary], scenario_alerts[boundary + 1]
                right["parent_process_id"] = left["process_id"]
                right["auth_session_id"] = left["auth_session_id"]
                right["flow_id"] = left["flow_id"]
                rel_token = token(rng)
                for family in FAMILIES:
                    if rng.random() < .015:
                        relation_truth.append({"relationship_token": rel_token, "family": family,
                            "true_relation": True, "condition": "missing"})
                        continue
                    available = max(left["event_minute"], right["event_minute"]) + (
                        rng.randrange(45, 75) if rng.random() < .025 else rng.randrange(2, 7))
                    c = claim(rng, queue, left, right, rel_token, family, available_minute=available)
                    claims.append(c)
                    relation_truth.append({"observation_id": c["observation_id"], "relationship_token": rel_token,
                        "family": family, "true_relation": True, "condition": "genuine"})
                    if rng.random() < .08:
                        copied = claim(rng, queue, left, right, rel_token, family,
                            derived_from=c["observation_id"], upstream_root=c["upstream_root_id"],
                            available_minute=available + 1)
                        claims.append(copied)
                        relation_truth.append({"observation_id": copied["observation_id"],
                            "relationship_token": rel_token, "family": family, "true_relation": True,
                            "condition": "derived_copy"})
        # Benign activity shares users, hosts, and temporal windows with attacks.
        for bi in range(CONFIG["benign_events_per_queue"]):
            host = f"host_{rng.randrange(5)}"; account = f"account_{rng.randrange(6)}"
            minute = rng.randrange(5, 95)
            a = make_alert(rng, queue, host, account, f"service_{rng.randrange(7)}", minute,
                FAMILIES[rng.randrange(3)], token(rng), rng.randrange(1, 6), rng.randrange(1, 6))
            alerts.append(a)
            truth.append({"alert_id": a["alert_id"], "incident_id": token(rng),
                "scenario_id": None, "malicious": False, "attack_stage": None})
        # False dual claims from distinct origins, including some same-context pairs.
        same_context_pairs = [(i, j) for i in range(len(incident_fragments))
            for j in range(i + 1, len(incident_fragments)) if
            incident_fragments[i][0]["host"] == incident_fragments[j][0]["host"] and
            incident_fragments[i][0]["account"] == incident_fragments[j][0]["account"]]
        for fi in range(10):
            if fi < 6 and same_context_pairs:
                left_inc, right_inc = rng.choice(same_context_pairs)
            else:
                left_inc = rng.randrange(len(incident_fragments))
                right_inc = (left_inc + rng.randrange(1, len(incident_fragments))) % len(incident_fragments)
            left = rng.choice(incident_fragments[left_inc]); right = rng.choice(incident_fragments[right_inc])
            rel_token = token(rng)
            families = FAMILIES if fi < 3 else FAMILIES[:2]
            for family in families:
                c = claim(rng, queue, left, right, rel_token, family,
                    corrupt=(family == "process" and fi < 3))
                claims.append(c)
                relation_truth.append({"observation_id": c["observation_id"],
                    "relationship_token": rel_token, "family": family,
                    "true_relation": False, "condition": "false_independent_looking_claim"})
            if fi == 0:
                # Receiver cannot use this late contradiction for minute-100 decisions.
                late = claim(rng, queue, left, right, rel_token, "network_flow",
                    available_minute=CONFIG["decision_minute"] + 20, corrupt=True)
                claims.append(late)
                relation_truth.append({"observation_id": late["observation_id"],
                    "relationship_token": rel_token, "family": "network_flow",
                    "true_relation": False, "condition": "delayed_contradiction"})
        priority.sort(key=lambda x: (-x["priority_score"], x["incident_id"]))
        for rank, row in enumerate(priority, 1): row["priority_rank"] = rank
        rng.shuffle(alerts); rng.shuffle(claims)
        ledger = [{"sequence": pos, "artifact_id": a["alert_id"],
            "evidence_available_minute": a["evidence_available_minute"],
            "event_minute": a["event_minute"]} for pos, a in enumerate(alerts, 1)]
        write_lines(visible / "alerts" / f"{queue}.jsonl", alerts)
        write_lines(visible / "claims" / f"{queue}.jsonl", claims)
        write_lines(visible / "evidence_ledger" / f"{queue}.jsonl", ledger)
        write_lines(private / "ground_truth_private" / f"{queue}.jsonl", truth)
        write_lines(private / "ground_truth_private" / f"{queue}_priority.jsonl", priority)
        write_lines(private / "relationship_truth" / f"{queue}.jsonl", relation_truth)
        manifest["queues"].append({"queue_id": queue, "alerts": len(alerts),
            "claims": len(claims), "incidents": len(priority)})
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"split": split, "queues": len(manifest["queues"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", required=True, choices=CONFIG["splits"])
    generate_split(parser.parse_args().split)
