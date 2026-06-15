# deployment-installation Specification

## Purpose

Define installation modes and smoke-test expectations so the Helm chart remains portable across supported deployments.

## Requirements

### Requirement: Helm chart is organized around install modes

The Helm chart MUST document and support three primary install modes: bundled PostgreSQL, direct external database, and external secrets. These install contracts MUST be portable across Kubernetes providers without requiring provider-specific chart forks.

#### Scenario: Bundled mode values exist

- **WHEN** a user wants a self-contained install
- **THEN** the chart provides a bundled mode values overlay with bundled PostgreSQL enabled

#### Scenario: External DB mode values exist

- **WHEN** a user wants to install against an already reachable PostgreSQL database
- **THEN** the chart provides an external DB values overlay and accepts direct DB URL or DB secret wiring

#### Scenario: External secrets mode values exist

- **WHEN** a user wants to source credentials from External Secrets Operator
- **THEN** the chart provides an external secrets values overlay that keeps migration and startup behavior fail-closed

#### Scenario: External secrets mode requires a SecretStore reference

- **WHEN** external secrets mode is enabled without `externalSecrets.secretStoreRef.name`
- **THEN** Helm rendering fails with an explicit configuration error

### Requirement: Helm chart checks are not default CI gates

The fork MUST NOT require Helm lint, Helm render, kubeconform, or kind smoke checks as default CI gates unless a change explicitly targets Helm deployment behavior.

#### Scenario: Default CI excludes Helm checks

- **WHEN** the standard CI workflow runs for a non-Helm change
- **THEN** it does not require Helm lint, render, kubeconform, or kind smoke jobs

#### Scenario: Helm-specific changes may opt in

- **WHEN** a change explicitly targets Helm deployment behavior
- **THEN** maintainers may run Helm checks manually or add a scoped validation path for that change

### Requirement: Helm support policy is pinned to modern Kubernetes minors

The chart MUST declare a minimum supported Kubernetes version of `1.32`, but the fork does not require Kubernetes render validation as a default CI gate.

#### Scenario: Chart metadata declares the minimum supported version

- **WHEN** a user inspects the chart metadata and README
- **THEN** the documented minimum supported Kubernetes version is `1.32`

#### Scenario: CI does not require Kubernetes render validation

- **WHEN** standard CI runs for a non-Helm change
- **THEN** Kubernetes render validation is not required
