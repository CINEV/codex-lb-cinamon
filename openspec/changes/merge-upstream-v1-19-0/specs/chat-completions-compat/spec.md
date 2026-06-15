## ADDED Requirements

### Requirement: Chat payload sanitation adopts upstream alias handling

The merged Chat Completions path MUST preserve upstream fixes for JSON-mode instruction handling and provider-specific thinking alias normalization without forwarding unsupported provider controls unchanged.

#### Scenario: JSON-mode instruction messages are preserved

- **WHEN** a chat request uses JSON mode with instruction-like messages
- **THEN** the merged sanitizer preserves the messages needed by upstream
- **AND** unsupported advisory aliases are normalized or removed according to the merged contract.
