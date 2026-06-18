## Context

The fork is currently at `origin/main` / `v1.17.2` (`8a6c9fde`). Upstream `v1.20.0` is tag `57b5e067`; the merge base is `fd0fd085`. A direct comparison spans 1421 files, about 164k insertions and 50k deletions. A dry merge predicts conflicts across release metadata, CI, Docker/install files, backend proxy/account/sticky/request-log modules, frontend account/dashboard/sticky code, OpenSpec specs, tests, and lockfiles.

The previous upstream sync failure mode was accepting too much upstream state and losing fork-owned behavior. This design therefore treats the merge as a preservation exercise first and an upstream adoption exercise second. Upstream changes are accepted only after the fork contract is identified for the touched subsystem.

The current working tree also contains an unrelated untracked `.agents/settings.local.json`. Implementation MUST leave unrelated local files untouched.

## Goals / Non-Goals

**Goals:**

- Integrate upstream `v1.20.0` into the fork from a reproducible baseline.
- Preserve fork package identity, repository metadata, release automation policy, CLI entry points, OpenSpec capabilities, dashboard/runtime features, and proxy fallback behavior.
- Resolve conflicts by subsystem so each local-only feature has an explicit keep/adopt decision.
- Align the merged fork version to `1.20.0` while retaining fork names such as `codex-lb-cinamon`.
- Produce a merge branch that can pass local CI-equivalent validation before push.

**Non-Goals:**

- Do not rename the fork back to upstream package, binary, repository, or release identity.
- Do not overwrite fork tags with upstream tags that happen to share names.
- Do not archive unrelated active OpenSpec changes during the merge.
- Do not add or update behavior docs under `docs/`; keep behavior documentation in OpenSpec.
- Do not require a container image build unless the implementation changes Docker/package runtime behavior.

## Decisions

### Decision: Merge the upstream tag, not moving upstream/main

Use `v1.20.0` as the source ref for implementation. The tag currently resolves to the same commit as `upstream/main`, but the tag is immutable in intent and matches the requested release. The alternative, merging `upstream/main`, would allow later upstream commits to enter the fork without being part of the planned scope.

### Decision: Use an isolated branch/worktree

Implementation MUST happen outside the current `main` checkout, on a branch such as `codex/merge-upstream-v1-20-0`. The merge should be started with `git merge --no-ff --no-commit v1.20.0` so conflict resolutions can be reviewed before the integration commit. The alternative, merging directly in the current checkout, risks contaminating local user files and repeats the prior failure mode.

### Decision: Create a fork preservation inventory before resolving conflicts

Before accepting upstream versions of conflicted files, implementation MUST inventory fork-only and fork-modified surfaces. At minimum this includes:

- release and CI: `.github/release-please-config.json`, `.github/release-please-manifest.json`, `.github/workflows/*`, `scripts/release_*`, `scripts/guard_beta_release.py`
- package/install/runtime: `pyproject.toml`, `uv.lock`, `app/__init__.py`, `app/cli.py`, `app/cli_runtime.py`, Dockerfiles, Helm chart files
- proxy/runtime: `app/modules/proxy/**`, `app/core/clients/openai_platform.py`, `app/modules/upstream_identities/**`, `app/core/upstream_proxy/**`
- account/quota/reporting: `app/modules/accounts/**`, `app/modules/api_keys/**`, `app/modules/usage/**`, `app/modules/quota_planner/**`, `app/modules/reports/**`
- frontend: `frontend/src/features/accounts/**`, `frontend/src/features/dashboard/**`, `frontend/src/features/settings/**`, `frontend/src/features/reports/**`, `frontend/src/features/runtime/**`, `frontend/src/features/sticky-sessions/**`
- OpenSpec: `openspec/specs/**`, `openspec/changes/**`

The alternative, resolving conflicts file-by-file without a preservation inventory, can pass tests while silently dropping fork-only behaviors that have no upstream equivalent.

### Decision: Resolve OpenSpec before implementation conflicts

For conflicted behavioral areas, update or preserve OpenSpec requirements before finalizing code conflict resolution. This keeps `spec.md` normative and prevents implementation from becoming the only source of truth. Narrative notes can live in this change's context or in capability context docs after implementation. The alternative, updating specs after code, makes it easier to backfill docs to match accidental behavior.

### Decision: Treat release tags as two namespaces even when names collide

The local fetch showed upstream tags `v1.15.0`, `v1.16.0`, `v1.17.0`, and `v1.19.0` collided with existing fork tags. Implementation MUST verify whether a tag is from fork or upstream before using it for release automation. The fork's future `v1.20.0` release tag MUST point to the merged fork commit, not blindly reuse upstream tag provenance. The alternative, trusting tag names alone, can retrigger release-please train confusion.

### Decision: Regenerate lockfiles only after metadata is intentionally resolved

`uv.lock` and `frontend/bun.lock` are conflicted and high churn. Resolve `pyproject.toml` and `frontend/package.json` first, preserving fork identity and setting version surfaces to `1.20.0`; then regenerate lockfiles with the repo's standard tooling. The alternative, accepting one side of lockfiles early, can pin dependencies that no longer match resolved manifests.

## Merge Plan

1. Create an isolated branch/worktree from `origin/main`.
2. Fetch `origin` and `upstream` tags without force-updating colliding fork tags.
3. Reconfirm `v1.20.0`, merge base, diff stat, and `git merge-tree` conflict set.
4. Build the fork preservation inventory from fork-only files and current OpenSpec capabilities.
5. Start `git merge --no-ff --no-commit v1.20.0`.
6. Resolve metadata and release files first, keeping fork package/repository/release identity.
7. Resolve OpenSpec main specs and capability deltas next.
8. Resolve backend runtime conflicts by subsystem: auth/accounts, proxy/Responses, admission/routing, sticky bridge, request logs, usage/quota, migrations, database sessions.
9. Resolve frontend contracts after backend schemas are stable.
10. Regenerate lockfiles and any generated frontend schemas only after manifests are final.
11. Run validation gates and inspect final diff for lost fork behavior.
12. Commit and push only after local CI-equivalent validation passes or blockers are explicitly documented.

## Risks / Trade-offs

- Tag collision can confuse release automation -> verify fork and upstream tag object IDs before release work, and create the fork `v1.20.0` tag only on the merged fork commit.
- Upstream may delete files that are fork-owned -> classify `git diff --diff-filter=D v1.20.0 HEAD` entries before accepting deletes.
- Upstream may add replacement architecture for fork code -> prefer merged behavior only when tests and specs prove the fork contract is still satisfied.
- OpenSpec conflicts can be mechanically resolved but semantically wrong -> run `uv run openspec validate --specs` and review changed specs by capability.
- Frontend tests can pass with stale mocks -> validate backend schemas, frontend schemas, mocks, and integration tests together.
- Migration heads can silently fork -> run Alembic graph and upgrade tests against SQLite and PostgreSQL when possible.
- Full validation may exceed the host environment -> use Podman for PostgreSQL or frontend tooling gaps and record any remaining blocker.

## Validation Strategy

- OpenSpec: `uv run openspec validate --specs` and `uv run openspec validate merge-upstream-v1-20-0 --strict`.
- Python hygiene: `uv run ruff check`, `uv run ruff format --check`, `uv run ty check`.
- Backend tests: targeted migration, proxy Responses/Chat/files/images/transcriptions/WebSocket, admission/routing, sticky sessions, API keys, request logs, auth, settings, usage/quota, runtime, reports, and release-version tests.
- Database tests: use Podman-backed PostgreSQL if the host database is unavailable.
- Frontend: run the repo's Bun/Node lint, typecheck, build, and test commands; use Podman if host tooling is not ready.
- Helm/deployment: lint/template the chart and External Secrets paths.
- Diff hygiene: `git diff --check`, no conflict markers, no absolute developer-machine paths, no unrelated `.agents/settings.local.json` changes.

## Open Questions

- Whether to split the actual implementation into multiple PRs if conflict resolution proves too large for one review. The default remains one integration branch, but the branch should be organized by subsystem commits if possible.
- Whether the fork should publish a stable `v1.20.0` immediately after merge or defer release publication to a separate explicit release step.
