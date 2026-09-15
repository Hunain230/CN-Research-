# Models and Architecture

## Multi-agent SOC pipeline

### AUTHOR CLAIM

The demonstration uses three synchronous agents in a fixed sequence:

1. **Triage agent:** retrieves and summarizes an alert using three allowed Wazuh tools.
2. **Enrichment agent:** receives the validated triage handoff and builds a host profile using seven allowed tools.
3. **Response agent:** receives the triage and enrichment outputs, uses six allowed tools, and produces recommended actions, an escalation flag, and a human-approval flag.

The response-only `propose_wazuh_rule` tool returns a formatted proposal and never changes the Wazuh system automatically. [Simões, Sections 3.1 and 3.3, pp. 5-7, 17]

## Model configuration

### AUTHOR CLAIM

All three agents use GPT-4o mini, snapshot `gpt-4o-mini-2024-07-18`, with temperature **0.1**, `top_p` **1.0**, no fixed seed, and an internal loop limited to eight tool iterations. Structured JSON is requested through prompts and parsed by the framework rather than enforced through the API response-format schema. [Simões, Section 3.3 and Table 4, pp. 16-17]

## MCP integration

### AUTHOR CLAIM

The agent layer communicates through a persistent security gateway rather than receiving direct MCP client references. The legitimate Rust MCP server exposes **16** Wazuh tools through JSON-RPC 2.0 over Streamable HTTP/SSE using MCP protocol version 2025-06-18. A separate Python MCP server supplies malicious tools. Only the gateway is connected to both Docker trust domains. [Simões, Sections 3.1 and 3.3, pp. 5-7, 15-17]

## Memory architecture

### AUTHOR CLAIM

The system uses an alert-history log, a cross-session agent knowledge base, and a per-session context store. The context store is namespaced because it carries the greatest poisoning and cross-client leakage risk. Memory is implemented as JSON files on persistent storage. [Simões, Sections 3.1 and 3.3, pp. 6-7, 16-17]

## Portability

### AUTHOR CLAIM

Most controls operate only at the tool invocation and response layers and are intended to be independent of the underlying LLM, number of agents, and server identity. Porting requires configuration of role permissions, tool schemas, trusted hashes, and the handoff sequence. The handoff validator assumes a linear topology and must be generalized to a transition graph for decentralized, hierarchical, or non-sequential systems. [Simões, Section 3.3, pp. 17-18]

## Architecture assessment

### OUR OBSERVATION

The architecture clearly separates model reasoning from deterministic security enforcement. This makes the security decisions auditable and avoids relying on an LLM to police its own tool use. However, the three agents are functionally sequential rather than argumentative: there is no proposer-critic-adjudicator process, explicit comparison of competing conclusions, calibrated confidence, or abstention mechanism for contradictory evidence.

