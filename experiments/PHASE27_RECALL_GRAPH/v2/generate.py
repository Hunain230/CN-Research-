"""Fresh graph-first SOC simulation; private incident membership is evaluator-only."""
import hashlib
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = ("host", "account", "indicator", "process_tree_ref", "auth_session_ref",
          "network_flow_ref", "event_type", "severity", "asset_criticality")
FAMILIES = ("credential_access", "lateral_path", "persistence_chain", "staged_transfer",
            "cloud_identity", "remote_execution", "service_abuse", "data_collection",
            "control_channel", "privilege_path")
EVENTS = ("auth", "process", "network", "file", "service", "identity")


def token(*parts):
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:20]


def write(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for value in values:
            stream.write(json.dumps(value, sort_keys=True) + "\n")


def queue_data(cfg, split, index, seed, variant):
    rng = random.Random(seed)
    q = f"{cfg['namespace']}_{split}_q{index:03d}"
    headers, atoms, expectations, truth, priority, faults = [], [], [], [], [], []
    source_records = []
    arrivals = []
    controller_pool = [token(q, "controller", i) for i in range(12)]

    def observation(incident, event_index, segment, values, event, arrival, controller,
                    family, mode, duplicate=False, correction=None):
        sid = token(q, "source", incident, event_index, segment)
        aid = token(sid, "alert", int(duplicate))
        header = {"alert_id": aid, "source_id": sid, "queue_id": q,
                  "event_minute": event, "evidence_available_minute": arrival}
        headers.append(header)
        source_records.append({"source_id": sid, "source_event_id": sid,
                               "source_system": "simulated_" + family,
                               "sensor_identity": EVENTS[event_index % len(EVENTS)],
                               "controller_root": controller, "receiver_arrival_timestamp": arrival,
                               "duplicate_of": token(sid, "alert", 0) if duplicate else None})
        truth.append({"alert_id": aid, "incident_id": incident})
        for field in FIELDS:
            value = values.get(field)
            field_arrival = arrival
            if field in ("host", "account") and value is not None and mode == "late_context" and segment > 0:
                field_arrival = 101 + rng.randrange(0, 31)
            if value is None:
                claim = "unavailable" if rng.random() < .65 else "pending"
            else:
                claim = "pending"
            expectations.append({"artifact_id": aid, "field": field,
                                 "declared_minute": min(arrival, 100),
                                 "availability_claim": claim, "source_event_id": sid})
            if value is not None:
                atoms.append({"artifact_id": aid, "field": field, "value": value,
                              "original_source_observation_id": sid,
                              "source_event_id": sid, "source_system": "simulated_" + family,
                              "sensor_identity": EVENTS[event_index % len(EVENTS)],
                              "evidence_type": field, "event_timestamp": event,
                              "receiver_arrival_timestamp": field_arrival,
                              "first_observable_timestamp": field_arrival,
                              "last_update_timestamp": field_arrival,
                              "observation_kind": "derived" if duplicate else "original",
                              "parent_observation_ids": [token(sid, "alert", 0)] if duplicate else [],
                              "duplicated": duplicate, "independence_verified": not duplicate,
                              "contradictory_information": False, "version": 0,
                              "controller_root": controller})
                if correction and field == "host":
                    atoms.append({**atoms[-1], "value": correction,
                                  "receiver_arrival_timestamp": 106,
                                  "first_observable_timestamp": 106,
                                  "last_update_timestamp": 106,
                                  "contradictory_information": True, "version": 1})
        arrivals.append((sid, arrival))
        return aid, sid

    for ii in range(cfg["incidents_per_queue"]):
        family = FAMILIES[(ii + index * 3) % len(FAMILIES)]
        incident = token(q, "incident", ii)
        mode = ("full", "dominant", "balanced", "late_context", "shared_controller",
                "balanced")[(ii + index) % 6]
        size = rng.randrange(8, 13)
        if mode == "full":
            split_points = [size]
        elif mode == "dominant":
            split_points = [size - 1, 1]
        else:
            split_points = [size // 2, size - size // 2]
        host = f"host_{ii//2}" if ii < 12 else f"host_{rng.randrange(16)}"
        account = f"acct_{ii//2}" if ii < 12 else f"acct_{rng.randrange(20)}"
        impact = rng.randrange(1, 6)
        criticality = rng.randrange(1, 6)
        priority.append({"incident_id": incident, "family": family,
                         "variant": variant, "priority_score": 4 * impact + 2 * criticality + rng.randrange(1, 8)})
        faults.append({"incident_id": incident, "family": family, "mode": mode,
                       "fragment_sizes": split_points})
        bridge_auth = token(q, "bridge_auth", ii)
        bridge_flow = token(q, "bridge_flow", ii)
        start = rng.randrange(4, 55)
        at = 0
        for segment, count in enumerate(split_points):
            tree = token(q, "process", ii, segment)
            for j in range(count):
                event = min(96, start + 3 * at + rng.randrange(0, 3))
                arrival = min(100, event + rng.randrange(0, 5))
                missing_segment = segment > 0 and mode in ("balanced", "late_context", "shared_controller")
                values = {"host": None if missing_segment else host,
                          "account": None if missing_segment else account,
                          "indicator": token("service", ii % 9),
                          "process_tree_ref": tree,
                          "auth_session_ref": bridge_auth if len(split_points) > 1 and
                              ((segment == 0 and j == count - 1) or (segment == 1 and j == 0)) else None,
                          "network_flow_ref": bridge_flow if len(split_points) > 1 and
                              ((segment == 0 and j == max(0, count - 2)) or
                               (segment == 1 and j == min(1, count - 1))) else None,
                          "event_type": EVENTS[(at + ii) % len(EVENTS)],
                          "severity": max(1, min(5, impact + rng.choice((-1, 0, 1)))),
                          "asset_criticality": criticality}
                if mode == "late_context" and missing_segment:
                    values["host"], values["account"] = host, account
                if rng.random() < .06:
                    values["network_flow_ref"] = None
                controller = controller_pool[ii % 12] if mode == "shared_controller" else token(q, "root", ii, at)
                aid, sid = observation(incident, at, segment, values, event, arrival,
                                       controller, family, mode)
                if rng.random() < .08:
                    observation(incident, at, segment, values, event, min(100, arrival + 1),
                                controller, family, mode, duplicate=True)
                at += 1

    # Interleaved benign activity, including shared-reference and delayed-host decoys.
    benign = []
    for bi in range(cfg["benign_sources_per_queue"]):
        incident = token(q, "benign", bi)
        family = "routine_activity"
        group = bi // 2
        host = f"host_{group % 6}" if bi % 2 == 0 else f"host_{(group + 1) % 6}"
        account = f"acct_{group % 6}"
        event = rng.randrange(5, 88)
        arrival = min(100, event + rng.randrange(0, 4))
        delayed = bi % 12 == 1
        values = {"host": host, "account": account,
                  "indicator": token("benign_service", bi % 8),
                  "process_tree_ref": token(q, "benign_process", group) if bi % 12 in (0, 1) else None,
                  "auth_session_ref": token(q, "benign_auth", group) if bi % 2 < 2 else None,
                  "network_flow_ref": token(q, "benign_flow", group) if bi % 8 in (0, 1) else None,
                  "event_type": EVENTS[bi % len(EVENTS)], "severity": rng.randrange(1, 5),
                  "asset_criticality": rng.randrange(1, 5)}
        if delayed:
            values["host"] = f"host_{(group + 1) % 6}"
        controller = controller_pool[group % 12]
        aid, sid = observation(incident, bi, 1 if delayed else 0, values, event, arrival,
                               controller, family, "late_context" if delayed else "benign",
                               correction="definitive_other_host" if delayed else None)
        benign.append((aid, sid))
    # Deliberate common-mode false dual-witness pairs are not private labels in inference.
    for bi in range(0, min(12, len(benign)), 2):
        a, b = benign[bi], benign[bi + 1]
        ref = token(q, "correlated_collision", bi)
        for aid in (a[0], b[0]):
            for field in ("auth_session_ref", "network_flow_ref"):
                old = next((x for x in atoms if x["artifact_id"] == aid and x["field"] == field), None)
                if old:
                    old["value"] = ref
    private = {x["incident_id"] for x in priority}
    assert len(private) == cfg["incidents_per_queue"]
    return q, headers, atoms, expectations, truth, priority, faults, source_records


def generate():
    cfg = json.loads((HERE / "config.json").read_text())
    base = HERE / "datasets"
    if base.exists():
        raise FileExistsError("Phase 27 data already exists")
    manifest = {"schema": cfg["schema"], "namespace": cfg["namespace"],
                "seeds": cfg["seeds"], "queues": {}}
    for split in ("train", "development"):
        manifest["queues"][split] = []
        for qi in range(cfg["queues"][split]):
            variant = "v27-train-a" if split == "train" and qi % 2 == 0 else \
                      "v27-train-b" if split == "train" else \
                      "v27-dev-a" if qi % 2 == 0 else "v27-dev-b"
            seed = cfg["seeds"][split] + qi * 1009
            q, headers, atoms, expectations, truth, priority, faults, sources = queue_data(
                cfg, split, qi, seed, variant)
            folder = base / split
            for kind, values in (("alert_headers", headers), ("evidence_atoms", atoms),
                                 ("evidence_expectations", expectations),
                                 ("ground_truth_private", truth), ("priority_private", priority),
                                 ("faults_private", faults), ("source_records", sources)):
                write(folder / kind / f"{q}.jsonl", values)
            manifest["queues"][split].append({"queue_id": q, "variant": variant,
                                                "seed": seed, "alerts": len(headers)})
    (base / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: len(v) for k, v in manifest["queues"].items()}))


if __name__ == "__main__":
    generate()
