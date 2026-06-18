## 1. Baseline And Safety Setup

- [x] 1.1 Create an isolated branch/worktree from `origin/main` using a branch name such as `codex/merge-upstream-v1-20-0`; do not merge in the current `main` checkout.
- [x] 1.2 Confirm the working tree in the implementation worktree is clean before merge work starts, and leave unrelated local files such as `.agents/settings.local.json` untouched.
- [x] 1.3 Fetch `origin` and `upstream` tags without force-updating colliding fork tags; record object IDs for `origin/main`, `v1.17.2`, upstream `v1.20.0`, and the merge base.
- [x] 1.4 Re-run `git merge-tree --name-only HEAD v1.20.0` from the implementation worktree and save the predicted conflict inventory in the PR notes.
- [x] 1.5 Generate fork-only and upstream-only file inventories with `git diff --name-only --diff-filter=A v1.20.0 HEAD` and `git diff --name-only --diff-filter=D v1.20.0 HEAD`; classify each high-risk delete before accepting it.
- [x] 1.6 Reconfirm that upstream `v1.20.0` is the source ref; do not use moving `upstream/main` unless it still resolves to the exact tag commit.

## 2. Fork Preservation Inventory

- [x] 2.1 Inventory release and CI surfaces: `.github/release-please-config.json`, `.github/release-please-manifest.json`, `.github/workflows/*`, release scripts, beta guards, and publish workflow inputs.
- [x] 2.2 Inventory package/install/runtime identity: `pyproject.toml`, `uv.lock`, `app/__init__.py`, `app/cli.py`, `app/cli_runtime.py`, Dockerfiles, Helm chart files, and frontend package metadata.
- [x] 2.3 Inventory fork proxy and provider behavior: `app/modules/proxy/**`, `app/core/clients/openai_platform.py`, `app/modules/upstream_identities/**`, provider adapters, upstream proxy routing, and Platform fallback policy.
- [x] 2.4 Inventory account, API-key, quota, request-log, reports, runtime, and sticky-session modules that exist in the fork and have no direct upstream equivalent.
- [x] 2.5 Inventory frontend fork workflows under accounts, dashboard, API keys, sticky sessions, reports, runtime, settings, and auth export.
- [x] 2.6 Inventory OpenSpec main specs and active changes; identify fork specs that upstream lacks and must not be deleted mechanically.

## 3. Start Merge And Resolve Metadata First

- [x] 3.1 Start the merge with `git merge --no-ff --no-commit v1.20.0` in the isolated worktree.
- [x] 3.2 Resolve `.github/release-please-manifest.json`, `.github/release-please-config.json`, release workflows, beta workflows, and release scripts so fork release policy and package names remain intact.
- [x] 3.3 Resolve `pyproject.toml`, `app/__init__.py`, `frontend/package.json`, Helm chart metadata, and Docker metadata so version surfaces read `1.20.0` while fork names and URLs remain fork-specific.
- [x] 3.4 Resolve `README.md` and `CHANGELOG.md` only as merge-history reconciliation; do not add new behavior documentation outside OpenSpec.
- [x] 3.5 Defer `uv.lock` and `frontend/bun.lock` final resolution until package manifests are intentionally resolved.

## 4. OpenSpec Reconciliation

- [x] 4.1 Resolve conflicted main specs under `openspec/specs/**` by preserving fork requirements and adding compatible upstream requirements; do not delete fork-only capabilities mechanically.
- [x] 4.2 Preserve active fork changes under `openspec/changes/**` unless a change is intentionally superseded and documented in the implementation notes.
- [x] 4.3 Keep `spec.md` requirements-only; put narrative rationale in change notes or capability `context.md` files if additional explanation is needed.
- [x] 4.4 Run `uv run openspec validate merge-upstream-v1-20-0 --strict` after OpenSpec conflict resolution.
- [x] 4.5 Run `uv run openspec validate --specs` before code validation gates.

## 5. Backend Runtime Reconciliation

- [x] 5.1 Resolve auth and dashboard-auth conflicts while preserving dashboard password, session refresh, TOTP, and guest read-only boundaries.
- [x] 5.2 Resolve accounts and API-key conflicts while preserving account assignment, enforced service tier, model visibility, reset-window behavior, and request-log attribution.
- [x] 5.3 Resolve Responses and Chat compatibility conflicts while preserving Codex continuity, durable bridge ownership, service-tier policy, file/image handling, streaming retry, and unsupported-parameter normalization.
- [x] 5.4 Resolve provider-management conflicts while preserving OpenAI Platform identity policy, upstream proxy routing, provider adapters, cache alerts, and fallback eligibility gates.
- [x] 5.5 Resolve proxy admission and sticky-session conflicts while preserving account routing, capacity controls, sticky affinity, file-id affinity, cleanup, and owner-forwarded bridge isolation.
- [x] 5.6 Resolve request-log, runtime observability, reports, usage refresh, quota planner, and warmup conflicts while preserving fork dashboard payloads and metrics/log fields.
- [x] 5.7 Resolve database model, session, backup, and Alembic conflicts so SQLite and PostgreSQL remain supported and migrations converge to a safe head.

## 6. Frontend Reconciliation

- [x] 6.1 Resolve frontend schemas only after backend schemas are stable; keep fork-only fields in API keys, accounts, dashboard, sticky sessions, settings, reports, runtime, and request logs.
- [x] 6.2 Resolve account/dashboard/sticky-session component conflicts without removing fork workflows or routes.
- [x] 6.3 Resolve settings, reports, runtime, auth export, and upstream proxy UI files that are fork-only or fork-modified.
- [x] 6.4 Update frontend mocks and integration tests so they cover preserved fork fields and adopted upstream fields.
- [ ] 6.5 Check responsive layout and text fit for changed UI surfaces if any frontend visual structure changes. Not run locally because frontend tooling was unavailable and Podman could not connect to its daemon.

## 7. Lockfiles, Generated Files, And Hygiene

- [x] 7.1 Regenerate `uv.lock` with `uv lock` after `pyproject.toml` is resolved.
- [x] 7.2 Regenerate or reconcile `frontend/bun.lock` after `frontend/package.json` is resolved; use Podman if host Bun/Node tooling is unavailable.
- [x] 7.3 Run formatters only after conflict markers are gone, and keep formatting changes scoped to touched files.
- [x] 7.4 Run `git diff --check` and confirm no conflict markers, absolute developer-machine paths, or unrelated local settings changes are present.

## 8. Validation Gates

- [x] 8.1 Run `uv run openspec validate merge-upstream-v1-20-0 --strict`.
- [x] 8.2 Run `uv run openspec validate --specs`.
- [x] 8.3 Run `uv run ruff check`, `uv run ruff format --check`, and `uv run ty check`.
- [x] 8.4 Run targeted Python tests for migrations, database repositories, auth, accounts, API keys, proxy Responses/Chat/files/images/transcriptions/WebSocket, sticky sessions, provider management, request logs, usage refresh, quota planner, reports, runtime, and release metadata.
- [ ] 8.5 Run Podman-backed PostgreSQL migration/repository tests if host services are unavailable. Not run: `podman ps` failed because the Podman socket refused connections.
- [ ] 8.6 Run frontend lint, typecheck, build, and tests with the repo's package manager; use Podman if host tooling is unavailable. Not run: host `bun` and `frontend/node_modules` were unavailable, and Podman could not connect to its daemon.
- [x] 8.7 Run Helm lint/template checks for the chart and External Secrets success/failure paths.
- [x] 8.8 Perform a final fork-preservation audit comparing the inventory from section 2 against the final diff.

## 9. Delivery

- [ ] 9.1 Commit the verified merge as an upstream integration commit or a small series of subsystem commits on the isolated branch.
- [ ] 9.2 Push only after local CI-equivalent checks pass or blockers are explicitly recorded.
- [ ] 9.3 Prepare a PR summary that includes source/target commits, conflict areas resolved, checks run, remaining risks, tag-provenance notes, and confirmation that fork-specific surfaces were preserved.
- [ ] 9.4 Do not publish a `v1.20.0` fork release until the merged fork commit is reviewed; if release is requested later, create or move the fork release tag only to the merged fork commit after validation.
