"""Fresh Phase 28 scenarios using the frozen Phase 27 simulation infrastructure."""
import json
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHASE27 = HERE.parents[1] / "PHASE27_RECALL_GRAPH" / "v3"
spec = importlib.util.spec_from_file_location("phase27_frozen_generator", PHASE27 / "generate.py")
simulator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simulator)

FAMILIES = ("branch_office_pivot", "token_exchange_abuse", "snapshot_transfer",
            "session_replay", "agent_service_abuse", "remote_admin_execution",
            "database_service_path", "archive_collection", "identity_fallback",
            "control_api_access")


def make_split(split, count, seed, namespace, families, variants, benign_count=48,
               incident_count=25, lineage_delay_mod=11):
    folder = HERE / "datasets" / split
    if folder.exists():
        raise FileExistsError(f"Existing {split} cohort")
    config = json.loads((HERE / "config.json").read_text())
    config = {**config, "namespace": namespace,
              "incidents_per_queue": incident_count,
              "benign_sources_per_queue": benign_count}
    simulator.FAMILIES = families
    manifest = {"schema": config["schema"], "namespace": namespace,
                "seed": seed, "families": list(families), "queues": []}
    for qi in range(count):
        variant = variants[qi % len(variants)]
        q, headers, atoms, expectations, truth, priority, faults, sources = simulator.queue_data(
            config, split, qi, seed + qi * 1031, variant)
        # Field arrival perturbation is label-blind and maintains event/arrival provenance.
        for atom in atoms:
            if atom["field"] in ("auth_session_ref", "network_flow_ref") and atom["value"]:
                key = int(simulator.token(atom["artifact_id"], atom["field"])[-2:], 16)
                if key % lineage_delay_mod == 0:
                    arrival = 101 + key % 29
                    atom["receiver_arrival_timestamp"] = arrival
                    atom["first_observable_timestamp"] = arrival
                    atom["last_update_timestamp"] = arrival
        for kind, data in (("alert_headers", headers), ("evidence_atoms", atoms),
                           ("evidence_expectations", expectations),
                           ("ground_truth_private", truth), ("priority_private", priority),
                           ("faults_private", faults), ("source_records", sources)):
            simulator.write(folder / kind / f"{q}.jsonl", data)
        manifest["queues"].append({"queue_id": q, "variant": variant,
                                   "seed": seed + qi * 1031, "alerts": len(headers)})
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    cfg = json.loads((HERE / "config.json").read_text())
    train = make_split("train", cfg["queues"]["train"], cfg["seeds"]["train"],
                       cfg["namespace"], FAMILIES, ("p28b-train-a", "p28b-train-b"))
    dev = make_split("development", cfg["queues"]["development"], cfg["seeds"]["development"],
                     cfg["namespace"], FAMILIES, ("p28b-dev-a", "p28b-dev-b"))
    (HERE / "datasets/manifest.json").write_text(json.dumps({
        "schema": cfg["schema"], "namespace": cfg["namespace"], "seeds": cfg["seeds"],
        "queues": {"train": train["queues"], "development": dev["queues"]},
        "scenario_variants": {"train": ["p28b-train-a", "p28b-train-b"],
                              "development": ["p28b-dev-a", "p28b-dev-b"]}}, indent=2) + "\n")
    print(json.dumps({"train": len(train["queues"]), "development": len(dev["queues"])}))


if __name__ == "__main__":
    main()
