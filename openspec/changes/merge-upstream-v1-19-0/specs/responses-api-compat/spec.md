## ADDED Requirements

### Requirement: Responses merge preserves upstream continuity fixes and fork fallback safety

The merged Responses implementation MUST include upstream v1.18/v1.19 fixes for HTTP bridge continuity, WebSocket errors, compact failover, backend compatibility, model visibility, oversized/compressed payloads, stale anchors, previous-response recovery, image generation tool advertisement, and payload sanitation. These changes MUST NOT weaken fork protections that keep continuity-bearing Codex requests on eligible continuity-preserving paths instead of unsafe Platform fallback paths.

#### Scenario: HTTP bridge continuity recovers or fails closed

- **WHEN** an HTTP bridge or WebSocket follow-up loses upstream previous-response continuity
- **THEN** the service either recovers through the merged continuity path or returns a retryable continuity failure
- **AND** it does not expose raw upstream continuity errors for internal bridge metadata loss.

#### Scenario: Backend-compatible Responses payloads are accepted

- **WHEN** a client sends an OpenAI-style or backend Codex Responses request shape supported by upstream v1.19.0
- **THEN** the merged service normalizes and forwards the supported payload
- **AND** unsupported provider-specific controls are stripped or normalized according to the merged contract.

#### Scenario: Continuity-bearing request avoids unsafe Platform fallback

- **GIVEN** a request depends on continuity state such as `previous_response_id`, prompt-cache locality, owner-forwarded bridge state, or file affinity
- **WHEN** the merged routing code evaluates fallback eligibility
- **THEN** the request remains on an eligible continuity-preserving route
- **AND** fork Platform fallback is not selected for that continuity-bearing request unless the merged contract explicitly proves it is safe.
