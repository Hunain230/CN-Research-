# Task 5 Live Dashboard Simulation

## Goal

Build a polished interactive dashboard demo that simulates alerts arriving and moving through correlate, prioritize, verify, and review stages. This is a software demonstration, not an operational SOC and not a research result.

## Required behavior

1. Inspect the current `dashboard/index.html`, `dashboard/guide_rerun_v2.html`, `dashboard/README.md`, and existing aggregate schemas before modifying the dashboard.
2. Preserve the existing aggregate research report view. Add a clearly separated “Synthetic live demo” mode or page.
3. Generate deterministic fictional events from a fixed seed. Never stream from raw GUIDE data, restricted derived data, actual alert identifiers, evaluator stores, or a real model/API.
4. Permanently display a high-visibility label such as **SIMULATION — FICTIONAL EVENTS — NOT LIVE SOC DATA** while demo mode is active. Keep this label visible on mobile and desktop.
5. Simulate an alert feed, grouping decisions, priority queue, verifier outcomes, review routing, and basic activity counters. Include controls for start, pause, reset, playback speed, and switching between clean, missing-evidence, and conflicting-evidence scenarios.
6. Show why an item was linked or sent for review using fictional evidence references. Show uncertainty and never imply autonomous containment or closure.
7. Keep simulation events separate from research metrics. Do not modify frozen metrics, reports, manifests, or experiment files.
8. Add responsive layout, keyboard-accessible controls, readable contrast, empty/error states, and a resettable deterministic demo.
9. If the project has no frontend framework, prefer a small static HTML/CSS/JavaScript implementation. Do not add dependencies unless clearly necessary.
10. Run the local dashboard, exercise all controls and scenarios, check the browser console, and capture a short verification record. Use the available browser/UI tools when appropriate.

## Required result

- Updated dashboard entry point and supporting assets.
- `dashboard/SIMULATION_README.md` describing that events are fictional, controls, and local run instructions.
- `submission/DASHBOARD_VERIFICATION.md` recording viewports, tested interactions, and any known limits.

## Acceptance checklist

- [ ] Synthetic demo is visually and textually unmistakable as simulated.
- [ ] No real or restricted row-level data reaches the demo.
- [ ] No API/model/network calls are used by simulation mode.
- [ ] All controls work and reset returns to the same seeded starting state.
- [ ] Research metrics remain separate from simulated counters.
- [ ] Dashboard makes no deployment, certification, or performance claims.

