## ADDED Requirements

### Requirement: Runtime observability survives conflict resolution

The merged proxy runtime MUST preserve fork request-log fields, runtime headers, platform cache alerts, streaming markers, and metrics while adopting upstream observability fixes.

#### Scenario: Request logs retain fork metadata

- **WHEN** a proxied request completes or fails
- **THEN** the merged request log MUST retain fork metadata such as account, API-key, service-tier, upstream, failure, and timing fields that remain part of the backend contract
- **AND** upstream request-log changes MUST NOT drop fork fields without a spec update

#### Scenario: Stream observability remains ordered

- **WHEN** a streaming request emits keepalive, retry, completion, or failure events
- **THEN** the merged runtime MUST preserve event ordering and observability markers
- **AND** tests MUST cover terminal and retry paths
