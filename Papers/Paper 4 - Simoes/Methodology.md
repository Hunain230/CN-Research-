# Methodology

## Threat model

### AUTHOR CLAIM

The authors compile **35** middleware-addressable attack vectors using three selection criteria: relevance to the proposed architecture, empirical grounding in published taxonomies or demonstrations, and applicability to an SOC deployment. The middleware addresses **29** vectors. [Simões, Section 3.2.8 and Table 2, pp. 12-14]

Four vectors are exercised end to end through the malicious MCP server: tool-description poisoning, tool shadowing/name collision, indirect prompt injection through a server response, and confused-deputy tool use. Other vectors are injected directly into the relevant framework component by the test harness. The authors distinguish these two levels of evidential strength. [Simões, Sections 3.2.8 and 3.4-3.5, pp. 12-23]

## Connection-phase controls

### AUTHOR CLAIM

Before agents receive a tool registry, the framework:

1. scans tool descriptions for adversarial instructions;
2. rejects tool-name collisions through namespace ownership;
3. computes and pins SHA-256 hashes for tool manifests; and
4. verifies trusted MCP server binary hashes when configured.

A changed manifest produces a warning rather than automatic rejection. [Simões, Section 3.2.1 and Table 6, pp. 7-8, 20]

## Five execution layers

### AUTHOR CLAIM

1. **Access control:** runtime role-based allowlists restrict each agent to its assigned tools.
2. **Rate limiting:** sliding 60-second limits permit 20 calls for triage and response and 30 for enrichment; human-approval requests are limited to 10 per hour.
3. **Input validation:** JSON Schema and pattern checks inspect tool arguments, memory context, external content, and inter-agent handoffs. A linear sequence validator enforces triage to enrichment to response.
4. **Output validation:** pattern checks cover injection, coercion, exfiltration, prompt extraction, and self-propagation; responses are limited to 100 KB.
5. **Audit logging:** append-only records capture session, role, tool/server, arguments, result or block reason, and a SHA-256 response digest; sensitive values are hashed.

[Simões, Sections 3.2.2-3.2.6, pp. 8-11]

## Session and deployment controls

### AUTHOR CLAIM

UUID session identifiers namespace context storage. The framework uses generic error messages, protocol and binary version checks, a shared-secret header, origin validation, loopback binding, and Docker network segmentation. The allowed-origin variable was not configured in the evaluated deployment, so DNS-rebinding protection depended on loopback binding and segmentation rather than the application-layer response check. [Simões, Sections 3.2.7 and 5, pp. 11-12, 27-28]

## Evaluation procedure

### AUTHOR CLAIM

Six suites, T00-T05, separately test registration, access control, rate limiting, input validation, output validation, and session/response controls. Each attack case is followed by a legitimate case on the same surface. A subtest succeeds only if the expected control blocks the attack, the attack does not reach the protected surface, the legitimate case is accepted, and the result remains stable across trials. [Simões, Sections 3.4-3.5.4, pp. 18-23]

## Baseline and ablation status

### AUTHOR CLAIM

The full-pipeline demonstration includes an unsecured condition with direct access to both MCP servers and a secured condition in which calls pass through the framework. The paper does not report a conventional component-ablation study or comparison with other security middleware. [Simões, Section 4.2, pp. 23-24]

### OUR OBSERVATION

The component-isolated suites show whether each control enforces its intended rule, but they do not quantify how much each layer contributes to end-to-end security when controls overlap. An ablation or comparative security baseline would strengthen the causal attribution of the full framework's results.

