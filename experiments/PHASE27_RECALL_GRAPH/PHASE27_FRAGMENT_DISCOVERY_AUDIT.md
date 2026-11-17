# Fragment-level incident discovery audit

A hypothesis qualifies when it contains at least 80% of an incident's cutoff-visible alerts and at least 80% of its own alerts belong to that incident. Each oracle top-20 incident is counted once. There are 400 development and 600 holdout incident opportunities. Private truth is applied only after graph and hypothesis predictions are frozen.

Development: **215/295 qualifying hypotheses (72.88% precision)**, covering **179/400** top-20 incidents outside baseline group recoverability. Holdout: **314/493 (63.69%)**, covering **231/600** such incidents. No uncertain-edge union was committed by the selected pipeline.

There were 80 nonqualifying development and 179 nonqualifying holdout hypotheses. All frozen hypotheses fell within each queue's first 20 confidence-ranked hypothesis slots, so those are also false top-20 hypothesis rankings. `PHASE27_HYPOTHESIS_RANKING.csv` lists the queue counts; `PHASE27_FRAGMENT_COUNTS.csv` gives the number and size of baseline committed fragments per top-20 incident. These predictions are discovery hypotheses, not recovered official groups.
