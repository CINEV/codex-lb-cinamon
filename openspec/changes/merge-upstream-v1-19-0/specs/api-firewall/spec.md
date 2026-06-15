## ADDED Requirements

### Requirement: Firewall and middleware behavior survives upstream request-path changes

The merged request path MUST keep API firewall cache semantics and middleware ordering coherent with upstream proxy and path rewrite changes.

#### Scenario: Firewall cache TTL remains effective

- **WHEN** repeated requests match the same firewall decision
- **THEN** the service reuses the cached decision according to the configured TTL
- **AND** upstream path rewrite or decompression changes do not bypass the firewall decision.
