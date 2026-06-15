## ADDED Requirements

### Requirement: Upstream file upload protocol preserves account affinity

The upstream file upload protocol MUST be adopted so backend file creation and finalization are available through the merged proxy surface. File identifiers created through the protocol MUST preserve the upstream account affinity needed by later Responses requests.

#### Scenario: Uploaded file drives later Responses routing

- **GIVEN** a client uploads a file through the merged backend files protocol
- **WHEN** a later Responses request references the uploaded `file_id`
- **THEN** routing uses the account affinity recorded for that file when eligible
- **AND** the request is not routed to an unrelated upstream account.

#### Scenario: File failures use proxy protections

- **WHEN** a file operation fails due to timeout, upstream error, invalid payload, or auth failure
- **THEN** the service returns the merged proxy error shape for that route
- **AND** request admission, auth, and rate-limit protections remain in force.
