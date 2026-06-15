## ADDED Requirements

### Requirement: Usage refresh merges reset recovery and stale usage handling

The merged usage refresh policy MUST adopt upstream reset recovery, stale post-reset usage suppression, limit warmup trigger, Pro/weekly quota display, and model quota changes while preserving fork routing policy.

#### Scenario: Post-reset stale usage is ignored

- **GIVEN** an account has reset its quota window
- **WHEN** a delayed upstream usage response reports stale pre-reset consumption
- **THEN** the merged updater ignores the stale usage for quota availability
- **AND** dashboard quota display remains coherent.

#### Scenario: Warmup and recovery do not promote unsafe routing

- **WHEN** limit warmup or background recovery updates account status
- **THEN** primary and fallback eligibility remain separated according to fork routing policy
- **AND** API-key enforced service-tier behavior remains respected.
