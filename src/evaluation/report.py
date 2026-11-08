from __future__ import annotations
import json
def render_report(result):
    return "# Synthetic evaluation report\n\n**SYNTHETIC ONLY — NOT EMPIRICAL.**\n\n"+"````json\n"+json.dumps(result,indent=2,sort_keys=True)+"\n````\n"
