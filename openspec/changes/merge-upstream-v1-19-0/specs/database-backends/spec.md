## ADDED Requirements

### Requirement: Background database usage merges with safe session ownership

The merged database layer MUST adopt upstream session ownership, detached refresh task, dependency, and SQLite writer fixes without regressing request-scoped sessions.

#### Scenario: Detached token refresh owns its DB session

- **WHEN** an account token refresh continues outside the original request context
- **THEN** it uses its own database session
- **AND** it does not reuse a closed request-scoped session.

#### Scenario: SQLite writer recovery remains serialized

- **WHEN** stale reservations or hot-path writes are recovered under SQLite
- **THEN** merged repository code serializes writes according to the merged database policy
- **AND** request-path sessions remain isolated from background work.
