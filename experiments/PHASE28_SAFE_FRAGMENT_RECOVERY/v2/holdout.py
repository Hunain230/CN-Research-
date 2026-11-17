"""One post-selection holdout with independent false dual-lineage stress."""
import json
import sys
from pathlib import Path

from generate import HERE, PHASE27, make_split, simulator

FAMILIES = ("mobile_identity_path", "serverless_control", "replica_exfiltration",
            "certificate_replay", "telemetry_agent_abuse", "remote_maintenance",
            "warehouse_access", "snapshot_collection", "privileged_recovery",
            "regional_control_access")


def inject_independent_false_witnesses(queue, benign_count=60):
    """Four unrelated benign events get two independent-looking false paths."""
    folder = HERE / "datasets/locked_test"
    source_path = folder / "source_records" / f"{queue}.jsonl"
    atom_path = folder / "evidence_atoms" / f"{queue}.jsonl"
    sources = simulator.read(source_path) if hasattr(simulator, "read") else [
        json.loads(x) for x in source_path.read_text().splitlines()]
    atoms = [json.loads(x) for x in atom_path.read_text().splitlines()]
    benign = sources[-benign_count:]
    chosen = benign[:4]
    assert len({x["source_id"] for x in chosen}) == 4
    ids = {x["source_id"] for x in chosen}
    for i, record in enumerate(chosen):
        record["controller_root"] = simulator.token(queue, "independent_false_root", i)
    shared = simulator.token(queue, "independent_false_lineage")
    for atom in atoms:
        if atom["source_event_id"] not in ids:
            continue
        if atom["field"] in ("auth_session_ref", "network_flow_ref"):
            atom["value"] = shared
        elif atom["field"] == "account" and atom["receiver_arrival_timestamp"] <= 100:
            atom["value"] = "shared_visible_account"
        elif atom["field"] == "host" and atom["receiver_arrival_timestamp"] <= 100:
            atom["value"] = "shared_visible_host"
    simulator.write(source_path, sources)
    simulator.write(atom_path, atoms)
    return {"queue_id": queue, "source_ids": sorted(ids),
            "injected_false_witness_sources": 4, "controller_roots": 4,
            "later_host_evidence_retained": True}


def main():
    folder = HERE / "datasets/locked_test"
    if folder.exists():
        raise FileExistsError("Locked cohort already exists")
    manifest = make_split("locked_test", 30, 282251, "phase28h", FAMILIES,
                          ("p28-h-independent", "p28-h-delay", "p28-h-dense"),
                          benign_count=60, incident_count=27, lineage_delay_mod=7)
    injections = [inject_independent_false_witnesses(x["queue_id"]) for x in manifest["queues"]]
    (folder / "injection_manifest.json").write_text(json.dumps(injections, indent=2) + "\n")
    print(json.dumps({"queues": len(manifest["queues"]), "independent_false_challenges": len(injections)}))


if __name__ == "__main__":
    main()
