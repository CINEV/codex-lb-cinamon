## ADDED Requirements

### Requirement: Fork CLI entry points remain available

The merged runtime MUST keep fork CLI entry points and lifecycle commands importable and executable after adopting upstream CLI changes.

#### Scenario: Installed fork exposes CLI commands

- **WHEN** the merged package is installed
- **THEN** the fork CLI entry points MUST resolve to valid Python callables
- **AND** command behavior MUST remain covered by CLI tests

#### Scenario: Runtime commands use portable paths

- **WHEN** a CLI command reads or writes runtime state
- **THEN** it MUST derive paths from settings or runtime context
- **AND** it MUST NOT contain developer-machine absolute paths
