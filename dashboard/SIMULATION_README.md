# Synthetic live demo

The dashboard's **SIMULATION — FICTIONAL EVENTS — NOT LIVE SOC DATA** banner remains visible throughout playback. Its scenes are scripted presentations built from `outputs/mvp/mvp-demo-20261112-v2/dashboard_events.json`, a hand-authored fictional workflow trace. The clean scene includes a display-only PASS status variant to isolate the clear path. These scenes are not new model predictions, evaluator results, or real alert samples.

## Controls

- **Scenario:** Clean evidence, missing evidence, or conflicting evidence. Changing it pauses playback and resets every counter and panel.
- **Start:** Plays the selected scene. At the end, Start replays it from the beginning.
- **Pause:** Stops the timer at the current step. Start resumes.
- **Reset:** Returns to step zero with the same deterministic events and empty panels.
- **Playback speed:** Slow, normal, or fast. A speed change during playback reschedules the remaining events.

The feed shows fictional arrivals. The correlation panel shows LINK, NO_LINK, or UNSURE decisions with fictional evidence references. The queue shows relative, uncalibrated stub scores and verifier outcomes. The review panel explains missing or conflicting evidence and makes no autonomous containment or closure decision. Counters count events already displayed; they are never research metrics.

## Open and rebuild

From the project root:

```powershell
.\.venv\Scripts\python.exe -m http.server 8765 --directory dashboard
```

Open `http://127.0.0.1:8765/simulation.html`, or open `dashboard/simulation.html` directly. To regenerate from the frozen synthetic event trace:

```powershell
.\.venv\Scripts\python.exe -m src.build_simulation_dashboard
```

`src.build_simulation_dashboard` checks the trace against its MVP manifest, rejects unexpected fields or non-fictional reference prefixes, and embeds only the selected fictional events in the static HTML. `dashboard/simulation_manifest.json` records the source, template, and output hashes. Playback is browser-local; it does not fetch raw GUIDE rows, evaluator stores, or model responses and makes no API or external network request. The aggregate research viewer remains at `dashboard/index.html`.
