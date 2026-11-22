# CPV Recorded Evidence Console

A local research instrument for replaying the Phase 33 locked-test evidence,
walking reviewers through the implemented CPV pipeline, and starting the
repository's fixed Phase 31 / Phase 32 development comparison. This is not a
SOC product or an external event-ingestion service.

## Start

From the repository root:

```powershell
python -m pip install -r dashboard/requirements.txt
cd dashboard/frontend
npm install
npm run dev
```

In a second terminal, from the repository root:

```powershell
python -m uvicorn dashboard.backend.app:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:5173>. Vite proxies `/api` and `/ws` to FastAPI. For a
separate frontend origin, set `VITE_API_BASE` at build time and set
`CPV_ALLOWED_ORIGINS` to the exact origin before starting the API.

## Modes

- **Recorded replay:** reads the saved Phase 33 baseline or candidate artifacts
  and the receiver-visible locked-test input. Rows advance in saved file order;
  chart buckets use the row's recorded event minute. These fields are not
  monotonic, so the playhead can move backwards on the chart?s minute axis.
- **Guided walkthrough:** reads the component labels, purposes, and source
  names from `GET /api/architecture`, then replays actual saved queue rows. It
  adds no simulated events.
- **Experiment run:** starts the real Phase 31 baseline and Phase 32 +1 / +2
  functions on the fixed 10-queue development split (`seed=31102`). The WebSocket
  and persisted event endpoint expose lifecycle events such as queue completion;
  they do not stream predictions per sample.

Accepted relationship markers are shown only after the saved endpoint rows are
reached and are placed using their joined `event_minute` values. Rejected
relationships are static handoff items: their saved record contains a reason
and relationship token, but no endpoint IDs or event time. The reviewer mark is
local to the open browser session and is not written to research artifacts.
The saved schema does not contain an explicit item-level abstention status.

The data contract and known gaps are documented in
[`docs/DATA_CONTRACT.md`](../docs/DATA_CONTRACT.md). Private evaluator truth is
never included in Recorded replay or its export. The Phase 33 result is limited
to the controlled synthetic holdout; development run results are not independent
confirmation.

## Evidence export

The replay export is assembled from the validated API response and includes the
selected queue name, model arm, source artifact paths, saved prediction,
saved decisions, receiver-visible alert rows, claims, and evidence ledger.
No evaluator-only files or browser-generated sample values are added.

## API retained for the rebuilt application

- `GET /api/health`
- `GET /api/replay/{baseline|candidate}/queues`
- `GET /api/replay/{baseline|candidate}/{queue_id}`
- `GET /api/architecture`
- `POST /api/runs`, `GET /api/runs`, `GET /api/runs/{id}`
- `GET /api/runs/{id}/events?after=<sequence>` and `/ws`
- `POST /api/runs/{id}/{pause|resume|stop}`
- `GET /api/runs/{id}/export`

Local run records and files are stored under `dashboard/runtime/` and are not
source-controlled.

## Frontend checks

```powershell
cd dashboard/frontend
npm run lint
npm run test
npm run build
```
