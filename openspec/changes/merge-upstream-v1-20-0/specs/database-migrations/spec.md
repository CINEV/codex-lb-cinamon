## ADDED Requirements

### Requirement: Alembic graph preserves fork and upstream migration history

The merged Alembic graph MUST include required upstream heads while preserving fork migrations, revision remaps, and merge heads needed by current fork installations.

#### Scenario: Upgrade graph has a safe head

- **WHEN** migration validation runs after conflict resolution
- **THEN** Alembic MUST expose a coherent upgrade graph with no accidental fork-only head loss
- **AND** upgrade tests MUST cover the merged head path

#### Scenario: Fork migration files are not deleted mechanically

- **WHEN** upstream lacks a migration that exists only in the fork
- **THEN** the merge MUST keep or intentionally supersede that migration
- **AND** the decision MUST be validated by migration tests rather than file deletion alone
