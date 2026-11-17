"""Isolated receipt-trust counterfactuals; not Phase 24 model selection data."""
import csv
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE = HERE.parent / "PHASE23_TRUST_DOMAINS" / "run_study.py"
spec = importlib.util.spec_from_file_location("phase23_trust", MODULE)
phase23 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phase23)

MODES = ("clean_independent", "shared_controller_corruption", "independent_corruption",
         "compromised_sensor", "false_consistent_receipts", "registry_error",
         "missing_attestation", "delayed_attestation", "two_sensors_one_upstream",
         "correlated_errors")


def scenario(mode, seed):
    # The private truth is a separate Boolean used only by this evaluator.
    alerts = [{"alert_id": f"{seed}_{side}_{i}", "fragment_ref": side,
               "severity": 2, "asset_criticality": 2}
              for side in ("L", "R") for i in range(3)]
    physical_same_incident = mode in ("clean_independent", "missing_attestation",
                                       "delayed_attestation", "two_sensors_one_upstream")
    claims = []
    receipts = [{"source_record_id": "parent", "sensor": "endpoint", "origin_event_id": "parent_event",
                 "observed_parent_event_ids": [], "observed_fragment_ref": "L"}]
    registry = {}
    for sensor, source, child in (("auth", "auth_source", "child_auth"),
                                  ("network", "network_source", "child_network")):
        claims.append({"claim_id": source, "sensor": sensor, "source_record_id": source,
                       "origin_event_id": child, "parent_event_id": "parent_event",
                       "left_fragment_ref": "L", "right_fragment_ref": "R"})
        receipts.append({"source_record_id": source, "sensor": sensor, "origin_event_id": child,
                         "observed_parent_event_ids": ["parent_event"],
                         "observed_fragment_ref": "R"})
        registry[source] = f"root_{sensor}"
    if mode in ("shared_controller_corruption", "two_sensors_one_upstream", "correlated_errors"):
        registry["network_source"] = registry["auth_source"]
    if mode == "registry_error":
        # Two corrupt receipts originate from one controller; registry falsely splits it.
        registry["network_source"] = "incorrectly_split_root"
    if mode in ("missing_attestation", "delayed_attestation"):
        registry.pop("network_source")
    return alerts, claims, receipts, registry, physical_same_incident


def main():
    output = []
    for mode in MODES:
        for seed in range(4):
            alerts, claims, receipts, registry, physical_same = scenario(mode, seed)
            groups, decisions, _ = phase23.decide_domains(alerts, claims, receipts, registry)
            accepted = any(d["decision"] == "accept" for d in decisions)
            false_pairs = 9 if accepted and not physical_same else 0
            output.append({"mode": mode, "seed": seed, "accepted": accepted,
                           "false_pairs": false_pairs,
                           "reason": next(d["reason"] for d in decisions if d["decision"] != "reject"),
                           "physical_same_incident_evaluator_only": physical_same})
    with (HERE / "PHASE24_TRUST_STRESS.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    print({mode: sum(x["false_pairs"] for x in output if x["mode"] == mode) for mode in MODES})


if __name__ == "__main__":
    main()
