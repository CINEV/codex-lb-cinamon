## ADDED Requirements

### Requirement: Admission and routing controls remain policy driven

The merged proxy admission layer MUST preserve fork behavior for account routing, upstream proxy pools, capacity waiting, warmup, and work admission while adopting compatible upstream routing fixes.

#### Scenario: Account routing constraints are enforced

- **WHEN** a request is constrained to a selected account, routing policy, or traffic class
- **THEN** the merged admission layer MUST enforce that constraint before selecting an upstream
- **AND** upstream route selection changes MUST NOT bypass fork admission policy

#### Scenario: Capacity controls remain observable

- **WHEN** a request waits, drains, or is rejected because capacity is unavailable
- **THEN** the merged service MUST preserve fork observability for the admission decision
- **AND** tests MUST cover the selected wait or rejection behavior
