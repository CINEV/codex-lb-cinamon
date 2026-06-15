## Context

`origin/main` is a fork branch at `v1.17.2`. Upstream tag `v1.19.0` includes release `v1.18.0`, `v1.18.1`, `v1.18.2`, beta release workflow additions, and final `v1.19.0` release changes. The comparison is not a fast-forward: `git merge-tree` predicts conflicts across metadata, backend runtime modules, frontend account/dashboard surfaces, OpenSpec specs, tests, and lockfiles.

Fork-only behavior that must survive includes:

- `codex-lb-cinamon` package and repository identity.
- Fork release-please manifest/configuration and origin-targeted delivery policy.
- Restored CLI lifecycle commands.
- Platform fallback semantics, Platform cache alert behavior, and enforced service-tier defaults.
- Local OpenSpec changes that encode the above fork contracts.

## Goals

- Adopt upstream tag `v1.19.0`, not later `upstream/main` changes.
- Keep fork-specific package, CLI, release, provider, and fallback behavior intentional.
- Resolve conflicts by subsystem so fork-only and upstream-only behavior can be reviewed.
- Keep OpenSpec requirements, implementation, tests, and lockfiles consistent.
- Push a branch only after local CI-equivalent checks have run.

## Non-Goals

- Do not rename the fork package, CLI entry points, or repository URLs back to upstream defaults.
- Do not create an upstream PR.
- Do not archive unrelated active OpenSpec changes.
- Do not require a container image build unless container packaging behavior itself is changed.
- Do not add feature documentation under `docs/`; keep behavioral notes under OpenSpec.

## Merge Strategy

1. Work from a clean branch based on `origin/main`.
2. Create OpenSpec artifacts before code merge so the conflict policy is explicit.
3. Merge `v1.19.0` with `--no-ff --no-commit` so conflicts can be resolved before the integration commit.
4. Resolve identity and release metadata first:
   - Keep `codex-lb-cinamon`, fork URLs, fork workflows, and fork release-please configuration.
   - Align version surfaces to the upstream release version only where that does not revert fork identity.
5. Resolve OpenSpec specs before runtime code where possible:
   - Keep fork requirements for Platform fallback, provider management, API-key enforced tiers, CLI lifecycle behavior, and cache alerts.
   - Add upstream requirements for files/images APIs, conversation archive, account aliasing, quota/cost UI, bridge continuity, model visibility, reset recovery, and workflow hardening.
6. Resolve backend conflicts by subsystem:
   - Proxy/Responses routing, HTTP bridge, WebSocket, compact failover, and model compatibility.
   - Account alias, quota, token refresh, OAuth isolation, usage refresh, and API-key cost behavior.
   - Request log repository, archive lookup, and dashboard response schemas.
   - Alembic graph, revision remaps, DB model fields, and background task session ownership.
7. Resolve frontend conflicts after backend schemas are settled:
   - Accounts list/detail/actions/hooks.
   - Dashboard account cards, recent requests, cost/pace utilities, and test setup.
   - Conversation archive and request-log detail surfaces.
8. Regenerate lockfiles only after package manifests are intentionally resolved.

## Risk Areas

- Upstream deletes provider identity modules that are related to fork Platform fallback behavior.
- Upstream package/release metadata can accidentally revert the fork to upstream identity.
- `app/modules/proxy/service.py`, `api.py`, `load_balancer.py`, and `sticky_repository.py` contain overlapping upstream bridge changes and fork fallback protections.
- `app/db/models.py`, Alembic revisions, and revision remaps can silently skip fork schema requirements if resolved incorrectly.
- Frontend schema tests can pass while backend payloads drift if request-log/account/dashboard integration tests are not included.
- `uv.lock` and `frontend/bun.lock` conflicts can hide unintended dependency downgrades or package name changes.

## Validation Plan

- OpenSpec: `uv run openspec validate --specs`.
- Python style/type: `uv run ruff check`, `uv run ruff format --check`, and `uv run ty check`.
- Backend tests: targeted migration, proxy, HTTP bridge, WebSocket, accounts, API keys, request logs, usage refresh, settings/auth, load-balancer, sticky-session, and graceful degradation suites.
- Database: use Podman-backed PostgreSQL for migration/repository tests when host services are not already available.
- Frontend: run the repo's frontend type/test/lint flow; use Podman Node/Bun if host tooling is insufficient.
- Helm/CI metadata: run local render/lint checks when chart files change.
- Hygiene: `git diff --check`, conflict marker search, and final inventory of preserved fork-only behavior before commit and push.

## Rollback Plan

Keep the upstream import as one integration commit after validation. If validation fails before commit, abort or reset the uncommitted merge and reapply accepted resolutions by subsystem. If a bad merge is committed but not pushed, revert the integration commit rather than rewriting unrelated history.
