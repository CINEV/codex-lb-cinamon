## MODIFIED Requirements

### Requirement: Platform fallback uses the remaining percentages visible to operators

For phase-1 fallback, the service MUST treat a compatible ChatGPT-web candidate as healthy only while both persisted usage snapshots required for fallback evaluation are present and their remaining percentages satisfy `primary_remaining_percent > 10` and `secondary_remaining_percent > 5`. Compatible candidates with either snapshot missing MUST NOT count as healthy for suppressing Platform fallback. When no compatible ChatGPT-web candidate remains positively healthy under those thresholds, the service MAY consider `openai_platform` as fallback, subject to the existing route-family eligibility checks.

#### Scenario: A compatible ChatGPT-web candidate with more than 10 percent primary remaining and more than 5 percent secondary remaining keeps Platform idle

- **WHEN** a request targets an eligible Platform fallback route family
- **AND** both `chatgpt_web` and `openai_platform` are configured for that route family
- **AND** at least one compatible ChatGPT-web candidate has both `primary_remaining_percent > 10` and `secondary_remaining_percent > 5`
- **THEN** the service keeps routing through the ChatGPT-web pool

#### Scenario: Platform fallback may activate once no compatible candidate remains healthy under the remaining-percent thresholds

- **WHEN** a request targets an eligible Platform fallback route family
- **AND** both `chatgpt_web` and `openai_platform` are configured for that route family
- **AND** each compatible ChatGPT-web candidate has `primary_remaining_percent <= 10` or `secondary_remaining_percent <= 5`
- **THEN** the service MAY select the Platform identity as fallback for that request

#### Scenario: Missing usage snapshots do not suppress Platform fallback

- **WHEN** a request targets an eligible Platform fallback route family
- **AND** both `chatgpt_web` and `openai_platform` are configured for that route family
- **AND** every compatible ChatGPT-web candidate with known persisted usage is outside the configured fallback thresholds
- **AND** another compatible ChatGPT-web candidate is missing either the primary or secondary persisted usage snapshot required for fallback evaluation
- **THEN** the missing usage snapshot MUST NOT keep the request on the ChatGPT path
- **AND** the service MAY select the Platform identity as fallback for that request
