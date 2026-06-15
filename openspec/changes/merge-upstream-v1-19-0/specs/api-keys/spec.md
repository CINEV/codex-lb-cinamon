## ADDED Requirements

### Requirement: API-key cost, assignment, and service-tier policy merge safely

The merged API-key implementation MUST include upstream account assignment, cost accounting, model visibility, and request-log filtering behavior while preserving fork enforced service-tier defaults.

#### Scenario: Enforced service tier still controls forwarded requests

- **GIVEN** an API key has an enforced service tier
- **WHEN** a proxy request authenticated by that key supplies a different tier
- **THEN** the merged proxy forwards the enforced tier
- **AND** API-key reservation and cost accounting use the effective billable tier.

#### Scenario: Account cost and request-log filters remain coherent

- **WHEN** the dashboard requests API-key/account cost details or filters request logs by API key
- **THEN** the backend returns the merged cost/filter fields
- **AND** pagination, labels, and existing account assignment behavior remain correct.
