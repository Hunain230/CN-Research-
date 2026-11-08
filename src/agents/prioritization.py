from __future__ import annotations

def prioritize(component,alerts,provider):
    evidence=[e for k in component["alert_keys"] for e in alerts[k]["evidence"]]
    return provider.prioritization(component,evidence)
