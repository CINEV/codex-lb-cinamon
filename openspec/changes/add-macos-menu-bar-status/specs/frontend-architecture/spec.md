## ADDED Requirements

### Requirement: macOS menu bar dashboard summary
The product SHALL provide a macOS menu bar status app that shows primary-window remaining capacity and exposes basic dashboard information without requiring the browser dashboard to be open.

#### Scenario: Show compact 5h remaining capacity
- **WHEN** the menu bar app successfully reads dashboard overview data
- **THEN** the menu bar title displays primary 5h remaining capacity as `5h N%`, where `N` is derived from `summary.primaryWindow.remainingPercent`
- **AND** the title does not append `left` or `used`

#### Scenario: Show unavailable 5h remaining capacity
- **WHEN** dashboard overview data is unavailable, malformed, or missing primary remaining percentage
- **THEN** the menu bar title displays `5h --`

#### Scenario: Open basic information menu
- **WHEN** a user clicks the macOS menu bar item
- **THEN** the menu shows last sync, routing, version, account status counts, primary and secondary remaining capacity, request count, token count, cost, and error rate when those values are available
- **AND** the menu shows a dashboard-style 5h remaining donut with account remaining-credit legend and used capacity when usage-window data is available
- **AND** the menu shows per-account summary cards with display name, plan, status badge, 5h and weekly remaining-capacity bars, reset timing, and a details action when account data is available
- **AND** the menu lets the user toggle between the dashboard-style donut and per-account progress bars so only one quota visualization is visible at a time
- **AND** the quota-view toggle and refresh controls appear in the quota visualization header and do not dismiss the menu when clicked

#### Scenario: Handle protected dashboards
- **WHEN** the dashboard requires a password session
- **THEN** the menu bar app can be launched with a dashboard session cookie value and sends it to the existing dashboard APIs

#### Scenario: Handle unsupported platforms
- **WHEN** a user tries to launch the menu bar app outside macOS
- **THEN** the command exits with a clear unsupported-platform message
