# Candidate generation experiments

The Phase 13 route ablation filters the **same frozen 1,942,648 edges** by flags. Routes overlap; rows are not additive. Every row uses 499 queues and 9,980 expert labels. Truth is consulted only in the evaluator after the candidate graph and route flags were frozen. The measured true/false columns are evaluator diagnostics, not generator inputs.

| Route | Candidate edges | Same-incident edges | Cross-incident edges | Top-20 labels candidate-connected |
| --- | ---: | ---: | ---: | ---: |
| all | 1,942,648 | 699,790 | 1,242,858 | 8,638/9,980 |
| parent_exact | 314,576 | 37,018 | 277,558 | 6,549/9,980 |
| entity | 1,586,669 | 656,469 | 930,200 | 8,519/9,980 |
| technique | 76,040 | 23,528 | 52,512 | 6,422/9,980 |

Removing non-entity routes loses 119 candidate-connected labels (8,519 versus 8,638); parent exact matching alone loses 2,089. This shows route complementarity, but does **not** show that adding more routes will produce safe complete groups. [Phase 9E](../../PHASE9E_CANDIDATE_RETRIEVAL_REPORT.md) previously added 49,455 bounded sixth-neighbor edges, gained only four candidate-connected labels, recovered zero additional complete-and-pure incidents, and lost 1,215 grouped true pairs. We therefore did not launch another broad candidate expansion on exposed GUIDE labels. Independent source-context, rare-entity, temporal-only, multi-hop, and complementary-type expansion require a feature-availability and false-collision design not established here. Runtime and peak memory for the shared label-blind C prediction pass were 143.12 s and 574,357,504 bytes; route-specific prediction runtime was not separately measured.
