## Why

Platform fallback currently treats a compatible ChatGPT account with missing persisted usage snapshots as healthy. In practice that means an account with no usable quota data can suppress fallback even when every known account is already drained, which leaves requests stuck on the ChatGPT path instead of switching to the configured Platform backup.

## What Changes

- Treat compatible ChatGPT candidates as healthy for Platform-fallback suppression only when both required persisted usage snapshots are actually present and above the configured remaining-percent thresholds.
- Ensure all-missing and partial-missing usage snapshots do not keep Platform fallback idle.
- Add regression coverage for public and backend fallback when the pool contains a drained account plus another account with missing usage snapshots.

## Impact

- Platform fallback can activate when the system has no positively healthy ChatGPT candidate, even if some compatible accounts have all-missing or partial-missing usage data.
- Weekly-only quota plans keep their existing healthy behavior through the existing normalization path.
