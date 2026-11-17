"""Generate one post-selection, scenario-disjoint Phase 27 locked cohort."""
import json
from pathlib import Path

import generate as simulator

HERE = Path(__file__).resolve().parent
FAMILIES = ("container_escape", "supply_chain_update", "federated_login",
            "database_exfiltration", "scheduled_persistence", "api_key_abuse",
            "cross_region_control", "endpoint_tamper", "backup_access", "service_impersonation")


def main():
    folder = HERE / "datasets/locked_test"
    if folder.exists():
        raise FileExistsError("Locked cohort already exists")
    config = json.loads((HERE / "config.json").read_text())
    config = {**config, "namespace": "phase27k", "incidents_per_queue": 28,
              "benign_sources_per_queue": 52}
    simulator.FAMILIES = FAMILIES
    manifest = {"namespace": config["namespace"], "seed": 273571,
                "scenario_families": FAMILIES, "queues": []}
    for qi in range(30):
        variant = ("h_path_swap", "h_delayed_lineage", "h_dense_benign")[qi % 3]
        q, headers, atoms, expectations, truth, priority, faults, sources = simulator.queue_data(
            config, "locked_test", qi, 273571 + qi * 1301, variant)
        # Receiver-only perturbation changes the availability pattern without using truth.
        for atom in atoms:
            if atom["field"] in ("auth_session_ref", "network_flow_ref") and atom["value"]:
                key = int(simulator.token(atom["artifact_id"], atom["field"])[-2:], 16)
                if key % (5 if qi % 3 == 1 else 9) == 0:
                    atom["receiver_arrival_timestamp"] = 101 + key % 31
                    atom["first_observable_timestamp"] = atom["receiver_arrival_timestamp"]
                    atom["last_update_timestamp"] = atom["receiver_arrival_timestamp"]
        for kind, values in (("alert_headers", headers), ("evidence_atoms", atoms),
                             ("evidence_expectations", expectations),
                             ("ground_truth_private", truth), ("priority_private", priority),
                             ("faults_private", faults), ("source_records", sources)):
            simulator.write(folder / kind / f"{q}.jsonl", values)
        manifest["queues"].append({"queue_id": q, "variant": variant,
                                   "seed": 273571 + qi * 1301, "alerts": len(headers)})
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"queues": len(manifest["queues"]), "namespace": manifest["namespace"]}))


if __name__ == "__main__":
    main()
