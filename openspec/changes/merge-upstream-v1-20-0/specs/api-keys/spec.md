## ADDED Requirements

### Requirement: API-key routing and quota policy survive upstream merge

The merged API-key implementation MUST preserve fork behavior for enforced service tiers, account assignment, model visibility, expiration, reset windows, and usage accounting while adopting compatible upstream fixes.

#### Scenario: Enforced service tier is retained

- **WHEN** an API key has an enforced service tier
- **THEN** the merged proxy MUST route requests using that service-tier policy
- **AND** upstream defaults MUST NOT remove or override the fork-specific enforced tier

#### Scenario: Account assignment is retained

- **WHEN** an API key is scoped to selected accounts
- **THEN** the merged service MUST keep the existing account assignment constraints
- **AND** usage, request logs, and dashboard summaries MUST reflect the selected account scope
