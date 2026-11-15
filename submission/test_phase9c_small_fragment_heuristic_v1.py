"""Synthetic-only regression checks for the frozen Phase 9C heuristic."""

from __future__ import annotations

import json
import math

from src.phase9c_small_fragment_heuristic_v1 import choose_merges, config


def proposal(a: int, b: int, score: float = .9, *, edges: int = 2,
             left_touched: int = 2, right_touched: int = 2,
             entity_frequency: int = 2, category: int = 1,
             technique: int = 0, category_conflict: int = 0,
             technique_conflict: int = 0, gap_hours: float = 0,
             combined: int = 4) -> dict:
    return {"base_group_left": a, "base_group_right": b,
            "model_probability": score,
            "evidence": {"combined_group_size": combined,
                         "log_cross_edges": math.log1p(edges),
                         "log_touched_left": math.log1p(left_touched),
                         "log_touched_right": math.log1p(right_touched),
                         "entity_group_frequency_min": entity_frequency,
                         "log_shared_category": math.log1p(category),
                         "log_shared_technique": math.log1p(technique),
                         "category_conflict": category_conflict,
                         "technique_conflict": technique_conflict,
                         "log_intergroup_hours": math.log1p(gap_hours)}}


def main() -> None:
    p = config()["policy"]
    groups = [["a", "b"], ["c", "d"], ["e", "f"]]
    assertions = 0
    def expect(rows, selected, settings=None):
        nonlocal assertions
        result, got, _ = choose_merges(groups, rows, settings or p)
        assert got == selected
        assert sorted(a for g in result for a in g) == sorted(a for g in groups for a in g)
        assertions += 2
    expect([proposal(0, 1)], [(0, 1)])
    expect([proposal(0, 1, edges=1)], [])
    expect([proposal(0, 1, left_touched=1)], [])
    expect([proposal(0, 1, right_touched=1)], [])
    expect([proposal(0, 1, entity_frequency=11)], [])
    expect([proposal(0, 1, category=0)], [])
    expect([proposal(0, 1, category_conflict=1, technique_conflict=1)], [])
    expect([proposal(0, 1, gap_hours=49)], [])
    expect([proposal(0, 1, score=.69)], [])
    expect([proposal(0, 1), proposal(1, 2, .89)], [])
    expect([proposal(0, 1), proposal(1, 2, .2)], [(0, 1)])
    expect([proposal(0, 1), proposal(1, 2, .2)], [],
           {**p, "maximum_structural_proposals_per_queue": 0})
    large = [[str(i) for i in range(60)],
             [str(i) for i in range(60, 110)]]
    _, selected, counts = choose_merges(large, [proposal(0, 1, combined=110)], p)
    assert not selected and counts["proposal_reasons"]["component_cap"] == 1
    assertions += 1
    try:
        choose_merges(groups, [proposal(0, 1), proposal(0, 1)], p)
    except ValueError:
        assertions += 1
    else:
        raise AssertionError("Duplicate proposal accepted")
    print(json.dumps({"status": "pass", "synthetic_assertions": assertions,
                      "guide_labels_read": 0}))


if __name__ == "__main__":
    main()
