## ADDED Requirements

### Requirement: Runtime observability merges archive, bridge, and fork cache alerts

The merged proxy runtime MUST expose upstream conversation archive, bridge routing, request-log cost/detail, stream retry, timeout, and model context observability while preserving fork Platform cache alert and fallback decision observability.

#### Scenario: Conversation archive remains opt-in and redacted

- **WHEN** conversation archive is disabled
- **THEN** no archive file is created by normal proxy traffic.
- **WHEN** conversation archive is enabled
- **THEN** archived records redact credential-bearing headers
- **AND** gzip/archive I/O does not block the request event loop during normal operation.

#### Scenario: Bridge and fallback decisions stay observable

- **WHEN** an HTTP bridge, WebSocket, compact failover, owner handoff, or Platform fallback decision occurs
- **THEN** the merged runtime records structured low-cardinality observability data
- **AND** fork cache-alert behavior remains available.
