## ADDED Requirements

### Requirement: Fork Platform provider semantics survive upstream cleanup

The merge MUST preserve fork Platform fallback/provider behavior that remains required by local specs, even if upstream removes related provider identity modules.

#### Scenario: Platform fallback remains explicit

- **WHEN** routing evaluates whether a request can use Platform fallback
- **THEN** the decision uses the fork's explicit eligibility checks
- **AND** missing upstream provider identity modules do not silently broaden fallback eligibility.
