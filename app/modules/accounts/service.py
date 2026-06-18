from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta
from typing import cast

import aiohttp
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.auth import (
    DEFAULT_EMAIL,
    DEFAULT_PLAN,
    claims_from_auth,
    generate_unique_account_id,
    parse_auth_json,
    token_expiry_epoch_ms,
)
from app.core.auth.api_key_cache import get_api_key_cache
from app.core.cache.invalidation import NAMESPACE_API_KEY, get_cache_invalidation_poller
from app.core.clients.http import lease_http_session
from app.core.clients.openai_platform import OpenAIPlatformError
from app.core.config.settings import get_settings
from app.core.crypto import TokenEncryptor
from app.core.plan_types import coerce_account_plan_type
from app.core.utils.time import naive_utc_to_epoch, to_utc_naive, utcnow
from app.db.models import Account, AccountStatus
from app.modules.accounts.auth_manager import AuthManager
from app.modules.accounts.mappers import build_account_summaries, build_account_usage_trends
from app.modules.accounts.repository import AccountRequestUsageSummary, AccountsRepository
from app.modules.accounts.schemas import (
    AccountAdditionalQuota,
    AccountAdditionalWindow,
    AccountAuthExportResponse,
    AccountAuthExportTokens,
    AccountExportResponse,
    AccountImportResponse,
    AccountOpenCodeAuthExportAccount,
    AccountOpenCodeAuthExportResponse,
    AccountProbeResponse,
    AccountRequestUsage,
    AccountSummary,
    AccountTrendsResponse,
    CodexAuthJson,
    CodexAuthTokens,
    OpenCodeAuthJson,
    OpenCodeOAuthAuth,
    PlatformIdentityCreateRequest,
    PlatformIdentityUpdateRequest,
)
from app.modules.limit_warmup.repository import LimitWarmupRepository
from app.modules.proxy.account_cache import get_account_selection_cache
from app.modules.proxy.provider_adapters import OpenAIPlatformProviderAdapter
from app.modules.upstream_identities.repository import (
    OpenAIPlatformIdentityConflictError as UpstreamIdentityConflictError,
)
from app.modules.upstream_identities.schemas import (
    PlatformIdentityCreateRequest as UpstreamPlatformIdentityCreateRequest,
)
from app.modules.upstream_identities.schemas import (
    PlatformIdentitySummary,
    PlatformIdentityValidationResult,
)
from app.modules.upstream_identities.schemas import (
    PlatformIdentityUpdateRequest as UpstreamPlatformIdentityUpdateRequest,
)
from app.modules.upstream_identities.service import OpenAIPlatformIdentitiesService
from app.modules.usage.additional_quota_keys import (
    get_additional_display_label_for_quota_key,
    get_additional_quota_routing_policy,
)
from app.modules.usage.repository import AdditionalUsageRepository, UsageRepository
from app.modules.usage.updater import AdditionalUsageRepositoryPort, UsageUpdater

logger = logging.getLogger(__name__)

_SPARKLINE_DAYS = 7
_DETAIL_BUCKET_SECONDS = 3600  # 1h → 168 points

DEFAULT_PROBE_MODEL = "gpt-5.5"
PROBE_REQUEST_TIMEOUT_SECONDS = 30.0
PROBE_CONNECT_TIMEOUT_SECONDS = 10.0
# Network/upstream failure sentinel for ``probe_status_code`` — kept as ``0`` so
# the value is distinguishable from any real HTTP status the upstream might
# return.
PROBE_NETWORK_FAILURE_STATUS = 0


class InvalidAuthJsonError(Exception):
    pass


class PlatformIdentityPrerequisiteError(ValueError):
    pass


class PlatformIdentityConflictError(Exception):
    pass


class PlatformIdentityNotFoundError(Exception):
    pass


class AccountNotProbableError(Exception):
    """Raised when an account is in a status that disallows probing."""


class AccountStateTransitionError(Exception):
    """Raised when an operator action is not valid for the account state."""


class AccountsService:
    def __init__(
        self,
        repo: AccountsRepository,
        usage_repo: UsageRepository | None = None,
        additional_usage_repo: AdditionalUsageRepository | AdditionalUsageRepositoryPort | None = None,
        limit_warmup_repo: LimitWarmupRepository | None = None,
        *,
        platform_service: OpenAIPlatformIdentitiesService | None = None,
        auth_manager: AuthManager | None = None,
    ) -> None:
        self._repo = repo
        self._usage_repo = usage_repo
        self._additional_usage_repo = additional_usage_repo
        self._platform_service = platform_service
        self._limit_warmup_repo = limit_warmup_repo
        self._usage_updater = UsageUpdater(usage_repo, repo, additional_usage_repo) if usage_repo else None
        self._encryptor = TokenEncryptor()
        self._platform_adapter = OpenAIPlatformProviderAdapter()
        self._auth_manager = auth_manager

    async def list_accounts(self) -> list[AccountSummary]:
        accounts = await self._repo.list_accounts()
        platform_summaries = (
            await self._platform_service.list_identities() if self._platform_service is not None else []
        )
        account_ids = [account.id for account in accounts]
        routing_subject_ids = list(account_ids)
        routing_subject_ids.extend(summary.routing_subject_id for summary in platform_summaries)
        if not accounts:
            if not routing_subject_ids:
                return []
            request_usage_rows = await self._repo.list_request_usage_summary_by_subject(routing_subject_ids)
            return [
                _platform_summary_to_account_summary(
                    summary,
                    request_usage_rows.get(summary.routing_subject_id),
                )
                for summary in platform_summaries
            ]
        account_id_set = set(account_ids)
        primary_usage = await self._usage_repo.latest_by_account(window="primary") if self._usage_repo else {}
        secondary_usage = await self._usage_repo.latest_by_account(window="secondary") if self._usage_repo else {}
        monthly_usage = await self._usage_repo.latest_by_account(window="monthly") if self._usage_repo else {}
        request_usage_rows = await self._repo.list_request_usage_summary_by_subject(routing_subject_ids)
        limit_warmups_by_account = (
            await self._limit_warmup_repo.latest_by_account(account_ids) if self._limit_warmup_repo else {}
        )
        request_usage_by_account = {
            account_id: AccountRequestUsage(
                request_count=row.request_count,
                total_tokens=row.total_tokens,
                cached_input_tokens=row.cached_input_tokens,
                total_cost_usd=row.total_cost_usd,
            )
            for account_id, row in request_usage_rows.items()
        }
        additional_quotas_by_account: dict[str, list[AccountAdditionalQuota]] = {}
        additional_usage_repo = cast(AdditionalUsageRepository | None, self._additional_usage_repo)
        if additional_usage_repo:
            additional_quota_routing_overrides = await self._repo.additional_quota_routing_policy_overrides()
            quota_keys = await additional_usage_repo.list_quota_keys(account_ids=account_ids)
            for quota_key in quota_keys:
                primary_entries = await additional_usage_repo.latest_by_account(quota_key, "primary")
                secondary_entries = await additional_usage_repo.latest_by_account(quota_key, "secondary")
                for account_id in (set(primary_entries) | set(secondary_entries)) & account_id_set:
                    primary_entry = primary_entries.get(account_id)
                    secondary_entry = secondary_entries.get(account_id)
                    reference_entry = primary_entry or secondary_entry
                    if reference_entry is None:
                        continue
                    additional_quotas_by_account.setdefault(account_id, []).append(
                        AccountAdditionalQuota(
                            quota_key=quota_key,
                            limit_name=reference_entry.limit_name,
                            metered_feature=reference_entry.metered_feature,
                            display_label=get_additional_display_label_for_quota_key(quota_key)
                            or reference_entry.limit_name,
                            routing_policy=get_additional_quota_routing_policy(
                                quota_key,
                                overrides=additional_quota_routing_overrides,
                            ),
                            primary_window=AccountAdditionalWindow(
                                used_percent=primary_entry.used_percent,
                                reset_at=primary_entry.reset_at,
                                window_minutes=primary_entry.window_minutes,
                            )
                            if primary_entry is not None
                            else None,
                            secondary_window=AccountAdditionalWindow(
                                used_percent=secondary_entry.used_percent,
                                reset_at=secondary_entry.reset_at,
                                window_minutes=secondary_entry.window_minutes,
                            )
                            if secondary_entry is not None
                            else None,
                        )
                    )
        for account_quota_list in additional_quotas_by_account.values():
            account_quota_list.sort(key=lambda quota: quota.display_label or quota.quota_key or quota.limit_name)

        summaries = build_account_summaries(
            accounts=accounts,
            primary_usage=primary_usage,
            secondary_usage=secondary_usage,
            monthly_usage=monthly_usage,
            request_usage_by_account=request_usage_by_account,
            additional_quotas_by_account=additional_quotas_by_account,
            limit_warmups_by_account=limit_warmups_by_account,
            encryptor=self._encryptor,
        )
        if self._platform_service is None:
            return summaries
        platform_accounts = [
            _platform_summary_to_account_summary(
                summary,
                request_usage_rows.get(summary.routing_subject_id),
            )
            for summary in platform_summaries
        ]
        return summaries + platform_accounts

    async def get_account_trends(self, account_id: str) -> AccountTrendsResponse | None:
        account = await self._repo.get_by_id(account_id)
        if account is None:
            if self._platform_service is not None and await self._platform_service.get_identity(account_id) is not None:
                return AccountTrendsResponse(account_id=account_id, primary=[], secondary=[])
            return None
        if not self._usage_repo:
            return None
        now = utcnow()
        since = now - timedelta(days=_SPARKLINE_DAYS)
        since_epoch = naive_utc_to_epoch(since)
        bucket_count = (_SPARKLINE_DAYS * 24 * 3600) // _DETAIL_BUCKET_SECONDS
        buckets = await self._usage_repo.trends_by_bucket(
            since=since,
            bucket_seconds=_DETAIL_BUCKET_SECONDS,
            account_id=account_id,
        )
        trends = build_account_usage_trends(buckets, since_epoch, _DETAIL_BUCKET_SECONDS, bucket_count)
        trend = trends.get(account_id)
        return AccountTrendsResponse(
            account_id=account_id,
            primary=trend.primary if trend else [],
            secondary=trend.secondary if trend else [],
            secondary_scheduled=trend.secondary_scheduled if trend else [],
        )

    async def export_opencode_auth(self, account_id: str) -> AccountOpenCodeAuthExportResponse | None:
        account = await self._repo.get_by_id(account_id)
        if account is None:
            return None

        access_token = self._encryptor.decrypt(account.access_token_encrypted)
        refresh_token = self._encryptor.decrypt(account.refresh_token_encrypted)
        expires = token_expiry_epoch_ms(access_token) or 0
        return AccountOpenCodeAuthExportResponse(
            filename=_opencode_auth_export_filename(account),
            account=AccountOpenCodeAuthExportAccount(
                account_id=account.id,
                chatgpt_account_id=account.chatgpt_account_id,
                email=account.email,
            ),
            auth_json=OpenCodeAuthJson(
                openai=OpenCodeOAuthAuth(
                    refresh=refresh_token,
                    access=access_token,
                    expires=expires,
                    account_id=account.chatgpt_account_id,
                ),
            ),
        )

    async def export_auth(self, account_id: str) -> AccountAuthExportResponse | None:
        account = await self._repo.get_by_id(account_id)
        if account is None:
            return None

        access_token = self._encryptor.decrypt(account.access_token_encrypted)
        refresh_token = self._encryptor.decrypt(account.refresh_token_encrypted)
        id_token = self._encryptor.decrypt(account.id_token_encrypted)
        expires = token_expiry_epoch_ms(access_token) or 0

        tokens = AccountAuthExportTokens(
            id_token=id_token,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at_ms=expires,
        )

        codex_auth_json = CodexAuthJson(
            auth_mode="chatgpt",
            openai_api_key=None,
            tokens=CodexAuthTokens(
                id_token=id_token,
                access_token=access_token,
                refresh_token=refresh_token,
                account_id=account.chatgpt_account_id,
            ),
            last_refresh=account.last_refresh.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z",
        )

        opencode_auth_json = OpenCodeAuthJson(
            openai=OpenCodeOAuthAuth(
                refresh=refresh_token,
                access=access_token,
                expires=expires,
                account_id=account.chatgpt_account_id,
            ),
        )

        return AccountAuthExportResponse(
            filename=_opencode_auth_export_filename(account),
            account=AccountOpenCodeAuthExportAccount(
                account_id=account.id,
                chatgpt_account_id=account.chatgpt_account_id,
                email=account.email,
            ),
            tokens=tokens,
            codex_auth_json=codex_auth_json,
            opencode_auth_json=opencode_auth_json,
        )

    async def import_account(self, raw: bytes) -> AccountImportResponse:
        try:
            auth = parse_auth_json(raw)
        except (json.JSONDecodeError, ValidationError, UnicodeDecodeError, TypeError) as exc:
            raise InvalidAuthJsonError("Invalid auth.json payload") from exc
        claims = claims_from_auth(auth)

        email = claims.email or DEFAULT_EMAIL
        raw_account_id = claims.account_id
        account_id = generate_unique_account_id(raw_account_id, email, claims.workspace_id, claims.workspace_label)
        plan_type = coerce_account_plan_type(claims.plan_type, DEFAULT_PLAN)
        last_refresh = to_utc_naive(auth.last_refresh_at) if auth.last_refresh_at else utcnow()

        account = Account(
            id=account_id,
            chatgpt_account_id=raw_account_id,
            email=email,
            workspace_id=claims.workspace_id,
            workspace_label=claims.workspace_label,
            seat_type=claims.seat_type,
            plan_type=plan_type,
            access_token_encrypted=self._encryptor.encrypt(auth.tokens.access_token),
            refresh_token_encrypted=self._encryptor.encrypt(auth.tokens.refresh_token),
            id_token_encrypted=self._encryptor.encrypt(auth.tokens.id_token),
            last_refresh=last_refresh,
            status=AccountStatus.ACTIVE,
            deactivation_reason=None,
        )

        saved = await self._repo.upsert_account_slot(account)
        if self._usage_repo and self._usage_updater:
            latest_usage = await self._usage_repo.latest_by_account(window="primary")
            await self._usage_updater.refresh_accounts([saved], latest_usage)
        get_account_selection_cache().invalidate()
        return AccountImportResponse(
            account_id=saved.id,
            email=saved.email,
            workspace_id=saved.workspace_id,
            workspace_label=saved.workspace_label,
            seat_type=saved.seat_type,
            plan_type=saved.plan_type,
            status=saved.status,
        )

    async def create_platform_identity(self, payload: PlatformIdentityCreateRequest) -> AccountImportResponse:
        if self._platform_service is None:
            raise RuntimeError("Platform identities are not configured")
        if not await self._has_active_chatgpt_accounts():
            raise PlatformIdentityPrerequisiteError(
                "OpenAI Platform fallback requires at least one active ChatGPT-web account."
            )
        if await self._has_platform_identity():
            raise PlatformIdentityConflictError("Only one OpenAI Platform fallback key can be registered.")
        validation = await self._validate_platform_identity(payload)
        upstream_payload = UpstreamPlatformIdentityCreateRequest.model_validate(payload.model_dump())
        try:
            result = await self._platform_service.create_identity(upstream_payload, validation=validation)
        except (IntegrityError, UpstreamIdentityConflictError) as exc:
            raise PlatformIdentityConflictError(str(exc)) from exc
        get_account_selection_cache().invalidate()
        return AccountImportResponse(
            account_id=result.identity.id,
            email=result.identity.label,
            plan_type="openai_platform",
            status=result.identity.status.value,
        )

    async def update_platform_identity(
        self,
        account_id: str,
        payload: PlatformIdentityUpdateRequest,
    ) -> AccountSummary:
        if self._platform_service is None:
            raise RuntimeError("Platform identities are not configured")
        identity = await self._platform_service.get_identity(account_id)
        if identity is None:
            raise PlatformIdentityNotFoundError(f"Platform identity not found: {account_id}")

        upstream_payload = UpstreamPlatformIdentityUpdateRequest.model_validate(payload.model_dump(exclude_unset=True))
        validation = None
        if _should_revalidate_platform_identity(upstream_payload):
            api_key = (
                upstream_payload.api_key
                if upstream_payload.api_key is not None
                else self._platform_service.decrypt_api_key(identity)
            )
            organization = (
                upstream_payload.organization
                if "organization" in upstream_payload.model_fields_set
                else identity.organization_id
            )
            project = (
                upstream_payload.project if "project" in upstream_payload.model_fields_set else identity.project_id
            )
            validation = await self._validate_platform_identity_fields(
                api_key=api_key,
                organization=organization,
                project=project,
            )

        result = await self._platform_service.update_identity(
            identity,
            upstream_payload,
            validation=validation,
        )
        get_account_selection_cache().invalidate()
        request_usage_rows = await self._repo.list_request_usage_summary_by_subject([result.identity.id])
        request_usage = request_usage_rows.get(result.identity.id)
        return _platform_summary_to_account_summary(
            self._platform_service.summarize_identity(result.identity),
            request_usage,
        )

    async def reactivate_account(self, account_id: str) -> bool:
        account = await self._repo.get_by_id(account_id)
        if account is None:
            result = await self._platform_service.reactivate_identity(account_id) if self._platform_service else False
        else:
            if account.status == AccountStatus.REAUTH_REQUIRED:
                raise AccountStateTransitionError(
                    "Account requires re-authentication and cannot be reactivated directly"
                )
            result = await self._repo.update_status_if_current(
                account_id,
                AccountStatus.ACTIVE,
                None,
                None,
                blocked_at=None,
                expected_status=account.status,
                expected_deactivation_reason=account.deactivation_reason,
                expected_reset_at=account.reset_at,
                expected_blocked_at=account.blocked_at,
            )
            if not result:
                raise AccountStateTransitionError("Account state changed; retry the operation")
        if result:
            get_account_selection_cache().invalidate()
        return result

    async def pause_account(self, account_id: str) -> bool:
        account = await self._repo.get_by_id(account_id)
        if account is None:
            result = await self._platform_service.pause_identity(account_id) if self._platform_service else False
        else:
            if account.status in (AccountStatus.REAUTH_REQUIRED, AccountStatus.DEACTIVATED):
                raise AccountStateTransitionError(f"Account is {account.status.value} and cannot be paused")
            result = await self._repo.update_status_if_current(
                account_id,
                AccountStatus.PAUSED,
                None,
                None,
                blocked_at=None,
                expected_status=account.status,
                expected_deactivation_reason=account.deactivation_reason,
                expected_reset_at=account.reset_at,
                expected_blocked_at=account.blocked_at,
            )
            if not result:
                raise AccountStateTransitionError("Account state changed; retry the operation")
        if result:
            get_account_selection_cache().invalidate()
        return result

    async def update_account(self, account_id: str, *, security_work_authorized: bool | None = None) -> bool:
        result = False
        if security_work_authorized is not None:
            result = await self._repo.update_security_work_authorized(account_id, security_work_authorized)
        if result:
            get_account_selection_cache().invalidate()
        return result

    async def set_limit_warmup_enabled(self, account_id: str, enabled: bool) -> bool:
        result = await self._repo.update_limit_warmup_enabled(account_id, enabled)
        if result:
            get_account_selection_cache().invalidate()
        return result

    async def set_routing_policy(self, account_id: str, routing_policy: str) -> bool:
        result = await self._repo.update_routing_policy(account_id, routing_policy)
        if result:
            get_account_selection_cache().invalidate()
        return result

    async def delete_account(self, account_id: str, *, delete_history: bool = False) -> bool:
        result = await self._repo.delete(account_id, delete_history=delete_history)
        if not result and self._platform_service is not None:
            result = await self._platform_service.delete_identity(account_id)
        if result:
            get_account_selection_cache().invalidate()
            get_api_key_cache().clear()
            poller = get_cache_invalidation_poller()
            if poller is not None:
                await poller.bump(NAMESPACE_API_KEY)
        return result

    async def set_account_alias(self, account_id: str, alias: str | None) -> bool:
        normalized = alias.strip() if isinstance(alias, str) else None
        if normalized == "":
            normalized = None
        return await self._repo.update_alias(account_id, normalized)

    async def export_account(self, account_id: str) -> AccountExportResponse | None:
        account = await self._repo.get_by_id(account_id)
        if not account:
            return None
        access_token = self._encryptor.decrypt(account.access_token_encrypted)
        refresh_token = self._encryptor.decrypt(account.refresh_token_encrypted)
        id_token = self._encryptor.decrypt(account.id_token_encrypted)
        auth_json = {
            "auth_mode": "chatgpt",
            "OPENAI_API_KEY": None,
            "tokens": {
                "id_token": id_token,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "account_id": account.chatgpt_account_id,
            },
            "last_refresh": account.last_refresh.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z",
        }
        return AccountExportResponse(
            account_id=account.id,
            email=account.email,
            workspace_id=account.workspace_id,
            workspace_label=account.workspace_label,
            seat_type=account.seat_type,
            plan_type=account.plan_type,
            status=account.status.value,
            auth_json=json.dumps(auth_json, indent=2),
        )

    async def probe_account(
        self,
        account_id: str,
        model: str | None = None,
    ) -> AccountProbeResponse | None:
        """Send a minimal upstream ``responses.create`` pinned to one account.

        Bypasses load-balancer scoring so an operator can wake the upstream
        rate-limiter for a stuck account. Triggers an immediate usage refresh
        after the probe and returns the before/after snapshot.
        """
        account = await self._repo.get_by_id(account_id)
        if account is None:
            return None
        if account.status in (AccountStatus.PAUSED, AccountStatus.REAUTH_REQUIRED, AccountStatus.DEACTIVATED):
            raise AccountNotProbableError(f"Account is {account.status.value} and cannot be probed")

        primary_before, secondary_before = await self._latest_usage_percents(account_id)
        status_before = account.status.value

        probe_account = account
        if self._auth_manager is not None:
            probe_account = await self._auth_manager.ensure_fresh(account, force=False)

        access_token = self._encryptor.decrypt(probe_account.access_token_encrypted)
        probe_model = model or DEFAULT_PROBE_MODEL
        probe_status = await self._send_probe_request(
            access_token=access_token,
            chatgpt_account_id=probe_account.chatgpt_account_id,
            model=probe_model,
        )

        if self._usage_repo and self._usage_updater:
            await self._usage_updater.force_refresh(probe_account)
            get_account_selection_cache().invalidate()

        refreshed = await self._repo.get_by_id(account_id) or account
        primary_after, secondary_after = await self._latest_usage_percents(account_id)

        return AccountProbeResponse(
            status="probed",
            account_id=account_id,
            probe_status_code=probe_status,
            primary_used_percent_before=primary_before,
            primary_used_percent_after=primary_after,
            secondary_used_percent_before=secondary_before,
            secondary_used_percent_after=secondary_after,
            account_status_before=status_before,
            account_status_after=refreshed.status.value,
        )

    async def _latest_usage_percents(self, account_id: str) -> tuple[float | None, float | None]:
        if self._usage_repo is None:
            return None, None
        primary_entry = await self._usage_repo.latest_entry_for_account(account_id, window="primary")
        secondary_entry = await self._usage_repo.latest_entry_for_account(account_id, window="secondary")
        return (
            primary_entry.used_percent if primary_entry is not None else None,
            secondary_entry.used_percent if secondary_entry is not None else None,
        )

    async def _send_probe_request(
        self,
        *,
        access_token: str,
        chatgpt_account_id: str | None,
        model: str,
    ) -> int:
        settings = get_settings()
        base = settings.upstream_base_url.rstrip("/")
        if "/backend-api" not in base:
            base = f"{base}/backend-api"
        url = f"{base}/codex/responses"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        }
        if chatgpt_account_id and not chatgpt_account_id.startswith(("email_", "local_")):
            headers["chatgpt-account-id"] = chatgpt_account_id
        body = {
            "model": model,
            "instructions": "Respond with a single dot.",
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": "."}],
                }
            ],
            "max_output_tokens": 1,
            "stream": True,
            "store": False,
        }
        timeout = aiohttp.ClientTimeout(
            total=PROBE_REQUEST_TIMEOUT_SECONDS,
            sock_connect=PROBE_CONNECT_TIMEOUT_SECONDS,
        )
        try:
            async with lease_http_session() as session:
                async with session.post(url, headers=headers, json=body, timeout=timeout) as resp:
                    return resp.status
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logger.warning(
                "Probe upstream request failed account=%s error=%s",
                chatgpt_account_id,
                exc,
            )
            return PROBE_NETWORK_FAILURE_STATUS

    async def _validate_platform_identity(
        self,
        payload: PlatformIdentityCreateRequest,
    ) -> PlatformIdentityValidationResult:
        return await self._validate_platform_identity_fields(
            api_key=payload.api_key,
            organization=payload.organization,
            project=payload.project,
        )

    async def _validate_platform_identity_fields(
        self,
        *,
        api_key: str,
        organization: str | None,
        project: str | None,
    ) -> PlatformIdentityValidationResult:
        try:
            response = await self._platform_adapter.validate_identity(
                api_key=api_key,
                organization=organization,
                project=project,
            )
        except OpenAIPlatformError as exc:
            reason = _platform_validation_reason(exc)
            return PlatformIdentityValidationResult(
                valid=False,
                last_validated_at=None,
                failure_reason=reason,
                models=[],
            )
        data = response.payload.get("data")
        models: list[str] = []
        if isinstance(data, list):
            models = [
                model_id for entry in data if isinstance(entry, dict) and isinstance(model_id := entry.get("id"), str)
            ]
        return PlatformIdentityValidationResult(
            valid=True,
            last_validated_at=utcnow(),
            failure_reason=None,
            models=models,
        )

    async def _has_active_chatgpt_accounts(self) -> bool:
        accounts = await self._repo.list_accounts()
        return any(account.status not in (AccountStatus.DEACTIVATED, AccountStatus.PAUSED) for account in accounts)

    async def _has_platform_identity(self) -> bool:
        if self._platform_service is None:
            return False
        return bool(await self._platform_service.list_identities())


def _platform_validation_reason(exc: OpenAIPlatformError) -> str:
    error = exc.payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    return f"platform_validation_failed:{exc.status_code}"


def _should_revalidate_platform_identity(payload: UpstreamPlatformIdentityUpdateRequest) -> bool:
    fields_set = payload.model_fields_set
    return payload.api_key is not None or "organization" in fields_set or "project" in fields_set


def _platform_summary_to_account_summary(
    summary: PlatformIdentitySummary,
    request_usage: AccountRequestUsageSummary | None,
) -> AccountSummary:
    payload = summary.model_dump()
    if request_usage is not None:
        payload["request_usage"] = AccountRequestUsage(
            request_count=request_usage.request_count,
            total_tokens=request_usage.total_tokens,
            cached_input_tokens=request_usage.cached_input_tokens,
            total_cost_usd=request_usage.total_cost_usd,
        )
    else:
        payload["request_usage"] = None
    return AccountSummary.model_validate(payload)


def _opencode_auth_export_filename(account: Account) -> str:
    source = account.email or account.id
    safe = "".join(char if char.isalnum() or char in "._-" else "-" for char in source).strip("-._")
    return f"opencode-auth-{safe or account.id}.json"
