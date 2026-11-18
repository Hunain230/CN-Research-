# Generator and leakage audit

Phase 35 used the Phase 31 v2 generator and validator byte-for-byte, with new train seed 35101/template v6 and development seed 35102/template v7. The planned locked-test seed 35103/template v8 was never generated. The validator passed on both generated splits, including process, authentication and network-flow evidence, delayed and missing evidence, duplicate alerts, independent and common-root claims, reused identifiers and cross-incident decoys.

The split-isolation check compared Phase 35 train/development against Phase 31 train/development, Phase 33 holdout and Phase 34 train/development. It found no overlap in hidden incident IDs, scenario IDs or exact templates across seven cohorts. Training truth was accessed only after training baseline predictions were sealed. Development baseline and candidate predictions were sealed before either was evaluated using the unchanged Phase 15 evaluator. The post-evaluation audit confirmed the seals, point-in-time eligibility at minute 100 and no private-truth fields in candidate predictions.

The Phase 34 historical inventory contains 179 files and its hashes still match. This audit verifies unchanged content, including the Phase 33 holdout records copied into the historical chain; it does not make Phase 35 development directly comparable to the Phase 33 holdout population.
