## ADDED Requirements

### Requirement: Runtime metadata and paths remain portable after merge

The merged runtime MUST report fork metadata and use portable paths after adopting upstream runtime changes.

#### Scenario: Fork version and package identity are coherent

- **WHEN** runtime version checks run after the merge
- **THEN** the package MUST report version `1.20.0`
- **AND** the package name and repository metadata MUST remain fork-specific

#### Scenario: Runtime files avoid machine-specific paths

- **WHEN** the runtime writes logs, debug dumps, backups, or state files
- **THEN** paths MUST be derived from configuration or runtime directories
- **AND** no developer-machine absolute path MUST be introduced by the merge
