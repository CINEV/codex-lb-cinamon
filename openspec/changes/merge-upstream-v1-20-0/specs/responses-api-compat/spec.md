## ADDED Requirements

### Requirement: Responses compatibility merges upstream fixes without losing fork continuity

The merged Responses and Chat compatibility layers MUST adopt upstream `v1.20.0` fixes while preserving fork Codex continuity, Platform fallback policy, file/image handling, service-tier enforcement, and streaming behavior.

#### Scenario: Continuity-bearing requests avoid unsafe fallback

- **GIVEN** a request depends on continuity state such as `previous_response_id`, prompt-cache locality, durable bridge ownership, or sticky affinity
- **WHEN** the merged router evaluates fallback eligibility
- **THEN** the request MUST remain on an eligible continuity-preserving route
- **AND** upstream fallback changes MUST NOT send the request to a stateless Platform path

#### Scenario: Upstream request normalization is retained

- **WHEN** a Responses or Chat request contains upstream-supported file, image, tool, or streaming fields
- **THEN** the merged service MUST normalize and forward those fields according to the merged contract
- **AND** fork-specific validation and API-key policy MUST still apply
