# Models and Architecture

## Attacker model

### AUTHOR CLAIM

The attacker is modeled as an MDP whose state includes known vulnerabilities, recent defender actions, and network configuration. Its discrete actions include Scan, Exploit, Privilege Escalation, and Evade; the experimental scenarios also cover lateral movement and data exfiltration. [Agrawal, “Developing an attacker agent model,” pp. 12-13; “Environment configuration,” p. 14]

DQN configuration:

- fully connected layers: 128, 64, and 32 neurons, all ReLU;
- learning rate: 0.001;
- discount factor: 0.95;
- epsilon: 0.8 to 0.1 over 5000 episodes;
- replay buffer: 100,000 tuples;
- batch size: 64;
- target network synchronized every 1000 steps.

[Agrawal, “Developing an attacker agent model,” p. 13]

The methodology section also mentions Policy Gradient methods, but the reported implementation and experiments specify a DQN attacker; the Policy Gradient configuration/results are not clearly specified. [Agrawal, “Research methodology,” p. 8; implementation and experiments, pp. 12-16]

## Defender model

### AUTHOR CLAIM

The defender is a weighted ensemble of:

- **Random Forest:** 100 trees, maximum depth 20, Gini splitting, trained with scikit-learn and 10-fold cross-validation; and
- **Autoencoder:** sigmoid hidden activations, linear output, MSE loss trained on benign traffic, with early stopping after 10 unimproved validation epochs.

[Agrawal, “Developing a defender agent model,” pp. 13-14]

The Autoencoder architecture dimensions, ensemble weights, anomaly threshold, and decision-fusion rule are **not clearly specified**.

## Cyber-range integration

### AUTHOR CLAIM

Agent components are modular Python services containerized with Docker. Custom APIs and event hooks connect agents to CyDER 2.0; ZeroMQ supports asynchronous JSON exchange. Preliminary integration reports action execution under 100 ms. [Agrawal, “Implementation overview” and “Integration with cyber range environment,” pp. 12, 14]

## Response mechanism

### AUTHOR CLAIM

Defender outputs trigger predefined response rules based on incident-response practices. Examples include blocking an IP after port scanning, quarantining a host after exploitation, terminating sessions and preserving forensic logs after privilege escalation, and blocking anomalous outbound traffic plus alerting staff after suspected exfiltration. [Agrawal, “Results,” p. 17]

### OUR OBSERVATION

This is automated action selection from a predefined rule library, not a demonstrated evidence-grounded multi-agent reasoning process. Detection adapts, but response logic is largely predetermined.

