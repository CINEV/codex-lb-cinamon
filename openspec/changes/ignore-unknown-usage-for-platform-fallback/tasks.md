## 1. Implementation

- [x] 1.1 Update Platform-fallback health evaluation so missing usage snapshots do not count as healthy ChatGPT candidates.
- [x] 1.2 Preserve weekly-only quota behavior while changing the unknown-usage fallback logic.

## 2. Verification

- [x] 2.1 Add unit coverage for all-missing, partial-missing, and weekly-only fallback decisions.
- [x] 2.2 Add integration coverage showing public and backend routes fall back to Platform when the remaining ChatGPT candidate has missing usage snapshots.
- [x] 2.3 Validate the touched specs with `openspec validate --specs`.
