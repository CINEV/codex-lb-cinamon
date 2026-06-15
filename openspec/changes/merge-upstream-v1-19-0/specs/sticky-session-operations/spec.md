## ADDED Requirements

### Requirement: Sticky routing remains deterministic after v1.19 merge

The merged routing implementation MUST keep sticky-session, prompt-cache, file-id affinity, bridge owner, soft-drain, same-account takeover, and fallback decisions deterministic.

#### Scenario: File and prompt affinity select eligible accounts

- **GIVEN** a file, prompt cache key, or continuity owner is associated with an account
- **WHEN** a later request references that affinity source
- **THEN** routing selects the associated account when eligible
- **AND** fallback only occurs according to the merged failure policy.

#### Scenario: Owner handoff avoids routing loops

- **WHEN** a hard-continuity bridge request reaches a non-owner instance
- **THEN** the merged service forwards to the owner or fails closed according to the owner policy
- **AND** it does not create an unsafe local session that breaks continuity.
