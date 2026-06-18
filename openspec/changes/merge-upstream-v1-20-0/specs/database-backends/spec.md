## ADDED Requirements

### Requirement: Database backend behavior remains compatible across SQLite and PostgreSQL

The merged database layer MUST adopt upstream session, pool, and backup fixes without regressing fork support for SQLite and PostgreSQL deployments.

#### Scenario: PostgreSQL repository tests remain valid

- **WHEN** PostgreSQL-backed repository tests run after the merge
- **THEN** database sessions, locks, and transactions MUST behave consistently with fork expectations
- **AND** host database gaps MUST be testable with a Podman-backed PostgreSQL service

#### Scenario: SQLite operational paths remain supported

- **WHEN** the service runs against SQLite
- **THEN** the merged database layer MUST preserve fork hot-path, backup, and contention handling behavior
- **AND** upstream pool changes MUST NOT introduce SQLite-only regressions
