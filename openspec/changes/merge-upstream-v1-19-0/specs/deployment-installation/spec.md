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
