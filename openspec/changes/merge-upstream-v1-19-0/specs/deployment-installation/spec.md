## ADDED Requirements

### Requirement: Deployment and release metadata preserve fork identity

The merged deployment files MUST adopt upstream Docker, Helm, CI, beta-release, dependency, and workflow hardening changes without reverting fork package identity, repository metadata, release-please policy, or origin-targeted delivery.

#### Scenario: Package identity remains fork-specific

- **WHEN** `pyproject.toml`, release manifests, workflows, lockfiles, and CLI entry points are resolved
- **THEN** they retain the fork package and repository identity
- **AND** upstream dependency and workflow updates are preserved where compatible.

#### Scenario: Release workflows do not target upstream by accident

- **WHEN** release or PR automation is inspected after the merge
- **THEN** it targets fork/origin repository policy unless an upstream PR is explicitly requested separately.

### Requirement: Fork CI excludes Helm and PostgreSQL-only test gates by default

The merged CI and local Makefile gates MUST exclude upstream Helm-specific tests, Helm smoke checks, and PostgreSQL-only test jobs unless the user confirms they are mandatory for a requested change.

#### Scenario: Standard CI omits upstream-only deployment test gates

- **WHEN** the fork CI workflow is inspected after this merge
- **THEN** it does not require Helm lint, Helm smoke, PostgreSQL pytest, or PostgreSQL migration-check jobs.

#### Scenario: Future upstream sync asks before reintroducing excluded gates

- **WHEN** a future upstream merge includes Helm-specific or PostgreSQL-only tests
- **AND** those tests appear mandatory for the requested change
- **THEN** the AI assistant asks the user before importing them into this fork.
