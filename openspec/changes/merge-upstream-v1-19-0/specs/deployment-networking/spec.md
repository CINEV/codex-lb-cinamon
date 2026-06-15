## ADDED Requirements

### Requirement: Helm and network deployment values remain renderable

The merged Helm chart and deployment values MUST adopt upstream chart changes while preserving fork-specific values and network-facing configuration.

#### Scenario: Chart renders with fork values

- **WHEN** the merged Helm chart is rendered with the reference values
- **THEN** Kubernetes manifests render successfully
- **AND** fork-specific deployment values are not dropped.
