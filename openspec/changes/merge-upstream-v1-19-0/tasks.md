## 1. Baseline And Planning

- [x] 1.1 Create a new branch from latest `origin/main`.
- [x] 1.2 Fetch `upstream` tags and verify tag `v1.19.0` exists.
- [x] 1.3 Identify fork baseline, upstream source, merge base, diff size, and predicted conflict groups.
- [x] 1.4 Record fork-specific behavior that must survive the merge.
- [x] 1.5 Create OpenSpec proposal, design, tasks, and capability deltas for this upstream integration.

## 2. Merge And Conflict Resolution

- [x] 2.1 Merge `v1.19.0` with `--no-ff --no-commit`.
- [x] 2.2 Resolve release/package metadata while preserving fork identity and version consistency.
- [x] 2.3 Resolve OpenSpec specs and active upstream change artifacts without deleting fork-only requirements.
- [x] 2.4 Resolve backend proxy, account, API-key, usage, request-log, auth, settings, and database conflicts.
- [x] 2.5 Resolve Alembic graph/model/revision conflicts to one safe head.
- [x] 2.6 Resolve frontend account/dashboard/archive/settings/schema/test conflicts.
- [x] 2.7 Resolve Docker, Helm, CI, release, and dependency lockfile conflicts.
- [x] 2.8 Search for conflict markers and review fork-only behavior preservation before validation.

## 3. Validation

- [x] 3.1 Run `uv run openspec validate --specs`.
- [x] 3.2 Run `uv run ruff check`.
- [x] 3.3 Run `uv run ruff format --check`.
- [x] 3.4 Run `uv run ty check`.
- [x] 3.5 Run targeted backend tests for changed proxy/account/request-log/usage/auth/migration behavior.
- [x] 3.6 Run frontend checks using host tooling or Podman fallback.
- [x] 3.7 Run Helm/chart checks if chart conflict resolution changes rendered behavior.
- [x] 3.8 Run `git diff --check` and verify no conflict markers remain.

## 4. Delivery

- [x] 4.1 Mark completed OpenSpec tasks.
- [x] 4.2 Commit the merge and OpenSpec artifacts.
- [x] 4.3 Push the branch to `origin`.
- [x] 4.4 Report actual checks run, any blocked checks, and the pushed branch.
