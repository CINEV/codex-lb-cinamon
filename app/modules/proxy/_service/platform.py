from __future__ import annotations

import logging
import sys
import time
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from typing import Any, cast

from app.core.auth.refresh import RefreshError
from app.core.balancer import RoutingStrategy
from app.core.clients.openai_platform import (
    OpenAIPlatformError,
    PlatformModelsResponse,
    PlatformResponseResult,
    PlatformStreamResponse,
)
from app.core.clients.proxy import ProxyResponseError
from app.core.config.settings import get_settings
from app.core.config.settings_cache import get_settings_cache
from app.core.openai.requests import ResponsesRequest
from app.core.utils.request_id import ensure_request_id, get_request_id
from app.db.models import Account, AccountStatus, StickySessionKind
from app.modules.api_keys.service import ApiKeyData
from app.modules.proxy._service.support import _REQUEST_TRANSPORT_WEBSOCKET
from app.modules.proxy.helpers import _normalize_error_code, _parse_openai_error
from app.modules.proxy.load_balancer import _filter_accounts_for_model, _gated_limit_name_for_model
from app.modules.proxy.platform_cache_alerts import (
    get_platform_cache_alert_service as _get_platform_cache_alert_service,
)
from app.modules.proxy.provider_adapters import (
    ChatGPTWebProviderAdapter,
    OpenAIPlatformProviderAdapter,
    ProviderAdapter,
    ProviderCapabilityDecision,
    ProviderModelsResult,
    ProviderSubject,
    RequestCapabilities,
    _platform_error_code,
    _platform_error_message,
)
from app.modules.upstream_identities.types import (
    BACKEND_CODEX_HTTP_ROUTE_FAMILY,
    CHATGPT_PRIVATE_ROUTE_CLASS,
    CHATGPT_WEB_PROVIDER_KIND,
    OPENAI_PLATFORM_PROVIDER_KIND,
    OPENAI_PUBLIC_HTTP_ROUTE_CLASS,
    PUBLIC_MODELS_HTTP_ROUTE_FAMILY,
    PUBLIC_RESPONSES_HTTP_ROUTE_FAMILY,
)

logger = logging.getLogger(__name__)

_REQUEST_TRANSPORT_HTTP = "http"


def _service_get_platform_cache_alert_service() -> Any:
    service_module = sys.modules.get("app.modules.proxy.service")
    if service_module is not None:
        func = getattr(service_module, "get_platform_cache_alert_service", _get_platform_cache_alert_service)
        return cast(Callable[[], Any], func)()
    return _get_platform_cache_alert_service()


@dataclass(frozen=True, slots=True)
class _SelectedPlatformIdentity:
    id: str
    api_key_encrypted: bytes
    organization_id: str | None
    project_id: str | None


@dataclass(frozen=True, slots=True)
class SelectedChatGPTSubject:
    provider_kind: str
    route_class: str
    routing_subject_id: str


@dataclass(frozen=True, slots=True)
class SelectedPlatformSubject:
    provider_kind: str
    route_class: str
    routing_subject_id: str
    identity: _SelectedPlatformIdentity


@dataclass(frozen=True, slots=True)
class ProviderSelectionFailure:
    http_status: int
    error_code: str
    error_message: str
    rejection_reason: str
    route_class: str
    error_param: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderSelectionResult:
    selected: SelectedChatGPTSubject | SelectedPlatformSubject | None = None
    failure: ProviderSelectionFailure | None = None

    @property
    def provider_kind(self) -> str | None:
        return self.selected.provider_kind if self.selected is not None else None

    @property
    def is_platform(self) -> bool:
        return isinstance(self.selected, SelectedPlatformSubject)

    @property
    def is_chatgpt(self) -> bool:
        return isinstance(self.selected, SelectedChatGPTSubject)


class _PlatformProviderMixin:
    _encryptor: Any
    _load_balancer: Any
    _provider_adapters: dict[str, ProviderAdapter]
    _repo_factory: Callable[[], Any]
    _handle_proxy_error: Any
    _select_account_with_budget_compatible: Any
    _write_request_log: Any

    def _provider_adapter(self, provider_kind: str) -> ProviderAdapter:
        return self._provider_adapters[provider_kind]

    @staticmethod
    def _platform_provider_subject(identity: _SelectedPlatformIdentity) -> ProviderSubject:
        return ProviderSubject(
            provider_kind=OPENAI_PLATFORM_PROVIDER_KIND,
            routing_subject_id=identity.id,
            api_key_encrypted=identity.api_key_encrypted,
            organization_id=identity.organization_id,
            project_id=identity.project_id,
        )

    def platform_api_key_suffix(self, identity: _SelectedPlatformIdentity | None) -> str | None:
        if identity is None:
            return None
        try:
            api_key = self._encryptor.decrypt(identity.api_key_encrypted).strip()
        except Exception:
            logger.warning(
                "Failed to decrypt Platform API key suffix routing_subject_id=%s",
                identity.id,
                exc_info=True,
            )
            return None
        if not api_key:
            return None
        return api_key[-4:]

    async def record_platform_cache_observation(
        self,
        *,
        input_tokens: int | None,
        cached_input_tokens: int | None,
        client_version: str | None = None,
        identity: _SelectedPlatformIdentity | None = None,
        api_key_suffix: str | None = None,
    ) -> bool:
        suffix = api_key_suffix or self.platform_api_key_suffix(identity)
        return await _service_get_platform_cache_alert_service().observe(
            api_key_suffix=suffix,
            client_version=client_version,
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
        )

    @staticmethod
    def _chatgpt_provider_subject(account: Account) -> ProviderSubject:
        return ProviderSubject(
            provider_kind=CHATGPT_WEB_PROVIDER_KIND,
            routing_subject_id=account.id,
            account=account,
        )

    @staticmethod
    def _provider_selection_failure(
        decision: ProviderCapabilityDecision,
        capabilities: RequestCapabilities,
    ) -> ProviderSelectionResult:
        if decision.allowed:
            raise ValueError("Provider selection failure requested for an allowed capability decision")
        if decision.error_code is None or decision.error_message is None or decision.rejection_reason is None:
            raise ValueError("Provider capability decision is missing failure metadata")
        return ProviderSelectionResult(
            failure=ProviderSelectionFailure(
                http_status=400,
                error_code=decision.error_code,
                error_message=decision.error_message,
                rejection_reason=decision.rejection_reason,
                route_class=capabilities.route_class,
                error_param=decision.error_param,
            )
        )

    async def has_chatgpt_candidates(
        self,
        model: str | None = None,
        *,
        account_ids: Collection[str] | None = None,
    ) -> bool:
        async with self._repo_factory() as repos:
            accounts = await repos.accounts.list_accounts()
            allowed_account_ids = None if account_ids is None else set(account_ids)
            active_accounts = [
                account
                for account in accounts
                if account.status not in (AccountStatus.PAUSED, AccountStatus.DEACTIVATED)
                and (allowed_account_ids is None or account.id in allowed_account_ids)
            ]
            if model is None:
                return bool(active_accounts)
            return bool(_filter_accounts_for_model(active_accounts, model))

    async def has_compatible_chatgpt_candidates(
        self,
        model: str | None = None,
        *,
        additional_limit_name: str | None = None,
        account_ids: Collection[str] | None = None,
    ) -> bool:
        return await self._load_balancer.has_compatible_chatgpt_candidates(
            model=model,
            additional_limit_name=additional_limit_name,
            account_ids=account_ids,
        )

    async def chatgpt_compatibility_failure(
        self,
        model: str | None = None,
        *,
        additional_limit_name: str | None = None,
        account_ids: Collection[str] | None = None,
    ) -> tuple[str | None, str | None]:
        return await self._load_balancer.chatgpt_compatibility_failure(
            model=model,
            additional_limit_name=additional_limit_name,
            account_ids=account_ids,
        )

    async def should_fallback_to_platform_for_usage_drain(
        self,
        *,
        model: str | None,
        additional_limit_name: str | None = None,
        account_ids: Collection[str] | None = None,
    ) -> bool:
        return await self._load_balancer.should_fallback_to_platform_for_usage_drain(
            model=model,
            additional_limit_name=additional_limit_name,
            account_ids=account_ids,
        )

    async def sticky_chatgpt_target_is_healthy_for_platform_fallback(
        self,
        *,
        sticky_key: str | None,
        sticky_kind: StickySessionKind | None,
        sticky_max_age_seconds: int | None,
        model: str | None,
        additional_limit_name: str | None = None,
        account_ids: Collection[str] | None = None,
    ) -> bool:
        return await self._load_balancer.sticky_chatgpt_target_is_healthy_for_platform_fallback(
            sticky_key=sticky_key,
            sticky_kind=sticky_kind,
            sticky_max_age_seconds=sticky_max_age_seconds,
            model=model,
            additional_limit_name=additional_limit_name,
            account_ids=account_ids,
        )

    async def sticky_chatgpt_target_is_selectable_for_platform_fallback(
        self,
        *,
        sticky_key: str | None,
        sticky_kind: StickySessionKind | None,
        sticky_max_age_seconds: int | None,
        model: str | None,
        additional_limit_name: str | None = None,
        account_ids: Collection[str] | None = None,
    ) -> bool:
        return await self._load_balancer.sticky_chatgpt_target_is_selectable_for_platform_fallback(
            sticky_key=sticky_key,
            sticky_kind=sticky_kind,
            sticky_max_age_seconds=sticky_max_age_seconds,
            model=model,
            additional_limit_name=additional_limit_name,
            account_ids=account_ids,
        )

    @staticmethod
    def _hard_affinity_for_provider_fallback(
        *,
        sticky_key: str | None,
        sticky_kind: StickySessionKind | None,
    ) -> bool:
        return bool(sticky_key) and sticky_kind == StickySessionKind.CODEX_SESSION

    @staticmethod
    def _platform_affinity_for_selection(
        *,
        sticky_key: str | None,
        sticky_kind: StickySessionKind | None,
        reallocate_sticky: bool,
        sticky_max_age_seconds: int | None,
        platform_sticky_key: str | None = None,
        platform_sticky_kind: StickySessionKind | None = None,
        platform_sticky_max_age_seconds: int | None = None,
    ) -> tuple[str | None, StickySessionKind | None, bool, int | None]:
        if platform_sticky_key and platform_sticky_kind == StickySessionKind.PROMPT_CACHE:
            return platform_sticky_key, platform_sticky_kind, False, platform_sticky_max_age_seconds
        if sticky_key and sticky_kind == StickySessionKind.PROMPT_CACHE:
            return sticky_key, sticky_kind, reallocate_sticky, sticky_max_age_seconds
        return None, None, False, None

    async def select_routing_subject(
        self,
        *,
        capabilities: RequestCapabilities,
        api_key: ApiKeyData | None = None,
        sticky_key: str | None = None,
        sticky_kind: StickySessionKind | None = None,
        reallocate_sticky: bool = False,
        sticky_max_age_seconds: int | None = None,
        platform_sticky_key: str | None = None,
        platform_sticky_kind: StickySessionKind | None = None,
        platform_sticky_max_age_seconds: int | None = None,
    ) -> ProviderSelectionResult:
        scoped_account_ids = (
            api_key.assigned_account_ids if api_key is not None and api_key.account_assignment_scope_enabled else None
        )
        additional_limit_name = _gated_limit_name_for_model(capabilities.model)
        has_active_chatgpt = await self.has_chatgpt_candidates(account_ids=scoped_account_ids)
        has_compatible_chatgpt = await self.has_compatible_chatgpt_candidates(
            capabilities.model,
            additional_limit_name=additional_limit_name,
            account_ids=scoped_account_ids,
        )
        platform_adapter = cast(
            OpenAIPlatformProviderAdapter,
            self._provider_adapter(OPENAI_PLATFORM_PROVIDER_KIND),
        )

        is_models_route = capabilities.route_family == PUBLIC_MODELS_HTTP_ROUTE_FAMILY or (
            capabilities.route_family == BACKEND_CODEX_HTTP_ROUTE_FAMILY and capabilities.model is None
        )

        if is_models_route:
            identity = await self.select_platform_identity(capabilities.route_family)
            if has_active_chatgpt:
                should_fallback = await self.should_fallback_to_platform_for_usage_drain(
                    model=None,
                    account_ids=scoped_account_ids,
                )
                if should_fallback:
                    if identity is not None:
                        decision = platform_adapter.check_capabilities(
                            self._platform_provider_subject(identity),
                            capabilities,
                        )
                        if decision.allowed:
                            return ProviderSelectionResult(
                                selected=SelectedPlatformSubject(
                                    provider_kind=OPENAI_PLATFORM_PROVIDER_KIND,
                                    route_class=capabilities.route_class,
                                    routing_subject_id=identity.id,
                                    identity=identity,
                                )
                            )
                return ProviderSelectionResult(
                    selected=SelectedChatGPTSubject(
                        provider_kind=CHATGPT_WEB_PROVIDER_KIND,
                        route_class=capabilities.route_class,
                        routing_subject_id="chatgpt_web_pool",
                    )
                )
            if identity is not None:
                return ProviderSelectionResult(
                    failure=ProviderSelectionFailure(
                        http_status=400,
                        error_code="provider_fallback_requires_chatgpt",
                        error_message="OpenAI Platform fallback requires at least one active ChatGPT-web account.",
                        rejection_reason="platform_fallback_requires_chatgpt",
                        route_class=capabilities.route_class,
                    )
                )
            return ProviderSelectionResult()

        if capabilities.transport == _REQUEST_TRANSPORT_WEBSOCKET:
            if has_compatible_chatgpt:
                return ProviderSelectionResult(
                    selected=SelectedChatGPTSubject(
                        provider_kind=CHATGPT_WEB_PROVIDER_KIND,
                        route_class=capabilities.route_class,
                        routing_subject_id="chatgpt_web_pool",
                    )
                )
            identity = await self.select_platform_identity(capabilities.route_family)
            if identity is None:
                if has_active_chatgpt:
                    error_code, error_message = await self.chatgpt_compatibility_failure(
                        capabilities.model,
                        additional_limit_name=additional_limit_name,
                        account_ids=scoped_account_ids,
                    )
                    if error_code is not None and error_message is not None:
                        return ProviderSelectionResult(
                            failure=ProviderSelectionFailure(
                                http_status=400,
                                error_code=error_code,
                                error_message=error_message,
                                rejection_reason=error_code,
                                route_class=capabilities.route_class,
                            )
                        )
                    return ProviderSelectionResult(
                        selected=SelectedChatGPTSubject(
                            provider_kind=CHATGPT_WEB_PROVIDER_KIND,
                            route_class=capabilities.route_class,
                            routing_subject_id="chatgpt_web_pool",
                        )
                    )
                return ProviderSelectionResult()
            decision = platform_adapter.check_capabilities(
                self._platform_provider_subject(identity),
                capabilities,
            )
            return self._provider_selection_failure(decision, capabilities)

        if capabilities.continuity_param is not None:
            if has_compatible_chatgpt:
                return ProviderSelectionResult(
                    selected=SelectedChatGPTSubject(
                        provider_kind=CHATGPT_WEB_PROVIDER_KIND,
                        route_class=capabilities.route_class,
                        routing_subject_id="chatgpt_web_pool",
                    )
                )
            identity = await self.select_platform_identity(capabilities.route_family)
            if identity is None:
                if has_active_chatgpt:
                    error_code, error_message = await self.chatgpt_compatibility_failure(
                        capabilities.model,
                        additional_limit_name=additional_limit_name,
                        account_ids=scoped_account_ids,
                    )
                    if error_code is not None and error_message is not None:
                        return ProviderSelectionResult(
                            failure=ProviderSelectionFailure(
                                http_status=400,
                                error_code=error_code,
                                error_message=error_message,
                                rejection_reason=error_code,
                                route_class=capabilities.route_class,
                            )
                        )
                    return ProviderSelectionResult(
                        selected=SelectedChatGPTSubject(
                            provider_kind=CHATGPT_WEB_PROVIDER_KIND,
                            route_class=capabilities.route_class,
                            routing_subject_id="chatgpt_web_pool",
                        )
                    )
                return ProviderSelectionResult()
            decision = platform_adapter.check_capabilities(
                self._platform_provider_subject(identity),
                capabilities,
            )
            return self._provider_selection_failure(decision, capabilities)

        (
            selection_platform_sticky_key,
            selection_platform_sticky_kind,
            selection_platform_reallocate_sticky,
            selection_platform_sticky_max_age_seconds,
        ) = self._platform_affinity_for_selection(
            sticky_key=sticky_key,
            sticky_kind=sticky_kind,
            reallocate_sticky=reallocate_sticky,
            sticky_max_age_seconds=sticky_max_age_seconds,
            platform_sticky_key=platform_sticky_key,
            platform_sticky_kind=platform_sticky_kind,
            platform_sticky_max_age_seconds=platform_sticky_max_age_seconds,
        )
        identity = await self.select_platform_identity(capabilities.route_family)
        if has_compatible_chatgpt:
            platform_sticky_identity = await self._select_platform_prompt_cache_identity(
                capabilities.route_family,
                sticky_key=selection_platform_sticky_key,
                sticky_kind=selection_platform_sticky_kind,
                sticky_max_age_seconds=selection_platform_sticky_max_age_seconds,
            )
            if platform_sticky_identity is not None:
                decision = platform_adapter.check_capabilities(
                    self._platform_provider_subject(platform_sticky_identity),
                    capabilities,
                )
                if decision.allowed:
                    if get_settings().log_proxy_request_shape:
                        logger.warning(
                            "proxy_request_shape_provider_affinity request_id=%s route_family=%s "
                            "affinity_decision_reason=platform_prompt_cache_hit sticky_kind=%s",
                            get_request_id(),
                            capabilities.route_family,
                            selection_platform_sticky_kind.value
                            if selection_platform_sticky_kind is not None
                            else None,
                        )
                    logger.info(
                        "Reusing Platform prompt-cache affinity request_id=%s route_family=%s sticky_kind=%s",
                        get_request_id(),
                        capabilities.route_family,
                        selection_platform_sticky_kind.value if selection_platform_sticky_kind is not None else None,
                    )
                    return ProviderSelectionResult(
                        selected=SelectedPlatformSubject(
                            provider_kind=OPENAI_PLATFORM_PROVIDER_KIND,
                            route_class=capabilities.route_class,
                            routing_subject_id=platform_sticky_identity.id,
                            identity=platform_sticky_identity,
                        )
                    )
            force_platform_fallback = bool(getattr(get_settings(), "platform_fallback_force_enabled", False))
            should_fallback = force_platform_fallback or await self.should_fallback_to_platform_for_usage_drain(
                model=capabilities.model,
                additional_limit_name=additional_limit_name,
                account_ids=scoped_account_ids,
            )
            if (
                should_fallback
                and not force_platform_fallback
                and self._hard_affinity_for_provider_fallback(
                    sticky_key=sticky_key,
                    sticky_kind=sticky_kind,
                )
            ):
                sticky_chatgpt_healthy = await self.sticky_chatgpt_target_is_healthy_for_platform_fallback(
                    sticky_key=sticky_key,
                    sticky_kind=cast(StickySessionKind, sticky_kind),
                    sticky_max_age_seconds=sticky_max_age_seconds,
                    model=capabilities.model,
                    additional_limit_name=additional_limit_name,
                    account_ids=scoped_account_ids,
                )
                if sticky_chatgpt_healthy:
                    should_fallback = False
                    logger.info(
                        "Suppressed usage-drain Platform fallback for healthy sticky ChatGPT target "
                        "request_id=%s route_family=%s sticky_kind=%s continuity_hint=%s",
                        get_request_id(),
                        capabilities.route_family,
                        sticky_kind.value if sticky_kind is not None else None,
                        capabilities.continuity_hint,
                    )
                elif capabilities.continuity_hint is not None:
                    sticky_chatgpt_selectable = await self.sticky_chatgpt_target_is_selectable_for_platform_fallback(
                        sticky_key=sticky_key,
                        sticky_kind=cast(StickySessionKind, sticky_kind),
                        sticky_max_age_seconds=sticky_max_age_seconds,
                        model=capabilities.model,
                        additional_limit_name=additional_limit_name,
                        account_ids=scoped_account_ids,
                    )
                    if sticky_chatgpt_selectable:
                        should_fallback = False
                        logger.info(
                            "Suppressed usage-drain Platform fallback for selectable sticky ChatGPT target "
                            "request_id=%s route_family=%s sticky_kind=%s continuity_hint=%s",
                            get_request_id(),
                            capabilities.route_family,
                            sticky_kind.value if sticky_kind is not None else None,
                            capabilities.continuity_hint,
                        )
            if should_fallback:
                if identity is not None:
                    identity = await self.select_platform_identity(
                        capabilities.route_family,
                        sticky_key=selection_platform_sticky_key,
                        sticky_kind=selection_platform_sticky_kind,
                        reallocate_sticky=selection_platform_reallocate_sticky,
                        sticky_max_age_seconds=selection_platform_sticky_max_age_seconds,
                    )
                if identity is not None:
                    decision = platform_adapter.check_capabilities(
                        self._platform_provider_subject(identity),
                        capabilities,
                    )
                    if decision.allowed:
                        return ProviderSelectionResult(
                            selected=SelectedPlatformSubject(
                                provider_kind=OPENAI_PLATFORM_PROVIDER_KIND,
                                route_class=capabilities.route_class,
                                routing_subject_id=identity.id,
                                identity=identity,
                            )
                        )
            return ProviderSelectionResult(
                selected=SelectedChatGPTSubject(
                    provider_kind=CHATGPT_WEB_PROVIDER_KIND,
                    route_class=capabilities.route_class,
                    routing_subject_id="chatgpt_web_pool",
                )
            )
        if identity is not None and has_active_chatgpt:
            platform_identity = await self.select_platform_identity(
                capabilities.route_family,
                sticky_key=selection_platform_sticky_key,
                sticky_kind=selection_platform_sticky_kind,
                reallocate_sticky=selection_platform_reallocate_sticky,
                sticky_max_age_seconds=selection_platform_sticky_max_age_seconds,
            )
            if platform_identity is not None:
                identity = platform_identity
            decision = platform_adapter.check_capabilities(
                self._platform_provider_subject(identity),
                capabilities,
            )
            if decision.allowed:
                return ProviderSelectionResult(
                    selected=SelectedPlatformSubject(
                        provider_kind=OPENAI_PLATFORM_PROVIDER_KIND,
                        route_class=capabilities.route_class,
                        routing_subject_id=identity.id,
                        identity=identity,
                    )
                )
            return self._provider_selection_failure(decision, capabilities)
        if identity is not None and not has_active_chatgpt:
            return ProviderSelectionResult(
                failure=ProviderSelectionFailure(
                    http_status=400,
                    error_code="provider_fallback_requires_chatgpt",
                    error_message="OpenAI Platform fallback requires at least one active ChatGPT-web account.",
                    rejection_reason="platform_fallback_requires_chatgpt",
                    route_class=capabilities.route_class,
                )
            )
        if has_active_chatgpt:
            return ProviderSelectionResult(
                selected=SelectedChatGPTSubject(
                    provider_kind=CHATGPT_WEB_PROVIDER_KIND,
                    route_class=capabilities.route_class,
                    routing_subject_id="chatgpt_web_pool",
                )
            )
        return ProviderSelectionResult()

    async def select_platform_identity(
        self,
        route_family: str,
        *,
        sticky_key: str | None = None,
        sticky_kind: StickySessionKind | None = None,
        reallocate_sticky: bool = False,
        sticky_max_age_seconds: int | None = None,
        exclude_routing_subject_ids: Collection[str] | None = None,
    ) -> _SelectedPlatformIdentity | None:
        selection = await self._load_balancer.select_routing_subject(
            provider_kind=OPENAI_PLATFORM_PROVIDER_KIND,
            route_family=route_family,  # type: ignore[arg-type]
            sticky_key=sticky_key,
            sticky_kind=sticky_kind,
            reallocate_sticky=reallocate_sticky,
            sticky_max_age_seconds=sticky_max_age_seconds,
            exclude_routing_subject_ids=exclude_routing_subject_ids,
        )
        if selection.routing_subject_id is None:
            return None
        async with self._repo_factory() as repos:
            platform_identities = repos.platform_identities
            if platform_identities is None:
                return None
            identity = await platform_identities.get_by_id(selection.routing_subject_id)
            if identity is None:
                return None
            return _SelectedPlatformIdentity(
                id=identity.id,
                api_key_encrypted=identity.api_key_encrypted,
                organization_id=identity.organization_id,
                project_id=identity.project_id,
            )

    async def _select_platform_prompt_cache_identity(
        self,
        route_family: str,
        *,
        sticky_key: str | None,
        sticky_kind: StickySessionKind | None,
        sticky_max_age_seconds: int | None,
    ) -> _SelectedPlatformIdentity | None:
        if not sticky_key or sticky_kind != StickySessionKind.PROMPT_CACHE:
            return None
        async with self._repo_factory() as repos:
            platform_identities = repos.platform_identities
            if platform_identities is None:
                return None
            sticky_target = await repos.sticky_sessions.get_target(
                sticky_key,
                kind=sticky_kind,
                provider_kind=OPENAI_PLATFORM_PROVIDER_KIND,
                max_age_seconds=sticky_max_age_seconds,
            )
            if sticky_target is None:
                return None
            identities = await platform_identities.list_eligible_identities(route_family)  # type: ignore[arg-type]
            identity = next(
                (candidate for candidate in identities if candidate.id == sticky_target.routing_subject_id),
                None,
            )
            if identity is None:
                await repos.sticky_sessions.delete_scoped(
                    sticky_key,
                    kind=sticky_kind,
                    provider_kind=OPENAI_PLATFORM_PROVIDER_KIND,
                )
                return None
            if sticky_max_age_seconds is not None:
                await repos.sticky_sessions.upsert_target(
                    sticky_key,
                    kind=sticky_kind,
                    provider_kind=OPENAI_PLATFORM_PROVIDER_KIND,
                    routing_subject_id=identity.id,
                )
            return _SelectedPlatformIdentity(
                id=identity.id,
                api_key_encrypted=identity.api_key_encrypted,
                organization_id=identity.organization_id,
                project_id=identity.project_id,
            )

    async def fetch_platform_models(
        self,
        api_key: ApiKeyData | None,
        *,
        identity: _SelectedPlatformIdentity | None = None,
        route_family: str = PUBLIC_MODELS_HTTP_ROUTE_FAMILY,
        route_class: str = OPENAI_PUBLIC_HTTP_ROUTE_CLASS,
    ) -> PlatformModelsResponse | None:
        if identity is None:
            identity = await self.select_platform_identity(route_family)
        if identity is None:
            return None
        adapter = cast(OpenAIPlatformProviderAdapter, self._provider_adapter(OPENAI_PLATFORM_PROVIDER_KIND))
        subject = self._platform_provider_subject(identity)
        request_id = ensure_request_id()
        start = time.monotonic()
        try:
            result = await adapter.fetch_models(subject, route_class=route_class)
        except OpenAIPlatformError as exc:
            await self._record_platform_auth_failure(identity.id, exc)
            await self._write_request_log(
                account_id=None,
                provider_kind=OPENAI_PLATFORM_PROVIDER_KIND,
                routing_subject_id=identity.id,
                api_key=api_key,
                request_id=request_id,
                model="",
                latency_ms=int((time.monotonic() - start) * 1000),
                status="error",
                error_code=_platform_error_code(exc.payload),
                error_message=_platform_error_message(exc.payload),
                route_class=route_class,
                rejection_reason="platform_models_request_failed",
                upstream_request_id=exc.upstream_request_id,
                transport=_REQUEST_TRANSPORT_HTTP,
            )
            raise
        await self._write_request_log(
            account_id=None,
            provider_kind=OPENAI_PLATFORM_PROVIDER_KIND,
            routing_subject_id=identity.id,
            api_key=api_key,
            request_id=request_id,
            model="",
            latency_ms=int((time.monotonic() - start) * 1000),
            status="success",
            route_class=route_class,
            upstream_request_id=result.upstream_request_id,
            transport=_REQUEST_TRANSPORT_HTTP,
        )
        return PlatformModelsResponse(
            payload=result.payload,
            upstream_request_id=result.upstream_request_id,
        )

    async def fetch_chatgpt_codex_models(
        self,
        api_key: ApiKeyData | None,
        *,
        headers: Mapping[str, str],
        route_class: str = CHATGPT_PRIVATE_ROUTE_CLASS,
    ) -> ProviderModelsResult | None:
        settings = await get_settings_cache().get()
        request_budget_seconds = getattr(get_settings(), "proxy_request_budget_seconds", 600.0)
        prefer_earlier_reset_accounts = getattr(settings, "prefer_earlier_reset_accounts", False)
        routing_strategy_value = getattr(settings, "routing_strategy", "capacity_weighted")
        if routing_strategy_value == "round_robin":
            routing_strategy: RoutingStrategy = "round_robin"
        elif routing_strategy_value == "usage_weighted":
            routing_strategy = "usage_weighted"
        else:
            routing_strategy = "capacity_weighted"
        adapter = cast(ChatGPTWebProviderAdapter, self._provider_adapter(CHATGPT_WEB_PROVIDER_KIND))
        request_id = ensure_request_id()
        start = time.monotonic()
        deadline = start + request_budget_seconds
        excluded_account_ids: set[str] = set()

        while True:
            try:
                selection = await self._select_account_with_budget_compatible(
                    deadline,
                    request_id=request_id,
                    kind="models",
                    api_key=api_key,
                    prefer_earlier_reset_accounts=prefer_earlier_reset_accounts,
                    routing_strategy=routing_strategy,
                    exclude_account_ids=excluded_account_ids,
                )
            except ProxyResponseError:
                logger.warning(
                    "Live ChatGPT model discovery exceeded request budget request_id=%s",
                    request_id,
                    exc_info=True,
                )
                return None

            account = selection.account
            if account is None:
                return None

            subject = self._chatgpt_provider_subject(account)
            try:
                result = await adapter.fetch_models(subject, headers=headers, route_class=route_class)
            except ProxyResponseError as exc:
                if exc.status_code == 401:
                    try:
                        refreshed_subject = await adapter.ensure_ready(subject, force=True)
                        account = refreshed_subject.require_account()
                        result = await adapter.fetch_models(
                            refreshed_subject,
                            headers=headers,
                            route_class=route_class,
                        )
                    except RefreshError:
                        logger.warning(
                            "Live ChatGPT model discovery refresh failed account_id=%s request_id=%s",
                            account.id,
                            request_id,
                            exc_info=True,
                        )
                        excluded_account_ids.add(account.id)
                        continue
                    except ProxyResponseError as retry_exc:
                        exc = retry_exc
                    else:
                        await self._load_balancer.record_success(account)
                        await self._write_request_log(
                            account_id=account.id,
                            provider_kind=CHATGPT_WEB_PROVIDER_KIND,
                            routing_subject_id=account.id,
                            api_key=api_key,
                            request_id=request_id,
                            model="",
                            latency_ms=int((time.monotonic() - start) * 1000),
                            status="success",
                            route_class=route_class,
                            upstream_request_id=result.upstream_request_id,
                            transport=_REQUEST_TRANSPORT_HTTP,
                        )
                        return result

                parsed_error = _parse_openai_error(exc.payload)
                error_code = _normalize_error_code(
                    parsed_error.code if parsed_error else None,
                    parsed_error.type if parsed_error else None,
                )
                error_message = parsed_error.message if parsed_error else "ChatGPT model discovery failed"
                await self._handle_proxy_error(account, exc)
                await self._write_request_log(
                    account_id=account.id,
                    provider_kind=CHATGPT_WEB_PROVIDER_KIND,
                    routing_subject_id=account.id,
                    api_key=api_key,
                    request_id=request_id,
                    model="",
                    latency_ms=int((time.monotonic() - start) * 1000),
                    status="error",
                    error_code=error_code,
                    error_message=error_message,
                    route_class=route_class,
                    upstream_request_id=exc.upstream_request_id,
                    rejection_reason="chatgpt_models_request_failed",
                    transport=_REQUEST_TRANSPORT_HTTP,
                )
                logger.warning(
                    "Live ChatGPT model discovery failed account_id=%s request_id=%s status=%s code=%s",
                    account.id,
                    request_id,
                    exc.status_code,
                    error_code,
                )
                excluded_account_ids.add(account.id)
                continue

            await self._load_balancer.record_success(account)
            await self._write_request_log(
                account_id=account.id,
                provider_kind=CHATGPT_WEB_PROVIDER_KIND,
                routing_subject_id=account.id,
                api_key=api_key,
                request_id=request_id,
                model="",
                latency_ms=int((time.monotonic() - start) * 1000),
                status="success",
                route_class=route_class,
                upstream_request_id=result.upstream_request_id,
                transport=_REQUEST_TRANSPORT_HTTP,
            )
            return result

    async def stream_platform_response_events(
        self,
        *,
        payload: ResponsesRequest,
        api_key: ApiKeyData | None,
        identity: _SelectedPlatformIdentity | None = None,
        route_family: str = PUBLIC_RESPONSES_HTTP_ROUTE_FAMILY,
        route_class: str = OPENAI_PUBLIC_HTTP_ROUTE_CLASS,
    ) -> tuple[_SelectedPlatformIdentity | None, PlatformStreamResponse | None]:
        if identity is None:
            identity = await self.select_platform_identity(route_family)
        if identity is None:
            return None, None
        adapter = cast(OpenAIPlatformProviderAdapter, self._provider_adapter(OPENAI_PLATFORM_PROVIDER_KIND))
        subject = self._platform_provider_subject(identity)
        request_id = ensure_request_id()
        start = time.monotonic()
        payload_dict = payload.model_dump(mode="json", exclude_none=True)
        forwarded_service_tier = payload.platform_forwarded_service_tier()
        if forwarded_service_tier is not None:
            payload_dict["service_tier"] = forwarded_service_tier
        try:
            result = await adapter.stream_responses(
                subject,
                payload_dict,
                route_class=route_class,
            )
        except OpenAIPlatformError as exc:
            await self._record_platform_auth_failure(identity.id, exc)
            await self.write_proxy_error_log(
                account_id=None,
                provider_kind=OPENAI_PLATFORM_PROVIDER_KIND,
                routing_subject_id=identity.id,
                api_key=api_key,
                request_id=request_id,
                model=payload.model,
                error_code=_platform_error_code(exc.payload) or "upstream_error",
                error_message=_platform_error_message(exc.payload) or "OpenAI Platform stream request failed",
                route_class=route_class,
                rejection_reason="platform_stream_request_failed",
                upstream_request_id=exc.upstream_request_id,
                transport=_REQUEST_TRANSPORT_HTTP,
                latency_ms=int((time.monotonic() - start) * 1000),
            )
            raise
        return identity, PlatformStreamResponse(
            event_stream=result.event_stream,
            upstream_request_id=result.upstream_request_id,
        )

    async def create_platform_response(
        self,
        *,
        payload: ResponsesRequest,
        api_key: ApiKeyData | None,
        identity: _SelectedPlatformIdentity | None = None,
        route_family: str = PUBLIC_RESPONSES_HTTP_ROUTE_FAMILY,
        route_class: str = OPENAI_PUBLIC_HTTP_ROUTE_CLASS,
    ) -> tuple[_SelectedPlatformIdentity | None, PlatformResponseResult | None]:
        if identity is None:
            identity = await self.select_platform_identity(route_family)
        if identity is None:
            return None, None
        adapter = cast(OpenAIPlatformProviderAdapter, self._provider_adapter(OPENAI_PLATFORM_PROVIDER_KIND))
        subject = self._platform_provider_subject(identity)
        request_id = ensure_request_id()
        start = time.monotonic()
        payload_dict = payload.model_dump(mode="json", exclude_none=True)
        forwarded_service_tier = payload.platform_forwarded_service_tier()
        if forwarded_service_tier is not None:
            payload_dict["service_tier"] = forwarded_service_tier
        try:
            result = await adapter.create_response(
                subject,
                payload_dict,
                route_class=route_class,
            )
        except OpenAIPlatformError as exc:
            await self._record_platform_auth_failure(identity.id, exc)
            await self.write_proxy_error_log(
                account_id=None,
                provider_kind=OPENAI_PLATFORM_PROVIDER_KIND,
                routing_subject_id=identity.id,
                api_key=api_key,
                request_id=request_id,
                model=payload.model,
                error_code=_platform_error_code(exc.payload) or "upstream_error",
                error_message=_platform_error_message(exc.payload) or "OpenAI Platform response request failed",
                route_class=route_class,
                rejection_reason="platform_response_request_failed",
                upstream_request_id=exc.upstream_request_id,
                transport=_REQUEST_TRANSPORT_HTTP,
                latency_ms=int((time.monotonic() - start) * 1000),
            )
            raise
        return identity, PlatformResponseResult(
            payload=result.payload,
            upstream_request_id=result.upstream_request_id,
        )

    async def write_provider_rejection_log(
        self,
        *,
        api_key: ApiKeyData | None,
        request_id: str,
        model: str | None,
        error_code: str,
        error_message: str,
        route_class: str,
        rejection_reason: str,
        transport: str = _REQUEST_TRANSPORT_HTTP,
    ) -> None:
        await self.write_proxy_error_log(
            account_id=None,
            provider_kind=None,
            routing_subject_id=None,
            api_key=api_key,
            request_id=request_id,
            model=model,
            error_code=error_code,
            error_message=error_message,
            route_class=route_class,
            rejection_reason=rejection_reason,
            transport=transport,
        )

    async def write_proxy_error_log(
        self,
        *,
        account_id: str | None,
        provider_kind: str | None,
        routing_subject_id: str | None,
        api_key: ApiKeyData | None,
        request_id: str,
        model: str | None,
        error_code: str,
        error_message: str,
        route_class: str | None,
        rejection_reason: str | None,
        upstream_request_id: str | None = None,
        transport: str = _REQUEST_TRANSPORT_HTTP,
        latency_ms: int = 0,
        session_id: str | None = None,
    ) -> None:
        await self._write_request_log(
            account_id=account_id,
            provider_kind=provider_kind,
            routing_subject_id=routing_subject_id,
            api_key=api_key,
            request_id=request_id,
            model=model,
            latency_ms=latency_ms,
            status="error",
            error_code=error_code,
            error_message=error_message,
            route_class=route_class,
            rejection_reason=rejection_reason,
            upstream_request_id=upstream_request_id,
            transport=transport,
            session_id=session_id,
        )

    async def _record_platform_auth_failure(self, identity_id: str, exc: OpenAIPlatformError) -> None:
        if exc.status_code not in (401, 403):
            return
        reason = _platform_error_message(exc.payload) or _platform_error_code(exc.payload) or f"http_{exc.status_code}"
        async with self._repo_factory() as repos:
            platform_identities = repos.platform_identities
            if platform_identities is None:
                return
            updated = await platform_identities.update_validation_state(
                identity_id,
                last_validated_at=None,
                last_auth_failure_reason=reason,
                status=AccountStatus.DEACTIVATED,
            )
        if updated:
            logger.warning(
                "provider_health_transition request_id=%s provider_kind=%s routing_subject_id=%s status=%s reason=%s",
                get_request_id(),
                OPENAI_PLATFORM_PROVIDER_KIND,
                identity_id,
                AccountStatus.DEACTIVATED.value,
                reason,
            )
