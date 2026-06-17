## ADDED Requirements

### Requirement: Usage refresh, quota planning, and reset-window behavior survive merge

The merged usage layer MUST preserve fork behavior for refresh scheduling, quota planner state, warmup exclusions, reset-window routing, and credit-backed availability while adopting compatible upstream fixes.

#### Scenario: Reset-window policy remains consistent

- **WHEN** usage refresh detects a changed or pending reset window
- **THEN** the merged service MUST preserve fork reset-window routing and availability behavior
- **AND** upstream usage changes MUST NOT mark accounts available or unavailable contrary to fork policy

#### Scenario: Quota planner outputs remain dashboard-compatible

- **WHEN** quota planner or usage summaries are returned to the dashboard
- **THEN** the merged payload MUST retain fields required by fork dashboard components
- **AND** frontend tests MUST cover those fields
