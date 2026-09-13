# Methodology

## Research design

### AUTHOR CLAIM

The study follows an iterative design-implement-evaluate process combining computational modeling, simulation, empirical evaluation on CICIDS2017 and UNSW-NB15, cyber-range integration, hold-out testing, cross-validation, stress testing, repeated trials, expert acceptance testing, and statistical significance testing. [Agrawal, “Research methodology,” pp. 7-8]

## Architecture and agent roles

### AUTHOR CLAIM

- **Attacker agents:** learn adaptive, multi-stage attack plans through an MDP and Deep Q-Network; successful and stealthy exploitation is rewarded, while detection and failure are penalized.
- **Defender agents:** use a Random Forest for known labeled attacks and an Autoencoder for anomalous/previously unseen behavior; defenders share alerts and coordinate mitigation.
- **Environment:** CyDER 2.0 cyber range with configurable network topologies, traffic, hosts, and vulnerabilities.
- **Communication:** asynchronous ZeroMQ messages encoded as JSON; the conceptual design also refers to FIPA-style agent communication.
- **Response:** predefined actions include isolating hosts, blocking malicious traffic/IPs, applying patches, terminating sessions, changing configurations, notifying administrators, generating forensic logs, and alerting human operators.

[Agrawal, “Model development” and “Multi-agent system architecture,” pp. 8, 11-12; “Results,” p. 17]

## Training procedure

### AUTHOR CLAIM

The attacker DQN is trained for up to 5000 episodes with replay memory, target-network updates, and decaying epsilon-greedy exploration; training can stop if average reward and attack success plateau. [Agrawal, “Developing an attacker agent model,” p. 13]

The defender uses 10-fold cross-validation for the Random Forest and early stopping for the Autoencoder when validation loss fails to improve for 10 consecutive epochs. Grid search and cross-validation are used for tuning. [Agrawal, “Developing a defender agent model,” pp. 13-14]

## Experimental scenarios

### AUTHOR CLAIM

- **Scenario A / small network:** 50 hosts; basic single-stage attacks such as brute force or port scanning.
- **Scenario B / medium network:** 120 hosts; reconnaissance, exploitation, privilege escalation, lateral movement, and data exfiltration.
- **Scenario C / large network:** 200 hosts; multiple simultaneous attack modes.
- Each size uses two attacker agents and three defender agents.

[Agrawal, “Environment configuration,” p. 14]

## Baselines

### AUTHOR CLAIM

The experimental baselines are a static cyber range with scripted attacks and a rule-based MAS with fixed attack and defense rules. The paper also gives a literature-level feature comparison against systems attributed to Lateș et al., Zhang et al., and Choi et al. [Agrawal, “Environment configuration,” pp. 14-15; Table 14, p. 18]

## Statistical and acceptance procedures

### AUTHOR CLAIM

The authors report paired t-tests and ANOVA and state that null hypotheses were rejected at p < 0.05. A separate 25-expert survey of the problem statement reports means above 4.1 and p < 0.001 for five questions. [Agrawal, Tables 2-3, pp. 5-6; “Comparative analysis,” p. 18]

No component ablation study is clearly reported.

