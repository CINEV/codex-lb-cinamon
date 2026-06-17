## ADDED Requirements

### Requirement: Upstream provider and Platform fallback policy remains fork-controlled

The merged provider management layer MUST preserve fork behavior for OpenAI Platform identities, upstream proxy routing, provider adapters, cache alerts, and Platform fallback eligibility.

#### Scenario: Platform identity routing remains explicit

- **WHEN** a request is eligible for OpenAI Platform routing
- **THEN** the merged service MUST select a Platform identity only through the fork provider-management policy
- **AND** upstream defaults MUST NOT implicitly enable Platform routing for continuity-bearing requests

#### Scenario: Upstream proxy settings survive merge

- **WHEN** an account or provider is configured to use an upstream proxy
- **THEN** the merged provider layer MUST preserve the configured proxy routing behavior
- **AND** frontend and backend settings MUST remain consistent
