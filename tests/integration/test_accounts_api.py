from __future__ import annotations

import base64
import json

import pytest
from sqlalchemy import func, select

import app.modules.accounts.service as accounts_service_module
import app.modules.proxy.provider_adapters as provider_adapters_module
from app.core.auth import DEFAULT_EMAIL, generate_unique_account_id, parse_auth_json
from app.core.clients.openai_platform import OpenAIPlatformError, PlatformModelsResponse
from app.core.utils.time import utcnow
from app.db.models import Account, AccountStatus, OpenAIPlatformIdentity, RequestLog, StickySession, StickySessionKind
from app.db.session import SessionLocal
from app.modules.upstream_identities.repository import (
    OpenAIPlatformIdentitiesRepository,
    OpenAIPlatformIdentityConflictError,
    OpenAIPlatformIdentityCreate,
    split_route_families,
)
from app.modules.upstream_identities.types import PlatformRouteFamily

pytestmark = pytest.mark.integration


def _encode_jwt(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    body = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    return f"header.{body}.sig"


EXPECTED_PLATFORM_ROUTE_FAMILY_TUPLE: tuple[PlatformRouteFamily, ...] = (
    "backend_codex_http",
    "public_models_http",
    "public_responses_http",
)
EXPECTED_PLATFORM_ROUTE_FAMILIES = list(EXPECTED_PLATFORM_ROUTE_FAMILY_TUPLE)


def _make_auth_json(account_id: str, email: str) -> dict[str, object]:
    payload = {
        "email": email,
        "chatgpt_account_id": account_id,
        "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"},
    }
    return {
        "tokens": {
            "idToken": _encode_jwt(payload),
            "accessToken": "access",
            "refreshToken": "refresh",
            "accountId": account_id,
        },
    }


@pytest.mark.asyncio
async def test_import_and_list_accounts(async_client):
    email = "tester@example.com"
    raw_account_id = "acc_explicit"
    payload = {
        "email": email,
        "chatgpt_account_id": "acc_payload",
        "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"},
    }
    auth_json = {
        "tokens": {
            "idToken": _encode_jwt(payload),
            "accessToken": "access",
            "refreshToken": "refresh",
            "accountId": raw_account_id,
        },
    }

    expected_account_id = generate_unique_account_id(raw_account_id, email)
    files = {"auth_json": ("auth.json", json.dumps(auth_json), "application/json")}
    response = await async_client.post("/api/accounts/import", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["accountId"] == expected_account_id
    assert data["email"] == email
    assert data["planType"] == "plus"

    list_response = await async_client.get("/api/accounts")
    assert list_response.status_code == 200
    accounts = list_response.json()["accounts"]
    assert any(account["accountId"] == expected_account_id for account in accounts)


@pytest.mark.asyncio
async def test_reactivate_missing_account_returns_404(async_client):
    response = await async_client.post("/api/accounts/missing/reactivate")
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "account_not_found"


@pytest.mark.asyncio
async def test_pause_missing_account_returns_404(async_client):
    response = await async_client.post("/api/accounts/missing/pause")
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "account_not_found"


@pytest.mark.asyncio
async def test_pause_account(async_client):
    email = "pause@example.com"
    raw_account_id = "acc_pause"
    payload = {
        "email": email,
        "chatgpt_account_id": raw_account_id,
        "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"},
    }
    auth_json = {
        "tokens": {
            "idToken": _encode_jwt(payload),
            "accessToken": "access",
            "refreshToken": "refresh",
            "accountId": raw_account_id,
        },
    }

    expected_account_id = generate_unique_account_id(raw_account_id, email)
    files = {"auth_json": ("auth.json", json.dumps(auth_json), "application/json")}
    response = await async_client.post("/api/accounts/import", files=files)
    assert response.status_code == 200

    pause = await async_client.post(f"/api/accounts/{expected_account_id}/pause")
    assert pause.status_code == 200
    assert pause.json()["status"] == "paused"

    accounts = await async_client.get("/api/accounts")
    assert accounts.status_code == 200
    data = accounts.json()["accounts"]
    matched = next((account for account in data if account["accountId"] == expected_account_id), None)
    assert matched is not None
    assert matched["status"] == "paused"


@pytest.mark.asyncio
async def test_pause_reauth_required_account_returns_conflict(async_client):
    email = "pause-reauth@example.com"
    raw_account_id = "acc_pause_reauth"
    payload = {
        "email": email,
        "chatgpt_account_id": raw_account_id,
        "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"},
    }
    auth_json = {
        "tokens": {
            "idToken": _encode_jwt(payload),
            "accessToken": "access",
            "refreshToken": "refresh",
            "accountId": raw_account_id,
        },
    }

    expected_account_id = generate_unique_account_id(raw_account_id, email)
    files = {"auth_json": ("auth.json", json.dumps(auth_json), "application/json")}
    response = await async_client.post("/api/accounts/import", files=files)
    assert response.status_code == 200

    async with SessionLocal() as session:
        account = await session.get(Account, expected_account_id)
        assert account is not None
        account.status = AccountStatus.REAUTH_REQUIRED
        account.deactivation_reason = "Authentication token invalidated - re-login required"
        await session.commit()

    pause = await async_client.post(f"/api/accounts/{expected_account_id}/pause")
    assert pause.status_code == 409
    assert pause.json()["error"]["code"] == "account_state_transition_invalid"

    accounts = await async_client.get("/api/accounts")
    assert accounts.status_code == 200
    matched = next(
        (account for account in accounts.json()["accounts"] if account["accountId"] == expected_account_id),
        None,
    )
    assert matched is not None
    assert matched["status"] == "reauth_required"


@pytest.mark.asyncio
async def test_reactivate_reauth_required_account_returns_conflict(async_client):
    email = "reactivate-reauth@example.com"
    raw_account_id = "acc_reactivate_reauth"
    payload = {
        "email": email,
        "chatgpt_account_id": raw_account_id,
        "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"},
    }
    auth_json = {
        "tokens": {
            "idToken": _encode_jwt(payload),
            "accessToken": "access",
            "refreshToken": "refresh",
            "accountId": raw_account_id,
        },
    }

    expected_account_id = generate_unique_account_id(raw_account_id, email)
    files = {"auth_json": ("auth.json", json.dumps(auth_json), "application/json")}
    response = await async_client.post("/api/accounts/import", files=files)
    assert response.status_code == 200

    async with SessionLocal() as session:
        account = await session.get(Account, expected_account_id)
        assert account is not None
        account.status = AccountStatus.REAUTH_REQUIRED
        account.deactivation_reason = "Authentication token invalidated - re-login required"
        await session.commit()

    reactivate = await async_client.post(f"/api/accounts/{expected_account_id}/reactivate")
    assert reactivate.status_code == 409
    assert reactivate.json()["error"]["code"] == "account_state_transition_invalid"

    accounts = await async_client.get("/api/accounts")
    assert accounts.status_code == 200
    matched = next(
        (account for account in accounts.json()["accounts"] if account["accountId"] == expected_account_id),
        None,
    )
    assert matched is not None
    assert matched["status"] == "reauth_required"


@pytest.mark.asyncio
async def test_update_account_limit_warmup_opt_in(async_client):
    email = "warmup@example.com"
    raw_account_id = "acc_warmup"
    payload = {
        "email": email,
        "chatgpt_account_id": raw_account_id,
        "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"},
    }
    auth_json = {
        "tokens": {
            "idToken": _encode_jwt(payload),
            "accessToken": "access",
            "refreshToken": "refresh",
            "accountId": raw_account_id,
        },
    }

    expected_account_id = generate_unique_account_id(raw_account_id, email)
    files = {"auth_json": ("auth.json", json.dumps(auth_json), "application/json")}
    response = await async_client.post("/api/accounts/import", files=files)
    assert response.status_code == 200

    update = await async_client.put(f"/api/accounts/{expected_account_id}/limit-warmup", json={"enabled": True})
    assert update.status_code == 200
    assert update.json() == {"status": "enabled", "enabled": True}

    accounts = await async_client.get("/api/accounts")
    assert accounts.status_code == 200
    data = accounts.json()["accounts"]
    matched = next((account for account in data if account["accountId"] == expected_account_id), None)
    assert matched is not None
    assert matched["limitWarmupEnabled"] is True
    assert matched["limitWarmup"] is None


@pytest.mark.asyncio
async def test_export_account_returns_latest_codex_auth_json_with_no_store_headers(async_client):
    email = "export@example.com"
    raw_account_id = "acc_export"
    payload = {
        "email": email,
        "chatgpt_account_id": raw_account_id,
        "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"},
    }
    auth_json = {
        "tokens": {
            "idToken": _encode_jwt(payload),
            "accessToken": "access",
            "refreshToken": "refresh",
            "accountId": raw_account_id,
        },
    }

    expected_account_id = generate_unique_account_id(raw_account_id, email)
    files = {"auth_json": ("auth.json", json.dumps(auth_json), "application/json")}
    response = await async_client.post("/api/accounts/import", files=files)
    assert response.status_code == 200

    export = await async_client.post(f"/api/accounts/{expected_account_id}/export")
    assert export.status_code == 200
    assert export.headers["cache-control"] == "no-store, no-cache, must-revalidate, private"
    assert export.headers["pragma"] == "no-cache"
    assert export.headers["expires"] == "0"

    payload = export.json()
    assert payload["accountId"] == expected_account_id
    assert payload["email"] == email
    assert payload["planType"] == "plus"
    assert payload["status"] == "active"

    parsed_auth = parse_auth_json(payload["authJson"].encode("utf-8"))
    assert parsed_auth.tokens.access_token == "access"
    assert parsed_auth.tokens.refresh_token == "refresh"
    assert parsed_auth.tokens.account_id == raw_account_id
    assert parsed_auth.last_refresh_at is not None


@pytest.mark.asyncio
async def test_export_missing_account_returns_404(async_client):
    response = await async_client.post("/api/accounts/missing/export")
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "account_not_found"


@pytest.mark.asyncio
async def test_delete_missing_account_returns_404(async_client):
    response = await async_client.delete("/api/accounts/missing")
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "account_not_found"


@pytest.mark.asyncio
async def test_set_alias_missing_account_returns_404(async_client):
    response = await async_client.put("/api/accounts/missing/alias", json={"alias": "Personal Plus"})
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "account_not_found"


@pytest.mark.asyncio
async def test_set_and_clear_account_alias(async_client):
    email = "alias@example.com"
    raw_account_id = "acc_alias"
    payload = {
        "email": email,
        "chatgpt_account_id": raw_account_id,
        "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"},
    }
    auth_json = {
        "tokens": {
            "idToken": _encode_jwt(payload),
            "accessToken": "access",
            "refreshToken": "refresh",
            "accountId": raw_account_id,
        },
    }

    expected_account_id = generate_unique_account_id(raw_account_id, email)
    files = {"auth_json": ("auth.json", json.dumps(auth_json), "application/json")}
    response = await async_client.post("/api/accounts/import", files=files)
    assert response.status_code == 200

    # Default summary uses the email since no alias is set yet.
    listing = await async_client.get("/api/accounts")
    matched = next(a for a in listing.json()["accounts"] if a["accountId"] == expected_account_id)
    assert matched["alias"] is None
    assert matched["displayName"] == email

    # Setting an alias updates both `alias` and `displayName`.
    set_response = await async_client.put(
        f"/api/accounts/{expected_account_id}/alias",
        json={"alias": "  Personal Plus  "},
    )
    assert set_response.status_code == 200
    body = set_response.json()
    assert body["alias"] == "Personal Plus"  # whitespace-trimmed
    listing = await async_client.get("/api/accounts")
    matched = next(a for a in listing.json()["accounts"] if a["accountId"] == expected_account_id)
    assert matched["alias"] == "Personal Plus"
    assert matched["displayName"] == "Personal Plus"

    # Empty alias clears the value and the display name falls back to email.
    clear_response = await async_client.put(
        f"/api/accounts/{expected_account_id}/alias",
        json={"alias": "   "},
    )
    assert clear_response.status_code == 200
    assert clear_response.json()["alias"] is None
    listing = await async_client.get("/api/accounts")
    matched = next(a for a in listing.json()["accounts"] if a["accountId"] == expected_account_id)
    assert matched["alias"] is None
    assert matched["displayName"] == email


@pytest.mark.asyncio
async def test_list_accounts_flags_email_duplicates(async_client):
    """Pin codex-lb #787 (B): after a token-invalidation cascade, the
    re-add OAuth flow creates a second account row with the same email
    but a fresh accountId for the same ChatGPT account identity and workspace
    slot. /api/accounts surfaces that pair via isEmailDuplicate=true on both
    rows so the dashboard can flag the operator's "stale + fresh" pair without
    forcing them to group by email, ChatGPT identity, and workspace themselves.
    """
    from app.core.crypto import TokenEncryptor
    from app.core.utils.time import utcnow
    from app.db.models import Account, AccountStatus
    from app.db.session import SessionLocal
    from app.modules.accounts.repository import AccountsRepository

    encryptor = TokenEncryptor()

    def _account(account_id: str, email: str, chatgpt_id: str, workspace_id: str | None = None) -> Account:
        return Account(
            id=account_id,
            chatgpt_account_id=chatgpt_id,
            workspace_id=workspace_id,
            email=email,
            plan_type="plus",
            access_token_encrypted=encryptor.encrypt("access"),
            refresh_token_encrypted=encryptor.encrypt("refresh"),
            id_token_encrypted=encryptor.encrypt("id"),
            last_refresh=utcnow(),
            status=AccountStatus.ACTIVE,
            deactivation_reason=None,
        )

    async with SessionLocal() as session:
        repo = AccountsRepository(session)
        await repo.upsert(_account("dup-stale", "dup@example.com", "chatgpt_same"), merge_by_email=False)
        await repo.upsert(_account("dup-fresh", "dup@example.com", "chatgpt_same"), merge_by_email=False)
        await repo.upsert(_account("workspace-a", "multi@example.com", "chatgpt_multi", "ws_a"), merge_by_email=False)
        await repo.upsert(_account("workspace-b", "multi@example.com", "chatgpt_multi", "ws_b"), merge_by_email=False)
        await repo.upsert(_account("workspace-other", "dup@example.com", "chatgpt_other"), merge_by_email=False)
        await repo.upsert(_account("solo", "solo@example.com", "chatgpt_solo"), merge_by_email=False)
        await repo.upsert(_account("placeholder-a", DEFAULT_EMAIL, "chatgpt_placeholder_a"), merge_by_email=False)
        await repo.upsert(_account("placeholder-b", DEFAULT_EMAIL, "chatgpt_placeholder_b"), merge_by_email=False)
        await repo.upsert(_account("blank-a", "   ", "chatgpt_blank"), merge_by_email=False)
        await repo.upsert(_account("blank-b", "   ", "chatgpt_blank"), merge_by_email=False)

    response = await async_client.get("/api/accounts")
    assert response.status_code == 200
    accounts_by_id = {a["accountId"]: a for a in response.json()["accounts"]}

    assert accounts_by_id["dup-stale"]["isEmailDuplicate"] is True
    assert accounts_by_id["dup-fresh"]["isEmailDuplicate"] is True
    assert accounts_by_id["workspace-a"]["isEmailDuplicate"] is False
    assert accounts_by_id["workspace-b"]["isEmailDuplicate"] is False
    assert accounts_by_id["workspace-other"]["isEmailDuplicate"] is False
    assert accounts_by_id["solo"]["isEmailDuplicate"] is False
    assert accounts_by_id["placeholder-a"]["isEmailDuplicate"] is False
    assert accounts_by_id["placeholder-b"]["isEmailDuplicate"] is False
    assert accounts_by_id["blank-a"]["isEmailDuplicate"] is False
    assert accounts_by_id["blank-b"]["isEmailDuplicate"] is False


# Fork-specific OpenAI Platform identity coverage preserved during upstream merge.


@pytest.mark.asyncio
async def test_list_accounts_includes_platform_request_usage(async_client, monkeypatch):
    async def fake_validate_platform_identity(self, *, api_key, organization=None, project=None):
        del self, api_key, organization, project
        return PlatformModelsResponse(
            payload={"object": "list", "data": [{"id": "gpt-5.1", "object": "model", "owned_by": "openai"}]},
            upstream_request_id="up_req_validate_platform",
        )

    monkeypatch.setattr(
        accounts_service_module.OpenAIPlatformProviderAdapter,
        "validate_identity",
        fake_validate_platform_identity,
    )

    import_response = await async_client.post(
        "/api/accounts/import",
        files={
            "auth_json": (
                "auth.json",
                json.dumps(_make_auth_json("acc_platform_usage", "platform-usage@example.com")),
                "application/json",
            )
        },
    )
    assert import_response.status_code == 200

    create_response = await async_client.post(
        "/api/accounts/platform",
        json={
            "label": "Platform Usage",
            "apiKey": "sk-platform-usage",
        },
    )
    assert create_response.status_code == 200
    identity_id = create_response.json()["accountId"]

    async with SessionLocal() as session:
        session.add(
            RequestLog(
                account_id=None,
                provider_kind="openai_platform",
                routing_subject_id=identity_id,
                api_key_id=None,
                request_id="req_platform_usage",
                requested_at=utcnow(),
                model="gpt-5.1",
                transport="http",
                route_class="openai_public_http",
                upstream_request_id="up_req_platform_usage",
                rejection_reason=None,
                service_tier=None,
                requested_service_tier=None,
                actual_service_tier=None,
                input_tokens=12,
                output_tokens=8,
                cached_input_tokens=3,
                reasoning_tokens=None,
                cost_usd=0.42,
                reasoning_effort=None,
                latency_ms=120,
                latency_first_token_ms=None,
                status="success",
                error_code=None,
                error_message=None,
            )
        )
        await session.commit()

    list_response = await async_client.get("/api/accounts")
    assert list_response.status_code == 200
    platform_account = next(
        account for account in list_response.json()["accounts"] if account["accountId"] == identity_id
    )

    assert platform_account["requestUsage"] == {
        "requestCount": 1,
        "totalTokens": 20,
        "cachedInputTokens": 3,
        "totalCostUsd": 0.42,
    }


@pytest.mark.asyncio
async def test_create_platform_identity_rejects_blank_required_strings(async_client):
    import_response = await async_client.post(
        "/api/accounts/import",
        files={
            "auth_json": (
                "auth.json",
                json.dumps(_make_auth_json("acc_platform_blank_create", "platform-blank-create@example.com")),
                "application/json",
            )
        },
    )
    assert import_response.status_code == 200

    response = await async_client.post(
        "/api/accounts/platform",
        json={
            "label": "   ",
            "apiKey": "   ",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_platform_identity_conflict_is_enforced_even_if_service_precheck_is_bypassed(
    async_client,
    monkeypatch,
):
    async def fake_validate_platform_identity(self, *, api_key, organization=None, project=None):
        del self, api_key, organization, project
        return PlatformModelsResponse(
            payload={"object": "list", "data": [{"id": "gpt-5.1", "object": "model", "owned_by": "openai"}]},
            upstream_request_id="up_req_validate_platform_conflict",
        )

    async def always_allow_platform_creation(self):
        del self
        return False

    monkeypatch.setattr(
        accounts_service_module.OpenAIPlatformProviderAdapter,
        "validate_identity",
        fake_validate_platform_identity,
    )
    monkeypatch.setattr(
        accounts_service_module.AccountsService,
        "_has_platform_identity",
        always_allow_platform_creation,
    )

    import_response = await async_client.post(
        "/api/accounts/import",
        files={
            "auth_json": (
                "auth.json",
                json.dumps(_make_auth_json("acc_platform_conflict_bypass", "platform-conflict-bypass@example.com")),
                "application/json",
            )
        },
    )
    assert import_response.status_code == 200

    first_response = await async_client.post(
        "/api/accounts/platform",
        json={
            "label": "Platform Primary",
            "apiKey": "sk-platform-primary",
        },
    )
    assert first_response.status_code == 200

    second_response = await async_client.post(
        "/api/accounts/platform",
        json={
            "label": "Platform Secondary",
            "apiKey": "sk-platform-secondary",
        },
    )
    assert second_response.status_code == 409
    assert second_response.json()["error"]["code"] == "platform_identity_conflict"


@pytest.mark.asyncio
async def test_platform_identity_repository_enforces_singleton(async_client):
    del async_client
    async with SessionLocal() as session:
        repo = OpenAIPlatformIdentitiesRepository(session)
        first = OpenAIPlatformIdentityCreate(
            id="platform_one",
            label="Platform One",
            api_key_encrypted=b"encrypted-1",
            organization_id=None,
            project_id=None,
            eligible_route_families=EXPECTED_PLATFORM_ROUTE_FAMILY_TUPLE,
            status=AccountStatus.ACTIVE,
            last_validated_at=None,
            last_auth_failure_reason=None,
        )
        second = OpenAIPlatformIdentityCreate(
            id="platform_two",
            label="Platform Two",
            api_key_encrypted=b"encrypted-2",
            organization_id=None,
            project_id=None,
            eligible_route_families=EXPECTED_PLATFORM_ROUTE_FAMILY_TUPLE,
            status=AccountStatus.ACTIVE,
            last_validated_at=None,
            last_auth_failure_reason=None,
        )

        await repo.create_identity(first)
        with pytest.raises(OpenAIPlatformIdentityConflictError):
            await repo.create_identity(second)


@pytest.mark.asyncio
async def test_update_platform_identity_ignores_legacy_route_family_payload(async_client, monkeypatch):
    async def fake_validate_platform_identity(self, *, api_key, organization=None, project=None):
        del self, api_key, organization, project
        return PlatformModelsResponse(
            payload={"object": "list", "data": [{"id": "gpt-5.1", "object": "model", "owned_by": "openai"}]},
            upstream_request_id="up_req_validate_platform_update_invalid",
        )

    monkeypatch.setattr(
        accounts_service_module.OpenAIPlatformProviderAdapter,
        "validate_identity",
        fake_validate_platform_identity,
    )

    import_response = await async_client.post(
        "/api/accounts/import",
        files={
            "auth_json": (
                "auth.json",
                json.dumps(_make_auth_json("acc_platform_edit_invalid", "platform-edit-invalid@example.com")),
                "application/json",
            )
        },
    )
    assert import_response.status_code == 200

    create_response = await async_client.post(
        "/api/accounts/platform",
        json={
            "label": "Platform Original",
            "apiKey": "sk-platform-original",
            "eligibleRouteFamilies": ["public_models_http"],
        },
    )
    assert create_response.status_code == 200
    account_id = create_response.json()["accountId"]

    async with SessionLocal() as session:
        result = await session.execute(select(OpenAIPlatformIdentity).where(OpenAIPlatformIdentity.id == account_id))
        identity = result.scalar_one()
        assert list(split_route_families(identity.eligible_route_families)) == EXPECTED_PLATFORM_ROUTE_FAMILIES

    update_response = await async_client.patch(
        f"/api/accounts/platform/{account_id}",
        json={"eligibleRouteFamilies": ["backend_codex_http"]},
    )
    assert update_response.status_code == 200
    assert update_response.json()["eligibleRouteFamilies"] == EXPECTED_PLATFORM_ROUTE_FAMILIES

    async with SessionLocal() as session:
        result = await session.execute(select(OpenAIPlatformIdentity).where(OpenAIPlatformIdentity.id == account_id))
        identity = result.scalar_one()
        assert list(split_route_families(identity.eligible_route_families)) == EXPECTED_PLATFORM_ROUTE_FAMILIES


@pytest.mark.asyncio
async def test_update_platform_identity_returns_404_for_chatgpt_account(async_client):
    import_response = await async_client.post(
        "/api/accounts/import",
        files={
            "auth_json": (
                "auth.json",
                json.dumps(_make_auth_json("acc_platform_edit_mismatch", "platform-edit-mismatch@example.com")),
                "application/json",
            )
        },
    )
    assert import_response.status_code == 200
    account_id = import_response.json()["accountId"]

    response = await async_client.patch(
        f"/api/accounts/platform/{account_id}",
        json={"label": "Should Fail"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "account_not_found"


@pytest.mark.asyncio
async def test_update_platform_identity_returns_404_for_missing_identity(async_client):
    response = await async_client.patch(
        "/api/accounts/platform/missing-platform",
        json={"label": "Missing Platform"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "account_not_found"


@pytest.mark.asyncio
async def test_update_platform_identity_revalidates_auth_affecting_fields(async_client, monkeypatch):
    validation_calls: list[tuple[str, str | None, str | None]] = []

    async def fake_validate_platform_identity(self, *, api_key, organization=None, project=None):
        del self
        validation_calls.append((api_key, organization, project))
        return PlatformModelsResponse(
            payload={"object": "list", "data": [{"id": "gpt-5.1", "object": "model", "owned_by": "openai"}]},
            upstream_request_id="up_req_validate_platform_update_auth",
        )

    monkeypatch.setattr(
        accounts_service_module.OpenAIPlatformProviderAdapter,
        "validate_identity",
        fake_validate_platform_identity,
    )

    import_response = await async_client.post(
        "/api/accounts/import",
        files={
            "auth_json": (
                "auth.json",
                json.dumps(_make_auth_json("acc_platform_edit_auth", "platform-edit-auth@example.com")),
                "application/json",
            )
        },
    )
    assert import_response.status_code == 200

    create_response = await async_client.post(
        "/api/accounts/platform",
        json={
            "label": "Platform Original",
            "apiKey": "sk-platform-original",
            "organization": "org_original",
            "project": "proj_original",
        },
    )
    assert create_response.status_code == 200
    account_id = create_response.json()["accountId"]

    update_response = await async_client.patch(
        f"/api/accounts/platform/{account_id}",
        json={
            "organization": "org_updated",
            "project": None,
        },
    )
    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["accountId"] == account_id
    assert payload["organization"] == "org_updated"
    assert payload["project"] is None
    assert validation_calls == [
        ("sk-platform-original", "org_original", "proj_original"),
        ("sk-platform-original", "org_updated", None),
    ]


@pytest.mark.asyncio
async def test_update_platform_identity_revalidates_key_rotation(async_client, monkeypatch):
    validation_calls: list[tuple[str, str | None, str | None]] = []

    async def fake_validate_platform_identity(self, *, api_key, organization=None, project=None):
        del self
        validation_calls.append((api_key, organization, project))
        return PlatformModelsResponse(
            payload={"object": "list", "data": [{"id": "gpt-5.1", "object": "model", "owned_by": "openai"}]},
            upstream_request_id="up_req_validate_platform_rotate",
        )

    monkeypatch.setattr(
        accounts_service_module.OpenAIPlatformProviderAdapter,
        "validate_identity",
        fake_validate_platform_identity,
    )

    import_response = await async_client.post(
        "/api/accounts/import",
        files={
            "auth_json": (
                "auth.json",
                json.dumps(_make_auth_json("acc_platform_rotate", "platform-rotate@example.com")),
                "application/json",
            )
        },
    )
    assert import_response.status_code == 200

    create_response = await async_client.post(
        "/api/accounts/platform",
        json={
            "label": "Platform Original",
            "apiKey": "sk-platform-original",
            "organization": "org_original",
            "project": "proj_original",
        },
    )
    assert create_response.status_code == 200
    account_id = create_response.json()["accountId"]

    update_response = await async_client.patch(
        f"/api/accounts/platform/{account_id}",
        json={"apiKey": "sk-platform-rotated"},
    )
    assert update_response.status_code == 200
    assert validation_calls == [
        ("sk-platform-original", "org_original", "proj_original"),
        ("sk-platform-rotated", "org_original", "proj_original"),
    ]


@pytest.mark.asyncio
async def test_update_platform_identity_surfaces_auth_failure_reason_for_rotated_key(async_client, monkeypatch):
    async def create_validate(self, *, api_key, organization=None, project=None):
        del self, api_key, organization, project
        return PlatformModelsResponse(
            payload={"object": "list", "data": [{"id": "gpt-5.1", "object": "model", "owned_by": "openai"}]},
            upstream_request_id="up_req_validate_platform_auth_failure_create",
        )

    async def fail_update_validate(self, *, api_key, organization=None, project=None):
        del self, api_key, organization, project
        raise OpenAIPlatformError(
            401,
            {
                "error": {
                    "code": "invalid_api_key",
                    "message": "The supplied API key is invalid.",
                    "type": "invalid_request_error",
                }
            },
        )

    monkeypatch.setattr(
        accounts_service_module.OpenAIPlatformProviderAdapter,
        "validate_identity",
        create_validate,
    )

    import_response = await async_client.post(
        "/api/accounts/import",
        files={
            "auth_json": (
                "auth.json",
                json.dumps(_make_auth_json("acc_platform_auth_fail", "platform-auth-fail@example.com")),
                "application/json",
            )
        },
    )
    assert import_response.status_code == 200

    create_response = await async_client.post(
        "/api/accounts/platform",
        json={
            "label": "Platform Auth Failure",
            "apiKey": "sk-platform-original",
        },
    )
    assert create_response.status_code == 200
    account_id = create_response.json()["accountId"]

    monkeypatch.setattr(
        accounts_service_module.OpenAIPlatformProviderAdapter,
        "validate_identity",
        fail_update_validate,
    )

    update_response = await async_client.patch(
        f"/api/accounts/platform/{account_id}",
        json={"apiKey": "sk-platform-invalid"},
    )
    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["status"] == "deactivated"
    assert payload["lastAuthFailureReason"] == "The supplied API key is invalid."

    async with SessionLocal() as session:
        repo = OpenAIPlatformIdentitiesRepository(session)
        identity = await repo.get_by_id(account_id)
        assert identity is not None
        decrypting_service = accounts_service_module.OpenAIPlatformIdentitiesService(repo)
        assert decrypting_service.decrypt_api_key(identity) == "sk-platform-invalid"
        assert identity.last_auth_failure_reason == "The supplied API key is invalid."
        assert identity.status == AccountStatus.DEACTIVATED


@pytest.mark.asyncio
async def test_update_platform_identity_updates_metadata_without_revalidating_label_only(async_client, monkeypatch):
    create_validation_calls: list[tuple[str, str | None, str | None]] = []
    update_validation_calls: list[tuple[str, str | None, str | None]] = []

    async def fake_create_validate(self, *, api_key, organization=None, project=None):
        del self
        create_validation_calls.append((api_key, organization, project))
        return PlatformModelsResponse(
            payload={"object": "list", "data": [{"id": "gpt-5.1", "object": "model", "owned_by": "openai"}]},
            upstream_request_id="up_req_validate_platform_update_create",
        )

    async def fail_update_validate(self, *, api_key, organization=None, project=None):
        del self, api_key, organization, project
        update_validation_calls.append(("unexpected", None, None))
        raise AssertionError("label-only edit must not revalidate the platform identity")

    monkeypatch.setattr(
        accounts_service_module.OpenAIPlatformProviderAdapter,
        "validate_identity",
        fake_create_validate,
    )

    import_response = await async_client.post(
        "/api/accounts/import",
        files={
            "auth_json": (
                "auth.json",
                json.dumps(_make_auth_json("acc_platform_edit_label", "platform-edit-label@example.com")),
                "application/json",
            )
        },
    )
    assert import_response.status_code == 200

    create_response = await async_client.post(
        "/api/accounts/platform",
        json={
            "label": "Platform Original",
            "apiKey": "sk-platform-original",
            "organization": "org_original",
            "project": "proj_original",
        },
    )
    assert create_response.status_code == 200
    account_id = create_response.json()["accountId"]
    assert create_validation_calls == [("sk-platform-original", "org_original", "proj_original")]

    monkeypatch.setattr(
        accounts_service_module.OpenAIPlatformProviderAdapter,
        "validate_identity",
        fail_update_validate,
    )

    update_response = await async_client.patch(
        f"/api/accounts/platform/{account_id}",
        json={
            "label": "Platform Renamed",
        },
    )
    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["accountId"] == account_id
    assert payload["label"] == "Platform Renamed"
    assert payload["organization"] == "org_original"
    assert payload["project"] == "proj_original"
    assert payload["eligibleRouteFamilies"] == EXPECTED_PLATFORM_ROUTE_FAMILIES
    assert update_validation_calls == []


@pytest.mark.asyncio
async def test_delete_platform_identity_cleans_up_provider_scoped_sticky_sessions(async_client, monkeypatch):
    async def fake_validate_platform_identity(self, *, api_key, organization=None, project=None):
        del self, api_key, organization, project
        return PlatformModelsResponse(
            payload={"object": "list", "data": [{"id": "gpt-5.1", "object": "model", "owned_by": "openai"}]},
            upstream_request_id="up_req_validate_platform_delete",
        )

    monkeypatch.setattr(
        provider_adapters_module.OpenAIPlatformProviderAdapter,
        "validate_identity",
        fake_validate_platform_identity,
    )

    import_response = await async_client.post(
        "/api/accounts/import",
        files={
            "auth_json": (
                "auth.json",
                json.dumps(_make_auth_json("acc_platform_delete", "platform-delete@example.com")),
                "application/json",
            )
        },
    )
    assert import_response.status_code == 200

    create_response = await async_client.post(
        "/api/accounts/platform",
        json={
            "label": "Platform Delete",
            "apiKey": "sk-platform-delete",
        },
    )
    assert create_response.status_code == 200
    identity_id = create_response.json()["accountId"]

    async with SessionLocal() as session:
        session.add(
            StickySession(
                key="platform-sticky",
                kind=StickySessionKind.PROMPT_CACHE,
                provider_kind="openai_platform",
                account_id=None,
                routing_subject_id=identity_id,
            )
        )
        await session.commit()

    delete_response = await async_client.delete(f"/api/accounts/{identity_id}")
    assert delete_response.status_code == 200

    async with SessionLocal() as session:
        remaining = await session.scalar(
            select(func.count())
            .select_from(StickySession)
            .where(
                StickySession.provider_kind == "openai_platform",
                StickySession.routing_subject_id == identity_id,
            )
        )
        assert remaining == 0
