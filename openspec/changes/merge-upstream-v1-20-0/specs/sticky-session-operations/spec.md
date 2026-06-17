## ADDED Requirements

### Requirement: Sticky continuity remains deterministic after upstream merge

The merged sticky-session implementation MUST preserve fork deterministic routing, durable bridge ownership, file-id affinity, cleanup, and failover semantics while adopting compatible upstream fixes.

#### Scenario: Existing sticky session remains usable

- **WHEN** a request references an existing sticky session or continuity anchor
- **THEN** the merged router MUST use the stored affinity according to fork policy
- **AND** upstream routing changes MUST NOT discard the affinity without an explicit invalidation path

#### Scenario: Durable bridge ownership remains isolated

- **WHEN** owner-forwarded bridge state is active
- **THEN** the merged service MUST preserve owner isolation and terminal state handling
- **AND** concurrent requests MUST NOT steal ownership because of upstream conflict resolution
