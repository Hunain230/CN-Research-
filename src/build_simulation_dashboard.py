"""Build a local, self-contained fictional dashboard from the frozen MVP event trace."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "outputs/mvp/mvp-demo-20261112-v2/dashboard_events.json"
RUN_MANIFEST = TRACE.with_name("run_manifest.json")
TEMPLATE = ROOT / "dashboard/simulation_template.html"
OUTPUT = ROOT / "dashboard/simulation.html"
MANIFEST = ROOT / "dashboard/simulation_manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_scenarios(events: list[dict]) -> dict[str, list[dict]]:
    def select(org: str, alerts: set[str], reasons: set[str]) -> list[dict]:
        selected = []
        for event in events:
            if event["org_key"] != org:
                continue
            kind = event["kind"]
            if kind == "alert_received" and event["alert_key"] in alerts:
                selected.append(dict(event))
            elif kind == "correlation_decision" and event["reason"] in reasons and event["left"] in alerts and event["right"] in alerts:
                selected.append(dict(event))
            elif kind == "component_ranked" and set(event["alert_keys"]).issubset(alerts):
                selected.append(dict(event))
        return selected

    clean = select(
        "org-mvp-01",
        {f"org-mvp-01-a{i}" for i in (1, 2, 3, 6)},
        {"shared_signal_within_window", "no_supported_match"},
    )
    # A display-only clean what-if: the frozen trace's linked group is marked
    # REVIEW because of uncertainty outside this selected scene. Keep the
    # evidence/score, but change its display status to show a clean path.
    for event in clean:
        if event["kind"] == "component_ranked" and len(event["alert_keys"]) > 1:
            event["status"] = "PASS"
            event["review_reason"] = None
            event["scripted_variant"] = True
    missing = select(
        "org-mvp-01",
        {"org-mvp-01-a1", "org-mvp-01-a5"},
        {"missing_evidence"},
    )
    conflict = select(
        "org-mvp-02",
        {"org-mvp-02-a1", "org-mvp-02-a4"},
        {"conflicting_evidence"},
    )
    scenarios = {"clean": clean, "missing": missing, "conflict": conflict}
    for name, stream in scenarios.items():
        if not stream or not any(e["kind"] == "component_ranked" for e in stream):
            raise ValueError(f"Incomplete {name} scenario")
        for step, event in enumerate(stream, 1):
            event["step"] = step
    return scenarios


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    manifest = json.loads(RUN_MANIFEST.read_text(encoding="utf-8"))
    if sha256(TRACE) != manifest["outputs_sha256"]["dashboard_events.json"]:
        raise ValueError("MVP event trace does not match its frozen run manifest")
    trace = json.loads(TRACE.read_text(encoding="utf-8"))
    if trace.get("classification") != "synthetic_end_to_end_demo_not_empirical":
        raise ValueError("Event trace is not classified as synthetic")
    events = trace["events"]
    allowed = {
        "step", "kind", "org_key", "alert_key", "evidence_count", "decision",
        "evidence_refs", "left", "right", "reason", "alert_keys", "component_key",
        "rank", "review_reason", "score", "status", "verification",
    }
    if len(events) != 30 or any(set(e) - allowed for e in events):
        raise ValueError("Unexpected or unsafe event schema")
    if any(not e["org_key"].startswith("org-mvp-") for e in events):
        raise ValueError("Nonfictional organization key")
    if any(not ref.startswith("demo-") for e in events for ref in e.get("evidence_refs", [])):
        raise ValueError("Nonfictional evidence reference")
    scenarios = build_scenarios(events)
    payload = {
        "classification": "fictional_scripted_simulation_not_research_metrics",
        "source_run": manifest["run_id"],
        "scenarios": scenarios,
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8")
    if html.count("__DEMO_DATA__") != 1:
        raise ValueError("Template must contain one data placeholder")
    OUTPUT.write_text(html.replace("__DEMO_DATA__", encoded), encoding="utf-8")
    record = {
        "classification": payload["classification"],
        "command": ".\\.venv\\Scripts\\python.exe -m src.build_simulation_dashboard",
        "source_run": manifest["run_id"],
        "source_trace_sha256": sha256(TRACE),
        "template_sha256": sha256(TEMPLATE),
        "output_sha256": sha256(OUTPUT),
        "scenario_event_counts": {name: len(stream) for name, stream in scenarios.items()},
        "external_calls": 0,
    }
    MANIFEST.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "synthetic_dashboard_built", "scenarios": record["scenario_event_counts"], "output": str(OUTPUT.relative_to(ROOT))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
