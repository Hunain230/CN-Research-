"""Build private, label-free per-organization GUIDE projections for local sensitivity runs."""

from __future__ import annotations

import json
import time
from pathlib import Path

import duckdb

from .guide_rerun_v2 import INPUT_HASHES
from .phase2 import sha256_file
from .submission_full_guide import ROOT, write_json


RAW = ROOT / "data/raw/GUIDE_Test.csv"
RANKS = ROOT / "data/raw/GUIDE_Test_Queue_Rankings.csv"
PRIVATE = ROOT / "data/derived/submission_entity_time_shards_20261114_v1"
PUBLIC = ROOT / "outputs/submission_entity_time_shards_20261114_v1.json"
FIELDS = ("OrgId", "AlertId", "Timestamp", "DetectorId", "Category",
          "MitreTechniques", "EntityType", "EvidenceRole", "DeviceId",
          "AccountObjectId", "Sha256", "IpAddress", "NetworkMessageId",
          "EmailClusterId")


def main() -> None:
    if PRIVATE.exists() or PUBLIC.exists():
        raise FileExistsError("Shards already exist; use a new versioned path")
    if sha256_file(RAW) != INPUT_HASHES[RAW.name] or sha256_file(RANKS) != INPUT_HASHES[RANKS.name]:
        raise ValueError("Raw source hash changed")
    PRIVATE.mkdir(parents=True)
    started = time.perf_counter()
    con = duckdb.connect(str(PRIVATE / "build.duckdb"))
    con.execute("SET memory_limit='1GB'")
    con.execute("SET threads=2")
    con.execute(f"SET temp_directory='{(PRIVATE / 'tmp').as_posix()}'")
    raw = RAW.as_posix().replace("'", "''")
    ranks = RANKS.as_posix().replace("'", "''")
    dest = (PRIVATE / "parts").as_posix().replace("'", "''")
    columns = ",".join('r."' + f + '"' for f in FIELDS)
    query = f"""COPY (
        SELECT {columns}
        FROM read_csv('{raw}', all_varchar=true, header=true) r
        WHERE r.OrgId IN (
            SELECT DISTINCT OrgId FROM read_csv('{ranks}', all_varchar=true, header=true)
        )
    ) TO '{dest}' (FORMAT PARQUET, PARTITION_BY (OrgId), OVERWRITE_OR_IGNORE TRUE)"""
    con.execute(query)
    con.close()
    parts = sorted((PRIVATE / "parts").rglob("*.parquet"))
    org_dirs = {p.parent.name for p in parts}
    if len(org_dirs) != 499 or not parts:
        raise ValueError(f"Expected 499 ranked organization partitions; got {len(org_dirs)}")
    manifest = {
        "classification": "private_label_free_projection_for_local_entity_time_sensitivity_only",
        "fields": FIELDS, "organizations": len(org_dirs),
        "parts": len(parts), "bytes": sum(p.stat().st_size for p in parts),
        "seconds": time.perf_counter() - started,
        "raw_sha256": {RAW.name: INPUT_HASHES[RAW.name], RANKS.name: INPUT_HASHES[RANKS.name]},
        "source_code_sha256": sha256_file(Path(__file__)),
        "parquet_sha256": {str(p.relative_to(ROOT)): sha256_file(p) for p in parts},
        "excluded_fields": ["IncidentId", "QueueRank", "IncidentGrade", "ActionGrouped", "ActionGranular"],
        "field_approval": "not_approved_for_operational_use",
    }
    write_json(PUBLIC, manifest)
    print(json.dumps({k: manifest[k] for k in ("organizations", "parts", "bytes", "seconds")}, sort_keys=True))


if __name__ == "__main__":
    main()
