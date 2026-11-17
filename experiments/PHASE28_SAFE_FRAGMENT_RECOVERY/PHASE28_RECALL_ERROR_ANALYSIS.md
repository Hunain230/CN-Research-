# Recall error analysis

On authoritative development, the Phase 27 selected ranker already recalled every recoverable baseline incident: 107/400. Component promotion lifted both recoverability and official Recall@20 to 207/400. This is a reconstruction gain, not a ranking-only gain. The remaining **193/400** priority incidents were unrecovered under the selected rule. The strongest score-only candidate reached 273/400 but made 72 false pairs and 72 mixed groups, demonstrating that simply promoting more hypotheses trades away safety.

On the holdout, baseline recoverability and recall were 171/600; selected reached 291/600, leaving **309/600** unrecovered. The 120-incident gain is invalid for promotion because false grouped pairs increased by 35 across seven queues. The false promotions were benign fragments with two independent-looking, mutually consistent but incorrect lineage paths. This explains why train/development precision of 127/127 did not generalize.

The discovery layer still had useful unpromoted information: 326/477 holdout hypotheses qualified by private retrospective truth, but the promoter retained 153 of these. Recovering them safely requires a signal independent of the two challenged relationship paths, or a reversible human-reviewed incident suggestion that does not claim permanent group recovery.
