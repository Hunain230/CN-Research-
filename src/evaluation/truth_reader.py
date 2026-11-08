"""The sole label reader. In real mode it requires an explicit gate token and path."""
from __future__ import annotations
import json
from pathlib import Path
from .prediction_validation import strict_load_json

def read_synthetic_truth(path: Path):
    if "fixtures" not in path.parts or "stage5" not in path.parts: raise ValueError("synthetic truth must be under fixtures/stage5")
    data=strict_load_json(path)
    required={"pair_truth","candidate_pairs","full_pair_universe","alert_truth","expert_rank","rank_candidate_universe","judgements","gold_top20_groups","review_annotations","high_priority_cases","org_scoped_incident_truth"}
    if set(data)!=required: raise ValueError("evaluator truth schema/model-artifact boundary mismatch")
    return data

def read_real_truth(path: Path, gate_token: str):
    if gate_token!="REAL_EVALUATION_GATES_OPEN": raise PermissionError("real evaluator truth access denied")
    return strict_load_json(path)
