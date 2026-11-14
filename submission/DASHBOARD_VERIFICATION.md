# Dashboard simulation verification

**2026-11-13.** Rebuilt the static fictional playback with `python -m src.build_simulation_dashboard`. The build verified the frozen MVP trace hash and wrote three scenes with 9 clean, 4 missing-evidence, and 4 conflicting-evidence events. The [simulation manifest](../dashboard/simulation_manifest.json) records source, template, and output SHA-256 values and zero external calls.

The generated page passed an inline JavaScript syntax check with Node. A source check found no `fetch`, `XMLHttpRequest`, or `WebSocket` calls in the playback script. The local HTTP server returned **200**, `text/html`, and the expected 19,374-byte page for `/simulation.html`. The page retains a prominent fictional-events banner and separates activity counters from empirical metrics. The [root README](../README.md) gives the local launch command. The playback has Start, Pause, Reset, speed, scenario changes, and clean/missing/conflict scenes; its counters are fictional activity, not research metrics.

Interactive browser QA could not be completed because the available browser-control environment failed to attach/open the local page. The control behavior has therefore been reviewed in source and syntax checks, but has **not** been verified by clicking through the page in a browser. This limitation remains open for manual submission review.
