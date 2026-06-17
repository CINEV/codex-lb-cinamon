## ADDED Requirements

### Requirement: Frontend merge preserves fork dashboard workflows

The merged frontend MUST adopt compatible upstream UI/schema fixes without removing fork workflows for accounts, API keys, dashboard summaries, sticky sessions, reports, settings, runtime controls, and auth export.

#### Scenario: Fork dashboard sections remain reachable

- **WHEN** a user opens the merged dashboard
- **THEN** fork-specific sections for reports, runtime controls, settings, sticky sessions, and account management MUST remain reachable where they existed before the merge
- **AND** upstream navigation changes MUST NOT silently remove those routes

#### Scenario: Frontend schemas match merged backend payloads

- **WHEN** frontend schema and mock tests run after backend conflict resolution
- **THEN** account, dashboard, API-key, sticky-session, settings, and request-log schemas MUST match the merged backend contract
- **AND** mocks MUST include fork-only fields that remain in the backend
