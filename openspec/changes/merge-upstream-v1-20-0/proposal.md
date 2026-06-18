## Why

The fork is currently back at `origin/main` / `v1.17.2` after a previous upstream sync attempt overwrote fork-specific behavior. Upstream has now released `v1.20.0`, so the fork needs a planned integration that adopts upstream fixes without reverting local package identity, release policy, dashboard/runtime features, or OpenSpec requirements.

This change records the integration contract before any merge work so conflict resolution can be audited against fork-owned behavior instead of accepting upstream files wholesale.

## What Changes

- Define the upstream source as tag `v1.20.0` at `57b5e067`, not the moving upstream branch after that tag.
- Define the fork baseline as `origin/main` / `v1.17.2` at `8a6c9fde`, with merge base `fd0fd085`.
- Require implementation to use an isolated branch/worktree and a non-committed merge (`git merge --no-ff --no-commit v1.20.0`) so the main checkout and local settings remain untouched.
- Preserve fork-specific surfaces, including `codex-lb-cinamon` package identity, fork URLs, CLI entry points, release-please configuration, stable/beta release controls, dashboard/runtime features, Platform fallback policy, account routing, quota planning, reports, and fork OpenSpec specs.
- Adopt upstream `v1.20.0` behavior where compatible, including runtime, proxy, auth, frontend, Helm, CI, dependency, and test fixes.
- Treat tag namespace conflicts as a first-class release risk: upstream tag names that collide with fork tags MUST NOT overwrite fork tags unless explicitly reviewed.
- Align post-merge fork version surfaces to `1.20.0` while keeping fork package/repository names.
- Reconcile the predicted conflict set before committing, especially release/CI metadata, backend proxy/accounts/sticky/request-log code, frontend account/dashboard/sticky schemas, OpenSpec main specs, tests, and lockfiles.
- Keep feature and behavior documentation under OpenSpec only. Do not add or update `docs/` behavior docs, and do not hand-edit `CHANGELOG.md` beyond merge-history conflict resolution.
- Validate with local CI-equivalent checks before push; use Podman for host-environment gaps and do not require an image build unless container packaging behavior changes.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `admin-auth`: dashboard auth/session behavior and upstream auth changes must merge without weakening fork auth boundaries.
- `api-keys`: API-key service-tier, account assignment, quota reset, and reporting behavior must survive upstream routing and schema changes.
- `command-line-runtime-control`: fork CLI entry points and lifecycle/runtime commands must remain available after upstream CLI changes.
- `database-backends`: database session, pool, SQLite/PostgreSQL, and backup behavior must converge without dropping fork persistence guarantees.
- `database-migrations`: Alembic heads and remaps must preserve fork migrations while adopting upstream heads.
- `deployment-installation`: Helm, Docker, package metadata, and install surfaces must adopt upstream fixes while keeping fork release identity.
- `frontend-architecture`: dashboard, accounts, API keys, sticky sessions, reports, settings, runtime, and auth UI contracts must keep fork features while adopting upstream UI fixes.
- `proxy-admission-control`: account routing, upstream proxy admission, work admission, and capacity controls must remain coherent after merge.
- `proxy-runtime-observability`: request logs, metrics, runtime headers, platform cache alerts, and streaming observability must not regress.
- `responses-api-compat`: Responses/Chat compatibility, file/image handling, Codex continuity, Platform fallback, and streaming behavior must be merged intentionally.
- `runtime-portability`: package/runtime paths and installed metadata must remain portable and fork-specific.
- `sticky-session-operations`: sticky routing, durable bridge, file-id affinity, and continuity behavior must stay deterministic.
- `upstream-provider-management`: OpenAI Platform identities, upstream proxy routing, and fallback policy must preserve fork constraints.
- `usage-refresh-policy`: quota refresh, planner, warmup, and reset-window behavior must survive upstream changes.

## Impact

- Merge scope observed: 1421 files changed between `v1.17.2` and upstream `v1.20.0`, with about 164k insertions and 50k deletions.
- Predicted conflict files include `.dockerignore`, `.github/release-please-manifest.json`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `CHANGELOG.md`, `Dockerfile`, `README.md`, `pyproject.toml`, `uv.lock`, `frontend/bun.lock`, backend proxy/account/sticky/request-log modules, frontend account/dashboard/sticky files, OpenSpec main specs, and targeted tests.
- `git fetch upstream --tags` brought in `v1.20.0` but rejected older colliding upstream tags such as `v1.15.0`, `v1.16.0`, `v1.17.0`, and `v1.19.0`; implementation must keep fork tag provenance explicit.
- High-risk fork-only surfaces include `.github` release/beta automation, `scripts/release_*`, `app/cli_runtime.py`, OpenAI Platform identity modules, upstream proxy routing, quota planner/reports/runtime modules, frontend reports/settings/runtime screens, and many OpenSpec capabilities.
- Successful completion requires OpenSpec validation, backend lint/type/test gates, migration checks, frontend checks, Helm rendering checks, diff hygiene, and a final fork-preservation audit.
