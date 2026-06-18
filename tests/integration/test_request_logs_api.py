from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.crypto import TokenEncryptor
from app.core.utils.time import utcnow
from app.db.models import Account, AccountStatus, ApiKey
from app.db.session import SessionLocal
from app.modules.accounts.repository import AccountsRepository
from app.modules.request_logs.repository import RequestLogsRepository

pytestmark = pytest.mark.integration


def _make_account(account_id: str, email: str) -> Account:
    encryptor = TokenEncryptor()
    return Account(
        id=account_id,
        email=email,
        plan_type="plus",
        access_token_encrypted=encryptor.encrypt("access"),
        refresh_token_encrypted=encryptor.encrypt("refresh"),
        id_token_encrypted=encryptor.encrypt("id"),
        last_refresh=utcnow(),
        status=AccountStatus.ACTIVE,
        deactivation_reason=None,
    )


@pytest.mark.asyncio
async def test_request_logs_api_returns_recent(async_client, db_setup):
    async with SessionLocal() as session:
        accounts_repo = AccountsRepository(session)
        logs_repo = RequestLogsRepository(session)
        await accounts_repo.upsert(_make_account("acc_logs", "logs@example.com"))
        session.add(
            ApiKey(
                id="key_logs_1",
                name="Debug Key",
                key_hash="hash_logs_1",
                key_prefix="sk-test",
            )
        )
        await session.commit()

        now = utcnow()
        await logs_repo.add_log(
            account_id="acc_logs",
            request_id="req_logs_1",
            model="gpt-5.1",
            input_tokens=100,
            output_tokens=200,
            latency_ms=1200,
            status="success",
            error_code=None,
            requested_at=now - timedelta(minutes=1),
            transport="http",
        )
        await logs_repo.add_log(
            account_id="acc_logs",
            request_id="req_logs_2",
            model="legacy-model",
            input_tokens=50,
            output_tokens=0,
            latency_ms=300,
            status="error",
            error_code="rate_limit_exceeded",
            error_message="Rate limit reached",
            failure_phase="owner_forward_status",
            failure_detail="owner_forward_non_200",
            failure_exception_type="ProxyResponseError",
            upstream_status_code=503,
            upstream_error_code="bridge_owner_forward_failed",
            bridge_stage="owner_forward",
            requested_at=now,
            api_key_id="key_logs_1",
            transport="websocket",
        )

    response = await async_client.get("/api/request-logs?limit=2")
    assert response.status_code == 200
    body = response.json()
    payload = body["requests"]
    assert len(payload) == 2
    assert body["total"] == 2
    assert body["hasMore"] is False

    latest = payload[0]
    assert latest["status"] == "rate_limit"
    assert latest["apiKeyId"] == "key_logs_1"
    assert latest["apiKeyName"] == "Debug Key"
    assert latest["errorCode"] == "rate_limit_exceeded"
    assert latest["errorMessage"] == "Rate limit reached"
    assert latest["failurePhase"] == "owner_forward_status"
    assert latest["failureDetail"] == "owner_forward_non_200"
    assert latest["failureExceptionType"] == "ProxyResponseError"
    assert latest["upstreamStatusCode"] == 503
    assert latest["upstreamErrorCode"] == "bridge_owner_forward_failed"
    assert latest["bridgeStage"] == "owner_forward"
    assert latest["costBreakdown"] == {
        "inputUsd": None,
        "cachedInputUsd": None,
        "outputUsd": None,
        "totalUsd": None,
    }
    assert latest["transport"] == "websocket"
    assert latest["requestKind"] == "normal"

    older = payload[1]
    assert older["status"] == "ok"
    assert older["apiKeyId"] is None
    assert older["apiKeyName"] is None
    assert older["tokens"] == 300
    assert older["inputTokens"] == 100
    assert older["outputTokens"] == 200
    assert older["cachedInputTokens"] is None
    assert older["costBreakdown"] == {
        "inputUsd": None,
        "cachedInputUsd": None,
        "outputUsd": pytest.approx(0.002),
        "totalUsd": pytest.approx(0.002125),
    }
    assert older["transport"] == "http"
    assert older["requestKind"] == "normal"


@pytest.mark.asyncio
async def test_request_logs_api_returns_useragent_fields(async_client, db_setup):
    async with SessionLocal() as session:
        accounts_repo = AccountsRepository(session)
        logs_repo = RequestLogsRepository(session)
        await accounts_repo.upsert(_make_account("acc_logs_useragent", "ua-logs@example.com"))

        now = utcnow()
        await logs_repo.add_log(
            account_id="acc_logs_useragent",
            request_id="req_logs_useragent_present",
            model="gpt-5.1",
            input_tokens=10,
            output_tokens=20,
            latency_ms=100,
            status="success",
            error_code=None,
            requested_at=now,
            useragent="opencode/1.15.13 ai-sdk/provider-utils/4.0.23 runtime/bun/1.3.14",
            useragent_group="opencode",
        )
        await logs_repo.add_log(
            account_id="acc_logs_useragent",
            request_id="req_logs_useragent_absent",
            model="gpt-5.1-mini",
            input_tokens=5,
            output_tokens=15,
            latency_ms=50,
            status="success",
            error_code=None,
            requested_at=now - timedelta(minutes=1),
        )

    response = await async_client.get("/api/request-logs?limit=2")
    assert response.status_code == 200
    payload = response.json()["requests"]
    assert [entry["requestId"] for entry in payload] == [
        "req_logs_useragent_present",
        "req_logs_useragent_absent",
    ]

    latest = payload[0]
    assert latest["useragent"] == "opencode/1.15.13 ai-sdk/provider-utils/4.0.23 runtime/bun/1.3.14"
    assert latest["useragentGroup"] == "opencode"

    older = payload[1]
    assert older["useragent"] is None
    assert older["useragentGroup"] is None


@pytest.mark.asyncio
async def test_request_logs_api_lists_limit_warmup_rows(async_client, db_setup):
    async with SessionLocal() as session:
        accounts_repo = AccountsRepository(session)
        logs_repo = RequestLogsRepository(session)
        await accounts_repo.upsert(_make_account("acc_warmup_logs", "warmup-logs@example.com"))

        await logs_repo.add_log(
            account_id="acc_warmup_logs",
            request_id="req_normal_traffic",
            model="gpt-5.2",
            input_tokens=100,
            output_tokens=100,
            latency_ms=100,
            status="success",
            error_code=None,
            plan_type="plus",
        )
        await logs_repo.add_log(
            account_id="acc_warmup_logs",
            request_id="req_limit_warmup",
            model="gpt-5.1-codex-mini",
            input_tokens=1,
            output_tokens=1,
            latency_ms=10,
            status="success",
            error_code=None,
            plan_type="plus",
            request_kind="warmup",
        )

    response = await async_client.get("/api/request-logs?limit=10")
    assert response.status_code == 200
    body = response.json()
    request_ids = [entry["requestId"] for entry in body["requests"]]
    assert request_ids == ["req_limit_warmup", "req_normal_traffic"]
    assert body["requests"][0]["requestKind"] == "warmup"
    assert body["requests"][1]["requestKind"] == "normal"
    assert body["total"] == 2

    options_response = await async_client.get("/api/request-logs/options")
    assert options_response.status_code == 200
    option_models = [entry["model"] for entry in options_response.json()["modelOptions"]]
    assert "gpt-5.1-codex-mini" in option_models


# Fork-specific provider-aware request-log filtering coverage preserved during upstream merge.


@pytest.mark.asyncio
async def test_request_logs_api_filters_platform_rows_by_routing_subject(async_client, db_setup):
    async with SessionLocal() as session:
        accounts_repo = AccountsRepository(session)
        logs_repo = RequestLogsRepository(session)
        await accounts_repo.upsert(_make_account("acc_logs_platform", "logs-platform@example.com"))

        now = utcnow()
        await logs_repo.add_log(
            account_id=None,
            provider_kind="openai_platform",
            routing_subject_id="plat_logs",
            request_id="req_logs_platform",
            model="gpt-5.1",
            input_tokens=12,
            output_tokens=8,
            latency_ms=180,
            status="error",
            error_code="provider_feature_unsupported",
            error_message="Unsupported route",
            requested_at=now,
            transport="http",
            route_class="openai_public_http",
            upstream_request_id="up_req_logs_platform",
            rejection_reason="platform_only_route",
        )

    response = await async_client.get("/api/request-logs", params={"accountId": "plat_logs"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["hasMore"] is False
    entry = body["requests"][0]
    assert entry["accountId"] is None
    assert entry["providerKind"] == "openai_platform"
    assert entry["routingSubjectId"] == "plat_logs"
    assert entry["upstreamRequestId"] == "up_req_logs_platform"
    assert entry["rejectionReason"] == "platform_only_route"

    options = await async_client.get("/api/request-logs/options")
    assert options.status_code == 200
    assert "plat_logs" in options.json()["accountIds"]


@pytest.mark.asyncio
async def test_request_logs_api_separates_chatgpt_and_platform_subject_filters(async_client, db_setup):
    async with SessionLocal() as session:
        accounts_repo = AccountsRepository(session)
        logs_repo = RequestLogsRepository(session)
        await accounts_repo.upsert(_make_account("acc_logs_chatgpt", "logs-chatgpt@example.com"))

        now = utcnow()
        await logs_repo.add_log(
            account_id="acc_logs_chatgpt",
            provider_kind="chatgpt_web",
            routing_subject_id="acc_logs_chatgpt",
            request_id="req_logs_chatgpt",
            model="gpt-5.1",
            input_tokens=24,
            output_tokens=6,
            latency_ms=210,
            status="success",
            error_code=None,
            requested_at=now - timedelta(seconds=30),
            transport="http",
            route_class="openai_public_http",
            upstream_request_id="up_req_logs_chatgpt",
        )
        await logs_repo.add_log(
            account_id=None,
            provider_kind="openai_platform",
            routing_subject_id="plat_logs_filtered",
            request_id="req_logs_platform_filtered",
            model="gpt-5.1",
            input_tokens=9,
            output_tokens=3,
            latency_ms=140,
            status="error",
            error_code="provider_feature_unsupported",
            error_message="Unsupported route",
            requested_at=now,
            transport="http",
            route_class="openai_public_http",
            upstream_request_id="up_req_logs_platform_filtered",
            rejection_reason="platform_only_route",
        )

    platform_response = await async_client.get(
        "/api/request-logs",
        params={"accountId": "plat_logs_filtered"},
    )
    assert platform_response.status_code == 200
    platform_payload = platform_response.json()
    assert platform_payload["total"] == 1
    assert platform_payload["requests"][0]["requestId"] == "req_logs_platform_filtered"
    assert platform_payload["requests"][0]["providerKind"] == "openai_platform"
    assert platform_payload["requests"][0]["routingSubjectId"] == "plat_logs_filtered"

    chatgpt_response = await async_client.get(
        "/api/request-logs",
        params={"accountId": "acc_logs_chatgpt"},
    )
    assert chatgpt_response.status_code == 200
    chatgpt_payload = chatgpt_response.json()
    assert chatgpt_payload["total"] == 1
    assert chatgpt_payload["requests"][0]["requestId"] == "req_logs_chatgpt"
    assert chatgpt_payload["requests"][0]["providerKind"] == "chatgpt_web"
    assert chatgpt_payload["requests"][0]["routingSubjectId"] == "acc_logs_chatgpt"
