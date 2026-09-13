# Models and Architecture

## Architectural modules

### AUTHOR CLAIM

| Module | Input/output and role |
|---|---|
| Causal Discovery Engine | Learns a weighted causal DAG from historical telemetry. |
| MDP-DAG Roadmap Constructor | Converts causal and ontology constraints into permitted investigation-state transitions. |
| Council of Rivals | Blue and Red policies propose/challenge actions and quantify disagreement. |
| HITL/ETS interface | Exposes evidence, explanations, uncertainty, costs, and escalation decisions. |

Source: [Zhang, Section 5, Table 7 and Fig. 2, pp. 7-8]

## Policy architecture

### AUTHOR CLAIM

- State dimension: 256.
- MLP hidden layers: [256, 256, 128] with ReLU and layer normalization.
- Optimizer: Adam, beta1 = 0.9, beta2 = 0.999, epsilon = 10^-8.
- Learning rate: 3 x 10^-4.
- Batch size: 128.
- Replay-buffer capacity: 5 x 10^5 transitions per agent.
- Discount factor: 0.99.
- Target-network update coefficient: 0.005.
- Exploration: epsilon-greedy, 1.0 to 0.05 over 3 x 10^5 environment steps.
- Training: 1.5 x 10^6 steps per agent; seeds {1, 2, 3}.

[Zhang, Table 10, p. 12]

Training stops early if smoothed episodic return and validation-set FPR under adversarial perturbation stabilize across 20 consecutive evaluation intervals. [Zhang, Section 5.3.1, p. 12]

## Structural assumptions

### AUTHOR CLAIM

The learned SCM is assumed acyclic and only an approximation of the true causal structure. The abstract roadmap assumes the Markov property. Formal safety and bounded-violation claims are conditional on bounded structural error. [Zhang, Section 3.3, p. 5]

## Adversary model

### AUTHOR CLAIM

“Shadow-Jitter” represents bounded partial compromise and telemetry perturbation intended to distort apparent causal relationships while preserving plausible observations. Its bounds cover perturbation amplitude, compromised channels, temporal displacement, and poisoned-data proportion. [Zhang, Sections 4.2-4.2.2, Tables 4-5, pp. 5-7]

## OUR OBSERVATION

The Blue and Red agents use the same model family and differ mainly through reward shaping. This controls architectural confounding, but it may also create correlated blind spots; the authors acknowledge this risk and propose heterogeneous model families as future work. [Zhang, Section 8.3, p. 20]

