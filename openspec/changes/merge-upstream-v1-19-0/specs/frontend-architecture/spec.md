## ADDED Requirements

### Requirement: Frontend contracts match merged account and dashboard behavior

The frontend MUST adopt upstream account alias, cost, quota, conversation archive, request-log, dashboard, and schema changes while preserving fork-only fields that remain present in the merged backend.

#### Scenario: Accounts UI supports aliases and quota rows

- **WHEN** the account list and detail pages render merged account payloads
- **THEN** they support account aliases, primary/weekly quota rows, reset timing, and existing account actions
- **AND** fork-specific labels and payload fields are not dropped from schemas or mocks.

#### Scenario: Dashboard request details include archive and cost data

- **WHEN** an operator opens a request-log detail view
- **THEN** the UI can render merged cost breakdown and conversation archive records when available
- **AND** existing request-log columns and filters continue to work.
