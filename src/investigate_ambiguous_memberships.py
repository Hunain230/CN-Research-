"""Write privacy-safe aggregate diagnostics from the restricted Phase 2 conflict ledger."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from pathlib import Path

DEFAULT_SOURCE = Path("data/derived/preprocessing/review/ambiguous_alert_memberships.csv")
DEFAULT_OUTPUT = Path("data/derived/preprocessing/review/conflict_investigation_aggregate.json")
EXPECTED_COLUMNS = {"OrgId", "AlertId", "IncidentAssignments", "SourceRowOrdinalsByAssignment"}


def build_report(source: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    with source.open("rb") as raw:
        for block in iter(lambda: raw.read(1024 * 1024), b""):
            digest.update(block)

    keys = assignments = source_rows = repeated_assignment_groups = 0
    keys_with_repeated = keys_all_once = 0
    by_assignment_count: dict[int, int] = {}
    with source.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or ()) != EXPECTED_COLUMNS:
            raise ValueError("Conflict ledger schema did not match the expected restricted artifact.")
        for row in reader:
            keys += 1
            packed = json.loads(row["SourceRowOrdinalsByAssignment"])
            assignment_count = len(packed)
            if assignment_count < 2:
                raise ValueError("Conflict ledger contains a row without multiple assignments.")
            assignments += assignment_count
            row_count = sum(len(item["source_row_ordinals"]) for item in packed)
            source_rows += row_count
            repeated = sum(len(item["source_row_ordinals"]) > 1 for item in packed)
            repeated_assignment_groups += repeated
            keys_with_repeated += bool(repeated)
            keys_all_once += row_count == assignment_count
            by_assignment_count[assignment_count] = by_assignment_count.get(assignment_count, 0) + 1

    return {
        "classification": "restricted aggregate investigation; not ground truth or pair labels",
        "source_artifact": source.as_posix(),
        "source_artifact_sha256": digest.hexdigest(),
        "source_artifact_rows": keys,
        "conflicting_composite_alert_keys": keys,
        "distinct_alert_to_incident_assignment_groups": assignments,
        "source_rows_across_conflicts": source_rows,
        "assignment_groups_repeated_across_multiple_evidence_rows": repeated_assignment_groups,
        "conflict_keys_with_at_least_one_repeated_assignment": keys_with_repeated,
        "conflict_keys_with_one_source_row_per_assignment": keys_all_once,
        "keys_by_distinct_assignment_count": {str(k): v for k, v in sorted(by_assignment_count.items())},
        "malformed_csv_rows_in_phase2": 0,
        "interpretation": (
            "Repeated evidence rows amplify many conflicting assignments, but do not explain why "
            "one composite alert key maps to multiple incidents. Source semantics and semantic "
            "corruption are unresolved; no assignment was selected, removed, voted, or converted to pairs."
        ),
        "limitations": [
            "Exact-duplicate overlap within conflict groups was not calculated.",
            "The reviewed publisher documentation does not define whether one scrubbed AlertId may legitimately occur under multiple incidents.",
            "No row-level identifiers or assignments are included in this aggregate artifact.",
        ],
        "environment": {"python": sys.version.split()[0], "platform": platform.platform()},
    }


def main() -> int:
    report = build_report(DEFAULT_SOURCE)
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "aggregate_written",
        "output": DEFAULT_OUTPUT.as_posix(),
        "conflicting_composite_alert_keys": report["conflicting_composite_alert_keys"],
        "distinct_alert_to_incident_assignment_groups": report["distinct_alert_to_incident_assignment_groups"],
        "source_rows_across_conflicts": report["source_rows_across_conflicts"],
        "assignment_groups_repeated_across_multiple_evidence_rows": report[
            "assignment_groups_repeated_across_multiple_evidence_rows"
        ],
        "conflict_keys_with_at_least_one_repeated_assignment": report[
            "conflict_keys_with_at_least_one_repeated_assignment"
        ],
        "conflict_keys_with_one_source_row_per_assignment": report[
            "conflict_keys_with_one_source_row_per_assignment"
        ],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
