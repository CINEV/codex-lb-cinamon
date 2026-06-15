## ADDED Requirements

### Requirement: Fork CLI lifecycle remains available after upstream CLI merge

The merged CLI MUST keep fork lifecycle commands and fork entry-point names available even when upstream CLI files or entry points change.

#### Scenario: Fork lifecycle command remains importable

- **WHEN** the fork package is installed after the merge
- **THEN** the fork-specific lifecycle CLI entry points import successfully
- **AND** upstream CLI changes do not remove the restored start, stop, restart, status, or log command surfaces.
