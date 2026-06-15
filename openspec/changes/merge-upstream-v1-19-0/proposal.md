## Why

The fork is currently based on `origin/main` at `v1.17.2`, while upstream has released `v1.18.x` and `v1.19.0`. The histories diverge across proxy runtime behavior, account/dashboard UX, OpenSpec specs, migrations, CI/release metadata, frontend contracts, and lockfiles, so this update needs an explicit integration plan rather than a mechanical merge.

This change brings upstream behavior through tag `v1.19.0` into the fork while preserving fork-specific behavior such as the `codex-lb-cinamon` package identity, fork release policy, CLI lifecycle restoration, Platform fallback controls, Platform cache alerts, and enforced service-tier defaults.

## What Changes

- Merge upstream tag `v1.19.0` into the fork branch based on `origin/main`.
- Adopt upstream v1.18/v1.19 behavior for HTTP bridge/WebSocket continuity, request archive observability, account aliases, quota/cost dashboard views, API-key cost accounting, OAuth isolation, model visibility, reset recovery, stale usage handling, workflow hardening, Helm chart updates, frontend schemas, and dependency refreshes.
- Add upstream `files-upload-protocol` and `images-api-compat` main specs that are not present on the fork baseline.
- Preserve fork-only changes that do not exist upstream, especially Platform fallback/cache behavior, enforced service-tier defaults, CLI command surfaces, package/repository metadata, and release-please fork configuration.
- Reconcile predicted conflicts in metadata, backend proxy/account/request-log code, migrations, frontend account/dashboard code, OpenSpec specs, tests, and lockfiles.
- Validate the merged tree with OpenSpec, Python lint/type checks, targeted backend tests, frontend checks, and repository hygiene before pushing.

## Capabilities

### New Capabilities

- `files-upload-protocol`: Backend file upload and file-id routing behavior introduced by upstream.
- `images-api-compat`: OpenAI-compatible images API behavior introduced by upstream.

### Modified Capabilities

- `admin-auth`: Dashboard auth/session lifetime and OAuth isolation behavior must merge without weakening existing auth boundaries.
- `api-firewall`: Firewall cache and middleware behavior must keep the merged request path deterministic.
- `api-keys`: Account assignment, cost accounting, service-tier enforcement, and request-log filtering must remain coherent.
- `chat-completions-compat`: Chat payload sanitation and provider-specific alias normalization must align with upstream.
- `command-line-runtime-control`: Fork CLI lifecycle commands must remain available after upstream CLI changes.
- `database-backends`: Session ownership, background jobs, and dependency refresh behavior must preserve safe DB usage.
- `database-migrations`: Upstream migrations and fork migrations must converge to a single safe Alembic graph.
- `deployment-installation`: Docker, Helm, CI, release, dependency, and package metadata must merge while preserving fork identity.
- `deployment-networking`: Helm/network defaults and ingress-related values must remain renderable after upstream chart changes.
- `frontend-architecture`: Accounts, dashboard, API-key, archive, settings, and request-log UI contracts must match the merged backend.
- `proxy-runtime-observability`: Conversation archive, bridge observability, cache alerts, request-log details, and metrics must survive conflict resolution.
- `responses-api-compat`: HTTP bridge, WebSocket, compact failover, backend compatibility, model visibility, and Responses sanitation must merge with local continuity protections.
- `sticky-session-operations`: Sticky routing, bridge ownership, file affinity, and fallback decisions must remain deterministic.
- `upstream-provider-management`: Fork Platform fallback/provider semantics must not be accidentally removed by upstream's provider cleanup.
- `usage-refresh-policy`: Reset recovery, stale usage suppression, limit warmup, and quota display behavior must align with upstream while preserving local routing policy.

## Impact

- Merge base: `fd0fd085b2a813b4ed89f362f5aa0a43f84b21dd`.
- Fork baseline: `origin/main` at `8a6c9fde` (`v1.17.2`).
- Upstream source: tag `v1.19.0` at `9f3c805c`.
- Diff size observed: 785 files, 62558 insertions, 33665 deletions.
- Predicted conflict groups: release/package metadata, Docker/CI, backend proxy/account/request-log modules, Alembic models and migrations, Helm chart metadata, frontend accounts/dashboard tests and schemas, OpenSpec specs, Python tests, `frontend/bun.lock`, and `uv.lock`.
- No PR is created by this change. Delivery target is a pushed branch on `origin`.
