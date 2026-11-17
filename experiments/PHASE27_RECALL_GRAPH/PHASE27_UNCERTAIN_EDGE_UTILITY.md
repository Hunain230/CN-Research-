# Uncertain-edge utility audit

After freeze, evaluator truth marked **7299/7379** development and **11693/11843** locked candidate alert edges as same-incident. Edge precision is 98.92% and 98.73%. Among all true same-incident alert pairs in different committed baseline groups, direct candidate edges covered **5587/15559** and **8870/25995**. This direct pair recall differs from incident-hypothesis recall.

Bounded paths over sparse candidate edges discovered 179 and 231 otherwise unrecoverable top-20 incidents. Candidate edges produced no false grouped pairs because they were not committed. But 80 development and 150 holdout candidate edges connected unrelated incidents. The downstream nonqualifying hypotheses number 80 and 179.

Graph witness counts deduplicate source pairs and require disjoint controller roots. This prevents duplicate or shared-controller observations from being counted as multiple independent paths. It does not certify that independently rooted claims are true. The selected ranker's graph feature contribution was mostly negative; historical rankers tied its official development Recall@20. No alternative ranker was evaluated on the opened holdout, so official rank gain cannot be uniquely credited to uncertain edges.
