## ADDED Requirements

### Requirement: Auth merge preserves dashboard session and OAuth isolation

The merged auth implementation MUST adopt upstream dashboard session lifetime and OAuth concurrency fixes without weakening existing password, TOTP, bootstrap-token, API-key, or session expiry boundaries.

#### Scenario: Session lifetime remains validated

- **WHEN** an operator updates dashboard session lifetime settings after the merge
- **THEN** invalid values are rejected by the backend
- **AND** existing authentication requirements remain enforced.

#### Scenario: Concurrent OAuth flows stay isolated

- **WHEN** multiple browser or device OAuth flows run at the same time
- **THEN** each flow uses isolated state and token handling
- **AND** one account refresh cannot overwrite another account's auth state.
