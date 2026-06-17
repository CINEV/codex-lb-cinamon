## ADDED Requirements

### Requirement: Upstream auth changes preserve fork dashboard boundaries

The merged auth implementation MUST adopt compatible upstream fixes without weakening fork dashboard authentication, guest access, session refresh, or password/TOTP boundaries.

#### Scenario: Dashboard auth remains enforced after merge

- **WHEN** a dashboard route requires an authenticated dashboard session
- **THEN** the merged service MUST continue to reject unauthenticated access
- **AND** any upstream auth changes MUST NOT bypass fork dashboard access controls

#### Scenario: Guest access remains scoped

- **WHEN** guest access is enabled for read-only dashboard use
- **THEN** the merged service MUST preserve the existing fork read-only boundary
- **AND** write operations MUST still require a privileged dashboard session
