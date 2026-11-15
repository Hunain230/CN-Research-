"""Phase 9A infrastructure for frozen-graph fragment boundaries.

There is deliberately no empirical fit, predict, or GUIDE runner. Only the
synthetic self-test is executable. Expert membership and ranks are absent from
this module. A future version must validate evidence provenance and choose
decision parameters on authorized development data before real prediction.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/small_fragment_recovery_v1.json"
CAP = 100


@dataclass(frozen=True)
class Witness:
    left_alert: int
    right_alert: int
    key: tuple[str, str]
    observation_ids: frozenset[str]


@dataclass
class Boundary:
    left: int
    right: int
    edges: list[tuple[int, int, float]] = field(default_factory=list)
    witnesses: list[Witness] = field(default_factory=list)
    shared_entities: set[tuple[str, str]] = field(default_factory=set)
    shared_categories: set[str] = field(default_factory=set)
    shared_techniques: set[str] = field(default_factory=set)
    shared_detectors: set[str] = field(default_factory=set)
    category_conflict: bool = False
    technique_conflict: bool = False
    entity_group_frequency: int | None = None
    temporal_gap_seconds: float = 0.0

    def features(self, provenance_verified: bool) -> dict[str, float | int | bool | None]:
        left = {a for a, _, _ in self.edges}
        right = {b for _, b, _ in self.edges}
        scores = [score for _, _, score in self.edges]
        return {
            "candidate_edge_count": len(self.edges),
            "distinct_left_alerts": len(left),
            "distinct_right_alerts": len(right),
            "max_frozen_pair_score": max(scores, default=0.0),
            "mean_frozen_pair_score": sum(scores) / len(scores) if scores else 0.0,
            "shared_entity_count": len(self.shared_entities),
            "shared_category_count": len(self.shared_categories),
            "shared_technique_count": len(self.shared_techniques),
            "shared_detector_count": len(self.shared_detectors),
            "category_conflict": self.category_conflict,
            "technique_conflict": self.technique_conflict,
            "minimum_entity_group_frequency": self.entity_group_frequency,
            "temporal_gap_seconds": self.temporal_gap_seconds,
            "verified_independent_paths": independent_path_count(
                self.witnesses, provenance_verified),
            "provenance_verified": provenance_verified,
        }


def load_infrastructure_config() -> dict:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if (config["hard_component_cap"] != CAP or
            config["guide_test_prediction_enabled"] or
            config["model_fitting_enabled"] or
            config["threshold_selection_enabled"] or
            config["operational_field_approval"] or
            config["provenance"]["verified_source"] is not None or
            config["provenance"]["observation_id_semantics_approved"] or
            config["provenance"]["arrival_time_contract_approved"]):
        raise ValueError("Phase 9A must remain infrastructure-only")
    if any(value is not None for value in
           config["parameters_requiring_authorized_development_data"].values()):
        raise ValueError("Unapproved development parameters were filled")
    return config


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_frozen_file(path: Path, expected_sha256: str) -> None:
    if sha256_file(path) != expected_sha256:
        raise ValueError(f"Frozen input hash changed: {path.name}")


def decode_edge(encoded: int, alert_count: int) -> tuple[int, int]:
    if alert_count < 2 or not isinstance(encoded, int):
        raise ValueError("Invalid edge or alert count")
    left, right = divmod(encoded, alert_count)
    if not 0 <= left < right < alert_count:
        raise ValueError("Candidate edge is outside the ordered alert scope")
    return left, right


def verify_alignment(keys: Sequence[str], edges: Sequence[int],
                     groups: Sequence[Sequence[str]], scores: Sequence[float]) -> list[int]:
    """Check the frozen key order, edge encoding, scores, and v2 partition."""
    if len(keys) != len(set(keys)) or len(edges) != len(scores):
        raise ValueError("Duplicate alerts or misaligned score vector")
    group_of: dict[str, int] = {}
    for group_id, group in enumerate(groups):
        if not group or len(group) > CAP:
            raise ValueError("Empty group or original group above cap")
        for alert in group:
            if alert in group_of:
                raise ValueError("Alert appears in more than one v2 group")
            group_of[alert] = group_id
    if set(group_of) != set(keys):
        raise ValueError("V2 groups do not partition the candidate alert scope")
    previous = -1
    for encoded, score in zip(edges, scores):
        value = int(encoded)
        if value <= previous:
            raise ValueError("Candidate edges must be unique and ascending")
        decode_edge(value, len(keys))
        if not math.isfinite(float(score)) or not 0 <= score <= 1:
            raise ValueError("Invalid or misaligned pair probability")
        previous = value
    return [group_of[alert] for alert in keys]


def rescore_verified_candidate_edges(
        keys: Sequence[str], frozen_edges: Sequence[int],
        regenerated_edges: Sequence[int], route_flags: Sequence[int],
        groups: Sequence[Sequence[str]], docs: Mapping[str, Mapping],
        frozen_model_path: Path, expected_model_sha256: str,
        scorer: Callable[[Sequence[str], Mapping[str, Mapping],
                          Sequence[int], Sequence[int]], Sequence[float]]) -> list[float]:
    """Versioned-runner handoff to the *frozen* v2 scorer.

    The future caller supplies the original v2 scoring function as `scorer`.
    The existing candidate file lacks pair probabilities and route flags, so
    regenerated edges must exactly match it before any score is accepted.
    This function is exercised only on fictional inputs in Phase 9A.
    """
    verify_frozen_file(frozen_model_path, expected_model_sha256)
    if list(map(int, frozen_edges)) != list(map(int, regenerated_edges)):
        raise ValueError("Regenerated edges do not match the frozen candidate graph")
    if len(route_flags) != len(frozen_edges):
        raise ValueError("Regenerated route flags are misaligned")
    scores = list(scorer(keys, docs, regenerated_edges, route_flags))
    verify_alignment(keys, frozen_edges, groups, scores)
    return scores


def _field(doc: Mapping, name: str) -> set[str]:
    return set(doc.get("fields", {}).get(name, set()))


def _shared_support_keys(left: Mapping, right: Mapping) -> set[tuple[str, str]]:
    keys = {(f"entity:{field}", str(value))
            for field, value in left.get("entities", set()) & right.get("entities", set())}
    for field, family in (("MitreTechniques", "technique"),
                          ("DetectorId", "detector")):
        keys.update((family, str(token)) for token in _field(left, field) & _field(right, field))
    return keys


def _witnesses(left_index: int, right_index: int, left: Mapping,
               right: Mapping) -> list[Witness]:
    """Missing observation lineage yields no verified witness, even for equal keys."""
    result = []
    for evidence_key in _shared_support_keys(left, right):
        left_ids = set(left.get("provenance", {}).get(evidence_key, set()))
        right_ids = set(right.get("provenance", {}).get(evidence_key, set()))
        if left_ids and right_ids:
            result.append(Witness(left_index, right_index, evidence_key,
                                  frozenset(left_ids | right_ids)))
    return result


def independent_path_count(witnesses: Sequence[Witness],
                           provenance_verified: bool) -> int:
    """Return at most two paths; key and observation disjointness are required."""
    if not provenance_verified:
        return 0
    for i, first in enumerate(witnesses):
        if not first.observation_ids:
            continue
        for second in witnesses[i + 1:]:
            if (first.left_alert != second.left_alert and
                    first.right_alert != second.right_alert and
                    first.key != second.key and
                    first.observation_ids.isdisjoint(second.observation_ids)):
                return 2
    return 1 if any(w.observation_ids for w in witnesses) else 0


def enumerate_boundaries(keys: Sequence[str], groups: Sequence[Sequence[str]],
                         encoded_edges: Sequence[int], pair_scores: Sequence[float],
                         docs: Mapping[str, Mapping], *, max_boundaries_per_queue: int,
                         max_boundaries_per_group: int) -> list[Boundary]:
    """Enumerate every frozen cross-group edge, including scores below 0.40.

    Budgets abort rather than silently truncate. No threshold or label is used.
    """
    if max_boundaries_per_queue < 1 or max_boundaries_per_group < 1:
        raise ValueError("Explicit positive proposal budgets are required")
    membership = verify_alignment(keys, encoded_edges, groups, pair_scores)
    if set(docs) != set(keys):
        raise ValueError("Evidence projection does not match alert scope")
    group_entities = [set().union(*(docs[a].get("entities", set()) for a in group))
                      for group in groups]
    group_fields = [{field: set().union(*(_field(docs[a], field) for a in group))
                     for field in ("Category", "MitreTechniques", "DetectorId")}
                    for group in groups]
    group_times = [(min(float(docs[a]["stamp"]) for a in group),
                    max(float(docs[a]["stamp"]) for a in group)) for group in groups]
    frequency = Counter(entity for entities in group_entities for entity in entities)
    boundaries: dict[tuple[int, int], Boundary] = {}
    degree = Counter()
    for encoded, probability in zip(encoded_edges, pair_scores):
        left, right = decode_edge(int(encoded), len(keys))
        ga, gb = membership[left], membership[right]
        if ga == gb:
            continue
        if ga > gb:
            ga, gb, left, right = gb, ga, right, left
        pair = (ga, gb)
        if pair not in boundaries:
            if (len(boundaries) >= max_boundaries_per_queue or
                    degree[ga] >= max_boundaries_per_group or
                    degree[gb] >= max_boundaries_per_group):
                raise ValueError("Proposal budget exceeded; no silent truncation")
            a, b = group_fields[ga], group_fields[gb]
            shared = group_entities[ga] & group_entities[gb]
            gap = max(0.0, group_times[ga][0] - group_times[gb][1],
                      group_times[gb][0] - group_times[ga][1])
            boundaries[pair] = Boundary(
                left=ga, right=gb, shared_entities=shared,
                shared_categories=a["Category"] & b["Category"],
                shared_techniques=a["MitreTechniques"] & b["MitreTechniques"],
                shared_detectors=a["DetectorId"] & b["DetectorId"],
                category_conflict=bool(a["Category"] and b["Category"] and
                                       not a["Category"] & b["Category"]),
                technique_conflict=bool(a["MitreTechniques"] and b["MitreTechniques"] and
                                        not a["MitreTechniques"] & b["MitreTechniques"]),
                entity_group_frequency=min((frequency[e] for e in shared), default=None),
                temporal_gap_seconds=gap,
            )
            degree[ga] += 1
            degree[gb] += 1
        boundary = boundaries[pair]
        boundary.edges.append((left, right, float(probability)))
        boundary.witnesses.extend(_witnesses(left, right, docs[keys[left]], docs[keys[right]]))
    return [boundaries[pair] for pair in sorted(boundaries)]


def merge_non_cascading(groups: Sequence[Sequence[str]], boundaries: Sequence[Boundary],
                        boundary_scores: Mapping[tuple[int, int], float],
                        parameters: Mapping[str, float | int], *,
                        provenance_verified: bool) -> tuple[list[list[str]], list[dict]]:
    """Apply an externally scored, development-authorized policy once.

    This function cannot infer gold purity or rank. Missing source provenance
    makes every proposed merge a review case, regardless of score.
    """
    required = ("acceptance_score", "minimum_mutual_best_margin",
                "maximum_entity_group_frequency", "maximum_temporal_gap_seconds")
    if any(parameters.get(name) is None for name in required):
        raise ValueError("No empirical decision cutoff has been authorized")
    if any(not group or len(group) > CAP for group in groups):
        raise ValueError("Invalid original group or component cap")
    if len({alert for group in groups for alert in group}) != sum(map(len, groups)):
        raise ValueError("Original groups overlap")
    if set(boundary_scores) != {(b.left, b.right) for b in boundaries}:
        raise ValueError("Boundary scores are missing or misaligned")
    alternatives: dict[int, list[tuple[float, int]]] = defaultdict(list)
    for boundary in boundaries:
        score = float(boundary_scores[boundary.left, boundary.right])
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Invalid boundary score")
        if not 0 <= boundary.left < boundary.right < len(groups):
            raise ValueError("Invalid original group indices")
        edge_endpoints = {(a, b) for a, b, _ in boundary.edges}
        if any((w.left_alert, w.right_alert) not in edge_endpoints
               for w in boundary.witnesses):
            raise ValueError("Support witness is not attached to a candidate edge")
        alternatives[boundary.left].append((score, boundary.right))
        alternatives[boundary.right].append((score, boundary.left))
    for group in alternatives:
        alternatives[group].sort(key=lambda row: (-row[0], row[1]))
    decisions = []
    eligible = []
    for boundary in boundaries:
        pair = (boundary.left, boundary.right)
        score = float(boundary_scores[pair])
        evidence = boundary.features(provenance_verified)
        if not provenance_verified:
            reason = "REVIEW_UNVERIFIED_PROVENANCE"
        elif len(groups[boundary.left]) + len(groups[boundary.right]) > CAP:
            reason = "REJECT_COMPONENT_CAP"
        elif evidence["verified_independent_paths"] < 2:
            reason = "REVIEW_INSUFFICIENT_INDEPENDENT_SUPPORT"
        elif boundary.entity_group_frequency is None:
            reason = "REVIEW_NO_ENTITY_ANCHOR"
        elif boundary.entity_group_frequency > parameters["maximum_entity_group_frequency"]:
            reason = "REVIEW_COMMON_ENTITY"
        elif boundary.category_conflict and boundary.technique_conflict:
            reason = "REJECT_DESCRIPTOR_CONFLICT"
        elif not (boundary.shared_categories or boundary.shared_techniques):
            reason = "REVIEW_NO_DESCRIPTOR_CORROBORATION"
        elif boundary.temporal_gap_seconds > parameters["maximum_temporal_gap_seconds"]:
            reason = "REVIEW_TEMPORAL_GAP"
        elif score < parameters["acceptance_score"]:
            reason = "REVIEW_SCORE"
        else:
            reason = "ELIGIBLE_PENDING_MATCH"
            eligible.append(pair)
        decisions.append({"base_group_left": pair[0], "base_group_right": pair[1],
                          "boundary_score": score, "evidence": evidence,
                          "decision": reason})
    by_pair = {(row["base_group_left"], row["base_group_right"]): row
               for row in decisions}
    selected = []
    used = set()
    for pair in sorted(eligible, key=lambda item: (-boundary_scores[item], item)):
        left, right = pair
        best_left = alternatives[left][0][1]
        best_right = alternatives[right][0][1]
        left_margin = (alternatives[left][0][0] - alternatives[left][1][0]
                       if len(alternatives[left]) > 1 else 1.0)
        right_margin = (alternatives[right][0][0] - alternatives[right][1][0]
                        if len(alternatives[right]) > 1 else 1.0)
        row = by_pair[pair]
        row["evidence"]["minimum_alternative_neighbor_margin"] = min(left_margin, right_margin)
        if (best_left != right or best_right != left or
                min(left_margin, right_margin) < parameters["minimum_mutual_best_margin"]):
            row["decision"] = "REVIEW_COMPETING_NEIGHBOR"
        elif left in used or right in used:
            row["decision"] = "REJECT_GROUP_ALREADY_USED"
        else:
            row["decision"] = "ACCEPT"
            used.update(pair)
            selected.append(pair)
    partner = {left: right for left, right in selected}
    partner.update({right: left for left, right in selected})
    output = []
    for group_id, group in enumerate(groups):
        if group_id not in partner:
            output.append(list(group))
        elif group_id < partner[group_id]:
            output.append(sorted(list(group) + list(groups[partner[group_id]])))
    output.sort(key=lambda group: group[0])
    if sum(map(len, output)) != sum(map(len, groups)) or any(len(g) > CAP for g in output):
        raise AssertionError("Merge changed alert scope or exceeded cap")
    return output, decisions


def _synthetic_doc(entity: tuple[str, str], observation: str) -> dict:
    evidence_key = (f"entity:{entity[0]}", entity[1])
    return {"entities": {entity},
            "fields": {"Category": {"same-category"},
                       "MitreTechniques": set(), "DetectorId": set()},
            "stamp": 100.0,
            "provenance": {evidence_key: {observation}}}


def _expect_value_error(action) -> None:
    try:
        action()
    except ValueError:
        return
    raise AssertionError("Expected a validation failure")


def self_test() -> None:
    """Synthetic-only invariants; no GUIDE reads and no fitted model."""
    load_infrastructure_config()
    checks = 0
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imported = {node.module for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)}
    assert not (imported & {"src.guide_rerun_v2", "src.offline_joint_comparison",
                            "src.submission_group_merge_v10_v2"})
    checks += 1
    keys = ["a", "b", "c", "d"]
    groups = [["a", "c"], ["b", "d"]]
    first = ("DeviceId", "fictional-device")
    second = ("AccountObjectId", "fictional-account")
    docs = {"a": _synthetic_doc(first, "source-a"),
            "b": _synthetic_doc(first, "source-b"),
            "c": _synthetic_doc(second, "source-c"),
            "d": _synthetic_doc(second, "source-d")}
    edges = [1, 11]  # a-b and c-d, encoded at n=4.
    assert decode_edge(11, 4) == (2, 3)
    assert verify_alignment(keys, edges, groups, [0.2, 0.3]) == [0, 1, 0, 1]
    checks += 2
    _expect_value_error(lambda: decode_edge(4, 4))
    _expect_value_error(lambda: verify_alignment(keys, edges, groups, [0.2]))
    _expect_value_error(lambda: verify_alignment(keys, [1, 1], groups, [0.2, 0.3]))
    checks += 3
    verified_scores = rescore_verified_candidate_edges(
        keys, edges, edges, [2, 8], groups, docs, CONFIG, sha256_file(CONFIG),
        lambda _keys, _docs, _edges, _flags: [0.2, 0.3])
    assert verified_scores == [0.2, 0.3]
    _expect_value_error(lambda: rescore_verified_candidate_edges(
        keys, edges, [1, 10], [2, 8], groups, docs, CONFIG,
        sha256_file(CONFIG), lambda *_: [0.2, 0.3]))
    _expect_value_error(lambda: rescore_verified_candidate_edges(
        keys, edges, edges, [2, 8], groups, docs, CONFIG, "0" * 64,
        lambda *_: [0.2, 0.3]))
    checks += 3
    boundaries = enumerate_boundaries(keys, groups, edges, [0.2, 0.3], docs,
                                      max_boundaries_per_queue=2,
                                      max_boundaries_per_group=2)
    assert len(boundaries) == 1 and len(boundaries[0].edges) == 2
    assert boundaries[0].features(True)["max_frozen_pair_score"] == 0.3
    assert boundaries[0].features(True)["verified_independent_paths"] == 2
    checks += 3  # Includes sub-0.40 enumeration.
    fixture_parameters = {"acceptance_score": 0.8,
                          "minimum_mutual_best_margin": 0.05,
                          "maximum_entity_group_frequency": 10,
                          "maximum_temporal_gap_seconds": 3600}
    score = {(0, 1): 0.9}
    original, records = merge_non_cascading(groups, boundaries, score,
                                             fixture_parameters,
                                             provenance_verified=False)
    assert original == groups and records[0]["decision"] == "REVIEW_UNVERIFIED_PROVENANCE"
    merged, records = merge_non_cascading(groups, boundaries, score,
                                           fixture_parameters,
                                           provenance_verified=True)
    assert merged == [["a", "b", "c", "d"]] and records[0]["decision"] == "ACCEPT"
    checks += 2
    _expect_value_error(lambda: merge_non_cascading(groups, boundaries, score,
                                                      {**fixture_parameters,
                                                       "acceptance_score": None},
                                                      provenance_verified=True))
    checks += 1
    one_edge = enumerate_boundaries(keys, groups, [1], [0.2], docs,
                                    max_boundaries_per_queue=2,
                                    max_boundaries_per_group=2)
    unchanged, records = merge_non_cascading(groups, one_edge, score,
                                               fixture_parameters,
                                               provenance_verified=True)
    assert unchanged == groups and records[0]["decision"] == "REVIEW_INSUFFICIENT_INDEPENDENT_SUPPORT"
    checks += 1
    same_alert = [Witness(0, 1, ("entity:DeviceId", "x"), frozenset({"a", "b"})),
                  Witness(0, 3, ("technique", "t1"), frozenset({"c", "d"}))]
    same_key = [Witness(0, 1, ("entity:DeviceId", "x"), frozenset({"a", "b"})),
                Witness(2, 3, ("entity:DeviceId", "x"), frozenset({"c", "d"}))]
    same_observation = [Witness(0, 1, ("entity:DeviceId", "x"), frozenset({"same"})),
                        Witness(2, 3, ("technique", "t1"), frozenset({"same"}))]
    assert all(independent_path_count(case, True) == 1
               for case in (same_alert, same_key, same_observation))
    checks += 3
    assert independent_path_count(boundaries[0].witnesses, False) == 0
    checks += 1
    missing = {alert: {key: value for key, value in doc.items()
                       if key != "provenance"} for alert, doc in docs.items()}
    no_lineage = enumerate_boundaries(keys, groups, edges, [0.2, 0.3], missing,
                                      max_boundaries_per_queue=2,
                                      max_boundaries_per_group=2)
    assert no_lineage[0].features(True)["verified_independent_paths"] == 0
    unchanged, records = merge_non_cascading(groups, no_lineage, score,
                                               fixture_parameters,
                                               provenance_verified=True)
    assert unchanged == groups and records[0]["decision"] == "REVIEW_INSUFFICIENT_INDEPENDENT_SUPPORT"
    checks += 2
    empty = enumerate_boundaries([], [], [], [], {},
                                 max_boundaries_per_queue=1,
                                 max_boundaries_per_group=1)
    assert empty == [] and merge_non_cascading([], [], {}, fixture_parameters,
                                               provenance_verified=True) == ([], [])
    checks += 1
    _expect_value_error(lambda: enumerate_boundaries(
        ["a", "b", "c"], [["a"], ["b"], ["c"]], [1, 2], [0.1, 0.1],
        {x: _synthetic_doc(first, x) for x in ("a", "b", "c")},
        max_boundaries_per_queue=1, max_boundaries_per_group=2))
    checks += 1
    # Competing partners cannot merge by a narrow score margin.
    rival = Boundary(0, 2, edges=[(0, 4, 0.3), (2, 5, 0.3)],
                     witnesses=[Witness(0, 4, ("entity:DeviceId", "x"),
                                        frozenset({"a", "b"})),
                                Witness(2, 5, ("technique", "t1"),
                                        frozenset({"c", "d"}))],
                     shared_entities={first}, shared_categories={"same-category"},
                     entity_group_frequency=2)
    three = [["a", "c"], ["b", "d"], ["e", "f"]]
    competing, records = merge_non_cascading(
        three, [boundaries[0], rival], {(0, 1): 0.9, (0, 2): 0.89},
        fixture_parameters, provenance_verified=True)
    assert competing == three and all(row["decision"] != "ACCEPT" for row in records)
    checks += 1
    # One original group cannot be reused to make a transitive three-way group.
    next_boundary = Boundary(1, 2, edges=[(1, 4, 0.3), (3, 5, 0.3)],
                             witnesses=[Witness(1, 4, ("entity:DeviceId", "x"),
                                                frozenset({"a", "b"})),
                                        Witness(3, 5, ("technique", "t1"),
                                                frozenset({"c", "d"}))],
                             shared_entities={first}, shared_categories={"same-category"},
                             entity_group_frequency=2)
    noncascade, records = merge_non_cascading(
        three, [boundaries[0], next_boundary], {(0, 1): 0.95, (1, 2): 0.8},
        {**fixture_parameters, "minimum_mutual_best_margin": 0.0},
        provenance_verified=True)
    assert noncascade == [["a", "b", "c", "d"], ["e", "f"]]
    assert sum(row["decision"] == "ACCEPT" for row in records) == 1
    checks += 2
    too_large = [list(map(str, range(60))), list(map(str, range(60, 110)))]
    capped, records = merge_non_cascading(
        too_large, [boundaries[0]], score, fixture_parameters,
        provenance_verified=True)
    assert capped == too_large and records[0]["decision"] == "REJECT_COMPONENT_CAP"
    checks += 1
    common = Boundary(0, 1, edges=list(boundaries[0].edges),
                      witnesses=list(boundaries[0].witnesses),
                      shared_entities={first}, shared_categories={"same-category"},
                      entity_group_frequency=11)
    unchanged, records = merge_non_cascading(groups, [common], score,
                                               fixture_parameters,
                                               provenance_verified=True)
    assert unchanged == groups and records[0]["decision"] == "REVIEW_COMMON_ENTITY"
    checks += 1
    conflict = Boundary(0, 1, edges=list(boundaries[0].edges),
                        witnesses=list(boundaries[0].witnesses),
                        shared_entities={first}, category_conflict=True,
                        technique_conflict=True, entity_group_frequency=2)
    unchanged, records = merge_non_cascading(groups, [conflict], score,
                                               fixture_parameters,
                                               provenance_verified=True)
    assert unchanged == groups and records[0]["decision"] == "REJECT_DESCRIPTOR_CONFLICT"
    checks += 1
    distant = Boundary(0, 1, edges=list(boundaries[0].edges),
                       witnesses=list(boundaries[0].witnesses),
                       shared_entities={first}, shared_categories={"same-category"},
                       entity_group_frequency=2, temporal_gap_seconds=7200)
    unchanged, records = merge_non_cascading(groups, [distant], score,
                                               fixture_parameters,
                                               provenance_verified=True)
    assert unchanged == groups and records[0]["decision"] == "REVIEW_TEMPORAL_GAP"
    checks += 1
    print(json.dumps({"status": "pass", "synthetic_assertions": checks,
                      "guide_data_reads": 0, "model_calls": 0}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("self-test",))
    args = parser.parse_args()
    if args.stage == "self-test":
        self_test()


if __name__ == "__main__":
    main()
