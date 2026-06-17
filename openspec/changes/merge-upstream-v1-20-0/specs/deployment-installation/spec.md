## ADDED Requirements

### Requirement: Fork release and install identity survive v1.20.0 merge

The merged deployment and install surfaces MUST report version `1.20.0` while preserving fork package, repository, CLI, Docker, Helm, and release automation identity.

#### Scenario: Package metadata remains fork-specific

- **WHEN** `pyproject.toml`, `app/__init__.py`, lockfiles, and release metadata are resolved
- **THEN** version surfaces MUST align to `1.20.0`
- **AND** package names, repository URLs, and CLI names MUST remain fork-specific

#### Scenario: Helm chart remains renderable

- **WHEN** Helm validation runs after the merge
- **THEN** the chart MUST render with fork deployment values
- **AND** upstream chart changes MUST NOT remove fork-required External Secrets behavior

#### Scenario: Release automation does not trust colliding tag names

- **WHEN** release automation evaluates the merged fork for publication
- **THEN** it MUST verify that the fork release tag points at the merged fork commit
- **AND** it MUST NOT rely on an upstream tag object solely because the tag name matches
