# Research dashboard

`index.html` is the static aggregate Phase 6 research viewer. It presents saved exploratory metrics and gates; it does not display live alerts or operational SOC state.

`simulation.html` is a separate, scripted playback of fictional events derived from the synthetic MVP trace. Its counters are demonstration activity only. See [SIMULATION_README.md](SIMULATION_README.md) for its controls and data boundary.

## Open locally

Open either HTML file directly, or run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m http.server 8765 --directory dashboard
```

Then visit `http://127.0.0.1:8765/`. The research landing page links to the simulation. No server endpoint, model call, or credential is required by the pages.

## Rebuild

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m src.phase6g_dashboard --root .
.\.venv\Scripts\python.exe -m src.build_simulation_dashboard
```

The first command embeds existing aggregate reports. The second verifies the frozen synthetic trace and embeds curated fictional scenes. Neither rebuilds research metrics.
