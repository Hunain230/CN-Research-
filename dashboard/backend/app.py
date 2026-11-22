from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import os
import sqlite3
import sys
import threading
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
PHASE31 = ROOT / "experiments/PHASE31_CONTROLLED_SOC_EVIDENCE"
PHASE32 = ROOT / "experiments/PHASE32_SAFE_EVIDENCE_RECOVERY"
PHASE33 = ROOT / "experiments/PHASE33_FROZEN_GENERALIZATION"
RUNTIME = ROOT / "dashboard/runtime"
RUNS = RUNTIME / "runs"
DB = RUNTIME / "command_center.sqlite3"
ARMS = ("baseline", "candidate_bonus1", "candidate_bonus2")

for folder in (RUNS,):
    folder.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="CPV Recorded Evidence Console", version="2.0.0")
cors_origins = [origin.strip() for origin in os.environ.get(
    "CPV_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)

_controls: dict[str, dict[str, Any]] = {}
_controls_lock = threading.Lock()
_sockets: set[WebSocket] = set()
_socket_lock = threading.Lock()
_event_loop: asyncio.AbstractEventLoop | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB, timeout=20)
    db.row_factory = sqlite3.Row
    return db


def init_db() -> None:
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS runs(
            id TEXT PRIMARY KEY, status TEXT NOT NULL, created_at TEXT NOT NULL,
            started_at TEXT, ended_at TEXT, config TEXT NOT NULL, result TEXT,
            artifact_dir TEXT, error TEXT
        );
        CREATE TABLE IF NOT EXISTS run_events(
            seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
            at TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL
        );
        """)


init_db()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def phase33_runs() -> dict[str, dict[str, list[dict[str, Any]]]]:
    artifacts = PHASE33 / "artifacts"
    result: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for arm in ("baseline", "candidate"):
        result[arm] = {
            "predictions": read_jsonl(artifacts / f"{arm}_predictions.jsonl"),
            "decisions": read_jsonl(artifacts / f"{arm}_decisions.jsonl"),
        }
    return result


def phase33_replay_paths(arm: str, queue_id: str | None = None) -> dict[str, str]:
    artifacts = PHASE33 / "artifacts"
    paths = {
        "predictions": artifacts / f"{arm}_predictions.jsonl",
        "decisions": artifacts / f"{arm}_decisions.jsonl",
    }
    if queue_id is not None:
        visible = PHASE33 / "dataset/receiver_visible/locked_test"
        paths.update({
            "alerts": visible / "alerts" / f"{queue_id}.jsonl",
            "claims": visible / "claims" / f"{queue_id}.jsonl",
            "ledger": visible / "evidence_ledger" / f"{queue_id}.jsonl",
        })
    return {key: path.relative_to(ROOT).as_posix() for key, path in paths.items()}


def require_replay_artifacts(paths: dict[str, str]) -> None:
    for relative in paths.values():
        if not (ROOT / relative).is_file():
            raise HTTPException(503, f"Missing saved replay artifact: {relative}")


def run_row(row: sqlite3.Row) -> dict[str, Any]:
    value = dict(row)
    for key in ("config", "result"):
        value[key] = json.loads(value[key]) if value.get(key) else None
    return value


def emit(run_id: str, kind: str, payload: dict[str, Any]) -> None:
    message = {"runId": run_id, "kind": kind, "at": utc_now(), **payload}
    with connect() as db:
        db.execute("INSERT INTO run_events(run_id,at,kind,payload) VALUES(?,?,?,?)",
                   (run_id, message["at"], kind, json.dumps(message, separators=(",", ":"))))
    loop = _event_loop
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast(message), loop)


async def broadcast(message: dict[str, Any]) -> None:
    with _socket_lock:
        sockets = list(_sockets)
    stale = []
    for socket in sockets:
        try:
            await socket.send_json(message)
        except Exception:
            stale.append(socket)
    if stale:
        with _socket_lock:
            for socket in stale:
                _sockets.discard(socket)


@app.on_event("startup")
async def register_loop() -> None:
    global _event_loop
    _event_loop = asyncio.get_running_loop()


@app.get("/api/health")
def health() -> dict[str, Any]:
    paths = {
        "phase31_model": PHASE31 / "model.py",
        "phase32_model": PHASE32 / "model.py",
        "phase33_candidate_predictions": PHASE33 / "artifacts/candidate_predictions.jsonl",
        "phase33_candidate_decisions": PHASE33 / "artifacts/candidate_decisions.jsonl",
        "phase33_baseline_predictions": PHASE33 / "artifacts/baseline_predictions.jsonl",
        "phase33_baseline_decisions": PHASE33 / "artifacts/baseline_decisions.jsonl",
        "development_manifest": PHASE31 / "dataset/development_manifest.json",
    }
    return {"status": "ready" if all(path.is_file() for path in paths.values()) else "degraded",
            "checkedAt": utc_now(),
            "checks": {key: path.is_file() for key, path in paths.items()},
            "lockedTestReplay": "recorded_artifacts_only"}


@app.get("/api/replay/{arm}/queues")
def replay_queues(arm: str) -> dict[str, Any]:
    if arm not in ("baseline", "candidate"):
        raise HTTPException(404, "Unknown Phase 33 arm")
    require_replay_artifacts(phase33_replay_paths(arm))
    data = phase33_runs()[arm]
    decisions = {row["queue_id"]: row for row in data["decisions"]}
    return {"arm": arm, "classification": "recorded_synthetic_holdout_replay",
            "queues": [
                {"queueId": row["queue_id"],
                 "alerts": len(read_jsonl(PHASE33 / "dataset/receiver_visible/locked_test/alerts" / f"{row['queue_id']}.jsonl")),
                 "groups": len(row["groups_ranked"]), "accepted": len(decisions[row["queue_id"]]["accepted"]),
                 "visibleClaims": decisions[row["queue_id"]].get("visible_claims", 0)}
                for row in data["predictions"]]}


@app.get("/api/replay/{arm}/{queue_id}")
def replay_queue(arm: str, queue_id: str) -> dict[str, Any]:
    if arm not in ("baseline", "candidate"):
        raise HTTPException(404, "Unknown Phase 33 arm")
    require_replay_artifacts(phase33_replay_paths(arm))
    data = phase33_runs()[arm]
    pred = next((x for x in data["predictions"] if x["queue_id"] == queue_id), None)
    decisions = next((x for x in data["decisions"] if x["queue_id"] == queue_id), None)
    if pred is None or decisions is None:
        raise HTTPException(404, "Queue is not part of this recorded split")
    artifact_paths = phase33_replay_paths(arm, queue_id)
    require_replay_artifacts(artifact_paths)
    visible = PHASE33 / "dataset/receiver_visible/locked_test"
    alert_path = visible / "alerts" / f"{queue_id}.jsonl"
    claims_path = visible / "claims" / f"{queue_id}.jsonl"
    ledger_path = visible / "evidence_ledger" / f"{queue_id}.jsonl"
    alerts = read_jsonl(alert_path)
    claims = read_jsonl(claims_path)
    ledger = read_jsonl(ledger_path)
    group_by_alert = {alert_id: i + 1 for i, group in enumerate(pred["groups_ranked"]) for alert_id in group}
    return {"arm": arm, "classification": "recorded_synthetic_holdout_replay",
            "queueId": queue_id, "prediction": pred, "decisions": decisions,
            "alerts": alerts, "claims": claims, "ledger": ledger,
            "groupByAlert": group_by_alert,
            "evidence": {"alertRows": len(alerts), "claimRows": len(claims),
                         "ledgerRows": len(ledger), "source": "receiver_visible only",
                         "artifactPaths": artifact_paths}}


@app.get("/api/architecture")
def architecture() -> dict[str, Any]:
    return {"classification": "code-grounded pipeline; measured holdout uses deterministic models",
            "components": [
                {"id": "input", "label": "Receiver-visible inputs", "source": "Phase 31/33 receiver_visible bundle",
                 "purpose": "Alerts, claims and evidence availability ledger; private truth stays evaluator-side."},
                {"id": "correlate", "label": "C · correlate", "source": "Phase 16 provenance reconstruction",
                 "purpose": "Propose alert groups using same-source, process-tree and provenance relationships."},
                {"id": "verify", "label": "V · verify", "source": "Phase 31 verified unions + Phase 32 endpoint fallback",
                 "purpose": "Check provenance, independent roots, causal fields, context and decision-time availability."},
                {"id": "prioritize", "label": "P · prioritize", "source": "Phase 31 source_depth + Phase 32 verified-union bonus",
                 "purpose": "Order verified groups for analyst review; this pipeline emits no confidence score."},
                {"id": "queue", "label": "Analyst queue", "source": "ranked group output",
                 "purpose": "Return proposed groups and evidence decisions for human review; no automatic containment."},
            ],
            "edgeOutcomes": ["accepted", "rejected", "abstained"],
            "actions": "No automated response action is implemented.",
            "readiness": "Real-SOC inference is blocked by the Phase 39 data and authorization gate."}


class StartRun(BaseModel):
    name: str = "Phase 32 development comparison"
    seed: int = 31102
    split: str = "development"


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def load_model(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load frozen research module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def set_status(run_id: str, status: str, **fields: Any) -> None:
    assignments = ["status=?"]
    values: list[Any] = [status]
    for key, value in fields.items():
        assignments.append(f"{key}=?")
        values.append(json.dumps(value) if key in ("result", "config") else value)
    values.append(run_id)
    with connect() as db:
        db.execute(f"UPDATE runs SET {','.join(assignments)} WHERE id=?", values)


def wait_if_paused(run_id: str, state: dict[str, Any]) -> bool:
    while state["pause"].is_set():
        if state["cancel"].is_set():
            return False
        time.sleep(0.12)
    return not state["cancel"].is_set()


def run_development(run_id: str, state: dict[str, Any], config: dict[str, Any]) -> None:
    out = RUNS / run_id
    out.mkdir(parents=True, exist_ok=False)
    set_status(run_id, "running", started_at=utc_now(), artifact_dir=str(out))
    emit(run_id, "started", {"status": "running", "message": "Loading the frozen Phase 31/32 development models."})
    try:
        sys.path.insert(0, str(PHASE32))
        p31 = load_model("command_center_phase31", PHASE31 / "model.py")
        p32 = load_model("command_center_phase32", PHASE32 / "model.py")
        manifest = read_json(PHASE31 / "dataset/development_manifest.json")
        visible = PHASE31 / "dataset/receiver_visible/development"
        truth_root = PHASE31 / "dataset/evaluator_only/development/ground_truth_private"
        rows: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
        audits: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
        total = len(manifest["queues"]) * len(ARMS)
        done = 0
        for item in manifest["queues"]:
            queue_id = item["queue_id"]
            for arm in ARMS:
                if not wait_if_paused(run_id, state):
                    raise InterruptedError("Run cancelled by user before all queues completed.")
                if arm == "baseline":
                    pred, audit = p31.predict_queue(visible, "development", queue_id,
                                                     "evidence_aware_ranked", 100, 100)
                else:
                    bonus = 1 if arm.endswith("bonus1") else 2
                    pred, audit = p32.predict_queue(visible, "development", queue_id, bonus)
                rows[arm].append(pred)
                audits[arm].append(audit)
                done += 1
                emit(run_id, "queue_complete", {"status": "running", "progress": done / total,
                     "completed": done, "total": total, "queueId": queue_id, "arm": arm,
                     "alerts": len(pred["eligible_alert_ids"]), "groups": len(pred["groups_ranked"]),
                     "accepted": audit.get("decision_counts", {}).get("accepted", pred.get("decisions", {}).get("accepted", 0)),
                     "runtimeSeconds": pred["runtime_seconds"]})
            # Save a recoverable checkpoint after each matched queue.
            for arm in ARMS:
                write_jsonl(out / f"{arm}_predictions.jsonl", rows[arm])
                write_jsonl(out / f"{arm}_decisions.jsonl", audits[arm])
        if state["cancel"].is_set():
            raise InterruptedError("Run cancelled by user before evaluation.")
        seal = {"cohort": "controlled_synthetic_development",
                "prediction_sha256": {arm: sha256(out / f"{arm}_predictions.jsonl") for arm in ARMS},
                "decision_sha256": {arm: sha256(out / f"{arm}_decisions.jsonl") for arm in ARMS},
                "phase31_model_sha256": sha256(PHASE31 / "model.py"),
                "phase32_model_sha256": sha256(PHASE32 / "model.py"),
                "created_at": utc_now(), "labels_read_before_prediction_seal": False}
        (out / "pre_evaluation_seal.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
        emit(run_id, "sealed", {"status": "evaluating", "message": "Prediction and decision files sealed; scoring the previously accessed development cohort."})
        set_status(run_id, "evaluating")
        evaluator = load_model("command_center_phase15_evaluator", ROOT / "experiments/PHASE15_CONTROLLED_SOC/evaluation/evaluate.py")
        metrics: dict[str, Any] = {}
        for arm in ARMS:
            result_path = out / f"{arm}_evaluation.json"
            evaluator.evaluate(out / f"{arm}_predictions.jsonl", truth_root, result_path)
            metrics[arm] = read_json(result_path)["summary"]
        baseline = metrics["baseline"]
        for arm in ARMS[1:]:
            old = baseline
            new = metrics[arm]
            new["paired_change"] = {
                "recall20": new["incident_recall20"] - old["incident_recall20"],
                "recoverability": new["group_recoverability"] - old["group_recoverability"],
                "p10": new["p10"] - old["p10"],
            }
            new["development_gate"] = bool(
                new["recall20_count"] >= 170 and new["recoverable"] >= 170 and
                new["p10_count"] >= old["p10_count"] and
                new["grouped_pair_precision"] >= 0.9 and
                new["false_grouped_pairs"] <= old["false_grouped_pairs"] and
                new["mixed_predicted_groups"] <= old["mixed_predicted_groups"])
        result = {"id": run_id, "name": config["name"], "status": "completed",
                  "classification": "development_only_previously_accessed",
                  "cohort": "controlled_synthetic_development", "split": "development",
                  "seed": 31102, "queues": len(manifest["queues"]), "arms": metrics,
                  "seal": seal, "completedAt": utc_now(),
                  "notes": ["Synthetic development evidence only; this split was previously used for candidate selection.",
                            "Official evaluator reads ground truth only after prediction and decision files are sealed.",
                            "Confidence and attack-class labels are not emitted by this pipeline."]}
        (out / "experiment_record.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        set_status(run_id, "completed", ended_at=utc_now(), result=result)
        emit(run_id, "completed", {"status": "completed", "result": result})
    except InterruptedError as exc:
        set_status(run_id, "cancelled", ended_at=utc_now(), error=str(exc))
        emit(run_id, "cancelled", {"status": "cancelled", "message": str(exc)})
    except Exception as exc:
        set_status(run_id, "failed", ended_at=utc_now(), error=f"{type(exc).__name__}: {exc}")
        emit(run_id, "failed", {"status": "failed", "message": f"{type(exc).__name__}: {exc}"})
    finally:
        try:
            sys.path.remove(str(PHASE32))
        except ValueError:
            pass
        with _controls_lock:
            _controls.pop(run_id, None)


@app.post("/api/runs", status_code=202)
def start_run(request: StartRun) -> dict[str, Any]:
    if request.split != "development" or request.seed != 31102:
        raise HTTPException(422, "Only the repository's fixed Phase 32 development split and seed are supported.")
    active_statuses = ("queued", "running", "paused", "evaluating")
    with connect() as db:
        active = db.execute("SELECT id FROM runs WHERE status IN (?,?,?,?) LIMIT 1", active_statuses).fetchone()
    if active:
        raise HTTPException(409, f"Experiment {active['id']} is already active.")
    run_id = f"dev-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}"
    config = {"name": request.name, "split": request.split, "seed": request.seed,
              "models": ["Phase 31 evidence-aware ranked baseline", "Phase 32 endpoint fallback +1", "Phase 32 endpoint fallback +2"],
              "code": "repository frozen model functions", "classification": "development_only_previously_accessed"}
    with connect() as db:
        db.execute("INSERT INTO runs(id,status,created_at,config) VALUES(?,?,?,?)",
                   (run_id, "queued", utc_now(), json.dumps(config)))
    state = {"pause": threading.Event(), "cancel": threading.Event()}
    with _controls_lock:
        _controls[run_id] = state
    threading.Thread(target=run_development, args=(run_id, state, config), daemon=True,
                     name=f"experiment-{run_id}").start()
    return {"id": run_id, "status": "queued", "config": config}


@app.get("/api/runs")
def list_runs() -> dict[str, Any]:
    with connect() as db:
        rows = db.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT 50").fetchall()
    return {"runs": [run_row(x) for x in rows]}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    with connect() as db:
        row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Experiment not found")
    return run_row(row)


@app.get("/api/runs/{run_id}/events")
def run_events(run_id: str, after: int = 0) -> dict[str, Any]:
    with connect() as db:
        rows = db.execute("SELECT seq,payload FROM run_events WHERE run_id=? AND seq>? ORDER BY seq LIMIT 250",
                          (run_id, after)).fetchall()
    return {"events": [{"seq": row["seq"], **json.loads(row["payload"])} for row in rows]}


@app.post("/api/runs/{run_id}/{action}")
def control_run(run_id: str, action: str) -> dict[str, Any]:
    if action not in ("pause", "resume", "stop"):
        raise HTTPException(404, "Action must be pause, resume or stop")
    with connect() as db:
        row = db.execute("SELECT status FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Experiment not found")
    status = row["status"]
    with _controls_lock:
        state = _controls.get(run_id)
    if not state:
        raise HTTPException(409, f"Experiment is {status}; it cannot be controlled now.")
    if action == "pause" and status == "running":
        state["pause"].set()
        set_status(run_id, "paused")
        emit(run_id, "paused", {"status": "paused", "message": "Paused between queue evaluations."})
    elif action == "resume" and status == "paused":
        state["pause"].clear()
        set_status(run_id, "running")
        emit(run_id, "resumed", {"status": "running", "message": "Resumed queue evaluation."})
    elif action == "stop" and status in ("queued", "running", "paused"):
        state["cancel"].set()
        state["pause"].clear()
        emit(run_id, "stop_requested", {"status": "stopping", "message": "Stop requested; current queue will finish before cancellation."})
    else:
        raise HTTPException(409, f"Cannot {action} an experiment in state {status}.")
    return {"id": run_id, "status": action if action != "stop" else "stopping"}


@app.get("/api/runs/{run_id}/export")
def export_run(run_id: str) -> FileResponse:
    with connect() as db:
        row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Experiment not found")
    folder = Path(row["artifact_dir"]) if row["artifact_dir"] else None
    if not folder or not folder.is_dir():
        raise HTTPException(409, "No experiment artifacts are available yet")
    archive = folder.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in folder.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(folder))
    return FileResponse(archive, media_type="application/zip", filename=f"{run_id}-evidence.zip")


@app.websocket("/ws")
async def websocket_endpoint(socket: WebSocket) -> None:
    await socket.accept()
    with _socket_lock:
        _sockets.add(socket)
    try:
        while True:
            await socket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        with _socket_lock:
            _sockets.discard(socket)
