## ADDED Requirements

### Requirement: Upstream and fork migrations converge to one safe graph

The merged Alembic graph MUST include upstream v1.18/v1.19 migrations and fork migrations without losing schema needed by Platform fallback, request logs, sticky sessions, durable bridge state, account aliases, API-key model visibility, request-log indexes, soft deletes, and limit warmup triggers.

#### Scenario: Fork database upgrades through merged head

- **GIVEN** a database created from the fork baseline
- **WHEN** the merged application upgrades to Alembic `head`
- **THEN** the upgrade succeeds
- **AND** all fork and upstream schema elements required by the merged code are present.

#### Scenario: Legacy revision remaps do not skip required schema

- **GIVEN** a database records a legacy revision id recognized by migration remap logic
- **WHEN** startup remaps and upgrades the revision
- **THEN** newer current migrations still apply any schema that is not already present.
