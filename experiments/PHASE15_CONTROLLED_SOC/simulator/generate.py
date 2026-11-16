"""Deterministic, non-executing defensive telemetry simulation."""
import argparse
import hashlib
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
FAMILIES = ["initial_access", "credential_compromise", "suspicious_authentication",
            "lateral_movement", "privilege_escalation", "persistence", "command_control",
            "data_staging", "exfiltration", "multi_stage_chain"]
BENIGN = ["normal_authentication", "routine_administration", "scheduled_task",
          "software_update", "network_connection", "service_activity", "file_access",
          "process_creation", "legitimate_privilege_use"]
EVENTS = ["auth", "process", "network", "file", "service", "privilege"]


def write_lines(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for value in values:
            stream.write(json.dumps(value, sort_keys=True) + "\n")


def token(text):
    return hashlib.sha256(text.encode()).hexdigest()[:14]


def generate(config_path):
    config = json.loads(Path(config_path).read_text())
    out = HERE / "datasets"
    if out.exists():
        raise FileExistsError("Dataset already exists; preserve sealed cohort")
    manifest = {"schema": config["schema"], "splits": {}, "template_assignment": {}}
    for split, variants in (("train", (0, 1, 2)), ("development", (3,)), ("locked_test", (4,))):
        rng = random.Random(config["seeds"][split])
        templates = [f"{family}:v{v}" for family in FAMILIES for v in variants]
        manifest["template_assignment"][split] = templates
        summary = []
        for q in range(config["queues"][split]):
            queue = f"{split}_q{q:02d}"
            alerts, source, ledger, truth, oracle, degradation = [], [], [], [], [], []
            incident_rows = []
            for i in range(config["incidents_per_queue"]):
                template = templates[(i + q * 7) % len(templates)]
                family, variant = template.split(":")
                incident = f"{queue}_incident_{i:03d}"
                scenario = f"{queue}_scenario_{i:03d}"
                anchor = token(scenario + "anchor")
                host = f"host_{rng.randrange(12)}"
                account = f"acct_{rng.randrange(15)}"
                indicator = f"service_{rng.randrange(10)}"
                criticality = rng.randrange(1, 5)
                impact = rng.randrange(1, 5)
                urgency = rng.randrange(1, 5)
                base = rng.randrange(1, 5)
                start = rng.randrange(5, 65)
                count = rng.randrange(6, 12)
                incident_rows.append({"incident_id": incident, "scenario_id": scenario,
                                      "template_id": template, "family": family,
                                      "priority_score": 4*impact+3*criticality+2*urgency+base,
                                      "impact": impact, "urgency": urgency,
                                      "criticality": criticality})
                for j in range(count):
                    event = min(88, start + j * rng.randrange(1, 4))
                    obs_id = f"{queue}_obs_{i:03d}_{j:02d}"
                    if j and rng.random() < .10:
                        degradation.append({"source_id": obs_id, "reason": "missing_source_observation"})
                        continue
                    collection = event + rng.randrange(0, 4)
                    detector = collection + rng.randrange(0, 4)
                    available = detector + (rng.randrange(15, 40) if j and rng.random() < .14 else rng.randrange(0, 5))
                    process = available + rng.randrange(0, 3)
                    trace = anchor if rng.random() < (.55 + .05*int(variant[-1])) else None
                    if rng.random() < .06:
                        trace = token(queue + "noisy" + str(rng.randrange(20)))
                    payload = {"source_id": obs_id, "event_minute": event, "collection_minute": collection,
                               "detector_minute": detector, "evidence_available_minute": available,
                               "processing_minute": process, "host": host if rng.random() > .08 else None,
                               "account": account if rng.random() > .08 else None,
                               "indicator": indicator if rng.random() > .30 else None,
                               "trace": trace, "event_type": EVENTS[(j+i) % len(EVENTS)],
                               "severity": max(1, min(5, impact + rng.choice((-1, 0, 0, 1)))),
                               "asset_criticality": criticality}
                    source.append(payload)
                    copies = 2 if rng.random() < .08 else 1
                    for copy in range(copies):
                        alert_id = f"{obs_id}_a{copy}"
                        alert = {k: payload[k] for k in ("source_id", "event_minute", "host", "account",
                            "indicator", "trace", "event_type", "severity", "asset_criticality")}
                        alert.update({"alert_id": alert_id, "evidence_available_minute": available+copy,
                                      "queue_id": queue})
                        alerts.append(alert)
                        ledger.append({"sequence": len(ledger)+1, "artifact_id": alert_id,
                                       "source_id": obs_id, "event_minute": event,
                                       "collection_minute": collection, "detector_minute": detector,
                                       "evidence_available_minute": available+copy,
                                       "processing_minute": process+copy,
                                       "analyst_decision_minute": config["decision_minute"],
                                       "reason": "detector_alert"})
                        truth.append({"alert_id": alert_id, "source_id": obs_id,
                                      "incident_id": incident, "scenario_id": scenario,
                                      "attack_stage": family, "malicious": True})
                    if available > config["decision_minute"]:
                        degradation.append({"source_id": obs_id, "reason": "late_evidence"})
            for j in range(config["benign_observations_per_queue"]):
                event = rng.randrange(0, 89)
                obs_id = f"{queue}_benign_{j:03d}"
                collection = event+rng.randrange(0, 4)
                detector = collection+rng.randrange(0, 4)
                available = detector+rng.randrange(0, 8)
                benign_type = BENIGN[j % len(BENIGN)]
                # Deliberately collide with scenario host/account and sometimes indicators.
                payload = {"source_id": obs_id, "event_minute": event,
                           "collection_minute": collection, "detector_minute": detector,
                           "evidence_available_minute": available, "processing_minute": available+1,
                           "host": f"host_{rng.randrange(12)}", "account": f"acct_{rng.randrange(15)}",
                           "indicator": f"service_{rng.randrange(10)}", "trace": None,
                           "event_type": EVENTS[j % len(EVENTS)],
                           "severity": rng.randrange(1, 5), "asset_criticality": rng.randrange(1, 5)}
                source.append(payload)
                alert_id = obs_id + "_a0"
                alerts.append({**{k: payload[k] for k in ("source_id", "event_minute", "host", "account",
                    "indicator", "trace", "event_type", "severity", "asset_criticality")},
                    "alert_id": alert_id, "evidence_available_minute": available, "queue_id": queue})
                ledger.append({"sequence": len(ledger)+1, "artifact_id": alert_id, "source_id": obs_id,
                               "event_minute": event, "collection_minute": collection,
                               "detector_minute": detector, "evidence_available_minute": available,
                               "processing_minute": available+1,
                               "analyst_decision_minute": config["decision_minute"], "reason": benign_type})
                truth.append({"alert_id": alert_id, "source_id": obs_id,
                              "incident_id": f"{queue}_benign_singleton_{j:03d}",
                              "scenario_id": None, "attack_stage": None, "malicious": False})
            oracle = sorted(incident_rows, key=lambda x: (-x["priority_score"], x["incident_id"]))
            for rank, row in enumerate(oracle, 1):
                row["priority_rank"] = rank
            rng.shuffle(alerts)
            rng.shuffle(source)
            write_lines(out / split / "generated_alerts" / f"{queue}.jsonl", alerts)
            write_lines(out / split / "source_observations" / f"{queue}.jsonl", source)
            write_lines(out / split / "evidence_ledger" / f"{queue}.jsonl", ledger)
            write_lines(out / split / "ground_truth_private" / f"{queue}.jsonl", truth)
            write_lines(out / split / "ground_truth_private" / f"{queue}_priority.jsonl", oracle)
            write_lines(out / split / "degradation" / f"{queue}.jsonl", degradation)
            summary.append({"queue_id": queue, "alerts": len(alerts), "observations": len(source),
                            "incidents": len(oracle), "benign": config["benign_observations_per_queue"]})
        manifest["splits"][split] = summary
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({k: len(v) for k,v in manifest["splits"].items()}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(HERE / "configs/study.json"))
    generate(parser.parse_args().config)
