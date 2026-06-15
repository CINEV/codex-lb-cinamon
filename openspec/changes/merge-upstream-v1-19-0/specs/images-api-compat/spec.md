## ADDED Requirements

### Requirement: OpenAI-compatible images API uses merged proxy controls

The upstream OpenAI-compatible images API MUST be adopted with request translation, validation, and response mapping intact. The merged implementation MUST route image generation through existing proxy admission and account-selection controls instead of creating a bypass path.

#### Scenario: Images request uses proxy controls

- **WHEN** a client sends a valid OpenAI-compatible image generation request
- **THEN** the service validates and translates the request according to the images API contract
- **AND** account selection, request admission, auth, rate-limit accounting, and error handling run through the merged proxy controls.

#### Scenario: Invalid images request is rejected consistently

- **WHEN** a client sends an invalid images API payload
- **THEN** the service returns a stable OpenAI-style error envelope
- **AND** the request is not forwarded upstream.
