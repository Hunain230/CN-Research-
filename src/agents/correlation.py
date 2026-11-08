from __future__ import annotations

def correlate(pair,alerts,provider):
    left,right=alerts[pair["left"]],alerts[pair["right"]]
    le=[e for a in (left,right) for e in a["evidence"]]
    return provider.correlation(pair,le)
