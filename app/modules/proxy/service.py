from __future__ import annotations

import asyncio
import dataclasses
import inspect
import json
import logging
import re
import time
from collections import deque
from collections.abc import AsyncGenerator, Awaitable, Callable, Collection
from contextlib import aclosing, asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Literal, Mapping, NoReturn, TypeVar, cast
from uuid import uuid4

import aiohttp
import anyio
from fastapi import WebSocket
from pydantic import ValidationError

import app.modules.proxy.provider_adapters as _provider_adapters
from app.core.auth.refresh import (
    RefreshError,
    pop_token_refresh_timeout_override,
    push_token_refresh_timeout_override,
)
from app.core.balancer import (
    PERMANENT_FAILURE_CODES,
    TRAFFIC_CLASS_FOREGROUND,
    TRAFFIC_CLASS_OPPORTUNISTIC,
    ResetPreferenceWindow,
    RoutingStrategy,
    TrafficClass,
    failover_decision,
)
from app.core.balancer.rendezvous_hash import select_node
from app.core.clients.files import FileProxyError, pop_files_timeout_overrides, push_files_timeout_overrides
from app.core.clients.files import create_file as core_create_file  # noqa: F401
from app.core.clients.files import finalize_file as core_finalize_file  # noqa: F401
from app.core.clients.http import lease_http_session as lease_http_session  # noqa: F401
from app.core.clients.openai_platform import (
    OpenAIPlatformError,
    PlatformModelsResponse,
    PlatformResponseResult,
    PlatformStreamResponse,
)
from app.core.clients.proxy import CodexControlResponse as CodexControlResponse
from app.core.clients.proxy import (  # noqa: F401
    ImageFetchSession,
    ProxyResponseError,
    UpstreamProxyRouteTrace,
    _as_image_fetch_session,
    _inline_content_images,
    _inline_input_image_urls,
    _ws_transport_payload_budget_bytes,
    filter_inbound_headers,
    pop_compact_timeout_overrides,
    pop_stream_timeout_overrides,
    pop_transcribe_timeout_overrides,
    push_compact_timeout_overrides,
    push_stream_timeout_overrides,
    push_transcribe_timeout_overrides,
)
from app.core.clients.proxy import codex_control_request as core_codex_control_request  # noqa: F401
from app.core.clients.proxy import thread_goal_request as core_thread_goal_request
from app.core.clients.proxy_websocket import (
    UpstreamResponsesWebSocket,
    filter_inbound_websocket_headers,
)
from app.core.clients.proxy_websocket import (
    connect_responses_websocket as connect_responses_websocket,
)
from app.core.config.settings import Settings, get_settings
from app.core.config.settings_cache import get_settings_cache
from app.core.crypto import TokenEncryptor
from app.core.errors import (
    PREVIOUS_RESPONSE_STALE_CODE as PREVIOUS_RESPONSE_STALE_CODE,
)
from app.core.errors import (
    PREVIOUS_RESPONSE_STALE_MESSAGE as PREVIOUS_RESPONSE_STALE_MESSAGE,
)
from app.core.errors import (
    OpenAIErrorEnvelope,
    ResponseFailedEvent,
    is_previous_response_not_found_error,
    is_previous_response_not_found_message,
    openai_error,
    previous_response_id_from_not_found_message,
    previous_response_stream_incomplete_error,
    response_failed_event,
)
from app.core.exceptions import AppError
from app.core.metrics.prometheus import (
    PROMETHEUS_AVAILABLE,
    bridge_durable_recover_total,
    bridge_forward_latency_seconds,
    bridge_owner_forward_total,
    bridge_same_account_takeover_total,
)
from app.core.openai.exceptions import ClientPayloadError
from app.core.openai.models import CompactResponsePayload, OpenAIResponsePayload
from app.core.openai.requests import (
    ResponsesCompactRequest,
    ResponsesRequest,
    extract_input_file_ids,
    extract_input_image_file_references,
)
from app.core.resilience.overload import is_local_overload_error_code
from app.core.types import JsonValue
from app.core.upstream_proxy import ResolvedUpstreamRoute, UpstreamProxyRouteError
from app.core.upstream_proxy.resolver import (
    resolve_upstream_route as resolve_upstream_route,
)
from app.core.utils.json_guards import is_json_mapping
from app.core.utils.request_id import ensure_request_id, get_request_id
from app.core.utils.retry import backoff_seconds
from app.core.utils.sse import CODEX_KEEPALIVE_FRAME as CODEX_KEEPALIVE_FRAME  # noqa: F401
from app.core.utils.sse import format_sse_event, parse_sse_data_json  # noqa: F401
from app.core.utils.time import to_utc_naive, utcnow
from app.db.models import (
    Account,
    AccountStatus,  # noqa: F401
    DashboardSettings,
    HttpBridgeSessionState,
    StickySessionKind,
)
from app.db.session import SessionLocal as SessionLocal
from app.modules.accounts.auth_manager import AccountsRepositoryPort, AuthManager
from app.modules.api_keys.service import (
    API_KEY_USAGE_RESERVATION_DEFAULT_INPUT_TOKENS,
    API_KEY_USAGE_RESERVATION_DEFAULT_OUTPUT_TOKENS,
    API_KEY_USAGE_RESERVATION_MAX_TOKEN_BUDGET,
    ApiKeyData,
    ApiKeyRequestUsageBudget,
    ApiKeyUsageReservationData,  # noqa: F401
)
from app.modules.api_keys.service import (
    ApiKeysService as ApiKeysService,
)
from app.modules.proxy._service.api_key_usage import (
    _API_KEY_RESERVATION_HEARTBEAT_SECONDS as _API_KEY_RESERVATION_HEARTBEAT_SECONDS,
)
from app.modules.proxy._service.api_key_usage import (
    _ApiKeyUsageMixin,
)
from app.modules.proxy._service.codex_control import (
    _CodexControlMixin,
)
from app.modules.proxy._service.compact import (
    _CompactMixin,
)
from app.modules.proxy._service.file_ops import (
    _FileOpsMixin,
)
from app.modules.proxy._service.http_bridge import (
    _HTTPBridgeMixin,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _build_http_bridge_prewarm_text as _build_http_bridge_prewarm_text,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _effective_http_bridge_idle_ttl_seconds as _effective_http_bridge_idle_ttl_seconds,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _forwarded_http_bridge_session_key as _forwarded_http_bridge_session_key,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _has_http_bridge_response_output_marker as _has_http_bridge_response_output_marker,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_continuity_lost_error_envelope as _http_bridge_continuity_lost_error_envelope,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_durable_lease_ttl_seconds as _http_bridge_durable_lease_ttl_seconds,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_endpoint_matches_current_instance as _http_bridge_endpoint_matches_current_instance,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_eviction_priority as _http_bridge_eviction_priority,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_input_item_type as _http_bridge_input_item_type,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_is_previous_response_owner_unavailable as _http_bridge_is_previous_response_owner_unavailable,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_owner_lookup_unavailable_error_envelope as _http_bridge_owner_lookup_unavailable_error_envelope,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_payload_looks_like_full_resend as _http_bridge_payload_looks_like_full_resend,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_payload_without_previous_response_id as _http_bridge_payload_without_previous_response_id,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_precreated_retry_failure_error as _http_bridge_precreated_retry_failure_error,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_previous_response_error_envelope as _http_bridge_previous_response_error_envelope,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_request_counts_against_queue as _http_bridge_request_counts_against_queue,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_requires_cluster_registration as _http_bridge_requires_cluster_registration,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_session_has_visible_requests as _http_bridge_session_has_visible_requests,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_session_retiring_with_visible_requests as _http_bridge_session_retiring_with_visible_requests,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_should_attempt_soft_affinity_reroute as _http_bridge_should_attempt_soft_affinity_reroute,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _http_bridge_startup_wait_timeout_error as _http_bridge_startup_wait_timeout_error,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _is_http_bridge_previous_response_output_item as _is_http_bridge_previous_response_output_item,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _is_missing_durable_bridge_table_error as _is_missing_durable_bridge_table_error,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _log_http_bridge_startup_wait_timeout as _log_http_bridge_startup_wait_timeout,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _normalize_http_bridge_error_event as _normalize_http_bridge_error_event,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _record_bridge_drain_recovery_allowed as _record_bridge_drain_recovery_allowed,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _record_bridge_first_turn_timeout as _record_bridge_first_turn_timeout,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _record_bridge_reattach as _record_bridge_reattach,
)
from app.modules.proxy._service.http_bridge.helpers import (
    _trim_http_bridge_previous_response_input_items as _trim_http_bridge_previous_response_input_items,
)
from app.modules.proxy._service.observability import (
    _hash_identifier as _hash_identifier,
)
from app.modules.proxy._service.observability import (
    _hash_identifier_or_none as _hash_identifier_or_none,
)
from app.modules.proxy._service.observability import (
    _interesting_header_keys as _interesting_header_keys,
)
from app.modules.proxy._service.observability import (
    _maybe_log_proxy_request_payload as _maybe_log_proxy_request_payload,
)
from app.modules.proxy._service.observability import (
    _maybe_log_proxy_request_shape as _maybe_log_proxy_request_shape,
)
from app.modules.proxy._service.observability import (
    _maybe_log_proxy_service_tier_trace as _maybe_log_proxy_service_tier_trace,
)
from app.modules.proxy._service.observability import (
    _record_continuity_fail_closed as _record_continuity_fail_closed,
)
from app.modules.proxy._service.observability import (
    _record_continuity_owner_resolution as _record_continuity_owner_resolution,
)
from app.modules.proxy._service.observability import (
    _summarize_input as _summarize_input,
)
from app.modules.proxy._service.observability import (
    _tools_hash as _tools_hash,
)
from app.modules.proxy._service.observability import (
    _truncate_identifier as _truncate_identifier,
)
from app.modules.proxy._service.observability import (
    continuity_fail_closed_total as continuity_fail_closed_total,
)
from app.modules.proxy._service.observability import (
    continuity_owner_resolution_total as continuity_owner_resolution_total,
)
from app.modules.proxy._service.rate_limit import (
    _RateLimitMixin,
)
from app.modules.proxy._service.request_log import (
    _RequestLogMixin,
)
from app.modules.proxy._service.response_create import (
    _count_external_image_urls as _count_external_image_urls,
)
from app.modules.proxy._service.response_create import (
    _enforce_response_create_size_limit as _enforce_response_create_size_limit,
)
from app.modules.proxy._service.response_create import (
    _fingerprint_input_items as _fingerprint_input_items,
)
from app.modules.proxy._service.response_create import (
    _function_call_output_call_ids as _function_call_output_call_ids,
)
from app.modules.proxy._service.response_create import (
    _inject_missing_interrupted_function_call_outputs as _inject_missing_interrupted_function_call_outputs,
)
from app.modules.proxy._service.response_create import (
    _inline_top_level_input_image_urls as _inline_top_level_input_image_urls,
)
from app.modules.proxy._service.response_create import (
    _input_part_is_image as _input_part_is_image,
)
from app.modules.proxy._service.response_create import (
    _is_inline_image_reference as _is_inline_image_reference,
)
from app.modules.proxy._service.response_create import (
    _json_size_bytes as _json_size_bytes,
)
from app.modules.proxy._service.response_create import (
    _json_value_contains_input_image_part as _json_value_contains_input_image_part,
)
from app.modules.proxy._service.response_create import (
    _maybe_dump_oversized_response_create_request as _maybe_dump_oversized_response_create_request,
)
from app.modules.proxy._service.response_create import (
    _missing_function_call_outputs_for_previous_response as _missing_function_call_outputs_for_previous_response,
)
from app.modules.proxy._service.response_create import (
    _oversized_response_create_dump_dir as _oversized_response_create_dump_dir,
)
from app.modules.proxy._service.response_create import (
    _response_create_history_omission_notice_item as _response_create_history_omission_notice_item,
)
from app.modules.proxy._service.response_create import (
    _response_create_inline_image_notice_item as _response_create_inline_image_notice_item,
)
from app.modules.proxy._service.response_create import (
    _response_create_inline_image_notice_part as _response_create_inline_image_notice_part,
)
from app.modules.proxy._service.response_create import (
    _response_create_recent_suffix_start as _response_create_recent_suffix_start,
)
from app.modules.proxy._service.response_create import (
    _response_create_text as _response_create_text,
)
from app.modules.proxy._service.response_create import (
    _response_create_text_with_size_guard as _response_create_text_with_size_guard,
)
from app.modules.proxy._service.response_create import (
    _response_create_too_large_error_envelope as _response_create_too_large_error_envelope,
)
from app.modules.proxy._service.response_create import (
    _response_output_item_done_function_call_id as _response_output_item_done_function_call_id,
)
from app.modules.proxy._service.response_create import (
    _responses_request_contains_input_image as _responses_request_contains_input_image,
)
from app.modules.proxy._service.response_create import (
    _responses_request_uses_image_generation as _responses_request_uses_image_generation,
)
from app.modules.proxy._service.response_create import (
    _safe_dump_slug as _safe_dump_slug,
)
from app.modules.proxy._service.response_create import (
    _should_dump_oversized_response_create as _should_dump_oversized_response_create,
)
from app.modules.proxy._service.response_create import (
    _should_slim_historical_tool_output as _should_slim_historical_tool_output,
)
from app.modules.proxy._service.response_create import (
    _slim_historical_response_content as _slim_historical_response_content,
)
from app.modules.proxy._service.response_create import (
    _slim_historical_response_content_part as _slim_historical_response_content_part,
)
from app.modules.proxy._service.response_create import (
    _slim_historical_response_input_item as _slim_historical_response_input_item,
)
from app.modules.proxy._service.response_create import (
    _slim_response_create_payload_for_upstream as _slim_response_create_payload_for_upstream,
)
from app.modules.proxy._service.response_create import (
    _summarize_response_create_input as _summarize_response_create_input,
)
from app.modules.proxy._service.response_create import (
    _summarize_response_create_payload as _summarize_response_create_payload,
)
from app.modules.proxy._service.response_create import (
    _synthetic_interrupted_function_call_output as _synthetic_interrupted_function_call_output,
)
from app.modules.proxy._service.response_create import (
    _write_response_create_dump as _write_response_create_dump,
)
from app.modules.proxy._service.streaming import (
    _StreamingMixin,
)
from app.modules.proxy._service.streaming.helpers import (
    _build_rewritten_stream_response_failed_event as _build_rewritten_stream_response_failed_event,
)
from app.modules.proxy._service.streaming.helpers import (
    _build_stream_incomplete_terminal_event_for_request as _build_stream_incomplete_terminal_event_for_request,
)
from app.modules.proxy._service.streaming.helpers import (
    _call_stream_with_supported_optional_kwargs as _call_stream_with_supported_optional_kwargs,
)
from app.modules.proxy._service.streaming.helpers import (
    _classify_upstream_close as _classify_upstream_close,
)
from app.modules.proxy._service.streaming.helpers import (
    _push_stream_attempt_timeout_overrides as _push_stream_attempt_timeout_overrides,
)
from app.modules.proxy._service.streaming.helpers import (
    _refresh_upstream_proxy_fail_closed_reason as _refresh_upstream_proxy_fail_closed_reason,
)
from app.modules.proxy._service.streaming.helpers import (
    _resolve_upstream_stream_transport as _resolve_upstream_stream_transport,
)
from app.modules.proxy._service.streaming.helpers import (
    _rewrite_previous_response_stream_error as _rewrite_previous_response_stream_error,
)
from app.modules.proxy._service.streaming.helpers import (
    _should_infer_upstream_status_from_proxy_error as _should_infer_upstream_status_from_proxy_error,
)
from app.modules.proxy._service.streaming.helpers import (
    _should_penalize_stream_error as _should_penalize_stream_error,
)
from app.modules.proxy._service.streaming.helpers import (
    _should_retry_stream_error as _should_retry_stream_error,
)
from app.modules.proxy._service.streaming.helpers import (
    _should_retry_transient_stream_error as _should_retry_transient_stream_error,
)
from app.modules.proxy._service.streaming.helpers import (
    _stream_request_budget_seconds as _stream_request_budget_seconds,
)
from app.modules.proxy._service.support import (
    _HARD_HTTP_BRIDGE_AFFINITY_KINDS,  # noqa: F401
    _REQUEST_TRANSPORT_WEBSOCKET,  # noqa: F401
    _WEBSOCKET_FULL_REPLAY_WAIT_MIN_ITEMS,  # noqa: F401
    _WEBSOCKET_FULL_REPLAY_WAIT_POLL_SECONDS,  # noqa: F401
    _ApiKeyReservationTouchState,  # noqa: F401
    _clear_websocket_request_error_overrides,  # noqa: F401
    _DownstreamWebSocketActivity,  # noqa: F401
    _event_type_from_payload,  # noqa: F401
    _FilePinEntry,
    _HTTPBridgeSession,
    _HTTPBridgeSessionKey,
    _PreparedWebSocketRequest,  # noqa: F401
    _record_response_event,  # noqa: F401
    _record_websocket_route_metadata,  # noqa: F401
    _request_log_useragent_fields,
    _RequestLogFailureMetadata,
    _RetryableStreamError,  # noqa: F401
    _stream_settlement_error_payload,  # noqa: F401
    _StreamSettlement,  # noqa: F401
    _TerminalStreamError,  # noqa: F401
    _TransientStreamError,  # noqa: F401
    _wait_for_websocket_continuity_gap,  # noqa: F401
    _websocket_full_replay_should_wait_for_continuity,  # noqa: F401
    _websocket_request_can_replay_before_visible_output,  # noqa: F401
    _WebSocketConnectFailureEmitted,  # noqa: F401
    _WebSocketContinuityAnchor,  # noqa: F401
    _WebSocketContinuityState,
    _WebSocketReceiveTimeout,  # noqa: F401
    _WebSocketRequestState,
    _WebSocketUpstreamControl,  # noqa: F401
)
from app.modules.proxy._service.support import (
    _HTTPBridgeOwnerForward as _HTTPBridgeOwnerForward,
)
from app.modules.proxy._service.support import (
    _websocket_route_log_kwargs as _websocket_route_log_kwargs,
)
from app.modules.proxy._service.transcribe import (
    _TranscribeMixin,
)
from app.modules.proxy._service.warmup import (
    WarmupExecutionData as WarmupExecutionData,
)
from app.modules.proxy._service.warmup import (
    WarmupFailedAccountData as WarmupFailedAccountData,
)
from app.modules.proxy._service.warmup import (
    WarmupSkippedAccountData as WarmupSkippedAccountData,
)
from app.modules.proxy._service.warmup import (
    WarmupSubmittedAccountData as WarmupSubmittedAccountData,
)
from app.modules.proxy._service.warmup import (
    _is_warmup_usage_eligible as _is_warmup_usage_eligible,
)
from app.modules.proxy._service.warmup import (
    _materialize_warmup_account as _materialize_warmup_account,
)
from app.modules.proxy._service.warmup import (
    _snapshot_warmup_account as _snapshot_warmup_account,
)
from app.modules.proxy._service.warmup import (
    _WarmupAccountSnapshot as _WarmupAccountSnapshot,
)
from app.modules.proxy._service.warmup import (
    _WarmupMixin,
)
from app.modules.proxy._service.warmup import (
    _WarmupSubmitResult as _WarmupSubmitResult,
)
from app.modules.proxy._service.warmup import (
    _WarmupUsageSnapshot as _WarmupUsageSnapshot,
)
from app.modules.proxy._service.websocket import (
    _WebSocketMixin,
)
from app.modules.proxy._service.websocket.helpers import (
    _app_error_to_websocket_event,  # noqa: F401
    _assign_websocket_response_id,  # noqa: F401
    _draining_websocket_request_states,  # noqa: F401
    _find_websocket_request_state_by_response_id,  # noqa: F401
    _is_websocket_previous_response_output_item,  # noqa: F401
    _is_websocket_response_create,  # noqa: F401
    _match_websocket_request_state_for_anonymous_event,  # noqa: F401
    _match_websocket_request_state_for_precreated_terminal_event,  # noqa: F401
    _match_websocket_request_state_for_previous_response_error,  # noqa: F401
    _matching_websocket_request_states_for_missing_tool_output_error,  # noqa: F401
    _matching_websocket_request_states_for_previous_response_error,  # noqa: F401
    _maybe_rewrite_websocket_previous_response_not_found_event,  # noqa: F401
    _parse_websocket_payload,  # noqa: F401
    _pop_matching_websocket_request_states,  # noqa: F401
    _pop_replayable_precreated_websocket_request_state,  # noqa: F401
    _pop_terminal_websocket_request_state,  # noqa: F401
    _prepare_websocket_request_state_for_auth_replay,  # noqa: F401
    _prepare_websocket_request_state_for_visible_output_replay,  # noqa: F401
    _record_websocket_continuity_completion,  # noqa: F401
    _refresh_websocket_request_input_fingerprint_from_text,  # noqa: F401
    _release_websocket_response_create_gate,  # noqa: F401
    _rewrite_websocket_continuity_corruption_event,  # noqa: F401
    _rewrite_websocket_downstream_response_id,  # noqa: F401
    _rewrite_websocket_previous_response_owner_unavailable_event,  # noqa: F401
    _rewrite_websocket_suppressed_duplicate_tool_call_completion_event,  # noqa: F401
    _sanitize_websocket_connect_failure,  # noqa: F401
    _sanitize_websocket_previous_response_error,  # noqa: F401
    _sanitize_websocket_terminal_error_fields,  # noqa: F401
    _serialize_websocket_error_event,  # noqa: F401
    _trim_websocket_previous_response_input_items,  # noqa: F401
    _upstream_websocket_disconnect_message,  # noqa: F401
    _websocket_auth_failure_permanent_code,  # noqa: F401
    _websocket_auth_failure_requires_reauth,  # noqa: F401
    _websocket_auth_request_can_switch_account,  # noqa: F401
    _websocket_client_previous_response_full_resend_is_retry_safe,  # noqa: F401
    _websocket_connect_deadline,  # noqa: F401
    _websocket_continuity_anchor_for_payload,  # noqa: F401
    _websocket_continuity_error_fields,  # noqa: F401
    _websocket_continuity_response_ids,  # noqa: F401
    _websocket_downstream_response_id,  # noqa: F401
    _websocket_event_error_code,  # noqa: F401
    _websocket_event_error_message,  # noqa: F401
    _websocket_event_error_param,  # noqa: F401
    _websocket_event_error_payload,  # noqa: F401
    _websocket_event_error_type,  # noqa: F401
    _websocket_full_resend_conflicts_with_visible_pending,  # noqa: F401
    _websocket_input_item_type,  # noqa: F401
    _websocket_owner_pinned_quota_error_code,  # noqa: F401
    _websocket_precreated_auth_error_code,  # noqa: F401
    _websocket_precreated_retry_error_code,  # noqa: F401
    _websocket_receive_timeout_for_pending_requests,  # noqa: F401
    _websocket_response_id,  # noqa: F401
    _websocket_top_level_error_payload,  # noqa: F401
    _wrapped_websocket_error_event,  # noqa: F401
)
from app.modules.proxy.affinity import (
    _AffinityPolicy,
    _derive_prompt_cache_key,
    _extract_model_class,
    _prompt_cache_key_from_request_model,
    _sticky_key_for_codex_control_request,
)
from app.modules.proxy.durable_bridge_coordinator import (
    DurableBridgeLookup as DurableBridgeLookup,
)
from app.modules.proxy.durable_bridge_coordinator import (
    DurableBridgeSessionCoordinator,
)
from app.modules.proxy.helpers import (
    _apply_error_metadata,
    _header_account_id,
    _normalize_error_code,
    _parse_openai_error,
    _upstream_error_from_openai,
)
from app.modules.proxy.http_bridge_forwarding import (
    HTTPBridgeForwardContext as HTTPBridgeForwardContext,
)
from app.modules.proxy.http_bridge_forwarding import (
    HTTPBridgeOwnerClient,
)
from app.modules.proxy.http_bridge_forwarding import (
    OwnerForwardRelayFailure as OwnerForwardRelayFailure,
)
from app.modules.proxy.load_balancer import (
    AccountLease,
    AccountLeaseKind,
    AccountSelection,
    LoadBalancer,
    _filter_accounts_for_model,
    _gated_limit_name_for_model,
)
from app.modules.proxy.platform_cache_alerts import get_platform_cache_alert_service
from app.modules.proxy.provider_adapters import (
    ChatGPTWebProviderAdapter,
    OpenAIPlatformProviderAdapter,
    ProviderAdapter,
    ProviderCapabilityDecision,
    ProviderCompactResponseResult,
    ProviderModelsResult,
    ProviderSubject,
    RequestCapabilities,
)
from app.modules.proxy.provider_adapters import (
    core_compact_responses as _adapter_core_compact_responses,
)
from app.modules.proxy.provider_adapters import (
    core_transcribe_audio as _adapter_core_transcribe_audio,
)
from app.modules.proxy.repo_bundle import ProxyRepoFactory
from app.modules.proxy.request_policy import (
    apply_api_key_enforcement,
    normalize_responses_request_payload,
    openai_client_payload_error,
    openai_invalid_payload_error,
    openai_validation_error,
    validate_model_access,
)
from app.modules.proxy.ring_membership import RingMembershipService
from app.modules.proxy.work_admission import WorkAdmissionController
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

# Compatibility seam for tests and legacy patch points. Provider adapters consult
# these callables when they retain their default transport bindings.
core_compact_responses = _adapter_core_compact_responses
core_transcribe_audio = _adapter_core_transcribe_audio


def core_stream_responses(*args: Any, **kwargs: Any) -> AsyncIterator[str]:
    return _provider_adapters.core_stream_responses(*args, **kwargs)


_UPSTREAM_RESPONSE_CREATE_MAX_BYTES = get_settings().upstream_response_create_max_bytes
_UPSTREAM_RESPONSE_CREATE_WARN_BYTES = int(_UPSTREAM_RESPONSE_CREATE_MAX_BYTES * 0.8)
# Keep this override unset by default so oversized-payload dumps follow the
# runtime ``data_dir``. Tests and legacy callers may still monkeypatch it.
_OVERSIZED_RESPONSE_CREATE_DUMP_DIR = None
_OVERSIZED_RESPONSE_CREATE_LARGEST_ITEMS = 10
_RESPONSE_CREATE_HISTORY_OMISSION_NOTICE = (
    "[codex-lb omitted {count} historical input items to fit upstream websocket budget]"
)
_RESPONSE_CREATE_TOOL_OUTPUT_OMISSION_NOTICE = (
    "[codex-lb omitted historical tool output ({bytes} bytes) to fit upstream websocket budget]"
)
_RESPONSE_CREATE_IMAGE_OMISSION_NOTICE = "[codex-lb omitted historical inline image to fit upstream websocket budget]"

_TASK_CANCEL_TIMEOUT_SECONDS = 1.0
_TaskResultT = TypeVar("_TaskResultT")
_ResponsesPayloadT = TypeVar("_ResponsesPayloadT", ResponsesRequest, ResponsesCompactRequest)
_DOWNSTREAM_WEBSOCKET_IDLE_CLOSE_REASON = "Idle downstream websocket timeout"
_DOWNSTREAM_WEBSOCKET_RECEIVE_POLL_SECONDS = 1.0
# Keep the first HTTP bridge liveness frame behind the API layer's startup
# error probe window. If a keepalive becomes the first yielded chunk, the HTTP
# status is committed as 200 and startup ProxyResponseError handling is masked.
_HTTP_BRIDGE_STARTUP_KEEPALIVE_GRACE_SECONDS = 0.5
_DEFAULT_PROXY_ADMISSION_WAIT_TIMEOUT_SECONDS = 10.0


def _proxy_admission_wait_timeout_seconds(settings: Any | None = None) -> float:
    settings = settings or get_settings()
    raw_timeout = getattr(
        settings,
        "proxy_admission_wait_timeout_seconds",
        _DEFAULT_PROXY_ADMISSION_WAIT_TIMEOUT_SECONDS,
    )
    try:
        timeout = float(raw_timeout)
    except (TypeError, ValueError):
        timeout = _DEFAULT_PROXY_ADMISSION_WAIT_TIMEOUT_SECONDS
    return max(0.001, timeout)


# Maximum time (seconds) to wait for a prewarm upstream response before
# giving up and letting the actual request proceed without prewarming.
# A blocked prewarm holds the response_create_gate semaphore and prevents
# the real request from being sent, leading to an indefinite :keepalive hang.
_PREWARM_RESPONSE_TIMEOUT_SECONDS = 2.0
_HTTP_BRIDGE_BACKGROUND_CLOSE_TIMEOUT_SECONDS = 5.0
_HTTP_BRIDGE_BACKGROUND_CLEANUP_WARN_THRESHOLD = 100
# Maximum consecutive keepalive frames sent before terminating the stream.
# 6 × 10s (default interval) = 60s.  Combined with the 0.5s startup-probe
# window this ensures the client sees a terminal event within ≈70s when the
# upstream silently stops responding.
_STREAM_KEEPALIVE_MAX_COUNT = 6


async def _await_cancelled_task(
    task: asyncio.Task[_TaskResultT],
    *,
    timeout_seconds: float = _TASK_CANCEL_TIMEOUT_SECONDS,
    label: str,
) -> bool:
    task.cancel()
    try:
        await asyncio.wait_for(task, timeout=timeout_seconds)
    except asyncio.CancelledError:
        return True
    except TimeoutError:
        logger.warning("Timed out waiting for %s cancellation", label)
        return False
    return True


_TEXT_DELTA_EVENT_TYPES = frozenset({"response.output_text.delta", "response.refusal.delta"})
_TEXT_DONE_CONTENT_PART_TYPES = frozenset({"output_text", "refusal"})
_REQUEST_TRANSPORT_HTTP = "http"
_COMPACT_SAME_CONTRACT_RETRY_BUDGET = 1
_ACCOUNT_RECOVERY_RETRY_CODES = frozenset(
    {
        "rate_limit_exceeded",
        "usage_limit_reached",
        "insufficient_quota",
        "usage_not_included",
        "quota_exceeded",
        *PERMANENT_FAILURE_CODES.keys(),
    }
)
_TRANSIENT_RETRY_CODES = frozenset(
    {
        "server_error",
        "stream_incomplete",
        "stream_idle_timeout",
        "upstream_request_timeout",
    }
)
_UPSTREAM_UNAVAILABLE_TRANSIENT_MESSAGE_MARKERS = (
    "broken pipe",
    "cannot connect",
    "connection aborted",
    "connection closed",
    "connection reset",
    "keepalive ping timeout",
    "no close frame",
    "server disconnected",
    "timed out",
    "timeout",
    "upstream closed",
)
_UPSTREAM_UNAVAILABLE_NON_TRANSIENT_MESSAGE_MARKERS = (
    "certificate verify failed",
    "clientconnectorcertificateerror",
    "sslcertverificationerror",
)
_UPSTREAM_CLOSE_CODES_SKIP_SAME_ACCOUNT_RETRY = frozenset({1011})
_MAX_TRANSIENT_SAME_ACCOUNT_RETRIES = 3
_COMPACT_MAX_ACCOUNT_ATTEMPTS = 2
_STREAM_MAX_ACCOUNT_ATTEMPTS = 3
_WEBSOCKET_MAX_ACCOUNT_ATTEMPTS = 3
_WEBSOCKET_TRANSPARENT_REPLAY_ERROR_CODES = frozenset(
    {
        "rate_limit_exceeded",
        "usage_limit_reached",
        "insufficient_quota",
        "usage_not_included",
        "quota_exceeded",
    }
)
_WEBSOCKET_AUTH_FAILURE_CODES = frozenset({"invalid_api_key", "invalid_authentication", "token_invalidated"})
_WEBSOCKET_REAUTH_REQUIRED_MESSAGE_MARKERS = (
    "session has ended",
    "session expired",
    "log in again",
    "login again",
    "reauth",
    "re-auth",
)
_WEBSOCKET_SESSION_EXPIRED_FAILURE_CODE = "account_session_expired"
_WEBSOCKET_AUTH_INVALIDATED_FAILURE_CODE = "account_auth_invalidated"
_SUPPRESSED_DUPLICATE_TOOL_CALL_MESSAGE = (
    "Suppressed duplicate side-effect tool call; upstream response cannot be continued safely."
)
_WEBSOCKET_PREVIOUS_RESPONSE_ACCOUNT_CACHE_LIMIT = 4096


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


_WEBSOCKET_CONTINUITY_CACHE_LIMIT = 4096
_SECURITY_WORK_AUTHORIZATION_REQUIRED_CODE = "security_work_authorization_required"
_NO_SECURITY_WORK_AUTHORIZED_ACCOUNTS_CODE = "no_security_work_authorized_accounts"
_SECURITY_WORK_AUTHORIZATION_REQUIRED_HINTS = (
    "flagged for possible cybersecurity risk",
    "authorized for security work",
    "chatgpt.com/cyber",
)
_SECURITY_WORK_RETRY_MESSAGE = (
    "Upstream flagged this request as possible cybersecurity work. "
    "codex-lb is retrying on an account marked as authorized for security work."
)
_SECURITY_WORK_NO_AUTHORIZED_ACCOUNTS_MESSAGE = (
    "Upstream flagged this request as possible cybersecurity work, but no account is marked as authorized for "
    "security work. codex-lb is continuing with normal account selection; the upstream request may still fail until "
    "an account with Trusted Access for Cyber is marked as security-work-authorized."
)


@dataclass(frozen=True, slots=True)
class _HTTPBridgeRuntimeConfig:
    enabled: bool
    idle_ttl_seconds: float
    codex_idle_ttl_seconds: float
    max_sessions: int
    queue_limit: int
    prompt_cache_idle_ttl_seconds: float
    gateway_safe_mode: bool


def _estimated_lease_tokens_from_request_usage_budget(budget: ApiKeyRequestUsageBudget | None) -> float:
    if budget is None:
        return 0.0
    input_tokens = _bounded_lease_token_estimate(
        budget.input_tokens,
        default=API_KEY_USAGE_RESERVATION_DEFAULT_INPUT_TOKENS,
    )
    output_tokens = _bounded_lease_token_estimate(
        budget.output_tokens,
        default=API_KEY_USAGE_RESERVATION_DEFAULT_OUTPUT_TOKENS,
    )
    return float(input_tokens + output_tokens)


def _bounded_lease_token_estimate(value: int | None, *, default: int) -> int:
    if value is None:
        return default
    return max(0, min(value, API_KEY_USAGE_RESERVATION_MAX_TOKEN_BUDGET))


class ProxyService(
    _ApiKeyUsageMixin,
    _RequestLogMixin,
    _RateLimitMixin,
    _WarmupMixin,
    _FileOpsMixin,
    _TranscribeMixin,
    _CodexControlMixin,
    _CompactMixin,
    _StreamingMixin,
    _WebSocketMixin,
    _HTTPBridgeMixin,
):
    def __init__(self, repo_factory: ProxyRepoFactory) -> None:
        self._repo_factory = repo_factory
        self._encryptor = TokenEncryptor()
        self._load_balancer = LoadBalancer(repo_factory)
        self._provider_adapters: dict[str, ProviderAdapter] = {
            CHATGPT_WEB_PROVIDER_KIND: ChatGPTWebProviderAdapter(repo_factory),
            OPENAI_PLATFORM_PROVIDER_KIND: cast(ProviderAdapter, OpenAIPlatformProviderAdapter()),
        }
        self._ring_membership = RingMembershipService(SessionLocal)
        self._durable_bridge = DurableBridgeSessionCoordinator(SessionLocal)
        self._http_bridge_owner_client = HTTPBridgeOwnerClient()
        self._http_bridge_sessions: dict[_HTTPBridgeSessionKey, _HTTPBridgeSession] = {}
        self._http_bridge_inflight_sessions: dict[_HTTPBridgeSessionKey, asyncio.Future[_HTTPBridgeSession]] = {}
        self._http_bridge_turn_state_index: dict[tuple[str, str | None], _HTTPBridgeSessionKey] = {}
        self._http_bridge_previous_response_index: dict[tuple[str, str | None], _HTTPBridgeSessionKey] = {}
        self._websocket_previous_response_account_index: dict[tuple[str, str | None, str | None], str] = {}
        self._websocket_continuity_index: dict[tuple[str, str | None], _WebSocketContinuityState] = {}
        self._background_cleanup_tasks: set[asyncio.Task[None]] = set()
        # In-memory pin from upstream-issued file_id -> codex-lb account_id.
        # Used so ``finalize_file`` for a given ``file_id`` is routed to
        # the same account that handled ``create_file``. Cross-instance
        # routing is best-effort: if the finalize request lands on a
        # different replica with no pin, we fall back to a fresh load-
        # balancer selection. The TTL is short enough (5 min) that we
        # never hold stale pins after the upstream upload window closes.
        self._file_account_pins: dict[str, _FilePinEntry] = {}
        self._file_account_pin_lock = asyncio.Lock()
        self._http_bridge_lock = anyio.Lock()
        self._work_admission: WorkAdmissionController | None = None
        self._request_log_tasks: set[asyncio.Task[None]] = set()

    def _get_work_admission(self) -> WorkAdmissionController:
        if self._work_admission is None:
            settings = get_settings()
            self._work_admission = WorkAdmissionController(
                token_refresh_limit=settings.proxy_token_refresh_limit,
                websocket_connect_limit=settings.proxy_upstream_websocket_connect_limit,
                response_create_limit=settings.proxy_response_create_limit,
                compact_response_create_limit=settings.proxy_compact_response_create_limit,
                admission_wait_timeout_seconds=getattr(
                    settings,
                    "proxy_admission_wait_timeout_seconds",
                    10.0,
                ),
            )
        return self._work_admission

    async def thread_goal_request(
        self,
        operation: str,
        payload: Mapping[str, JsonValue],
        headers: Mapping[str, str],
        *,
        method: str = "POST",
        codex_session_affinity: bool = True,
        api_key: ApiKeyData | None = None,
    ) -> dict[str, JsonValue]:
        filtered = filter_inbound_headers(headers)
        useragent, useragent_group = _request_log_useragent_fields(headers)
        request_id = get_request_id() or ensure_request_id(None)
        start = time.monotonic()
        base_settings = get_settings()
        deadline = start + base_settings.proxy_request_budget_seconds
        settings = await get_settings_cache().get()
        affinity = _sticky_key_for_codex_control_request(
            headers,
            codex_session_affinity=codex_session_affinity,
        )
        selection_model = api_key.enforced_model if api_key is not None else None
        routing_strategy = _routing_strategy(settings)
        account_id_value: str | None = None
        log_status = "error"
        log_error_code: str | None = None
        log_error_message: str | None = None
        failure_metadata = _RequestLogFailureMetadata()
        route_mode: str | None = None
        route_pool_id: str | None = None
        route_endpoint_id: str | None = None
        route_fallback_used: bool | None = None
        route_fail_closed_reason: str | None = None
        request_kind = f"thread_goal_{operation}"

        try:
            selection = await self._select_account_with_budget_compatible(
                deadline,
                request_id=request_id,
                kind=request_kind,
                api_key=api_key,
                sticky_key=affinity.key,
                sticky_kind=affinity.kind,
                reallocate_sticky=affinity.reallocate_sticky,
                sticky_max_age_seconds=affinity.max_age_seconds,
                prefer_earlier_reset_accounts=settings.prefer_earlier_reset_accounts,
                prefer_earlier_reset_window=_prefer_earlier_reset_window(settings),
                routing_strategy=routing_strategy,
                model=selection_model,
            )
            account = selection.account
            if not account:
                account = await self._select_codex_control_account_without_budget(
                    affinity=affinity,
                    api_key=api_key,
                    traffic_class=TRAFFIC_CLASS_OPPORTUNISTIC
                    if api_key is not None and api_key.traffic_class == TRAFFIC_CLASS_OPPORTUNISTIC
                    else TRAFFIC_CLASS_FOREGROUND,
                    prefer_earlier_reset_window=_prefer_earlier_reset_window(settings),
                )
                if account is None:
                    log_error_code = selection.error_code or "no_accounts"
                    log_error_message = selection.error_message or "No active accounts available"
                    raise ProxyResponseError(
                        503,
                        openai_error(log_error_code, log_error_message),
                    )
            account_id_value = account.id

            async def _call_goal(target: Account) -> dict[str, JsonValue]:
                nonlocal route_fallback_used, route_mode, route_pool_id, route_endpoint_id
                access_token = self._encryptor.decrypt(target.access_token_encrypted)
                upstream_account_id = _header_account_id(target.chatgpt_account_id)
                remaining_budget = _remaining_budget_seconds(deadline)
                if remaining_budget <= 0:
                    logger.warning(
                        "Thread goal request budget exhausted before upstream call request_id=%s operation=%s "
                        "account_id=%s",
                        request_id,
                        operation,
                        target.id,
                    )
                    _raise_proxy_budget_exhausted()
                route = await self._resolve_upstream_route_for_account(target, operation=request_kind)
                if route is not None:
                    route_mode = route.mode
                    route_pool_id = route.pool_id
                    route_endpoint_id = route.endpoint_id
                route_trace = UpstreamProxyRouteTrace()
                try:
                    return await core_thread_goal_request(
                        operation,
                        payload,
                        filtered,
                        access_token,
                        upstream_account_id,
                        method=method,
                        timeout_seconds=remaining_budget,
                        route=route,
                        allow_direct_egress=route is None,
                        route_trace=route_trace,
                    )
                finally:
                    if route_trace.mode is not None:
                        route_mode = route_trace.mode
                        route_pool_id = route_trace.pool_id
                        route_endpoint_id = route_trace.endpoint_id
                        route_fallback_used = route_trace.fallback_used

            async def _select_goal_failover(excluded_account_ids: set[str]) -> AccountSelection:
                return await self._select_account_with_budget(
                    deadline,
                    request_id=request_id,
                    kind=request_kind,
                    api_key=api_key,
                    sticky_key=affinity.key,
                    sticky_kind=affinity.kind,
                    reallocate_sticky=affinity.reallocate_sticky,
                    sticky_max_age_seconds=affinity.max_age_seconds,
                    prefer_earlier_reset_accounts=settings.prefer_earlier_reset_accounts,
                    routing_strategy=routing_strategy,
                    model=selection_model,
                    exclude_account_ids=excluded_account_ids,
                )

            try:
                account = await self._ensure_previsible_unary_fresh_with_failover(
                    account,
                    deadline=deadline,
                    request_id=request_id,
                    kind=request_kind,
                    select_next_account=_select_goal_failover,
                )
                account_id_value = account.id
                response = await _call_goal(account)
                await self._load_balancer.record_success(account)
                log_status = "success"
                return response
            except RefreshError as refresh_exc:
                if refresh_exc.is_permanent:
                    failed_account = _refresh_error_failed_account(refresh_exc, account)
                    account_id_value = failed_account.id
                    await self._load_balancer.mark_permanent_failure(failed_account, refresh_exc.code)
                raise ProxyResponseError(
                    401,
                    openai_error(
                        "invalid_api_key",
                        refresh_exc.message,
                        error_type="invalid_request_error",
                    ),
                ) from refresh_exc
            except ProxyResponseError as exc:
                if exc.status_code != 401:
                    failover = await self._retry_previsible_unary_call_failover(
                        exc,
                        account,
                        deadline=deadline,
                        select_next_account=_select_goal_failover,
                        call_next=_call_goal,
                    )
                    if failover is not None:
                        account, response = failover
                        account_id_value = account.id
                        log_status = "success"
                        return response
                if exc.status_code == 401:
                    try:
                        remaining_budget = _remaining_budget_seconds(deadline)
                        if remaining_budget <= 0:
                            logger.warning(
                                "Thread goal request budget exhausted before forced refresh retry request_id=%s "
                                "operation=%s account_id=%s",
                                request_id,
                                operation,
                                account.id,
                            )
                            _raise_proxy_budget_exhausted()
                        try:
                            account = await self._ensure_previsible_unary_fresh_with_failover(
                                account,
                                deadline=deadline,
                                request_id=request_id,
                                kind=request_kind,
                                select_next_account=_select_goal_failover,
                                force=True,
                            )
                        except ProxyResponseError as refresh_failover_exc:
                            failed_account = _proxy_response_failed_account(refresh_failover_exc, account)
                            account_id_value = failed_account.id
                            await self._handle_proxy_error(failed_account, refresh_failover_exc)
                            raise
                        account_id_value = account.id
                        try:
                            response = await _call_goal(account)
                            await self._load_balancer.record_success(account)
                            log_status = "success"
                            return response
                        except ProxyResponseError as retry_exc:
                            await self._handle_proxy_error(account, retry_exc)
                            if retry_exc.status_code == 401:
                                selection = await self._select_account_with_budget_compatible(
                                    deadline,
                                    request_id=request_id,
                                    kind=request_kind,
                                    api_key=api_key,
                                    sticky_key=affinity.key,
                                    sticky_kind=affinity.kind,
                                    reallocate_sticky=affinity.reallocate_sticky,
                                    sticky_max_age_seconds=affinity.max_age_seconds,
                                    prefer_earlier_reset_accounts=settings.prefer_earlier_reset_accounts,
                                    prefer_earlier_reset_window=_prefer_earlier_reset_window(settings),
                                    routing_strategy=routing_strategy,
                                    model=selection_model,
                                    exclude_account_ids={account.id},
                                )
                                if selection.account is not None:
                                    account = selection.account
                                    account_id_value = account.id
                                    account = await self._ensure_fresh_with_budget_or_auth_error(
                                        account,
                                        timeout_seconds=_remaining_budget_seconds(deadline),
                                    )
                                    try:
                                        response = await _call_goal(account)
                                        await self._load_balancer.record_success(account)
                                        log_status = "success"
                                        return response
                                    except ProxyResponseError as failover_exc:
                                        await self._handle_proxy_error(account, failover_exc)
                                        raise
                            raise
                    except RefreshError as refresh_exc:
                        if refresh_exc.is_permanent:
                            failed_account = _refresh_error_failed_account(refresh_exc, account)
                            account_id_value = failed_account.id
                            await self._load_balancer.mark_permanent_failure(failed_account, refresh_exc.code)
                        raise exc
                    except (aiohttp.ClientError, asyncio.TimeoutError) as timeout_exc:
                        logger.warning(
                            "Thread goal forced refresh/connect failed request_id=%s operation=%s account_id=%s",
                            request_id,
                            operation,
                            account.id,
                            exc_info=True,
                        )
                        _raise_proxy_unavailable(str(timeout_exc) or "Request to upstream timed out")
                if operation == "get" and _is_missing_thread_goal_protocol_error(exc):
                    log_status = "success"
                    return {"goal": None}
                failed_account = _proxy_response_failed_account(exc, account)
                account_id_value = failed_account.id
                await self._handle_proxy_error(failed_account, exc)
                raise
        except ProxyResponseError as exc:
            failed_account = getattr(exc, _FAILED_ACCOUNT_ATTR, None)
            if isinstance(failed_account, Account):
                account_id_value = failed_account.id
            failure_metadata = _request_log_failure_metadata(exc)
            error = _parse_openai_error(exc.payload)
            log_error_code = log_error_code or _normalize_error_code(
                error.code if error else None,
                error.type if error else None,
            )
            log_error_message = log_error_message or (error.message if error else None)
            raise
        except UpstreamProxyRouteError as exc:
            route_fail_closed_reason = exc.reason
            log_error_code = "upstream_proxy_unavailable"
            log_error_message = exc.reason
            raise ProxyResponseError(
                502,
                openai_error("upstream_proxy_unavailable", f"Upstream proxy route unavailable: {exc.reason}"),
            ) from exc
        finally:
            await self._write_request_log(
                account_id=account_id_value,
                api_key=api_key,
                request_id=request_id,
                model=None,
                latency_ms=int((time.monotonic() - start) * 1000),
                status=log_status,
                error_code=log_error_code,
                error_message=log_error_message,
                transport=_REQUEST_TRANSPORT_HTTP,
                failure_phase=failure_metadata.failure_phase,
                failure_detail=failure_metadata.failure_detail,
                failure_exception_type=failure_metadata.failure_exception_type,
                upstream_status_code=failure_metadata.upstream_status_code,
                upstream_error_code=failure_metadata.upstream_error_code,
                bridge_stage=failure_metadata.bridge_stage,
                upstream_proxy_route_mode=route_mode,
                upstream_proxy_pool_id=route_pool_id,
                upstream_proxy_endpoint_id=route_endpoint_id,
                upstream_proxy_fallback_used=route_fallback_used if route_endpoint_id else None,
                upstream_proxy_fail_closed_reason=route_fail_closed_reason,
                useragent=useragent,
                useragent_group=useragent_group,
            )

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
        return await get_platform_cache_alert_service().observe(
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
            should_fallback = await self.should_fallback_to_platform_for_usage_drain(
                model=capabilities.model,
                additional_limit_name=additional_limit_name,
                account_ids=scoped_account_ids,
            )
            if (
                should_fallback
                and not bool(getattr(get_settings(), "platform_fallback_force_enabled", False))
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

    def stream_responses(
        self,
        payload: ResponsesRequest,
        headers: Mapping[str, str],
        *,
        codex_session_affinity: bool = False,
        propagate_http_errors: bool = False,
        openai_cache_affinity: bool = False,
        api_key: ApiKeyData | None = None,
        api_key_reservation: ApiKeyUsageReservationData | None = None,
        suppress_text_done_events: bool = False,
        request_transport: str = _REQUEST_TRANSPORT_HTTP,
        codex_session_budget_reallocation_enabled: bool = True,
    ) -> AsyncIterator[str]:
        _maybe_log_proxy_request_payload("stream", payload, headers)
        filtered = filter_inbound_headers(headers)
        return self._stream_with_retry(
            payload,
            filtered,
            codex_session_affinity=codex_session_affinity,
            propagate_http_errors=propagate_http_errors,
            openai_cache_affinity=openai_cache_affinity,
            api_key=api_key,
            api_key_reservation=api_key_reservation,
            suppress_text_done_events=suppress_text_done_events,
            request_transport=request_transport,
            codex_session_budget_reallocation_enabled=codex_session_budget_reallocation_enabled,
        )

    def stream_http_responses(
        self,
        payload: ResponsesRequest,
        headers: Mapping[str, str],
        *,
        codex_session_affinity: bool = False,
        propagate_http_errors: bool = False,
        openai_cache_affinity: bool = False,
        api_key: ApiKeyData | None = None,
        api_key_reservation: ApiKeyUsageReservationData | None = None,
        suppress_text_done_events: bool = False,
        downstream_turn_state: str | None = None,
        forwarded_request: bool = False,
        forwarded_affinity_kind: str | None = None,
        forwarded_affinity_key: str | None = None,
        codex_session_budget_reallocation_enabled: bool = True,
    ) -> AsyncIterator[str]:
        _maybe_log_proxy_request_payload("stream_http", payload, headers)
        proxy_api_authorization = _header_value_case_insensitive(headers, "authorization")
        filtered = filter_inbound_headers(headers)
        return self._stream_http_bridge_or_retry(
            payload,
            filtered,
            codex_session_affinity=codex_session_affinity,
            propagate_http_errors=propagate_http_errors,
            openai_cache_affinity=openai_cache_affinity,
            api_key=api_key,
            api_key_reservation=api_key_reservation,
            suppress_text_done_events=suppress_text_done_events,
            downstream_turn_state=downstream_turn_state,
            forwarded_request=forwarded_request,
            proxy_api_authorization=proxy_api_authorization,
            forwarded_affinity_kind=forwarded_affinity_kind,
            forwarded_affinity_key=forwarded_affinity_key,
            codex_session_budget_reallocation_enabled=codex_session_budget_reallocation_enabled,
        )

    async def _stream_http_bridge_or_retry(
        self,
        payload: ResponsesRequest,
        headers: Mapping[str, str],
        *,
        codex_session_affinity: bool,
        propagate_http_errors: bool,
        openai_cache_affinity: bool,
        api_key: ApiKeyData | None,
        api_key_reservation: ApiKeyUsageReservationData | None,
        suppress_text_done_events: bool,
        downstream_turn_state: str | None = None,
        forwarded_request: bool = False,
        proxy_api_authorization: str | None = None,
        forwarded_affinity_kind: str | None = None,
        forwarded_affinity_key: str | None = None,
        codex_session_budget_reallocation_enabled: bool = True,
    ) -> AsyncIterator[str]:
        async for line in _HTTPBridgeMixin._stream_http_bridge_or_retry(
            self,
            payload,
            headers,
            codex_session_affinity=codex_session_affinity,
            propagate_http_errors=propagate_http_errors,
            openai_cache_affinity=openai_cache_affinity,
            api_key=api_key,
            api_key_reservation=api_key_reservation,
            suppress_text_done_events=suppress_text_done_events,
            downstream_turn_state=downstream_turn_state,
            forwarded_request=forwarded_request,
            proxy_api_authorization=proxy_api_authorization,
            forwarded_affinity_kind=forwarded_affinity_kind,
            forwarded_affinity_key=forwarded_affinity_key,
            codex_session_budget_reallocation_enabled=codex_session_budget_reallocation_enabled,
        ):
            yield line
        return

        dashboard_settings = await get_settings_cache().get()
        runtime_config = _http_bridge_runtime_config(dashboard_settings, get_settings())
        request_id = ensure_request_id()
        self._raise_for_unsupported_input_image_references(payload)
        payload_size_estimate_bytes = len(
            json.dumps(payload.to_payload(), ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        )
        rewritten_file_account_id = await self._resolve_file_account_for_responses(payload, headers)
        ws_payload_budget_bytes = _ws_transport_payload_budget_bytes(get_settings())
        if runtime_config.enabled and payload_size_estimate_bytes > ws_payload_budget_bytes:
            logger.info(
                "stream_responses bypassing http bridge for large payload size=%s budget=%s request_id=%s",
                payload_size_estimate_bytes,
                ws_payload_budget_bytes,
                request_id,
            )
            runtime_config = dataclasses.replace(runtime_config, enabled=False)
        if not runtime_config.enabled:
            async for line in self._stream_with_retry(
                payload,
                headers,
                codex_session_affinity=codex_session_affinity,
                propagate_http_errors=propagate_http_errors,
                openai_cache_affinity=openai_cache_affinity,
                api_key=api_key,
                api_key_reservation=api_key_reservation,
                suppress_text_done_events=suppress_text_done_events,
                request_transport=_REQUEST_TRANSPORT_HTTP,
                codex_session_budget_reallocation_enabled=codex_session_budget_reallocation_enabled,
                rewritten_file_account_id=rewritten_file_account_id,
            ):
                yield line
            return

        async for line in self._stream_via_http_bridge(
            payload,
            headers,
            codex_session_affinity=codex_session_affinity,
            propagate_http_errors=propagate_http_errors,
            openai_cache_affinity=openai_cache_affinity,
            api_key=api_key,
            api_key_reservation=api_key_reservation,
            suppress_text_done_events=suppress_text_done_events,
            idle_ttl_seconds=runtime_config.idle_ttl_seconds,
            codex_idle_ttl_seconds=runtime_config.codex_idle_ttl_seconds,
            max_sessions=runtime_config.max_sessions,
            queue_limit=runtime_config.queue_limit,
            prompt_cache_idle_ttl_seconds=runtime_config.prompt_cache_idle_ttl_seconds,
            downstream_turn_state=downstream_turn_state,
            forwarded_request=forwarded_request,
            proxy_api_authorization=proxy_api_authorization,
            forwarded_affinity_kind=forwarded_affinity_kind,
            forwarded_affinity_key=forwarded_affinity_key,
            codex_session_budget_reallocation_enabled=codex_session_budget_reallocation_enabled,
            rewritten_file_account_id=rewritten_file_account_id,
        ):
            yield line

    async def _stream_via_http_bridge(
        self,
        payload: ResponsesRequest,
        headers: Mapping[str, str],
        *,
        codex_session_affinity: bool,
        propagate_http_errors: bool,
        openai_cache_affinity: bool,
        api_key: ApiKeyData | None,
        api_key_reservation: ApiKeyUsageReservationData | None,
        suppress_text_done_events: bool,
        idle_ttl_seconds: float,
        codex_idle_ttl_seconds: float,
        max_sessions: int,
        queue_limit: int,
        prompt_cache_idle_ttl_seconds: float | None = None,
        downstream_turn_state: str | None = None,
        forwarded_request: bool = False,
        proxy_api_authorization: str | None = None,
        forwarded_affinity_kind: str | None = None,
        forwarded_affinity_key: str | None = None,
        codex_session_budget_reallocation_enabled: bool = True,
        rewritten_file_account_id: str | None = None,
    ) -> AsyncIterator[str]:
        async for line in _HTTPBridgeMixin._stream_via_http_bridge(
            self,
            payload,
            headers,
            codex_session_affinity=codex_session_affinity,
            propagate_http_errors=propagate_http_errors,
            openai_cache_affinity=openai_cache_affinity,
            api_key=api_key,
            api_key_reservation=api_key_reservation,
            suppress_text_done_events=suppress_text_done_events,
            idle_ttl_seconds=idle_ttl_seconds,
            codex_idle_ttl_seconds=codex_idle_ttl_seconds,
            max_sessions=max_sessions,
            queue_limit=queue_limit,
            prompt_cache_idle_ttl_seconds=prompt_cache_idle_ttl_seconds,
            downstream_turn_state=downstream_turn_state,
            forwarded_request=forwarded_request,
            proxy_api_authorization=proxy_api_authorization,
            forwarded_affinity_kind=forwarded_affinity_kind,
            forwarded_affinity_key=forwarded_affinity_key,
            codex_session_budget_reallocation_enabled=codex_session_budget_reallocation_enabled,
            rewritten_file_account_id=rewritten_file_account_id,
        ):
            yield line
        return

        del suppress_text_done_events
        request_id = ensure_request_id()
        dashboard_settings = await get_settings_cache().get()
        runtime_config = _http_bridge_runtime_config(dashboard_settings, get_settings())
        incoming_turn_state_header = _sticky_key_from_turn_state_header(headers) if not forwarded_request else None
        incoming_session_header = _sticky_key_from_session_header(headers) if not forwarded_request else None
        had_prompt_cache_key = _prompt_cache_key_from_request_model(payload) is not None
        affinity = _sticky_key_for_responses_request(
            payload,
            headers,
            codex_session_affinity=codex_session_affinity,
            openai_cache_affinity=openai_cache_affinity,
            openai_cache_affinity_max_age_seconds=dashboard_settings.openai_cache_affinity_max_age_seconds,
            sticky_threads_enabled=dashboard_settings.sticky_threads_enabled,
            api_key=api_key,
            codex_session_budget_reallocation_enabled=codex_session_budget_reallocation_enabled,
        )
        sticky_key_source = "none"
        if affinity.kind == StickySessionKind.CODEX_SESSION:
            sticky_key_source = (
                "turn_state_header" if _sticky_key_from_turn_state_header(headers) is not None else "session_header"
            )
        elif affinity.key:
            sticky_key_source = "payload" if had_prompt_cache_key else "derived"
        _maybe_log_proxy_request_shape(
            "stream_http_bridge",
            payload,
            headers,
            sticky_kind=affinity.kind.value if affinity.kind is not None else None,
            sticky_key_source=sticky_key_source,
            prompt_cache_key_set=_prompt_cache_key_from_request_model(payload) is not None,
        )

        bridge_session_key = _make_http_bridge_session_key(
            payload,
            headers=headers,
            affinity=affinity,
            api_key=api_key,
            request_id=request_id,
            allow_forwarded_affinity_headers=forwarded_request,
            forwarded_affinity_kind=forwarded_affinity_kind,
            forwarded_affinity_key=forwarded_affinity_key,
        )
        try:
            durable_lookup = await self._durable_bridge.lookup_request_targets(
                session_key_kind=bridge_session_key.affinity_kind,
                session_key_value=bridge_session_key.affinity_key,
                api_key_id=bridge_session_key.api_key_id,
                turn_state=incoming_turn_state_header,
                session_header=incoming_session_header,
                previous_response_id=payload.previous_response_id,
            )
        except Exception:
            if payload.previous_response_id is not None or bridge_session_key.strength == "hard":
                _record_continuity_fail_closed(
                    surface="http_bridge",
                    reason="durable_lookup_failed",
                    previous_response_id=payload.previous_response_id,
                    session_id=bridge_session_key.affinity_key,
                )
                raise ProxyResponseError(502, _http_bridge_owner_lookup_unavailable_error_envelope())
            logger.warning("Durable bridge lookup failed; falling back to non-durable request handling", exc_info=True)
            durable_lookup = None
        effective_payload = payload
        proxy_injected_previous_response_id = False
        fresh_upstream_request_text: str | None = None
        if durable_lookup is not None:
            bridge_session_key = _HTTPBridgeSessionKey(
                durable_lookup.canonical_kind,
                durable_lookup.canonical_key,
                bridge_session_key.api_key_id,
            )
            live_local_session_exists = await self._http_bridge_has_live_local_session(
                key=bridge_session_key,
                incoming_turn_state=incoming_turn_state_header,
                api_key=api_key,
            )
            forwards_to_active_owner = await self._http_bridge_can_forward_to_active_owner(durable_lookup)
            if (
                not live_local_session_exists
                and not forwards_to_active_owner
                and payload.previous_response_id is None
                and bridge_session_key.strength == "hard"
                and durable_lookup.latest_response_id is not None
                and not _http_bridge_payload_looks_like_full_resend(payload)
            ):
                effective_payload = payload.model_copy(
                    update={"previous_response_id": durable_lookup.latest_response_id}
                )
                proxy_injected_previous_response_id = True
                _fresh_request_state, fresh_upstream_request_text = self._prepare_http_bridge_request(
                    payload,
                    headers,
                    api_key=api_key,
                    api_key_reservation=api_key_reservation,
                    request_id=request_id,
                )
                del _fresh_request_state
                _log_http_bridge_event(
                    "fresh_reattach_anchor_injected",
                    bridge_session_key,
                    account_id=None,
                    model=payload.model,
                    detail=f"response_id={durable_lookup.latest_response_id}",
                    cache_key_family=bridge_session_key.affinity_kind,
                    model_class=_extract_model_class(payload.model) if payload.model else None,
                )
        request_state, text_data = self._prepare_http_bridge_request(
            effective_payload,
            headers,
            api_key=api_key,
            api_key_reservation=api_key_reservation,
            request_id=request_id,
        )
        if downstream_turn_state is not None:
            request_state.session_id = _normalize_session_id(downstream_turn_state)
        request_state.transport = _REQUEST_TRANSPORT_HTTP
        request_state.request_stage = _http_bridge_request_stage(
            headers=headers,
            payload=effective_payload,
            durable_lookup=durable_lookup,
        )
        request_state.preferred_account_id = (
            durable_lookup.account_id
            if (
                durable_lookup is not None
                and (
                    request_state.previous_response_id is not None
                    or bridge_session_key.strength == "hard"
                    or (
                        bridge_session_key.affinity_kind == "prompt_cache"
                        and request_state.request_stage == "follow_up"
                        and durable_lookup.latest_turn_state is not None
                    )
                )
            )
            else request_state.preferred_account_id
        )
        if request_state.previous_response_id is not None and request_state.preferred_account_id is None:
            request_state.preferred_account_id = await self._http_bridge_local_owner_account_id(
                key=bridge_session_key,
                incoming_turn_state=incoming_turn_state_header,
                previous_response_id=request_state.previous_response_id,
                api_key=api_key,
            )
        if request_state.previous_response_id is not None and request_state.preferred_account_id is None:
            request_state.preferred_account_id = await self._resolve_websocket_previous_response_owner(
                previous_response_id=request_state.previous_response_id,
                api_key=api_key,
                session_id=request_state.session_id,
                surface="http_bridge",
            )
        if request_state.preferred_account_id is None:
            # ``input_file.file_id`` references must land on the account
            # that registered the upload (chatgpt-account-id-scoped).
            # The helper returns ``None`` when stronger affinity signals
            # are present, so this never overrides existing routing.
            request_state.preferred_account_id = rewritten_file_account_id
        if request_state.preferred_account_id is None:
            request_state.preferred_account_id = await self._resolve_file_account_for_responses(
                effective_payload, headers
            )
        if proxy_injected_previous_response_id:
            request_state.proxy_injected_previous_response_id = True
            request_state.fresh_upstream_request_text = fresh_upstream_request_text or text_data
            # Durable-anchor injection actually runs when the incoming
            # payload is *not* a full resend (see the
            # ``not _http_bridge_payload_looks_like_full_resend(payload)``
            # guard above), so the captured unanchored text is typically
            # just a short follow-up. Replaying it as a fresh turn would
            # drop the conversational context the anchor was pointing at.
            # Only the trim branch below (which verifies the stored prefix
            # fingerprint) is allowed to flip this flag to ``True``.
            request_state.fresh_upstream_request_is_retry_safe = False
        session_or_forward = await self._get_or_create_http_bridge_session(
            bridge_session_key,
            headers=dict(headers),
            affinity=affinity,
            api_key=api_key,
            request_model=effective_payload.model,
            idle_ttl_seconds=_effective_http_bridge_idle_ttl_seconds(
                affinity=affinity,
                idle_ttl_seconds=idle_ttl_seconds,
                codex_idle_ttl_seconds=codex_idle_ttl_seconds,
                prompt_cache_idle_ttl_seconds=prompt_cache_idle_ttl_seconds,
            ),
            max_sessions=max_sessions,
            previous_response_id=request_state.previous_response_id,
            gateway_safe_mode=runtime_config.gateway_safe_mode,
            allow_forward_to_owner=True,
            forwarded_request=forwarded_request,
            forwarded_affinity_kind=forwarded_affinity_kind,
            forwarded_affinity_key=forwarded_affinity_key,
            durable_lookup=durable_lookup,
            request_stage=request_state.request_stage,
            preferred_account_id=request_state.preferred_account_id,
        )
        if isinstance(session_or_forward, _HTTPBridgeOwnerForward):
            forwarded_any = False
            try:
                async for line in self._forward_http_bridge_request_to_owner(
                    owner_forward=session_or_forward,
                    payload=effective_payload,
                    headers=headers,
                    api_key_reservation=api_key_reservation,
                    codex_session_affinity=codex_session_affinity,
                    downstream_turn_state=downstream_turn_state,
                    request_started_at=request_state.started_at,
                    proxy_api_authorization=proxy_api_authorization,
                ):
                    forwarded_any = True
                    yield line
                return
            except ProxyResponseError as exc:
                if forwarded_any:
                    raise
                should_attempt_previous_response_recovery = (
                    effective_payload.previous_response_id is not None
                    and _http_bridge_should_attempt_local_previous_response_recovery(exc)
                )
                should_attempt_bootstrap_rebind = _http_bridge_should_attempt_local_bootstrap_rebind(
                    exc,
                    key=bridge_session_key,
                    headers=headers,
                    previous_response_id=effective_payload.previous_response_id,
                )
                if not should_attempt_previous_response_recovery and not should_attempt_bootstrap_rebind:
                    raise
                if PROMETHEUS_AVAILABLE and bridge_durable_recover_total is not None:
                    bridge_durable_recover_total.labels(
                        path="owner_forward_fail"
                        if should_attempt_previous_response_recovery
                        else "owner_forward_bootstrap"
                    ).inc()
                _log_http_bridge_event(
                    "previous_response_recover_local"
                    if should_attempt_previous_response_recovery
                    else "bootstrap_rebind_local",
                    bridge_session_key,
                    account_id=None,
                    model=effective_payload.model,
                    detail=(
                        "outcome=local_rebind_after_forward_failure"
                        if should_attempt_previous_response_recovery
                        else "outcome=local_bootstrap_after_forward_failure"
                    ),
                    cache_key_family=bridge_session_key.affinity_kind,
                    model_class=_extract_model_class(effective_payload.model) if effective_payload.model else None,
                    owner_check_applied=True,
                )
                session = await self._get_or_create_http_bridge_session(
                    bridge_session_key,
                    headers=dict(headers),
                    affinity=affinity,
                    api_key=api_key,
                    request_model=effective_payload.model,
                    idle_ttl_seconds=_effective_http_bridge_idle_ttl_seconds(
                        affinity=affinity,
                        idle_ttl_seconds=idle_ttl_seconds,
                        codex_idle_ttl_seconds=codex_idle_ttl_seconds,
                        prompt_cache_idle_ttl_seconds=prompt_cache_idle_ttl_seconds,
                    ),
                    max_sessions=max_sessions,
                    previous_response_id=request_state.previous_response_id,
                    gateway_safe_mode=runtime_config.gateway_safe_mode,
                    allow_forward_to_owner=False,
                    forwarded_request=False,
                    allow_previous_response_recovery_rebind=should_attempt_previous_response_recovery,
                    allow_bootstrap_owner_rebind=should_attempt_bootstrap_rebind,
                    durable_lookup=durable_lookup,
                    request_stage="reattach",
                    preferred_account_id=request_state.preferred_account_id,
                )
                _record_bridge_reattach(
                    path="owner_forward_fail"
                    if should_attempt_previous_response_recovery
                    else "owner_forward_bootstrap",
                    outcome="success",
                )
                retry_request_state: _WebSocketRequestState | None = None
                try:
                    retry_api_key_reservation = api_key_reservation
                    retry_reservation_reacquired = False
                    if api_key is not None and api_key_reservation is not None:
                        retry_api_key_reservation = await self._reserve_websocket_api_key_usage(
                            api_key,
                            request_model=effective_payload.model,
                            request_service_tier=_normalize_service_tier_value(
                                dict(effective_payload.to_payload()).get("service_tier"),
                            ),
                        )
                        retry_reservation_reacquired = True

                    retry_request_state, retry_text_data = self._prepare_http_bridge_request(
                        effective_payload,
                        headers,
                        api_key=api_key,
                        api_key_reservation=retry_api_key_reservation,
                        request_id=request_id,
                    )
                    if downstream_turn_state is not None:
                        retry_request_state.session_id = _normalize_session_id(downstream_turn_state)
                    retry_request_state.transport = _REQUEST_TRANSPORT_HTTP
                    retry_request_state.request_stage = "reattach"
                    retry_request_state.preferred_account_id = request_state.preferred_account_id

                    await self._submit_http_bridge_request(
                        session,
                        request_state=retry_request_state,
                        text_data=retry_text_data,
                        queue_limit=queue_limit,
                    )
                    if downstream_turn_state is not None:
                        await self._register_http_bridge_turn_state(session, downstream_turn_state)
                    event_queue = retry_request_state.event_queue
                    assert event_queue is not None
                    while True:
                        event_block = await event_queue.get()
                        if event_block is None:
                            break
                        if retry_request_state.latency_first_token_ms is None:
                            block_payload = parse_sse_data_json(event_block)
                            block_event_type = _event_type_from_payload(None, block_payload)
                            if block_event_type in _TEXT_DELTA_EVENT_TYPES:
                                retry_request_state.latency_first_token_ms = int(
                                    (time.monotonic() - retry_request_state.started_at) * 1000
                                )
                        yield event_block
                except BaseException:
                    if retry_reservation_reacquired and retry_api_key_reservation is not None:
                        await self._release_websocket_reservation(retry_api_key_reservation)
                    raise
                finally:
                    if retry_request_state is not None:
                        with anyio.CancelScope(shield=True):
                            await self._detach_http_bridge_request(session, request_state=retry_request_state)
                            session.last_used_at = time.monotonic()
                return
        session = session_or_forward
        # --- Session-level previous_response_id injection ---
        # If the client didn't send previous_response_id and the durable
        # lookup didn't inject one, but this bridge session is carrying
        # Codex-style conversational continuity and has already completed a
        # request on this logical conversation, inject the session's last
        # completed response ID so the trim branch below can strip the
        # already-stored prefix.
        #
        # Correctness guards:
        # - Soft affinity reuse (for example prompt cache / sticky-thread
        #   sharing) must stay self-contained, so only true Codex
        #   continuity sessions opt in.
        # - Injecting an anchor when the incoming payload is a full-resend
        #   whose prefix cannot be safely trimmed (non-list input, prefix
        #   mismatch, or shorter-than-stored history) would send both the
        #   full history *and* the anchor upstream, which duplicates
        #   context and distorts output/cost. Gate injection so it only
        #   fires when the trim branch below would actually succeed.
        incoming_input_preview = effective_payload.input
        stored_count_preview = session.last_completed_input_count
        stored_fingerprint_preview = session.last_completed_input_prefix_fingerprint
        session_anchor_trimmable = (
            stored_count_preview > 0
            and stored_fingerprint_preview is not None
            and isinstance(incoming_input_preview, list)
            and len(incoming_input_preview) > stored_count_preview
            and _fingerprint_input_items(cast(list[JsonValue], incoming_input_preview)[:stored_count_preview])
            == stored_fingerprint_preview
        )
        if (
            session.codex_session
            and not proxy_injected_previous_response_id
            and effective_payload.previous_response_id is None
            and session.last_completed_response_id is not None
            and session_anchor_trimmable
        ):
            fresh_upstream_request_text = text_data
            effective_payload = effective_payload.model_copy(
                update={"previous_response_id": session.last_completed_response_id}
            )
            proxy_injected_previous_response_id = True
            request_state, text_data = self._prepare_http_bridge_request(
                effective_payload,
                headers,
                api_key=api_key,
                api_key_reservation=api_key_reservation,
                request_id=request_id,
            )
            request_state.transport = _REQUEST_TRANSPORT_HTTP
            request_state.request_stage = _http_bridge_request_stage(
                headers=headers,
                payload=effective_payload,
                durable_lookup=durable_lookup,
            )
            request_state.preferred_account_id = durable_lookup.account_id if durable_lookup is not None else None
            request_state.proxy_injected_previous_response_id = True
            request_state.fresh_upstream_request_text = fresh_upstream_request_text
            # Session-level anchor injection may be attached to a payload
            # that relied on the anchor for context (for example a
            # single-item follow-up turn whose prior history is only
            # represented by ``previous_response_id``). Replaying without
            # the anchor would silently turn it into a fresh turn and drop
            # conversational context, so opt this path out of fresh-upstream
            # fresh-turn replay.
            request_state.fresh_upstream_request_is_retry_safe = False
            logger.info(
                "session_anchor_injected request_id=%s response_id=%s",
                request_id,
                session.last_completed_response_id,
            )
        # Trim already-stored prefix when previous_response_id anchors context.
        has_previous_response_id = (
            proxy_injected_previous_response_id or effective_payload.previous_response_id is not None
        )
        incoming_input = effective_payload.input
        stored_count = session.last_completed_input_count
        stored_fingerprint = session.last_completed_input_prefix_fingerprint
        if (
            has_previous_response_id
            and stored_count > 0
            and stored_fingerprint is not None
            and isinstance(incoming_input, list)
            and len(incoming_input) > stored_count
        ):
            incoming_input_list = cast(list[JsonValue], incoming_input)
            incoming_prefix_fingerprint = _fingerprint_input_items(incoming_input_list[:stored_count])
            if incoming_prefix_fingerprint == stored_fingerprint:
                original_count = len(incoming_input_list)
                trimmed_input = incoming_input_list[stored_count:]
                trimmed_payload = effective_payload.model_copy(update={"input": trimmed_input})
                previous_preferred_account_id = request_state.preferred_account_id
                request_state, text_data = self._prepare_http_bridge_request(
                    trimmed_payload,
                    headers,
                    api_key=api_key,
                    api_key_reservation=api_key_reservation,
                    request_id=request_id,
                )
                if downstream_turn_state is not None:
                    request_state.session_id = _normalize_session_id(downstream_turn_state)
                request_state.transport = _REQUEST_TRANSPORT_HTTP
                request_state.request_stage = _http_bridge_request_stage(
                    headers=headers,
                    payload=trimmed_payload,
                    durable_lookup=durable_lookup,
                )
                request_state.preferred_account_id = previous_preferred_account_id
                request_state.input_item_count = original_count
                request_state.input_full_fingerprint = _fingerprint_input_items(incoming_input_list)
                if proxy_injected_previous_response_id:
                    request_state.proxy_injected_previous_response_id = True
                    request_state.fresh_upstream_request_text = fresh_upstream_request_text
                    # The trim branch only fires when the untrimmed payload
                    # is a true full resend whose prefix exactly matches the
                    # already-stored context, so the unanchored request text
                    # is a safe fresh-turn replay target regardless of
                    # whether the anchor came from the durable or
                    # session-level injection path.
                    request_state.fresh_upstream_request_is_retry_safe = True
                logger.info(
                    "store_context_input_trimmed request_id=%s original_items=%s trimmed_to=%s previous_response_id=%s",
                    request_id,
                    original_count,
                    len(trimmed_input),
                    effective_payload.previous_response_id,
                )
            else:
                logger.warning(
                    "store_context_input_trim_skipped_prefix_mismatch request_id=%s incoming_items=%s "
                    "stored_items=%s previous_response_id=%s",
                    request_id,
                    len(incoming_input_list),
                    stored_count,
                    effective_payload.previous_response_id,
                )
        session_events: AsyncGenerator[str, None] = self._stream_http_bridge_session_events(
            session,
            request_state=request_state,
            text_data=text_data,
            queue_limit=queue_limit,
            propagate_http_errors=propagate_http_errors,
            downstream_turn_state=downstream_turn_state,
        )
        try:
            async for event_block in session_events:
                yield event_block
        except ProxyResponseError as exc:
            is_context_overflow = _http_bridge_is_context_overflow_error(exc)
            should_rollover_after_context_overflow = _http_bridge_should_rollover_after_context_overflow(
                exc,
                key=bridge_session_key,
            )
            should_attempt_previous_response_recovery = (
                effective_payload.previous_response_id is not None
                and _http_bridge_should_attempt_local_previous_response_recovery(exc)
            )
            should_attempt_context_overflow_fresh_turn_recovery = (
                is_context_overflow
                and effective_payload.previous_response_id is not None
                and bridge_session_key.strength != "hard"
            )
            if (
                not should_attempt_previous_response_recovery
                and not should_rollover_after_context_overflow
                and not should_attempt_context_overflow_fresh_turn_recovery
            ):
                if is_context_overflow:
                    _log_http_bridge_event(
                        "context_overflow_no_rollover",
                        bridge_session_key,
                        account_id=None,
                        model=effective_payload.model,
                        detail="outcome=preserve_hard_affinity_session",
                        cache_key_family=bridge_session_key.affinity_kind,
                        model_class=_extract_model_class(effective_payload.model) if effective_payload.model else None,
                        owner_check_applied=True,
                    )
                raise

            if should_attempt_context_overflow_fresh_turn_recovery:
                if PROMETHEUS_AVAILABLE and bridge_durable_recover_total is not None:
                    bridge_durable_recover_total.labels(path="context_overflow_fresh_turn").inc()
                _log_http_bridge_event(
                    "context_overflow_fresh_turn_recover",
                    bridge_session_key,
                    account_id=None,
                    model=effective_payload.model,
                    detail="outcome=retry_without_previous_response_id",
                    cache_key_family=bridge_session_key.affinity_kind,
                    model_class=_extract_model_class(effective_payload.model) if effective_payload.model else None,
                    owner_check_applied=True,
                )
                await self._reset_http_bridge_session_after_local_terminal_error(
                    session,
                    error_code="stream_incomplete",
                    error_message="Upstream websocket closed before response.completed",
                )
                recovery_path = "context_overflow_fresh_turn"
                retry_payload = _http_bridge_payload_without_previous_response_id(effective_payload)
                retry_previous_response_id = None
                retry_request_stage = "context_overflow_recover"
                retry_preferred_account_id = None
                allow_previous_response_recovery_rebind = False
            elif should_rollover_after_context_overflow:
                _log_http_bridge_event(
                    "context_overflow_rollover",
                    bridge_session_key,
                    account_id=None,
                    model=effective_payload.model,
                    detail="outcome=close_session_after_context_length_exceeded",
                    cache_key_family=bridge_session_key.affinity_kind,
                    model_class=_extract_model_class(effective_payload.model) if effective_payload.model else None,
                    owner_check_applied=True,
                )
                await self._reset_http_bridge_session_after_local_terminal_error(
                    session,
                    error_code="stream_incomplete",
                    error_message="Upstream websocket closed before response.completed",
                )
                raise
            else:
                if PROMETHEUS_AVAILABLE and bridge_durable_recover_total is not None:
                    bridge_durable_recover_total.labels(path="local_previous_response_error").inc()
                _log_http_bridge_event(
                    "previous_response_recover_local",
                    bridge_session_key,
                    account_id=None,
                    model=effective_payload.model,
                    detail="outcome=local_rebind_after_local_error",
                    cache_key_family=bridge_session_key.affinity_kind,
                    model_class=_extract_model_class(effective_payload.model) if effective_payload.model else None,
                    owner_check_applied=True,
                )
                await self._reset_http_bridge_session_after_local_terminal_error(
                    session,
                    error_code="stream_incomplete",
                    error_message="Upstream websocket closed before response.completed",
                )
                recovery_path = "local_previous_response_error"
                retry_payload = effective_payload
                retry_previous_response_id = request_state.previous_response_id
                retry_request_stage = "reattach"
                retry_preferred_account_id = request_state.preferred_account_id
                allow_previous_response_recovery_rebind = True

            session = await self._get_or_create_http_bridge_session(
                bridge_session_key,
                headers=dict(headers),
                affinity=affinity,
                api_key=api_key,
                request_model=retry_payload.model,
                idle_ttl_seconds=_effective_http_bridge_idle_ttl_seconds(
                    affinity=affinity,
                    idle_ttl_seconds=idle_ttl_seconds,
                    codex_idle_ttl_seconds=codex_idle_ttl_seconds,
                    prompt_cache_idle_ttl_seconds=prompt_cache_idle_ttl_seconds,
                ),
                max_sessions=max_sessions,
                previous_response_id=retry_previous_response_id,
                gateway_safe_mode=runtime_config.gateway_safe_mode,
                allow_forward_to_owner=False,
                forwarded_request=False,
                allow_previous_response_recovery_rebind=allow_previous_response_recovery_rebind,
                durable_lookup=durable_lookup,
                request_stage=retry_request_stage,
                preferred_account_id=retry_preferred_account_id,
            )
            _record_bridge_reattach(path=recovery_path, outcome="success")

            try:
                retry_api_key_reservation = api_key_reservation
                retry_reservation_reacquired = False
                if api_key is not None and api_key_reservation is not None:
                    retry_api_key_reservation = await self._reserve_websocket_api_key_usage(
                        api_key,
                        request_model=retry_payload.model,
                        request_service_tier=_normalize_service_tier_value(
                            dict(retry_payload.to_payload()).get("service_tier"),
                        ),
                    )
                    retry_reservation_reacquired = True

                retry_request_state, retry_text_data = self._prepare_http_bridge_request(
                    retry_payload,
                    headers,
                    api_key=api_key,
                    api_key_reservation=retry_api_key_reservation,
                    request_id=request_id,
                )
                if downstream_turn_state is not None:
                    retry_request_state.session_id = _normalize_session_id(downstream_turn_state)
                retry_request_state.transport = _REQUEST_TRANSPORT_HTTP
                retry_request_state.request_stage = retry_request_stage
                retry_request_state.preferred_account_id = retry_preferred_account_id

                retry_events: AsyncGenerator[str, None] = self._stream_http_bridge_session_events(
                    session,
                    request_state=retry_request_state,
                    text_data=retry_text_data,
                    queue_limit=queue_limit,
                    propagate_http_errors=propagate_http_errors,
                    downstream_turn_state=downstream_turn_state,
                )
                try:
                    async for event_block in retry_events:
                        yield event_block
                finally:
                    try:
                        await retry_events.aclose()
                    except Exception:
                        pass
            except BaseException:
                if retry_reservation_reacquired and retry_api_key_reservation is not None:
                    await self._release_websocket_reservation(retry_api_key_reservation)
                raise
        finally:
            try:
                await session_events.aclose()
            except Exception:
                pass

    async def _reset_http_bridge_session_after_local_terminal_error(
        self,
        session: "_HTTPBridgeSession",
        *,
        error_code: str,
        error_message: str,
    ) -> None:
        async with self._http_bridge_lock:
            if self._http_bridge_sessions.get(session.key) is session:
                self._http_bridge_sessions.pop(session.key, None)
        async with session.pending_lock:
            session.queued_request_count = 0
        await self._fail_pending_websocket_requests(
            account_id_value=session.account.id,
            pending_requests=session.pending_requests,
            pending_lock=session.pending_lock,
            error_code=error_code,
            error_message=error_message,
            api_key=None,
            response_create_gate=session.response_create_gate,
        )
        await self._close_http_bridge_session(session)

    async def _stream_http_bridge_session_events(
        self,
        session: "_HTTPBridgeSession",
        *,
        request_state: _WebSocketRequestState,
        text_data: str,
        queue_limit: int,
        propagate_http_errors: bool,
        downstream_turn_state: str | None,
    ) -> AsyncGenerator[str, None]:
        stream = _HTTPBridgeMixin._stream_http_bridge_session_events(
            self,
            session,
            request_state=request_state,
            text_data=text_data,
            queue_limit=queue_limit,
            propagate_http_errors=propagate_http_errors,
            downstream_turn_state=downstream_turn_state,
        )
        try:
            async for line in stream:
                yield line
        finally:
            await stream.aclose()
        return

        await self._submit_http_bridge_request(
            session,
            request_state=request_state,
            text_data=text_data,
            queue_limit=queue_limit,
        )
        if downstream_turn_state is not None:
            await self._register_http_bridge_turn_state(session, downstream_turn_state)

        try:
            event_queue = request_state.event_queue
            assert event_queue is not None
            yielded_any = False
            while True:
                event_block = await event_queue.get()
                if event_block is None:
                    break
                block_payload = parse_sse_data_json(event_block)
                block_event_type = _event_type_from_payload(None, block_payload)
                if request_state.latency_first_token_ms is None and block_event_type in _TEXT_DELTA_EVENT_TYPES:
                    request_state.latency_first_token_ms = int((time.monotonic() - request_state.started_at) * 1000)
                if (
                    not propagate_http_errors
                    and request_state.previous_response_id is not None
                    and _is_previous_response_not_found_error(
                        code=_normalize_error_code(
                            _websocket_event_error_code(block_event_type, block_payload),
                            _websocket_event_error_type(block_event_type, block_payload),
                        ),
                        param=_websocket_event_error_param(block_event_type, block_payload),
                        message=_websocket_event_error_message(block_event_type, block_payload),
                    )
                ):
                    session.upstream_control.reconnect_requested = True
                    request_state.error_http_status_override = 502
                    (
                        event_block,
                        _event,
                        block_payload,
                        block_event_type,
                    ) = _build_rewritten_stream_response_failed_event(
                        response_id=request_state.response_id or request_state.request_id,
                        error_code="stream_incomplete",
                        error_message="Upstream websocket closed before response.completed",
                    )
                if (
                    not yielded_any
                    and propagate_http_errors
                    and block_event_type == "response.failed"
                    and request_state.error_http_status_override is not None
                    and request_state.error_http_status_override >= 400
                ):
                    raise ProxyResponseError(
                        request_state.error_http_status_override,
                        _openai_error_envelope_from_response_failed_payload(block_payload),
                    )
                yield event_block
                yielded_any = True
        finally:
            with anyio.CancelScope(shield=True):
                await self._detach_http_bridge_request(session, request_state=request_state)
                session.last_used_at = time.monotonic()

    async def _http_bridge_has_live_local_session(
        self,
        *,
        key: "_HTTPBridgeSessionKey",
        incoming_turn_state: str | None,
        api_key: ApiKeyData | None,
    ) -> bool:
        api_key_id = api_key.id if api_key is not None else None
        async with self._http_bridge_lock:
            candidate_keys = [key]
            if incoming_turn_state is not None:
                alias_key = self._http_bridge_turn_state_index.get(
                    _http_bridge_turn_state_alias_key(incoming_turn_state, api_key_id)
                )
                if alias_key is not None and alias_key not in candidate_keys:
                    candidate_keys.append(alias_key)
            for candidate_key in candidate_keys:
                session = self._http_bridge_sessions.get(candidate_key)
                if session is None or session.closed or session.account.status != AccountStatus.ACTIVE:
                    continue
                if not _http_bridge_session_allows_api_key(session, api_key):
                    continue
                return True
        return False

    async def _http_bridge_local_owner_account_id(
        self,
        *,
        key: "_HTTPBridgeSessionKey",
        incoming_turn_state: str | None,
        previous_response_id: str,
        api_key: ApiKeyData | None,
    ) -> str | None:
        api_key_id = api_key.id if api_key is not None else None
        candidate_keys: list[_HTTPBridgeSessionKey] = [key]
        async with self._http_bridge_lock:
            if incoming_turn_state is not None:
                alias_key = self._http_bridge_turn_state_index.get(
                    _http_bridge_turn_state_alias_key(incoming_turn_state, api_key_id)
                )
                if alias_key is not None and alias_key not in candidate_keys:
                    candidate_keys.append(alias_key)
            previous_alias_key = _http_bridge_previous_response_alias_key(previous_response_id, api_key_id)
            previous_key = self._http_bridge_previous_response_index.get(previous_alias_key)
            if previous_key is not None and previous_key not in candidate_keys:
                candidate_keys.append(previous_key)
            for candidate_key in candidate_keys:
                session = self._http_bridge_sessions.get(candidate_key)
                if session is None or session.closed or session.account.status != AccountStatus.ACTIVE:
                    continue
                if not _http_bridge_session_allows_api_key(session, api_key):
                    continue
                if not _http_bridge_session_reusable_for_request(
                    session=session,
                    key=candidate_key,
                    incoming_turn_state=incoming_turn_state,
                    previous_response_id=previous_response_id,
                ):
                    continue
                _record_continuity_owner_resolution(
                    surface="http_bridge",
                    source="local_bridge_session",
                    outcome="hit",
                    previous_response_id=previous_response_id,
                    session_id=incoming_turn_state,
                )
                return session.account.id
        _record_continuity_owner_resolution(
            surface="http_bridge",
            source="local_bridge_session",
            outcome="miss",
            previous_response_id=previous_response_id,
            session_id=incoming_turn_state,
        )
        return None

    async def _http_bridge_can_forward_to_active_owner(
        self,
        durable_lookup: DurableBridgeLookup,
    ) -> bool:
        owner_instance = _durable_bridge_lookup_active_owner(durable_lookup)
        if owner_instance is None:
            return False
        if owner_instance == get_settings().http_responses_session_bridge_instance_id:
            return False
        if self._ring_membership is None:
            return False
        try:
            owner_endpoint = await self._ring_membership.resolve_endpoint(owner_instance)
        except Exception:
            logger.debug("Failed to resolve HTTP bridge owner endpoint during anchor injection decision", exc_info=True)
            return False
        return owner_endpoint is not None

    async def _forward_http_bridge_request_to_owner(
        self,
        *,
        owner_forward: _HTTPBridgeOwnerForward,
        payload: ResponsesRequest,
        headers: Mapping[str, str],
        api_key_reservation: ApiKeyUsageReservationData | None,
        codex_session_affinity: bool,
        downstream_turn_state: str | None,
        request_started_at: float,
        proxy_api_authorization: str | None,
    ) -> AsyncIterator[str]:
        owner_stream = cast(
            AsyncGenerator[str, None],
            _HTTPBridgeMixin._forward_http_bridge_request_to_owner(
                self,
                owner_forward=owner_forward,
                payload=payload,
                headers=headers,
                api_key_reservation=api_key_reservation,
                codex_session_affinity=codex_session_affinity,
                downstream_turn_state=downstream_turn_state,
                request_started_at=request_started_at,
                proxy_api_authorization=proxy_api_authorization,
            ),
        )
        async with aclosing(owner_stream) as stream:
            async for event_block in stream:
                yield event_block
        return

        current_instance, _ = _normalized_http_bridge_instance_ring(get_settings())
        forwarded_turn_state = _header_value_case_insensitive(headers, "x-codex-turn-state") or downstream_turn_state
        forward_context = HTTPBridgeForwardContext(
            origin_instance=current_instance,
            target_instance=owner_forward.owner_instance,
            reservation=api_key_reservation,
            codex_session_affinity=codex_session_affinity,
            downstream_turn_state=forwarded_turn_state,
            original_affinity_kind=owner_forward.key.affinity_kind,
            original_affinity_key=owner_forward.key.affinity_key,
        )
        forward_headers = _headers_with_authorization(headers, proxy_api_authorization)
        start = time.monotonic()
        _log_http_bridge_event(
            "owner_forward_start",
            owner_forward.key,
            account_id=None,
            model=payload.model,
            detail=(
                f"owner_instance={owner_forward.owner_instance}, current_instance={current_instance}, "
                f"owner_endpoint={owner_forward.owner_endpoint}"
            ),
            cache_key_family=owner_forward.key.affinity_kind,
            model_class=_extract_model_class(payload.model) if payload.model else None,
            owner_check_applied=True,
        )

        forwarded_any = False
        try:
            async for event_block in self._http_bridge_owner_client.stream_responses(
                owner_endpoint=owner_forward.owner_endpoint,
                payload=payload,
                headers=forward_headers,
                context=forward_context,
                request_started_at=request_started_at,
            ):
                forwarded_any = True
                yield event_block
        except OwnerForwardRelayFailure as exc:
            if PROMETHEUS_AVAILABLE and bridge_owner_forward_total is not None:
                bridge_owner_forward_total.labels(outcome="fail").inc()
            _log_http_bridge_event(
                "owner_forward_fail",
                owner_forward.key,
                account_id=None,
                model=payload.model,
                detail=(
                    f"owner_instance={owner_forward.owner_instance}, current_instance={current_instance}, "
                    "error=relay_failure"
                ),
                cache_key_family=owner_forward.key.affinity_kind,
                model_class=_extract_model_class(payload.model) if payload.model else None,
                owner_check_applied=True,
            )
            if forwarded_any:
                yield exc.event_block
                return
            raise ProxyResponseError(
                503,
                openai_error(
                    "bridge_owner_unreachable",
                    "HTTP bridge owner relay timed out",
                    error_type="server_error",
                ),
            ) from exc
        except ProxyResponseError:
            if PROMETHEUS_AVAILABLE and bridge_owner_forward_total is not None:
                bridge_owner_forward_total.labels(outcome="fail").inc()
            _log_http_bridge_event(
                "owner_forward_fail",
                owner_forward.key,
                account_id=None,
                model=payload.model,
                detail=f"owner_instance={owner_forward.owner_instance}, current_instance={current_instance}",
                cache_key_family=owner_forward.key.affinity_kind,
                model_class=_extract_model_class(payload.model) if payload.model else None,
                owner_check_applied=True,
            )
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            if PROMETHEUS_AVAILABLE and bridge_owner_forward_total is not None:
                bridge_owner_forward_total.labels(outcome="fail").inc()
            _log_http_bridge_event(
                "owner_forward_fail",
                owner_forward.key,
                account_id=None,
                model=payload.model,
                detail=(
                    f"owner_instance={owner_forward.owner_instance}, current_instance={current_instance}, error={exc}"
                ),
                cache_key_family=owner_forward.key.affinity_kind,
                model_class=_extract_model_class(payload.model) if payload.model else None,
                owner_check_applied=True,
            )
            raise ProxyResponseError(
                503,
                openai_error(
                    "bridge_owner_unreachable",
                    "HTTP bridge owner request failed",
                    error_type="server_error",
                ),
            ) from exc
        else:
            if PROMETHEUS_AVAILABLE and bridge_owner_forward_total is not None:
                bridge_owner_forward_total.labels(outcome="success").inc()
            _log_http_bridge_event(
                "owner_forward_success",
                owner_forward.key,
                account_id=None,
                model=payload.model,
                detail=f"owner_instance={owner_forward.owner_instance}, current_instance={current_instance}",
                cache_key_family=owner_forward.key.affinity_kind,
                model_class=_extract_model_class(payload.model) if payload.model else None,
                owner_check_applied=True,
            )
        finally:
            if PROMETHEUS_AVAILABLE and bridge_forward_latency_seconds is not None:
                bridge_forward_latency_seconds.observe(max(time.monotonic() - start, 0.0))

    async def compact_responses(
        self,
        payload: ResponsesCompactRequest,
        headers: Mapping[str, str],
        *,
        codex_session_affinity: bool = False,
        openai_cache_affinity: bool = False,
        api_key: ApiKeyData | None = None,
        api_key_reservation: ApiKeyUsageReservationData | None = None,
        selected_subject: SelectedChatGPTSubject | SelectedPlatformSubject | None = None,
        route_family: str = BACKEND_CODEX_HTTP_ROUTE_FAMILY,
        route_class: str = CHATGPT_PRIVATE_ROUTE_CLASS,
        codex_session_budget_reallocation_enabled: bool = True,
    ) -> CompactResponsePayload:
        if selected_subject is None:
            return await _CompactMixin.compact_responses(
                self,
                payload,
                headers,
                codex_session_affinity=codex_session_affinity,
                openai_cache_affinity=openai_cache_affinity,
                api_key=api_key,
                api_key_reservation=api_key_reservation,
                codex_session_budget_reallocation_enabled=codex_session_budget_reallocation_enabled,
            )

        _maybe_log_proxy_request_payload("compact", payload, headers)
        filtered = filter_inbound_headers(headers)
        request_id = get_request_id() or ensure_request_id(None)
        start = time.monotonic()
        base_settings = get_settings()
        deadline = start + base_settings.compact_request_budget_seconds
        account_id_value: str | None = None
        provider_kind_value: str | None = None
        routing_subject_id_value: str | None = None
        upstream_request_id: str | None = None
        log_rejection_reason: str | None = None
        log_status = "error"
        log_error_code: str | None = None
        log_error_message: str | None = None
        response: CompactResponsePayload | None = None
        platform_api_key_suffix_value: str | None = None
        requested_service_tier = _normalize_service_tier_value(payload.service_tier)
        effective_request_service_tier = requested_service_tier
        actual_service_tier: str | None = None
        self._raise_for_unsupported_input_image_references(payload)
        rewritten_file_account_id = await self._resolve_file_account_for_responses(payload, headers)
        settings = await get_settings_cache().get()
        prefer_earlier_reset = settings.prefer_earlier_reset_accounts
        had_prompt_cache_key = _prompt_cache_key_from_request_model(payload) is not None
        affinity = _sticky_key_for_compact_request(
            payload,
            headers,
            codex_session_affinity=codex_session_affinity,
            openai_cache_affinity=openai_cache_affinity,
            openai_cache_affinity_max_age_seconds=settings.openai_cache_affinity_max_age_seconds,
            sticky_threads_enabled=settings.sticky_threads_enabled,
            api_key=api_key,
            codex_session_budget_reallocation_enabled=codex_session_budget_reallocation_enabled,
        )
        sticky_key_source = "none"
        if affinity.kind == StickySessionKind.CODEX_SESSION:
            sticky_key_source = "session_header"
        elif affinity.key:
            sticky_key_source = "payload" if had_prompt_cache_key else "derived"
        _maybe_log_proxy_request_shape(
            "compact",
            payload,
            headers,
            sticky_kind=affinity.kind.value if affinity.kind is not None else None,
            sticky_key_source=sticky_key_source,
            prompt_cache_key_set=_prompt_cache_key_from_request_model(payload) is not None,
        )
        routing_strategy = _routing_strategy(settings)
        # ``input_file.file_id`` references must land on the account that
        # registered the upload (chatgpt-account-id-scoped). The helper
        # returns ``None`` when stronger affinity signals are present
        # (prompt_cache_key / session header / turn_state header /
        # previous_response_id), so existing routing wins.
        file_preferred_account_id = rewritten_file_account_id
        if file_preferred_account_id is None:
            file_preferred_account_id = await self._resolve_file_account_for_responses(payload, headers)
        try:
            selected_subject = selected_subject or SelectedChatGPTSubject(
                provider_kind=CHATGPT_WEB_PROVIDER_KIND,
                route_class=route_class,
                routing_subject_id="chatgpt_web_pool",
            )
            if isinstance(selected_subject, SelectedChatGPTSubject):
                provider_kind_value = CHATGPT_WEB_PROVIDER_KIND

            async def _call_compact_timeout(
                callback: Callable[[], Awaitable[ProviderCompactResponseResult]],
            ) -> ProviderCompactResponseResult:
                remaining_budget = _remaining_budget_seconds(deadline)
                if remaining_budget <= 0:
                    logger.warning("Compact request budget exhausted before upstream call request_id=%s", request_id)
                    _raise_proxy_budget_exhausted()
                if base_settings.upstream_compact_timeout_seconds is None:
                    timeout_tokens = push_compact_timeout_overrides(connect_timeout_seconds=remaining_budget)
                else:
                    timeout_tokens = push_compact_timeout_overrides(
                        connect_timeout_seconds=remaining_budget,
                        total_timeout_seconds=remaining_budget,
                    )
                create_lease = await self._get_work_admission().acquire_response_create(compact=True)
                try:
                    return await callback()
                finally:
                    create_lease.release()
                    pop_compact_timeout_overrides(timeout_tokens)

            async def _call_chatgpt_compact(target: Account) -> ProviderCompactResponseResult:
                adapter = cast(ChatGPTWebProviderAdapter, self._provider_adapter(CHATGPT_WEB_PROVIDER_KIND))
                return await _call_compact_timeout(
                    lambda: adapter.compact_response(
                        self._chatgpt_provider_subject(target),
                        payload,
                        filtered,
                    )
                )

            async def _call_platform_compact(
                identity: _SelectedPlatformIdentity,
            ) -> ProviderCompactResponseResult:
                adapter = cast(OpenAIPlatformProviderAdapter, self._provider_adapter(OPENAI_PLATFORM_PROVIDER_KIND))
                return await _call_compact_timeout(
                    lambda: adapter.compact_response(
                        self._platform_provider_subject(identity),
                        payload,
                        filtered,
                        route_class=route_class,
                    )
                )

            if isinstance(selected_subject, SelectedPlatformSubject):
                provider_kind_value = OPENAI_PLATFORM_PROVIDER_KIND
                effective_request_service_tier = payload.platform_forwarded_service_tier()
                (
                    platform_sticky_key,
                    platform_sticky_kind,
                    platform_reallocate_sticky,
                    platform_sticky_max_age_seconds,
                ) = self._platform_affinity_for_selection(
                    sticky_key=affinity.key,
                    sticky_kind=affinity.kind,
                    reallocate_sticky=affinity.reallocate_sticky,
                    sticky_max_age_seconds=affinity.max_age_seconds,
                    platform_sticky_key=affinity.platform_key,
                    platform_sticky_kind=affinity.platform_kind,
                    platform_sticky_max_age_seconds=affinity.platform_max_age_seconds,
                )
                current_identity = selected_subject.identity
                platform_api_key_suffix_value = self.platform_api_key_suffix(current_identity)
                excluded_identity_ids: set[str] = set()
                safe_retry_budget = _COMPACT_SAME_CONTRACT_RETRY_BUDGET
                transient_retries = 0
                while True:
                    routing_subject_id_value = current_identity.id
                    try:
                        platform_result = await _call_platform_compact(current_identity)
                        upstream_request_id = platform_result.upstream_request_id
                        response = platform_result.payload
                        actual_service_tier = _service_tier_from_response(response)
                        await self._settle_compact_api_key_usage(
                            api_key=api_key,
                            api_key_reservation=api_key_reservation,
                            response=response,
                            request_service_tier=effective_request_service_tier,
                        )
                        log_status = "success"
                        return response
                    except OpenAIPlatformError as exc:
                        upstream_request_id = exc.upstream_request_id
                        await self._record_platform_auth_failure(current_identity.id, exc)
                        if exc.status_code in {401, 403}:
                            excluded_identity_ids.add(current_identity.id)
                            replacement_identity = await self.select_platform_identity(
                                route_family,
                                sticky_key=platform_sticky_key,
                                sticky_kind=platform_sticky_kind,
                                reallocate_sticky=platform_reallocate_sticky,
                                sticky_max_age_seconds=platform_sticky_max_age_seconds,
                                exclude_routing_subject_ids=excluded_identity_ids,
                            )
                            if replacement_identity is not None:
                                current_identity = replacement_identity
                                platform_api_key_suffix_value = self.platform_api_key_suffix(current_identity)
                                safe_retry_budget = _COMPACT_SAME_CONTRACT_RETRY_BUDGET
                                transient_retries = 0
                                continue
                        if exc.status_code == 500:
                            transient_retries += 1
                            if (
                                transient_retries < _MAX_TRANSIENT_SAME_ACCOUNT_RETRIES
                                and _remaining_budget_seconds(deadline) > 0
                            ):
                                delay = backoff_seconds(transient_retries)
                                logger.info(
                                    "Transient compact error, retrying same platform identity "
                                    "request_id=%s routing_subject_id=%s retry=%s/%s delay=%.2fs",
                                    request_id,
                                    current_identity.id,
                                    transient_retries,
                                    _MAX_TRANSIENT_SAME_ACCOUNT_RETRIES,
                                    delay,
                                )
                                await asyncio.sleep(delay)
                                continue
                        if exc.status_code in {502, 503, 504} and safe_retry_budget > 0:
                            safe_retry_budget -= 1
                            continue
                        await self._settle_compact_api_key_usage(
                            api_key=api_key,
                            api_key_reservation=api_key_reservation,
                            response=None,
                            request_service_tier=effective_request_service_tier,
                        )
                        raise ProxyResponseError(
                            exc.status_code,
                            cast(OpenAIErrorEnvelope, exc.payload),
                            upstream_request_id=exc.upstream_request_id,
                            provider_kind=OPENAI_PLATFORM_PROVIDER_KIND,
                            routing_subject_id=current_identity.id,
                        ) from exc

            last_exc: ProxyResponseError | None = None
            excluded_account_ids: set[str] = set()
            for _account_attempt in range(_COMPACT_MAX_ACCOUNT_ATTEMPTS):
                selection = await self._select_account_with_budget_compatible(
                    deadline,
                    request_id=request_id,
                    kind="compact",
                    api_key=api_key,
                    sticky_key=affinity.key,
                    sticky_kind=affinity.kind,
                    reallocate_sticky=affinity.reallocate_sticky,
                    sticky_max_age_seconds=affinity.max_age_seconds,
                    sticky_budget_reallocation_enabled=affinity.budget_reallocation_enabled,
                    prefer_earlier_reset_accounts=prefer_earlier_reset,
                    routing_strategy=routing_strategy,
                    model=payload.model,
                    exclude_account_ids=excluded_account_ids,
                    preferred_account_id=file_preferred_account_id,
                )
                account = selection.account
                if not account:
                    if last_exc is not None:
                        raise last_exc
                    log_error_code = selection.error_code or "no_accounts"
                    log_error_message = selection.error_message or "No active accounts available"
                    raise ProxyResponseError(
                        503,
                        openai_error(log_error_code, log_error_message),
                    )
                account_id_value = account.id
                routing_subject_id_value = account.id
                remaining_budget = _remaining_budget_seconds(deadline)
                if remaining_budget <= 0:
                    logger.warning("Compact request budget exhausted before freshness check request_id=%s", request_id)
                    _raise_proxy_budget_exhausted()
                try:
                    account = await self._ensure_fresh_with_budget(account, timeout_seconds=remaining_budget)
                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    logger.warning(
                        "Compact refresh/connect failed request_id=%s account_id=%s",
                        request_id,
                        account.id,
                        exc_info=True,
                    )
                    _raise_proxy_unavailable(str(exc) or "Request to upstream timed out")

                safe_retry_budget = _COMPACT_SAME_CONTRACT_RETRY_BUDGET
                transient_retries = 0
                refresh_retry_used = False
                transient_exhausted = False
                while True:
                    try:
                        provider_result = await _call_chatgpt_compact(account)
                        upstream_request_id = provider_result.upstream_request_id
                        response = provider_result.payload
                        actual_service_tier = _service_tier_from_response(response)
                        await self._load_balancer.record_success(account)
                        await self._settle_compact_api_key_usage(
                            api_key=api_key,
                            api_key_reservation=api_key_reservation,
                            response=response,
                            request_service_tier=effective_request_service_tier,
                        )
                        log_status = "success"
                        return response
                    except ProxyResponseError as exc:
                        if exc.status_code == 401:
                            if refresh_retry_used:
                                await self._settle_compact_api_key_usage(
                                    api_key=api_key,
                                    api_key_reservation=api_key_reservation,
                                    response=None,
                                    request_service_tier=effective_request_service_tier,
                                )
                                await self._handle_proxy_error(account, exc)
                                raise
                            try:
                                remaining_budget = _remaining_budget_seconds(deadline)
                                if remaining_budget <= 0:
                                    logger.warning(
                                        "Compact request budget exhausted before forced refresh retry request_id=%s "
                                        "account_id=%s",
                                        request_id,
                                        account.id,
                                    )
                                    _raise_proxy_budget_exhausted()
                                account = await self._ensure_fresh_with_budget(
                                    account,
                                    force=True,
                                    timeout_seconds=remaining_budget,
                                )
                            except RefreshError as refresh_exc:
                                if refresh_exc.is_permanent:
                                    await self._load_balancer.mark_permanent_failure(account, refresh_exc.code)
                                await self._settle_compact_api_key_usage(
                                    api_key=api_key,
                                    api_key_reservation=api_key_reservation,
                                    response=None,
                                    request_service_tier=effective_request_service_tier,
                                )
                                raise exc
                            except (aiohttp.ClientError, asyncio.TimeoutError) as timeout_exc:
                                await self._settle_compact_api_key_usage(
                                    api_key=api_key,
                                    api_key_reservation=api_key_reservation,
                                    response=None,
                                    request_service_tier=effective_request_service_tier,
                                )
                                logger.warning(
                                    "Compact forced refresh/connect failed request_id=%s account_id=%s",
                                    request_id,
                                    account.id,
                                    exc_info=True,
                                )
                                _raise_proxy_unavailable(str(timeout_exc) or "Request to upstream timed out")
                            refresh_retry_used = True
                            continue
                        if exc.status_code == 500:
                            transient_retries += 1
                            if (
                                transient_retries < _MAX_TRANSIENT_SAME_ACCOUNT_RETRIES
                                and _remaining_budget_seconds(deadline) > 0
                            ):
                                delay = backoff_seconds(transient_retries)
                                logger.info(
                                    "Transient compact error, retrying same account "
                                    "request_id=%s account_id=%s retry=%s/%s delay=%.2fs",
                                    request_id,
                                    account.id,
                                    transient_retries,
                                    _MAX_TRANSIENT_SAME_ACCOUNT_RETRIES,
                                    delay,
                                )
                                await asyncio.sleep(delay)
                                continue
                            # Exhausted same-account transient retries — penalize and failover
                            logger.warning(
                                "Compact transient retries exhausted for account "
                                "request_id=%s account_id=%s retries=%s code=server_error",
                                request_id,
                                account.id,
                                transient_retries,
                            )
                            await self._handle_proxy_error(account, exc)
                            # Record remaining errors so total equals transient_retries,
                            # meeting the load balancer backoff threshold (error_count >= 3).
                            await self._load_balancer.record_errors(account, transient_retries - 1)
                            last_exc = exc
                            excluded_account_ids.add(account.id)
                            transient_exhausted = True
                            break  # break inner loop → outer loop tries different account
                        if exc.retryable_same_contract and safe_retry_budget > 0:
                            safe_retry_budget -= 1
                            continue
                        error = _parse_openai_error(exc.payload)
                        code = _normalize_error_code(
                            error.code if error else None,
                            error.type if error else None,
                        )
                        if _is_account_neutral_error_code(code):
                            await self._settle_compact_api_key_usage(
                                api_key=api_key,
                                api_key_reservation=api_key_reservation,
                                response=None,
                                request_service_tier=effective_request_service_tier,
                            )
                            raise
                        classified = await self._handle_stream_error(
                            account,
                            _upstream_error_from_openai(error),
                            code,
                            http_status=exc.status_code,
                        )
                        if getattr(base_settings, "deterministic_failover_enabled", True):
                            action = failover_decision(
                                failure_class=classified["failure_class"],
                                downstream_visible=False,
                                candidates_remaining=_COMPACT_MAX_ACCOUNT_ATTEMPTS - _account_attempt - 1,
                            )
                        else:
                            action = "surface"
                        logger.info(
                            "Failover decision request_id=%s transport=compact account_id=%s "
                            "attempt=%d failure_class=%s action=%s",
                            request_id,
                            account.id,
                            _account_attempt + 1,
                            classified["failure_class"],
                            action,
                        )
                        if action == "failover_next":
                            last_exc = exc
                            excluded_account_ids.add(account.id)
                            transient_exhausted = True
                            break
                        await self._settle_compact_api_key_usage(
                            api_key=api_key,
                            api_key_reservation=api_key_reservation,
                            response=None,
                            request_service_tier=effective_request_service_tier,
                        )
                        raise
                if transient_exhausted:
                    continue  # outer loop: try different account
            # All account attempts exhausted — raise last error
            await self._settle_compact_api_key_usage(
                api_key=api_key,
                api_key_reservation=api_key_reservation,
                response=None,
                request_service_tier=effective_request_service_tier,
            )
            if last_exc is not None:
                raise last_exc
            raise ProxyResponseError(
                502,
                openai_error("upstream_unavailable", "All account attempts exhausted"),
            )
        except NotImplementedError as exc:
            log_error_code = "not_implemented"
            log_error_message = str(exc) or "Requested compact provider is not implemented"
            log_rejection_reason = "provider_compact_not_implemented"
            raise
        except ProxyResponseError as exc:
            error = _parse_openai_error(exc.payload)
            log_error_code = log_error_code or _normalize_error_code(
                error.code if error else None,
                error.type if error else None,
            )
            log_error_message = log_error_message or (error.message if error else None)
            raise
        finally:
            usage = response.usage if response else None
            reasoning_effort = payload.reasoning.effort if payload.reasoning else None
            input_tokens = usage.input_tokens if usage else None
            output_tokens = usage.output_tokens if usage else None
            cached_input_tokens = (
                usage.input_tokens_details.cached_tokens if usage and usage.input_tokens_details else None
            )
            reasoning_tokens = (
                usage.output_tokens_details.reasoning_tokens if usage and usage.output_tokens_details else None
            )
            if log_status == "success" and provider_kind_value == OPENAI_PLATFORM_PROVIDER_KIND:
                await self.record_platform_cache_observation(
                    api_key_suffix=platform_api_key_suffix_value,
                    client_version=None,
                    input_tokens=input_tokens,
                    cached_input_tokens=cached_input_tokens,
                )
            await self._write_request_log(
                account_id=account_id_value,
                provider_kind=provider_kind_value,
                routing_subject_id=routing_subject_id_value,
                api_key=api_key,
                request_id=request_id,
                model=payload.model,
                latency_ms=int((time.monotonic() - start) * 1000),
                status=log_status,
                error_code=log_error_code,
                error_message=log_error_message,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_input_tokens=cached_input_tokens,
                reasoning_tokens=reasoning_tokens,
                reasoning_effort=reasoning_effort,
                transport=_REQUEST_TRANSPORT_HTTP,
                service_tier=_effective_service_tier(effective_request_service_tier, actual_service_tier),
                requested_service_tier=requested_service_tier,
                actual_service_tier=actual_service_tier,
                route_class=route_class,
                upstream_request_id=upstream_request_id,
                rejection_reason=log_rejection_reason,
            )
            _maybe_log_proxy_service_tier_trace(
                "compact",
                requested_service_tier=requested_service_tier,
                actual_service_tier=actual_service_tier,
            )

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        filename: str,
        content_type: str | None,
        prompt: str | None,
        headers: Mapping[str, str],
        api_key: ApiKeyData | None = None,
    ) -> dict[str, JsonValue]:
        return await _TranscribeMixin.transcribe(
            self,
            audio_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
            prompt=prompt,
            headers=headers,
            api_key=api_key,
        )

        filtered = filter_inbound_headers(headers)
        request_id = get_request_id() or ensure_request_id(None)
        start = time.monotonic()
        base_settings = get_settings()
        deadline = start + base_settings.transcription_request_budget_seconds
        account_id_value: str | None = None
        log_status = "error"
        log_error_code: str | None = None
        log_error_message: str | None = None
        transcribe_model = "gpt-4o-transcribe"

        settings = await get_settings_cache().get()
        prefer_earlier_reset = settings.prefer_earlier_reset_accounts
        routing_strategy = _routing_strategy(settings)
        try:
            selection = await self._select_account_with_budget_compatible(
                deadline,
                request_id=request_id,
                kind="transcribe",
                api_key=api_key,
                prefer_earlier_reset_accounts=prefer_earlier_reset,
                routing_strategy=routing_strategy,
                model=None,
            )
            account = selection.account
            if not account:
                log_error_code = selection.error_code or "no_accounts"
                log_error_message = selection.error_message or "No active accounts available"
                raise ProxyResponseError(
                    503,
                    openai_error(log_error_code, log_error_message),
                )
            account_id_value = account.id

            async def _call_transcribe(target: Account) -> dict[str, JsonValue]:
                adapter = cast(ChatGPTWebProviderAdapter, self._provider_adapter(CHATGPT_WEB_PROVIDER_KIND))
                remaining_budget = _remaining_budget_seconds(deadline)
                if remaining_budget <= 0:
                    logger.warning(
                        "Transcription request budget exhausted before upstream call request_id=%s account_id=%s",
                        request_id,
                        target.id,
                    )
                    _raise_proxy_budget_exhausted()
                timeout_tokens = push_transcribe_timeout_overrides(
                    connect_timeout_seconds=remaining_budget,
                    total_timeout_seconds=remaining_budget,
                )
                try:
                    return await adapter.transcribe_audio(
                        self._chatgpt_provider_subject(target),
                        audio_bytes=audio_bytes,
                        filename=filename,
                        content_type=content_type,
                        prompt=prompt,
                        headers=filtered,
                    )
                finally:
                    pop_transcribe_timeout_overrides(timeout_tokens)

            try:
                remaining_budget = _remaining_budget_seconds(deadline)
                if remaining_budget <= 0:
                    logger.warning(
                        "Transcription request budget exhausted before freshness check request_id=%s", request_id
                    )
                    _raise_proxy_budget_exhausted()
                try:
                    account = await self._ensure_fresh_with_budget(account, timeout_seconds=remaining_budget)
                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    logger.warning(
                        "Transcription refresh/connect failed request_id=%s account_id=%s",
                        request_id,
                        account.id,
                        exc_info=True,
                    )
                    _raise_proxy_unavailable(str(exc) or "Request to upstream timed out")
                result = await _call_transcribe(account)
                await self._load_balancer.record_success(account)
                log_status = "success"
                return result
            except RefreshError as refresh_exc:
                if refresh_exc.is_permanent:
                    await self._load_balancer.mark_permanent_failure(account, refresh_exc.code)
                raise ProxyResponseError(
                    401,
                    openai_error(
                        "invalid_api_key",
                        refresh_exc.message,
                        error_type="invalid_request_error",
                    ),
                ) from refresh_exc
            except ProxyResponseError as exc:
                if exc.status_code != 401:
                    await self._handle_proxy_error(account, exc)
                    raise
                try:
                    remaining_budget = _remaining_budget_seconds(deadline)
                    if remaining_budget <= 0:
                        logger.warning(
                            "Transcription request budget exhausted before forced refresh retry "
                            "request_id=%s account_id=%s",
                            request_id,
                            account.id,
                        )
                        _raise_proxy_budget_exhausted()
                    account = await self._ensure_fresh_with_budget(
                        account, force=True, timeout_seconds=remaining_budget
                    )
                except RefreshError as refresh_exc:
                    if refresh_exc.is_permanent:
                        await self._load_balancer.mark_permanent_failure(account, refresh_exc.code)
                    raise exc
                except (aiohttp.ClientError, asyncio.TimeoutError) as timeout_exc:
                    logger.warning(
                        "Transcription forced refresh/connect failed request_id=%s account_id=%s",
                        request_id,
                        account.id,
                        exc_info=True,
                    )
                    _raise_proxy_unavailable(str(timeout_exc) or "Request to upstream timed out")
                try:
                    result = await _call_transcribe(account)
                    await self._load_balancer.record_success(account)
                    log_status = "success"
                    return result
                except ProxyResponseError as exc:
                    await self._handle_proxy_error(account, exc)
                    raise
        except ProxyResponseError as exc:
            error = _parse_openai_error(exc.payload)
            log_error_code = log_error_code or _normalize_error_code(
                error.code if error else None,
                error.type if error else None,
            )
            log_error_message = log_error_message or (error.message if error else None)
            raise
        finally:
            await self._write_request_log(
                account_id=account_id_value,
                api_key=api_key,
                request_id=request_id,
                model=transcribe_model,
                latency_ms=int((time.monotonic() - start) * 1000),
                status=log_status,
                error_code=log_error_code,
                error_message=log_error_message,
                transport=_REQUEST_TRANSPORT_HTTP,
            )

    # File-account pin TTL: long enough to cover a slow client-side
    # PUT of a 512 MiB upload (the upstream limit) plus the finalize
    # poll loop and a follow-up ``/responses`` that references the
    # file_id, while still bounding how long stale pins can sit in
    # memory on long-lived workers. 30 minutes covers a 512 MiB
    # upload at ~280 KiB/s -- well below typical broadband uplink --
    # while keeping the table size negligible (each pin is a short
    # string tuple). Eviction runs opportunistically on every write,
    # so this acts as an upper bound, not a fixed retention.
    _FILE_ACCOUNT_PIN_TTL_SECONDS: float = 30 * 60.0

    async def _pin_file_account(
        self,
        file_id: str,
        account_id: str,
    ) -> None:
        """Remember that ``file_id`` was registered through ``account_id``.

        Used so a subsequent ``finalize_file`` can be routed to the same
        account that created the file. Cross-instance handoff is
        best-effort: if the finalize lands on a different replica with
        no pin, we fall back to a fresh load-balancer selection.
        """
        if not file_id or not account_id:
            return
        expires_at = time.monotonic() + self._FILE_ACCOUNT_PIN_TTL_SECONDS
        async with self._file_account_pin_lock:
            self._file_account_pins[file_id] = _FilePinEntry(
                account_id=account_id,
                expires_at=expires_at,
            )
            self._evict_expired_file_pins_locked()

    async def _resolve_file_account(self, file_id: str) -> str | None:
        """Return the pinned account_id for ``file_id`` if still live."""
        entry = await self._lookup_file_pin(file_id)
        return entry.account_id if entry is not None else None

    async def _lookup_file_pin(self, file_id: str) -> _FilePinEntry | None:
        if not file_id:
            return None
        async with self._file_account_pin_lock:
            self._evict_expired_file_pins_locked()
            entry = self._file_account_pins.get(file_id)
            if entry is None:
                return None
            if entry.expires_at <= time.monotonic():
                self._file_account_pins.pop(file_id, None)
                return None
            return entry

    def _evict_expired_file_pins_locked(self) -> None:
        """Drop pins past their TTL. Called under ``_file_account_pin_lock``."""
        now = time.monotonic()
        expired = [file_id for file_id, entry in self._file_account_pins.items() if entry.expires_at <= now]
        for file_id in expired:
            self._file_account_pins.pop(file_id, None)

    async def _resolve_file_account_for_responses(
        self,
        payload: ResponsesRequest | ResponsesCompactRequest,
        headers: Mapping[str, str],
    ) -> str | None:
        """Resolve a ``preferred_account_id`` from ``input_file.file_id`` pins.

        Looks up the in-memory ``file_id -> account_id`` pin table built
        by ``create_file``. Used by ``/responses`` flows so a request
        carrying an ``{type: "input_file", file_id: "file_xxx"}`` part
        is routed to the same upstream account that registered the
        upload (the upstream contract is account-scoped via
        ``chatgpt-account-id``).

        The pin is only consulted when the request has *no* stronger
        client-supplied affinity signal: a ``prompt_cache_key`` that
        the client itself sent, a session / turn-state header
        (codex_session affinity), or a ``previous_response_id`` all
        imply an existing conversation continuation and must keep
        their routing intact. Returning ``None`` from here means
        "fall back to the standard sticky / codex / cache affinity
        path".

        Note: ``_sticky_key_for_responses_request`` can *derive* and
        write a ``prompt_cache_key`` onto the payload when openai cache
        affinity is enabled. We must not treat that derived key as a
        stronger signal -- it is itself the load balancer's choice to
        route consistently, not a client-supplied continuation marker.
        Inspect ``model_fields_set`` so we only honor an *explicit*
        client-supplied cache key.

        Tie-breaking when the payload references multiple ``file_id``s:
        prefer the most-recently-pinned one (matches the most recent
        upload in a multi-attachment thread). If two pins share the
        same expiry timestamp, the lexicographically smallest
        ``file_id`` wins for determinism.
        """
        # Stronger affinity signals always win, but only when the
        # client supplied them. Derived ``prompt_cache_key`` values
        # added by the affinity helper itself must not block file-pin
        # routing for first-turn upload-then-converse flows.
        # Honor both the canonical ``prompt_cache_key`` and the
        # OpenAI-compat camelCase ``promptCacheKey`` alias as
        # client-supplied. Pydantic populates ``model_fields_set`` with
        # the canonical name when V1 normalization runs ahead of us, but
        # raw clients posting directly to ``/backend-api/codex/responses``
        # bypass that normalization and we still want to respect their
        # explicit cache key.
        explicit_fields = getattr(payload, "model_fields_set", set())
        explicit_cache_key = "prompt_cache_key" in explicit_fields or "promptCacheKey" in explicit_fields
        if explicit_cache_key and _prompt_cache_key_from_request_model(payload) is not None:
            return None
        # ``ensure_downstream_turn_state`` / ``ensure_http_downstream_turn_state``
        # synthesize a fresh ``x-codex-turn-state`` header on first turns when
        # the client did not supply one (see
        # ``app/modules/proxy/api.py`` websocket / HTTP handlers). Treat those
        # synthetic values as "no client-supplied turn state" so the file-pin
        # lookup still runs on first-turn upload-then-converse flows. Only a
        # turn-state value that does *not* match the synthesizer prefix counts
        # as a client-supplied continuation marker.
        turn_state_value = _sticky_key_from_turn_state_header(headers)
        if turn_state_value is not None and not _is_synthesized_turn_state(turn_state_value):
            return None
        if _sticky_key_from_session_header(headers) is not None:
            return None
        if getattr(payload, "previous_response_id", None):
            return None

        file_ids = extract_input_file_ids(payload.input)
        if not file_ids:
            return None

        async with self._file_account_pin_lock:
            self._evict_expired_file_pins_locked()
            best_account: str | None = None
            best_expires_at = -1.0
            best_file_id: str | None = None
            for file_id in file_ids:
                entry = self._file_account_pins.get(file_id)
                if entry is None:
                    continue
                if entry.expires_at > best_expires_at or (
                    entry.expires_at == best_expires_at and (best_file_id is None or file_id < best_file_id)
                ):
                    best_account = entry.account_id
                    best_expires_at = entry.expires_at
                    best_file_id = file_id
            return best_account

    def _raise_for_unsupported_input_image_references(self, payload: _ResponsesPayloadT) -> None:
        references = extract_input_image_file_references(payload.input)
        if not references:
            return
        raise ProxyResponseError(
            400,
            openai_error(
                "unsupported_input_image_format",
                (
                    "input_image references via file_id or sediment:// URIs are not supported on "
                    "/v1/responses; the upstream API only accepts inline data: URLs. Send the "
                    "image inline (codex-cli style) or use the upload protocol exclusively for "
                    "MCP tool arguments."
                ),
            ),
        )

    async def create_file(
        self,
        payload: Mapping[str, JsonValue],
        headers: Mapping[str, str],
        *,
        api_key: ApiKeyData | None = None,
    ) -> dict[str, JsonValue]:
        return await _FileOpsMixin.create_file(self, payload, headers, api_key=api_key)

        """Forward an inbound `POST /backend-api/files` registration to upstream.

        The body is whatever the caller sent (already validated as
        ``FileCreateRequest`` at the API edge). Returns the upstream
        ``{file_id, upload_url, ...}`` JSON verbatim. Mirrors the
        account-selection / refresh / 401-retry pattern from ``transcribe``.

        On success we record a ``file_id -> account_id`` pin so a
        subsequent ``finalize_file`` for the same ``file_id`` is routed
        to the same account; the upstream contract is account-scoped
        (chatgpt-account-id) so a finalize on a different account would
        fail with not-found / unauthorized.
        """
        result, account_id = await self._proxy_files_call(
            log_model="files-create",
            kind="files-create",
            api_key=api_key,
            headers=headers,
            invoke=lambda access_token, upstream_account_id, filtered_headers: core_create_file(
                payload=payload,
                headers=filtered_headers,
                access_token=access_token,
                account_id=upstream_account_id,
            ),
        )
        # Best-effort pin so finalize lands on the same account.
        if isinstance(result, dict) and account_id:
            file_id = result.get("file_id")
            if isinstance(file_id, str) and file_id:
                await self._pin_file_account(file_id, account_id)
        return result

    async def finalize_file(
        self,
        file_id: str,
        headers: Mapping[str, str],
        *,
        api_key: ApiKeyData | None = None,
    ) -> dict[str, JsonValue]:
        return await _FileOpsMixin.finalize_file(self, file_id, headers, api_key=api_key)

        """Forward an inbound `POST /backend-api/files/{file_id}/uploaded` finalize call.

        The upstream client (Codex CLI) polls this endpoint while
        ``status == "retry"``; ``core_finalize_file`` mirrors that loop
        server-side with a 30 s budget. Returns the upstream JSON
        verbatim.

        Routes to the account that handled the matching ``create_file``
        (via the in-memory pin table) so the upstream finalize call
        carries the same ``chatgpt-account-id`` that registered the
        file. Falls back to a fresh load-balancer selection when no
        pin is found (unknown ``file_id`` or pin expired / missed across
        a replica boundary).
        """
        pinned_account_id = await self._resolve_file_account(file_id)
        result, account_id = await self._proxy_files_call(
            log_model="files-finalize",
            kind="files-finalize",
            api_key=api_key,
            headers=headers,
            preferred_account_id=pinned_account_id,
            invoke=lambda access_token, upstream_account_id, filtered_headers: core_finalize_file(
                file_id=file_id,
                headers=filtered_headers,
                access_token=access_token,
                account_id=upstream_account_id,
            ),
        )
        if isinstance(result, dict) and account_id:
            status = result.get("status")
            if status == "success":
                await self._pin_file_account(file_id, account_id)
        return result

    async def _proxy_files_call(
        self,
        *,
        log_model: str,
        kind: str,
        api_key: ApiKeyData | None,
        headers: Mapping[str, str],
        invoke: Callable[..., Awaitable[dict[str, JsonValue]]],
        preferred_account_id: str | None = None,
    ) -> tuple[dict[str, JsonValue], str | None]:
        invoke_for_mixin = invoke
        try:
            invoke_signature = inspect.signature(invoke)
        except (TypeError, ValueError):
            invoke_signature = None
        if invoke_signature is not None:
            accepts_variadic = any(
                parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
                for parameter in invoke_signature.parameters.values()
            )
            positional_count = sum(
                parameter.kind
                in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                )
                for parameter in invoke_signature.parameters.values()
            )
            if not accepts_variadic and positional_count <= 3:

                async def invoke_for_mixin(
                    access_token: str,
                    upstream_account_id: str | None,
                    filtered_headers: Mapping[str, str],
                    route: ResolvedUpstreamRoute | None,
                    route_trace: UpstreamProxyRouteTrace,
                ) -> dict[str, JsonValue]:
                    del route, route_trace
                    return await invoke(access_token, upstream_account_id, filtered_headers)

        return await _FileOpsMixin._proxy_files_call(
            self,
            log_model=log_model,
            kind=kind,
            api_key=api_key,
            headers=headers,
            invoke=invoke_for_mixin,
            preferred_account_id=preferred_account_id,
        )

        """Shared account-selection / refresh / 401-retry plumbing for `/files` calls.

        Mirrors the structure of ``transcribe``: pick an account with budget,
        ensure freshness, invoke upstream, on 401 force-refresh and retry once,
        translate ``FileProxyError`` -> ``ProxyResponseError``, and always
        write a request-log entry on the way out. When
        ``preferred_account_id`` is provided (e.g. from the file_id pin
        for ``finalize_file``), prefer that account if it is still live;
        fall back to a fresh selection otherwise.
        """
        filtered = filter_inbound_headers(headers)
        request_id = get_request_id() or ensure_request_id(None)
        start = time.monotonic()
        base_settings = get_settings()
        deadline = start + base_settings.transcription_request_budget_seconds
        account_id_value: str | None = None
        log_status = "error"
        log_error_code: str | None = None
        log_error_message: str | None = None

        settings = await get_settings_cache().get()
        prefer_earlier_reset = settings.prefer_earlier_reset_accounts
        routing_strategy = _routing_strategy(settings)
        try:
            selection = await self._select_account_with_budget_compatible(
                deadline,
                request_id=request_id,
                kind=kind,
                api_key=api_key,
                prefer_earlier_reset_accounts=prefer_earlier_reset,
                routing_strategy=routing_strategy,
                model=None,
                preferred_account_id=preferred_account_id,
            )
            account = selection.account
            if not account:
                log_error_code = selection.error_code or "no_accounts"
                log_error_message = selection.error_message or "No active accounts available"
                raise ProxyResponseError(
                    503,
                    openai_error(log_error_code, log_error_message),
                )
            account_id_value = account.id

            async def _call(target: Account) -> dict[str, JsonValue]:
                access_token = self._encryptor.decrypt(target.access_token_encrypted)
                account_id = _header_account_id(target.chatgpt_account_id)
                remaining_budget = _remaining_budget_seconds(deadline)
                if remaining_budget <= 0:
                    logger.warning(
                        "%s request budget exhausted before upstream call request_id=%s account_id=%s",
                        kind,
                        request_id,
                        target.id,
                    )
                    _raise_proxy_budget_exhausted()
                # Propagate the per-request budget so file create/finalize
                # calls inherit the same effective timeout as the rest of
                # the request, instead of letting them block on the
                # module-default 60 s timeout regardless of how much
                # budget is left.
                timeout_tokens = push_files_timeout_overrides(
                    connect_timeout_seconds=remaining_budget,
                    total_timeout_seconds=remaining_budget,
                )
                try:
                    return await invoke(access_token, account_id, filtered)
                except FileProxyError as files_exc:
                    raise ProxyResponseError(files_exc.status_code, files_exc.payload) from files_exc
                finally:
                    pop_files_timeout_overrides(timeout_tokens)

            try:
                remaining_budget = _remaining_budget_seconds(deadline)
                if remaining_budget <= 0:
                    logger.warning(
                        "%s request budget exhausted before freshness check request_id=%s",
                        kind,
                        request_id,
                    )
                    _raise_proxy_budget_exhausted()
                try:
                    account = await self._ensure_fresh_with_budget(account, timeout_seconds=remaining_budget)
                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    logger.warning(
                        "%s refresh/connect failed request_id=%s account_id=%s",
                        kind,
                        request_id,
                        account.id,
                        exc_info=True,
                    )
                    _raise_proxy_unavailable(str(exc) or "Request to upstream timed out")
                result = await _call(account)
                await self._load_balancer.record_success(account)
                log_status = "success"
                return result, account_id_value
            except RefreshError as refresh_exc:
                if refresh_exc.is_permanent:
                    await self._load_balancer.mark_permanent_failure(account, refresh_exc.code)
                raise ProxyResponseError(
                    401,
                    openai_error(
                        "invalid_api_key",
                        refresh_exc.message,
                        error_type="invalid_request_error",
                    ),
                ) from refresh_exc
            except ProxyResponseError as exc:
                if exc.status_code != 401:
                    await self._handle_proxy_error(account, exc)
                    raise
                try:
                    remaining_budget = _remaining_budget_seconds(deadline)
                    if remaining_budget <= 0:
                        logger.warning(
                            "%s request budget exhausted before forced refresh retry request_id=%s account_id=%s",
                            kind,
                            request_id,
                            account.id,
                        )
                        _raise_proxy_budget_exhausted()
                    account = await self._ensure_fresh_with_budget(
                        account, force=True, timeout_seconds=remaining_budget
                    )
                except RefreshError as refresh_exc:
                    if refresh_exc.is_permanent:
                        await self._load_balancer.mark_permanent_failure(account, refresh_exc.code)
                    raise exc
                except (aiohttp.ClientError, asyncio.TimeoutError) as timeout_exc:
                    logger.warning(
                        "%s forced refresh/connect failed request_id=%s account_id=%s",
                        kind,
                        request_id,
                        account.id,
                        exc_info=True,
                    )
                    _raise_proxy_unavailable(str(timeout_exc) or "Request to upstream timed out")
                try:
                    result = await _call(account)
                    # The forced-refresh retry can swap to a refreshed
                    # account row -- re-pin to that account id so the
                    # caller's pin is consistent with the upstream call.
                    account_id_value = account.id
                    await self._load_balancer.record_success(account)
                    log_status = "success"
                    return result, account_id_value
                except ProxyResponseError as retry_exc:
                    await self._handle_proxy_error(account, retry_exc)
                    raise
        except ProxyResponseError as exc:
            error = _parse_openai_error(exc.payload)
            log_error_code = log_error_code or _normalize_error_code(
                error.code if error else None,
                error.type if error else None,
            )
            log_error_message = log_error_message or (error.message if error else None)
            raise
        finally:
            await self._write_request_log(
                account_id=account_id_value,
                api_key=api_key,
                request_id=request_id,
                model=log_model,
                latency_ms=int((time.monotonic() - start) * 1000),
                status=log_status,
                error_code=log_error_code,
                error_message=log_error_message,
                transport=_REQUEST_TRANSPORT_HTTP,
            )

    async def proxy_responses_websocket(
        self,
        websocket: WebSocket,
        headers: Mapping[str, str],
        *,
        codex_session_affinity: bool,
        openai_cache_affinity: bool,
        api_key: ApiKeyData | None,
    ) -> None:
        await _WebSocketMixin.proxy_responses_websocket(
            self,
            websocket,
            headers,
            codex_session_affinity=codex_session_affinity,
            openai_cache_affinity=openai_cache_affinity,
            api_key=api_key,
        )
        return

        filtered_headers = filter_inbound_websocket_headers(dict(headers))
        runtime_settings = get_settings()
        settings = await get_settings_cache().get()
        prefer_earlier_reset = settings.prefer_earlier_reset_accounts
        sticky_threads_enabled = settings.sticky_threads_enabled
        openai_cache_affinity_max_age_seconds = settings.openai_cache_affinity_max_age_seconds
        routing_strategy = _routing_strategy(settings)
        pending_requests: deque[_WebSocketRequestState] = deque()
        pending_lock = anyio.Lock()
        client_send_lock = anyio.Lock()
        response_create_gate = asyncio.Semaphore(1)
        upstream: UpstreamResponsesWebSocket | None = None
        upstream_reader: asyncio.Task[None] | None = None
        upstream_control: _WebSocketUpstreamControl | None = None
        account: Account | None = None
        upstream_turn_state: str | None = _sticky_key_from_turn_state_header(headers)
        downstream_activity = _DownstreamWebSocketActivity()
        replay_request_state: _WebSocketRequestState | None = None

        try:
            while True:
                if upstream_reader is not None and upstream_reader.done():
                    try:
                        await upstream_reader
                    except asyncio.CancelledError:
                        pass
                    if replay_request_state is None and upstream_control is not None:
                        replay_request_state = upstream_control.replay_request_state
                    upstream_reader = None
                    upstream_control = None
                    if upstream is not None:
                        try:
                            await upstream.close()
                        except Exception:
                            logger.debug("Failed to close upstream websocket", exc_info=True)
                    upstream = None
                    account = None

                text_data: str | None = None
                bytes_data: bytes | None = None
                request_state: _WebSocketRequestState | None = None
                request_state_registered = False
                response_create_gate_acquired = False
                request_affinity = _AffinityPolicy()
                payload: dict[str, JsonValue] | None = None

                if replay_request_state is not None:
                    request_state = replay_request_state
                    replay_request_state = None
                    request_affinity = request_state.affinity_policy
                    text_data = request_state.request_text
                    if text_data is None:
                        await self._release_websocket_reservation(request_state.api_key_reservation)
                        await self._emit_websocket_terminal_error(
                            websocket,
                            client_send_lock=client_send_lock,
                            request_state=request_state,
                            error_code="stream_incomplete",
                            error_message="Upstream websocket closed before response.completed",
                            error_type="server_error",
                            downstream_activity=downstream_activity,
                        )
                        _release_websocket_response_create_gate(request_state, response_create_gate)
                        continue
                    payload = _parse_websocket_payload(text_data)
                    if payload is None:
                        await self._release_websocket_reservation(request_state.api_key_reservation)
                        await self._emit_websocket_terminal_error(
                            websocket,
                            client_send_lock=client_send_lock,
                            request_state=request_state,
                            error_code="upstream_error",
                            error_message="Invalid replay request payload",
                            error_type="server_error",
                            downstream_activity=downstream_activity,
                        )
                        _release_websocket_response_create_gate(request_state, response_create_gate)
                        continue
                    async with pending_lock:
                        pending_requests.append(request_state)
                    request_state_registered = True
                else:
                    downstream_idle_timeout_seconds = runtime_settings.proxy_downstream_websocket_idle_timeout_seconds
                    try:
                        message = await asyncio.wait_for(
                            websocket.receive(),
                            timeout=min(downstream_idle_timeout_seconds, _DOWNSTREAM_WEBSOCKET_RECEIVE_POLL_SECONDS),
                        )
                    except asyncio.TimeoutError:
                        if not await self._downstream_websocket_is_idle(
                            pending_requests,
                            pending_lock=pending_lock,
                            downstream_activity=downstream_activity,
                            idle_timeout_seconds=downstream_idle_timeout_seconds,
                        ):
                            continue
                        idle_close = False
                        async with client_send_lock:
                            if await self._downstream_websocket_is_idle(
                                pending_requests,
                                pending_lock=pending_lock,
                                downstream_activity=downstream_activity,
                                idle_timeout_seconds=downstream_idle_timeout_seconds,
                            ):
                                try:
                                    message = await asyncio.wait_for(websocket.receive(), timeout=0.05)
                                except asyncio.TimeoutError:
                                    try:
                                        await websocket.close(code=1001, reason=_DOWNSTREAM_WEBSOCKET_IDLE_CLOSE_REASON)
                                    except Exception:
                                        logger.debug("Failed to close idle downstream websocket", exc_info=True)
                                    idle_close = True
                        if idle_close:
                            break
                    downstream_activity.mark()
                    message_type = message["type"]

                    if message_type == "websocket.disconnect":
                        break
                    if message_type != "websocket.receive":
                        continue

                    text_data = message.get("text")
                    bytes_data = message.get("bytes")

                    if text_data is not None:
                        payload = _parse_websocket_payload(text_data)
                        if payload is not None and _is_websocket_response_create(payload):
                            try:
                                prepared_request = await self._prepare_websocket_response_create_request(
                                    payload,
                                    headers=headers,
                                    codex_session_affinity=codex_session_affinity,
                                    openai_cache_affinity=openai_cache_affinity,
                                    sticky_threads_enabled=sticky_threads_enabled,
                                    openai_cache_affinity_max_age_seconds=openai_cache_affinity_max_age_seconds,
                                    api_key=api_key,
                                )
                                request_state = prepared_request.request_state
                                request_affinity = prepared_request.affinity_policy
                                text_data = prepared_request.text_data
                            except ProxyResponseError as exc:
                                async with client_send_lock:
                                    await websocket.send_text(
                                        _serialize_websocket_error_event(
                                            _wrapped_websocket_error_event(exc.status_code, exc.payload)
                                        )
                                    )
                                continue
                            except AppError as exc:
                                async with client_send_lock:
                                    await websocket.send_text(
                                        _serialize_websocket_error_event(_app_error_to_websocket_event(exc))
                                    )
                                continue
                            except ClientPayloadError as exc:
                                async with client_send_lock:
                                    await websocket.send_text(
                                        _serialize_websocket_error_event(
                                            _wrapped_websocket_error_event(400, openai_client_payload_error(exc))
                                        )
                                    )
                                continue
                            except ValidationError as exc:
                                async with client_send_lock:
                                    await websocket.send_text(
                                        _serialize_websocket_error_event(
                                            _wrapped_websocket_error_event(400, openai_validation_error(exc))
                                        )
                                    )
                                continue

                if upstream_reader is not None and upstream_reader.done():
                    try:
                        await upstream_reader
                    except asyncio.CancelledError:
                        pass
                    if replay_request_state is None and upstream_control is not None:
                        replay_request_state = upstream_control.replay_request_state
                    upstream_reader = None
                    upstream_control = None
                    if upstream is not None:
                        try:
                            await upstream.close()
                        except Exception:
                            logger.debug("Failed to close upstream websocket", exc_info=True)
                    upstream = None
                    account = None

                if (
                    request_state is not None
                    and upstream_control is not None
                    and upstream_control.reconnect_requested
                    and upstream_reader is not None
                ):
                    await upstream_reader
                    if replay_request_state is None:
                        replay_request_state = upstream_control.replay_request_state
                    upstream_reader = None
                    upstream_control = None
                    if upstream is not None:
                        try:
                            await upstream.close()
                        except Exception:
                            logger.debug("Failed to close upstream websocket", exc_info=True)
                    upstream = None
                    account = None

                if (
                    request_state is not None
                    and request_state.previous_response_id is not None
                    and request_state.preferred_account_id is None
                ):
                    try:
                        request_state.preferred_account_id = await self._resolve_websocket_previous_response_owner(
                            previous_response_id=request_state.previous_response_id,
                            api_key=request_state.api_key or api_key,
                            session_id=request_state.session_id,
                            surface="websocket",
                        )
                    except ProxyResponseError as exc:
                        error = _parse_openai_error(exc.payload)
                        error_code = _normalize_error_code(
                            error.code if error else None,
                            error.type if error else None,
                        )
                        error_message = error.message if error and error.message else "Upstream error"
                        error_type = error.type if error and error.type else "server_error"
                        await self._release_websocket_reservation(request_state.api_key_reservation)
                        await self._write_websocket_connect_failure(
                            account_id=None,
                            api_key=api_key,
                            request_state=request_state,
                            error_code=error_code or "upstream_error",
                            error_message=error_message,
                        )
                        await self._emit_websocket_terminal_error(
                            websocket,
                            client_send_lock=client_send_lock,
                            request_state=request_state,
                            error_code=error_code or "upstream_error",
                            error_message=error_message,
                            error_type=error_type,
                            downstream_activity=downstream_activity,
                        )
                        request_state = None
                        text_data = None
                        payload = None
                        continue

                if request_state is not None and not request_state_registered:
                    try:
                        await self._acquire_request_state_response_create_admission(
                            request_state,
                            response_create_gate=response_create_gate,
                        )
                        async with pending_lock:
                            pending_requests.append(request_state)
                        request_state_registered = True
                    except ProxyResponseError as exc:
                        error = _parse_openai_error(exc.payload)
                        error_code = _normalize_error_code(
                            error.code if error else None,
                            error.type if error else None,
                        )
                        error_message = error.message if error and error.message else "Upstream error"
                        error_type = error.type if error and error.type else "server_error"
                        await self._release_websocket_reservation(request_state.api_key_reservation)
                        await self._write_websocket_connect_failure(
                            account_id=account.id if account else None,
                            api_key=api_key,
                            request_state=request_state,
                            error_code=error_code or "upstream_error",
                            error_message=error_message,
                        )
                        await self._emit_websocket_terminal_error(
                            websocket,
                            client_send_lock=client_send_lock,
                            request_state=request_state,
                            error_code=error_code or "upstream_error",
                            error_message=error_message,
                            error_type=error_type,
                            downstream_activity=downstream_activity,
                        )
                        _release_websocket_response_create_gate(request_state, response_create_gate)
                        continue
                    except asyncio.CancelledError:
                        await self._release_websocket_reservation(request_state.api_key_reservation)
                        if request_state_registered:
                            async with pending_lock:
                                if request_state in pending_requests:
                                    pending_requests.remove(request_state)
                        _release_websocket_response_create_gate(request_state, response_create_gate)
                        raise
                    except Exception:
                        await self._release_websocket_reservation(request_state.api_key_reservation)
                        if request_state_registered:
                            async with pending_lock:
                                if request_state in pending_requests:
                                    pending_requests.remove(request_state)
                        _release_websocket_response_create_gate(request_state, response_create_gate)
                        raise

                if upstream is None:
                    if text_data is not None and payload is None:
                        async with client_send_lock:
                            await websocket.send_text(
                                _serialize_websocket_error_event(
                                    _wrapped_websocket_error_event(400, openai_invalid_payload_error())
                                )
                            )
                        continue
                    if request_state is None:
                        async with client_send_lock:
                            await websocket.send_text(
                                _serialize_websocket_error_event(
                                    _wrapped_websocket_error_event(
                                        400,
                                        openai_error(
                                            "invalid_request_error",
                                            "WebSocket connection has no active upstream session",
                                            error_type="invalid_request_error",
                                        ),
                                    )
                                )
                            )
                        continue
                    connect_headers = _headers_with_turn_state(filtered_headers, upstream_turn_state)
                    account, upstream = await self._connect_proxy_websocket(
                        connect_headers,
                        sticky_key=request_affinity.key,
                        sticky_kind=request_affinity.kind,
                        reallocate_sticky=request_affinity.reallocate_sticky,
                        sticky_max_age_seconds=request_affinity.max_age_seconds,
                        prefer_earlier_reset=prefer_earlier_reset,
                        routing_strategy=routing_strategy,
                        model=request_state.model,
                        request_state=request_state,
                        api_key=api_key,
                        client_send_lock=client_send_lock,
                        websocket=websocket,
                    )
                    if upstream is None or account is None:
                        if request_state_registered:
                            async with pending_lock:
                                if request_state in pending_requests:
                                    pending_requests.remove(request_state)
                            _release_websocket_response_create_gate(request_state, response_create_gate)
                        continue
                    upstream_turn_state = _upstream_turn_state_from_socket(upstream) or upstream_turn_state
                    upstream_control = _WebSocketUpstreamControl()
                    upstream_reader = asyncio.create_task(
                        self._relay_upstream_websocket_messages(
                            websocket,
                            upstream,
                            account=account,
                            account_id_value=account.id,
                            pending_requests=pending_requests,
                            pending_lock=pending_lock,
                            client_send_lock=client_send_lock,
                            api_key=api_key,
                            upstream_control=upstream_control,
                            response_create_gate=response_create_gate,
                            proxy_request_budget_seconds=runtime_settings.proxy_request_budget_seconds,
                            stream_idle_timeout_seconds=runtime_settings.stream_idle_timeout_seconds,
                            downstream_activity=downstream_activity,
                        )
                    )

                try:
                    if text_data is not None:
                        await upstream.send_text(text_data)
                    elif bytes_data is not None:
                        await upstream.send_bytes(bytes_data)
                except asyncio.CancelledError:
                    if request_state is not None and not request_state_registered:
                        await self._cleanup_unregistered_websocket_request(
                            request_state,
                            response_create_gate=response_create_gate,
                            gate_acquired=response_create_gate_acquired,
                        )
                    raise
                except Exception:
                    replay_candidate = await _pop_replayable_precreated_websocket_request_state(
                        pending_requests,
                        pending_lock=pending_lock,
                    )
                    if replay_candidate is not None:
                        logger.info(
                            "Transparent websocket replay after upstream send failure request_id=%s",
                            replay_candidate.request_log_id or replay_candidate.request_id,
                        )
                        replay_request_state = replay_candidate
                        if upstream_reader is not None:
                            await _await_cancelled_task(upstream_reader, label="proxy websocket upstream reader")
                            upstream_reader = None
                        upstream_control = None
                        if upstream is not None:
                            try:
                                await upstream.close()
                            except Exception:
                                logger.debug(
                                    "Failed to close upstream websocket after replayable send failure",
                                    exc_info=True,
                                )
                        upstream = None
                        account = None
                        continue
                    await self._fail_pending_websocket_requests(
                        account_id_value=account.id if account else None,
                        pending_requests=pending_requests,
                        pending_lock=pending_lock,
                        error_code="stream_incomplete",
                        error_message="Upstream websocket closed before response.completed",
                        api_key=api_key,
                        websocket=websocket,
                        client_send_lock=client_send_lock,
                        response_create_gate=response_create_gate,
                        downstream_activity=downstream_activity,
                    )
                    if upstream_reader is not None:
                        await _await_cancelled_task(upstream_reader, label="proxy websocket upstream reader")
                        upstream_reader = None
                    upstream_control = None
                    if upstream is not None:
                        try:
                            await upstream.close()
                        except Exception:
                            logger.debug("Failed to close upstream websocket after send failure", exc_info=True)
                    upstream = None
                    account = None
                    continue
        finally:
            if upstream_reader is not None:
                await _await_cancelled_task(upstream_reader, label="proxy websocket upstream reader")
            if upstream is not None:
                try:
                    await upstream.close()
                except Exception:
                    logger.debug("Failed to close upstream websocket", exc_info=True)
            await self._fail_pending_websocket_requests(
                account_id_value=account.id if account else None,
                pending_requests=pending_requests,
                pending_lock=pending_lock,
                error_code="stream_incomplete",
                error_message="Upstream websocket closed before response.completed",
                api_key=api_key,
                websocket=websocket,
                client_send_lock=client_send_lock,
                response_create_gate=response_create_gate,
                downstream_activity=downstream_activity,
            )

    async def _prepare_websocket_response_create_request(
        self,
        payload: dict[str, JsonValue],
        *,
        headers: Mapping[str, str],
        codex_session_affinity: bool,
        openai_cache_affinity: bool,
        sticky_threads_enabled: bool,
        openai_cache_affinity_max_age_seconds: int,
        api_key: ApiKeyData | None,
        continuity_state: _WebSocketContinuityState | None = None,
        useragent: str | None = None,
        useragent_group: str | None = None,
    ) -> _PreparedWebSocketRequest:
        return await _WebSocketMixin._prepare_websocket_response_create_request(
            self,
            payload,
            headers=headers,
            codex_session_affinity=codex_session_affinity,
            openai_cache_affinity=openai_cache_affinity,
            sticky_threads_enabled=sticky_threads_enabled,
            openai_cache_affinity_max_age_seconds=openai_cache_affinity_max_age_seconds,
            api_key=api_key,
            continuity_state=continuity_state,
            useragent=useragent,
            useragent_group=useragent_group,
        )

        refreshed_api_key = await self._refresh_websocket_api_key_policy(api_key)
        client_metadata = _response_create_client_metadata(payload, headers=headers)
        responses_payload = normalize_responses_request_payload(payload, openai_compat=openai_cache_affinity)
        apply_api_key_enforcement(responses_payload, refreshed_api_key)
        validate_model_access(refreshed_api_key, responses_payload.model)
        self._raise_for_unsupported_input_image_references(responses_payload)
        rewritten_file_account_id = await self._resolve_file_account_for_responses(responses_payload, headers)
        reservation = await self._reserve_websocket_api_key_usage(
            refreshed_api_key,
            request_model=responses_payload.model,
            request_service_tier=_normalize_service_tier_value(
                dict(responses_payload.to_payload()).get("service_tier")
            ),
        )
        try:
            session_id = _owner_lookup_session_id_from_headers(headers)
            request_state, text_data = self._prepare_response_bridge_request_state(
                responses_payload,
                api_key=refreshed_api_key,
                api_key_reservation=reservation,
                include_type_field=True,
                attach_event_queue=False,
                transport=_REQUEST_TRANSPORT_WEBSOCKET,
                client_metadata=client_metadata,
                session_id=session_id,
            )
        except ProxyResponseError:
            await self._release_websocket_reservation(reservation)
            raise
        had_prompt_cache_key = _prompt_cache_key_from_request_model(responses_payload) is not None
        affinity_policy = _sticky_key_for_responses_request(
            responses_payload,
            headers,
            codex_session_affinity=codex_session_affinity,
            openai_cache_affinity=openai_cache_affinity,
            openai_cache_affinity_max_age_seconds=openai_cache_affinity_max_age_seconds,
            sticky_threads_enabled=sticky_threads_enabled,
            api_key=api_key,
        )
        sticky_key_source = "none"
        if affinity_policy.kind == StickySessionKind.CODEX_SESSION:
            sticky_key_source = (
                "turn_state_header" if _sticky_key_from_turn_state_header(headers) is not None else "session_header"
            )
        elif affinity_policy.key:
            sticky_key_source = "payload" if had_prompt_cache_key else "derived"
        _maybe_log_proxy_request_shape(
            "websocket",
            responses_payload,
            headers,
            sticky_kind=affinity_policy.kind.value if affinity_policy.kind is not None else None,
            sticky_key_source=sticky_key_source,
            prompt_cache_key_set=_prompt_cache_key_from_request_model(responses_payload) is not None,
        )
        request_state.affinity_policy = affinity_policy

        # First-turn ``input_file.file_id`` references must land on the
        # account that registered the upload (chatgpt-account-id-scoped).
        # Codex CLI's typical flow is upload-then-converse, so a fresh
        # turn often references a file_id with no other affinity signal
        # set. The helper short-circuits to ``None`` when stronger
        # affinity signals (prompt_cache_key / session header /
        # turn_state header / previous_response_id) are present, so this
        # never overrides existing routing.
        if request_state.preferred_account_id is None:
            request_state.preferred_account_id = rewritten_file_account_id
        if request_state.preferred_account_id is None:
            request_state.preferred_account_id = await self._resolve_file_account_for_responses(
                responses_payload, headers
            )

        return _PreparedWebSocketRequest(
            text_data=text_data,
            request_state=request_state,
            affinity_policy=affinity_policy,
        )

    def _prepare_http_bridge_request(
        self,
        payload: ResponsesRequest,
        headers: Mapping[str, str],
        *,
        api_key: ApiKeyData | None,
        api_key_reservation: ApiKeyUsageReservationData | None,
        request_id: str | None = None,
    ) -> tuple[_WebSocketRequestState, str]:
        return _HTTPBridgeMixin._prepare_http_bridge_request(
            self,
            payload,
            headers,
            api_key=api_key,
            api_key_reservation=api_key_reservation,
            request_id=request_id,
        )

    def _prepare_response_bridge_request_state(
        self,
        payload: ResponsesRequest,
        *,
        api_key: ApiKeyData | None,
        api_key_reservation: ApiKeyUsageReservationData | None,
        include_type_field: bool,
        attach_event_queue: bool,
        transport: str,
        client_metadata: Mapping[str, JsonValue] | None,
        session_id: str | None = None,
        request_id: str | None = None,
        request_log_id: str | None = None,
    ) -> tuple[_WebSocketRequestState, str]:
        return _HTTPBridgeMixin._prepare_response_bridge_request_state(
            self,
            payload,
            api_key=api_key,
            api_key_reservation=api_key_reservation,
            include_type_field=include_type_field,
            attach_event_queue=attach_event_queue,
            transport=transport,
            client_metadata=client_metadata,
            session_id=session_id,
            request_id=request_id,
            request_log_id=request_log_id,
        )

        upstream_payload = dict(payload.to_payload())
        service_tier = _normalize_service_tier_value(upstream_payload.get("service_tier"))
        if service_tier is not None:
            upstream_payload["service_tier"] = service_tier
        upstream_payload.pop("stream", None)
        upstream_payload.pop("background", None)
        if include_type_field:
            upstream_payload["type"] = "response.create"
        if client_metadata:
            upstream_payload["client_metadata"] = client_metadata
        forwarded_service_tier = _normalize_service_tier_value(upstream_payload.get("service_tier"))
        input_item_count = 0
        input_full_fingerprint: str | None = None
        payload_input = payload.input
        if isinstance(payload_input, list):
            payload_input_list = cast(list[JsonValue], payload_input)
            input_item_count = len(payload_input_list)
            if input_item_count > 0:
                input_full_fingerprint = _fingerprint_input_items(payload_input_list)

        request_state = _WebSocketRequestState(
            request_id=request_id or f"ws_{uuid4().hex}",
            request_log_id=request_log_id,
            model=payload.model,
            service_tier=forwarded_service_tier,
            reasoning_effort=payload.reasoning.effort if payload.reasoning else None,
            api_key_reservation=api_key_reservation,
            started_at=time.monotonic(),
            requested_service_tier=forwarded_service_tier,
            awaiting_response_created=True,
            event_queue=asyncio.Queue() if attach_event_queue else None,
            transport=transport,
            api_key=api_key,
            previous_response_id=payload.previous_response_id,
            session_id=_normalize_session_id(session_id),
            input_item_count=input_item_count,
            input_full_fingerprint=input_full_fingerprint,
        )
        text_data = json.dumps(upstream_payload, ensure_ascii=True, separators=(",", ":"))
        payload_size = len(text_data.encode("utf-8"))
        if payload_size > _UPSTREAM_RESPONSE_CREATE_MAX_BYTES:
            slimmed_payload, slim_summary = _slim_response_create_payload_for_upstream(
                upstream_payload,
                max_bytes=_UPSTREAM_RESPONSE_CREATE_MAX_BYTES,
            )
            if slim_summary is not None:
                upstream_payload = slimmed_payload
                text_data = json.dumps(upstream_payload, ensure_ascii=True, separators=(",", ":"))
                logger.warning(
                    (
                        "Slimmed response.create request_id=%s request_log_id=%s transport=%s "
                        "original_bytes=%s slimmed_bytes=%s "
                        "historical_tool_outputs_slimmed=%s historical_images_slimmed=%s"
                    ),
                    request_state.request_id,
                    request_state.request_log_id,
                    transport,
                    payload_size,
                    len(text_data.encode("utf-8")),
                    slim_summary["historical_tool_outputs_slimmed"],
                    slim_summary["historical_images_slimmed"],
                )
        request_state.request_text = text_data
        _enforce_response_create_size_limit(request_state)
        return request_state, text_data

    async def _acquire_request_state_response_create_admission(
        self,
        request_state: _WebSocketRequestState,
        *,
        response_create_gate: asyncio.Semaphore,
        bridge_session: "_HTTPBridgeSession | None" = None,
        compact: bool = False,
        account_id: str | None = None,
        surface: str = "websocket",
    ) -> None:
        timeout_seconds = _proxy_admission_wait_timeout_seconds()
        request_state.response_create_gate = response_create_gate
        if account_id is not None:
            request_state.account_response_create_lease = await self._acquire_account_response_create_lease_or_overload(
                account_id=account_id,
                request_id=request_state.request_id,
                surface=surface,
            )
            request_state.account_response_create_release = self._load_balancer.release_account_lease
        try:
            await asyncio.wait_for(response_create_gate.acquire(), timeout=timeout_seconds)
        except TimeoutError as exc:
            await self._release_request_state_account_response_create_lease(request_state)
            request_state.response_create_gate = None
            request_state.response_create_gate_acquired = False
            request_state.awaiting_response_created = False
            pending_count = None
            queued_count = None
            pending_request_ids: list[str] | None = None
            pending_request_ages_seconds: list[float] | None = None
            if bridge_session is not None:
                now = time.monotonic()
                async with bridge_session.pending_lock:
                    pending_states = list(bridge_session.pending_requests)
                    pending_count = len(pending_states)
                    queued_count = bridge_session.queued_request_count
                pending_request_ids = [state.request_log_id or state.request_id for state in pending_states]
                pending_request_ages_seconds = [max(0.0, now - state.started_at) for state in pending_states]
            _log_http_bridge_startup_wait_timeout(
                stage="response_create_gate",
                timeout_seconds=timeout_seconds,
                key=bridge_session.key if bridge_session is not None else None,
                request_id=request_state.request_id,
                request_model=request_state.model,
                pending_count=pending_count,
                queued_count=queued_count,
                available=getattr(response_create_gate, "_value", None),
                pending_request_ids=pending_request_ids,
                pending_request_ages_seconds=pending_request_ages_seconds,
            )
            raise _http_bridge_startup_wait_timeout_error(
                "http_bridge_response_create_gate",
                code="response_create_gate_timeout",
            ) from exc
        except BaseException:
            await self._release_request_state_account_response_create_lease(request_state)
            request_state.response_create_gate = None
            request_state.response_create_gate_acquired = False
            request_state.awaiting_response_created = False
            raise
        request_state.response_create_gate_acquired = True
        request_state.awaiting_response_created = True
        try:
            request_state.response_create_admission = await self._get_work_admission().acquire_response_create(
                compact=compact
            )
        except BaseException:
            await self._release_request_state_account_response_create_lease(request_state)
            await _release_websocket_response_create_gate(request_state, response_create_gate)
            raise

    async def _release_request_state_account_response_create_lease(
        self,
        request_state: "_WebSocketRequestState",
    ) -> None:
        lease = request_state.account_response_create_lease
        request_state.account_response_create_lease = None
        request_state.account_response_create_release = None
        await self._load_balancer.release_account_lease(lease)

    async def _select_account_with_budget_compatible(
        self,
        deadline: float,
        **kwargs: object,
    ) -> AccountSelection:
        select_account = self._select_account_with_budget
        select_account_any = cast(Any, select_account)
        try:
            signature = inspect.signature(select_account)
        except (TypeError, ValueError):
            return await select_account_any(deadline, **kwargs)

        if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()):
            return await select_account_any(deadline, **kwargs)

        supported_kwargs = {name: value for name, value in kwargs.items() if name in signature.parameters}
        return await select_account_any(deadline, **supported_kwargs)

    async def _select_codex_control_account_without_budget(
        self,
        *,
        affinity: _AffinityPolicy,
        api_key: ApiKeyData | None,
        traffic_class: TrafficClass = TRAFFIC_CLASS_FOREGROUND,
        prefer_earlier_reset_window: ResetPreferenceWindow = "secondary",
    ) -> Account | None:
        scoped_account_ids = (
            set(api_key.assigned_account_ids)
            if api_key is not None and api_key.account_assignment_scope_enabled
            else None
        )
        settings = await get_settings_cache().get()
        if _routing_strategy(settings) == "single_account":
            selected_account_id = (settings.single_account_id or "").strip()
            if not selected_account_id:
                return None
            if scoped_account_ids is not None and selected_account_id not in scoped_account_ids:
                return None
            scoped_account_ids = {selected_account_id}
        selection = await self._load_balancer.select_account(
            sticky_key=affinity.key,
            sticky_kind=affinity.kind,
            reallocate_sticky=affinity.reallocate_sticky,
            sticky_max_age_seconds=affinity.max_age_seconds,
            account_ids=scoped_account_ids,
            prefer_earlier_reset_window=prefer_earlier_reset_window,
            routing_strategy=_routing_strategy(settings),
            budget_threshold_pct=_sticky_reallocation_primary_budget_threshold_pct(settings),
            secondary_budget_threshold_pct=_sticky_reallocation_secondary_budget_threshold_pct(settings),
            traffic_class=traffic_class,
        )
        if selection.account is None:
            return None
        return _detached_account_copy(selection.account)

    @asynccontextmanager
    async def _accounts_refresh_scope(self) -> AsyncIterator[AccountsRepositoryPort]:
        # Fresh, self-contained accounts repo (own DB session) for AuthManager's
        # detached/shielded token-refresh task. A client disconnect cancels the
        # request and closes the request-scoped session below; without this the
        # still-running refresh task would touch that closed session and strand
        # a background-pool connection (the codex-lb pool-exhaustion leak).
        async with self._repo_factory() as repos:
            yield repos.accounts

    async def _ensure_fresh(
        self,
        account: Account,
        *,
        force: bool = False,
        timeout_seconds: float | None = None,
    ) -> Account:
        token = push_token_refresh_timeout_override(timeout_seconds)
        try:
            async with self._repo_factory() as repos:
                auth_manager = AuthManager(
                    repos.accounts,
                    acquire_refresh_admission=self._get_work_admission().acquire_token_refresh,
                    refresh_repo_factory=self._accounts_refresh_scope,
                )
                return await auth_manager.ensure_fresh(account, force=force)
        finally:
            pop_token_refresh_timeout_override(token)

    async def _ensure_fresh_with_budget(
        self,
        account: Account,
        *,
        force: bool = False,
        timeout_seconds: float | None = None,
    ) -> Account:
        try:
            return await self._ensure_fresh(account, force=force, timeout_seconds=timeout_seconds)
        except RefreshError as exc:
            reason = _refresh_upstream_proxy_fail_closed_reason(exc)
            if reason is not None:
                raise UpstreamProxyRouteError(reason, account_id=account.id) from exc
            raise

    async def _ensure_previsible_unary_fresh_with_failover(
        self,
        account: Account,
        *,
        deadline: float,
        request_id: str,
        kind: str,
        select_next_account: Callable[[set[str]], Awaitable[AccountSelection]],
        strict_account_id: str | None = None,
        force: bool = False,
        max_account_attempts: int = 2,
    ) -> Account:
        current: Account = account
        excluded_account_ids: set[str] = set()
        attempt = 0
        force_current = force
        while True:
            attempt += 1
            remaining_budget = _remaining_budget_seconds(deadline)
            if remaining_budget <= 0:
                logger.warning(
                    "%s request budget exhausted before freshness check request_id=%s account_id=%s",
                    kind,
                    request_id,
                    current.id,
                )
                _raise_proxy_budget_exhausted()
            try:
                return await self._ensure_fresh_with_budget(
                    current,
                    force=force_current,
                    timeout_seconds=remaining_budget,
                )
            except RefreshError as exc:
                if exc.transport_error:
                    message = exc.message or str(exc) or "Request to upstream timed out"
                    logger.warning(
                        "%s refresh transport failed request_id=%s account_id=%s",
                        kind,
                        request_id,
                        current.id,
                        exc_info=True,
                    )
                    if not _should_retry_transient_stream_error("upstream_unavailable", message):
                        _raise_proxy_unavailable_for_account(message, current)
                    if (
                        strict_account_id is not None and current.id == strict_account_id
                    ) or attempt >= max_account_attempts:
                        _raise_proxy_unavailable_for_account(message, current)
                    excluded_account_ids.add(current.id)
                    selection = await select_next_account(excluded_account_ids)
                    selected_account = selection.account
                    if selected_account is None:
                        _raise_proxy_unavailable_for_account(message, current)
                    assert selected_account is not None
                    await self._handle_stream_error(
                        current,
                        {"message": message},
                        "upstream_unavailable",
                    )
                    current = selected_account
                    force_current = False
                    continue
                setattr(exc, _FAILED_ACCOUNT_ATTR, current)
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                message = str(exc) or "Request to upstream timed out"
                logger.warning(
                    "%s refresh/connect failed request_id=%s account_id=%s",
                    kind,
                    request_id,
                    current.id,
                    exc_info=True,
                )
                if not _should_retry_transient_stream_error("upstream_unavailable", message):
                    _raise_proxy_unavailable_for_account(message, current)
                if (
                    strict_account_id is not None and current.id == strict_account_id
                ) or attempt >= max_account_attempts:
                    _raise_proxy_unavailable_for_account(message, current)
                excluded_account_ids.add(current.id)
                selection = await select_next_account(excluded_account_ids)
                selected_account = selection.account
                if selected_account is None:
                    _raise_proxy_unavailable_for_account(message, current)
                assert selected_account is not None
                await self._handle_stream_error(
                    current,
                    {"message": message},
                    "upstream_unavailable",
                )
                current = selected_account
                force_current = False

    async def _retry_previsible_unary_call_failover(
        self,
        exc: ProxyResponseError,
        account: Account,
        *,
        deadline: float,
        select_next_account: Callable[[set[str]], Awaitable[AccountSelection]],
        call_next: Callable[[Account], Awaitable[Any]],
        strict_account_id: str | None = None,
    ) -> tuple[Account, Any] | None:
        if hasattr(exc, _FAILED_ACCOUNT_ATTR):
            return None
        if not _should_failover_previsible_unary_proxy_error(exc):
            return None
        failed_account = _proxy_response_failed_account(exc, account)
        if strict_account_id is not None and failed_account.id == strict_account_id:
            return None
        selection = await select_next_account({failed_account.id})
        if selection.account is None:
            return None
        await self._handle_proxy_error(failed_account, exc)
        try:
            next_account = await self._ensure_fresh_with_budget_or_auth_error(
                selection.account,
                timeout_seconds=_remaining_budget_seconds(deadline),
            )
        except ProxyResponseError as failover_exc:
            failover_failed_account = _proxy_response_failed_account(failover_exc, selection.account)
            setattr(failover_exc, _FAILED_ACCOUNT_ATTR, failover_failed_account)
            if failover_exc.status_code != 401:
                await self._handle_proxy_error(failover_failed_account, failover_exc)
            raise
        try:
            result = await call_next(next_account)
        except ProxyResponseError as failover_exc:
            failover_failed_account = _proxy_response_failed_account(failover_exc, next_account)
            setattr(failover_exc, _FAILED_ACCOUNT_ATTR, failover_failed_account)
            if failover_exc.status_code == 401:
                remaining_budget = _remaining_budget_seconds(deadline)
                if remaining_budget <= 0:
                    _raise_proxy_budget_exhausted()
                try:
                    refreshed_account = await self._ensure_fresh_with_budget_or_auth_error(
                        next_account,
                        force=True,
                        timeout_seconds=remaining_budget,
                    )
                except ProxyResponseError as refresh_exc:
                    refresh_failed_account = _proxy_response_failed_account(refresh_exc, next_account)
                    setattr(refresh_exc, _FAILED_ACCOUNT_ATTR, refresh_failed_account)
                    if refresh_exc.status_code != 401:
                        await self._handle_proxy_error(refresh_failed_account, refresh_exc)
                    raise
                try:
                    retry_result = await call_next(refreshed_account)
                except ProxyResponseError as retry_exc:
                    retry_failed_account = _proxy_response_failed_account(retry_exc, refreshed_account)
                    setattr(retry_exc, _FAILED_ACCOUNT_ATTR, retry_failed_account)
                    await self._handle_proxy_error(retry_failed_account, retry_exc)
                    raise
                await self._load_balancer.record_success(refreshed_account)
                return refreshed_account, retry_result
            await self._handle_proxy_error(failover_failed_account, failover_exc)
            raise
        await self._load_balancer.record_success(next_account)
        return next_account, result

    async def _ensure_fresh_with_budget_or_auth_error(
        self,
        account: Account,
        *,
        force: bool = False,
        timeout_seconds: float | None = None,
        error_type: str = "invalid_request_error",
    ) -> Account:
        try:
            return await self._ensure_fresh_with_budget(account, force=force, timeout_seconds=timeout_seconds)
        except RefreshError as refresh_exc:
            failed_account = _refresh_error_failed_account(refresh_exc, account)
            if refresh_exc.transport_error:
                _raise_proxy_unavailable_for_account(
                    refresh_exc.message or str(refresh_exc) or "Request to upstream timed out",
                    failed_account,
                )
            if refresh_exc.is_permanent:
                await self._load_balancer.mark_permanent_failure(failed_account, refresh_exc.code)
            raise ProxyResponseError(
                401,
                openai_error(
                    "invalid_api_key",
                    refresh_exc.message,
                    error_type=error_type,
                ),
            ) from refresh_exc
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            _raise_proxy_unavailable(str(exc) or "Request to upstream timed out")

    async def _select_account_with_budget(
        self,
        deadline: float,
        *,
        request_id: str,
        kind: str,
        request_stage: str = "first_turn",
        api_key: ApiKeyData | None = None,
        sticky_key: str | None = None,
        sticky_kind: StickySessionKind | None = None,
        reallocate_sticky: bool = False,
        sticky_max_age_seconds: int | None = None,
        sticky_budget_reallocation_enabled: bool = True,
        prefer_earlier_reset_accounts: bool = False,
        prefer_earlier_reset_window: ResetPreferenceWindow = "secondary",
        routing_strategy: RoutingStrategy = "capacity_weighted",
        model: str | None = None,
        additional_limit_name: str | None = None,
        exclude_account_ids: Collection[str] | None = None,
        preferred_account_id: str | None = None,
        require_security_work_authorized: bool = False,
        lease_kind: Literal["response_create", "stream"] | None = None,
        estimated_lease_tokens: float = 0.0,
        fallback_on_preferred_account_unavailable: bool = True,
        traffic_class: TrafficClass = TRAFFIC_CLASS_FOREGROUND,
    ) -> AccountSelection:
        remaining_budget = _remaining_budget_seconds(deadline)
        if remaining_budget <= 0:
            logger.warning(
                "%s request budget exhausted before account selection request_id=%s", kind.title(), request_id
            )
            _raise_proxy_budget_exhausted()
        scoped_account_ids = (
            set(api_key.assigned_account_ids)
            if api_key is not None and api_key.account_assignment_scope_enabled
            else None
        )
        effective_traffic_class = (
            TRAFFIC_CLASS_OPPORTUNISTIC
            if api_key is not None and api_key.traffic_class == TRAFFIC_CLASS_OPPORTUNISTIC
            else traffic_class
        )
        excluded_account_ids_set = set(exclude_account_ids or ())
        logger.info(
            "Proxy account selection start request_id=%s kind=%s request_stage=%s model=%s "
            "additional_limit=%s sticky=%s sticky_kind=%s reallocate_sticky=%s prefer_earlier_reset=%s "
            "routing_strategy=%s api_key_present=%s api_key_scope_enabled=%s scoped_count=%s "
            "excluded_count=%s preferred_account_id=%s remaining_budget=%.2f",
            request_id,
            kind,
            request_stage,
            model,
            additional_limit_name,
            bool(sticky_key),
            sticky_kind.value if sticky_kind is not None else None,
            reallocate_sticky,
            prefer_earlier_reset_accounts,
            routing_strategy,
            api_key is not None,
            bool(api_key is not None and api_key.account_assignment_scope_enabled),
            None if scoped_account_ids is None else len(scoped_account_ids),
            len(excluded_account_ids_set),
            preferred_account_id,
            remaining_budget,
        )
        try:
            with anyio.fail_after(remaining_budget):
                settings = await get_settings_cache().get()
                required_preferred_account = (
                    preferred_account_id is not None and not fallback_on_preferred_account_unavailable
                )
                if _routing_strategy(settings) == "single_account" and not required_preferred_account:
                    selected_account_id = (settings.single_account_id or "").strip()
                    if not selected_account_id:
                        return AccountSelection(
                            account=None,
                            error_message="Single account routing is enabled but no account is selected",
                            error_code="single_account_not_configured",
                        )
                    if selected_account_id in excluded_account_ids_set:
                        return AccountSelection(
                            account=None,
                            error_message="Selected single account is unavailable",
                            error_code="single_account_unavailable",
                        )
                    if scoped_account_ids is not None and selected_account_id not in scoped_account_ids:
                        return AccountSelection(
                            account=None,
                            error_message="Selected single account is outside the API key account scope",
                            error_code="single_account_scope_mismatch",
                        )
                    scoped_account_ids = {selected_account_id}
                    routing_strategy = "single_account"
                preferred_eligible = (
                    preferred_account_id is not None
                    and preferred_account_id not in excluded_account_ids_set
                    and (scoped_account_ids is None or preferred_account_id in scoped_account_ids)
                )
                if preferred_account_id is not None and not preferred_eligible:
                    logger.warning(
                        "Proxy preferred account skipped request_id=%s kind=%s request_stage=%s "
                        "preferred_account_id=%s excluded=%s outside_api_key_scope=%s",
                        request_id,
                        kind,
                        request_stage,
                        preferred_account_id,
                        preferred_account_id in excluded_account_ids_set,
                        scoped_account_ids is not None and preferred_account_id not in scoped_account_ids,
                    )
                    if not fallback_on_preferred_account_unavailable:
                        return AccountSelection(
                            account=None,
                            error_message="Preferred account is not available",
                            error_code="preferred_account_unavailable",
                        )
                if preferred_eligible:
                    preferred_selection = await self._load_balancer.select_account(
                        sticky_key=sticky_key,
                        sticky_kind=sticky_kind,
                        reallocate_sticky=reallocate_sticky,
                        sticky_max_age_seconds=sticky_max_age_seconds,
                        sticky_budget_reallocation_enabled=sticky_budget_reallocation_enabled,
                        prefer_earlier_reset_accounts=prefer_earlier_reset_accounts,
                        prefer_earlier_reset_window=prefer_earlier_reset_window,
                        routing_strategy=routing_strategy,
                        relative_availability_power=_relative_availability_power(settings),
                        relative_availability_top_k=_relative_availability_top_k(settings),
                        model=model,
                        additional_limit_name=additional_limit_name,
                        account_ids={preferred_account_id},
                        require_security_work_authorized=require_security_work_authorized,
                        budget_threshold_pct=_sticky_reallocation_primary_budget_threshold_pct(settings),
                        secondary_budget_threshold_pct=_sticky_reallocation_secondary_budget_threshold_pct(settings),
                        lease_kind=lease_kind,
                        estimated_lease_tokens=estimated_lease_tokens,
                        traffic_class=effective_traffic_class,
                    )
                    if preferred_selection.account is not None:
                        logger.info(
                            "Selected preferred account request_id=%s kind=%s request_stage=%s account_id=%s",
                            request_id,
                            kind,
                            request_stage,
                            preferred_account_id,
                        )
                        return preferred_selection
                    if not fallback_on_preferred_account_unavailable:
                        logger.warning(
                            "Proxy preferred account unavailable request_id=%s kind=%s request_stage=%s "
                            "preferred_account_id=%s error_code=%s error=%s",
                            request_id,
                            kind,
                            request_stage,
                            preferred_account_id,
                            preferred_selection.error_code,
                            preferred_selection.error_message,
                        )
                        return preferred_selection
                selection = await self._load_balancer.select_account(
                    sticky_key=sticky_key,
                    sticky_kind=sticky_kind,
                    reallocate_sticky=reallocate_sticky,
                    sticky_max_age_seconds=sticky_max_age_seconds,
                    sticky_budget_reallocation_enabled=sticky_budget_reallocation_enabled,
                    prefer_earlier_reset_accounts=prefer_earlier_reset_accounts,
                    prefer_earlier_reset_window=prefer_earlier_reset_window,
                    routing_strategy=routing_strategy,
                    relative_availability_power=_relative_availability_power(settings),
                    relative_availability_top_k=_relative_availability_top_k(settings),
                    model=model,
                    additional_limit_name=additional_limit_name,
                    account_ids=scoped_account_ids,
                    exclude_account_ids=excluded_account_ids_set,
                    require_security_work_authorized=require_security_work_authorized,
                    budget_threshold_pct=_sticky_reallocation_primary_budget_threshold_pct(settings),
                    secondary_budget_threshold_pct=_sticky_reallocation_secondary_budget_threshold_pct(settings),
                    lease_kind=lease_kind,
                    estimated_lease_tokens=estimated_lease_tokens,
                    traffic_class=effective_traffic_class,
                )
                if selection.account is not None and selection.account.id in excluded_account_ids_set:
                    logger.warning(
                        "Proxy account selection returned excluded account request_id=%s kind=%s request_stage=%s "
                        "account_id=%s excluded_count=%s",
                        request_id,
                        kind,
                        request_stage,
                        selection.account.id,
                        len(excluded_account_ids_set),
                    )
                    return AccountSelection(
                        account=None,
                        error_message="No active accounts available",
                        error_code="no_accounts",
                    )
                logger.info(
                    "Proxy account selection result request_id=%s kind=%s request_stage=%s model=%s "
                    "selected_account_id=%s error_code=%s error=%s scoped_count=%s excluded_count=%s",
                    request_id,
                    kind,
                    request_stage,
                    model,
                    selection.account.id if selection.account is not None else None,
                    selection.error_code,
                    selection.error_message,
                    None if scoped_account_ids is None else len(scoped_account_ids),
                    len(excluded_account_ids_set),
                )
                return selection
        except TimeoutError:
            logger.warning("%s account selection exceeded request budget request_id=%s", kind.title(), request_id)
            _raise_proxy_budget_exhausted()

    async def _acquire_account_response_create_lease_or_overload(
        self,
        *,
        account_id: str,
        request_id: str,
        surface: str,
    ) -> AccountLease:
        lease = await self._load_balancer.acquire_account_lease(
            account_id,
            kind="response_create",
        )
        if lease is not None:
            return lease
        inflight_create, inflight_stream, leased_tokens = await self._load_balancer.account_pressure_snapshot(
            account_id
        )
        logger.warning(
            "Responses account response-create cap reached request_id=%s surface=%s account_id=%s "
            "inflight_create=%s inflight_stream=%s leased_tokens=%.3f",
            request_id,
            surface,
            account_id,
            inflight_create,
            inflight_stream,
            leased_tokens,
        )
        raise ProxyResponseError(
            429,
            openai_error(
                "account_response_create_cap",
                "Account response-create capacity is exhausted",
                error_type="rate_limit_error",
            ),
        )

    async def check_opportunistic_admission(
        self,
        *,
        api_key: ApiKeyData | None,
        model: str | None,
        lease_kind: AccountLeaseKind | None = None,
    ) -> AccountSelection:
        settings = await get_settings_cache().get()
        scoped_account_ids = (
            set(api_key.assigned_account_ids)
            if api_key is not None and api_key.account_assignment_scope_enabled
            else None
        )
        if _routing_strategy(settings) == "single_account":
            selected_account_id = (settings.single_account_id or "").strip()
            if selected_account_id:
                scoped_account_ids = (
                    {selected_account_id}
                    if scoped_account_ids is None or selected_account_id in scoped_account_ids
                    else set()
                )
            else:
                scoped_account_ids = set()
        return await self._load_balancer.check_opportunistic_admission(
            model=model,
            account_ids=scoped_account_ids,
            prefer_earlier_reset_accounts=settings.prefer_earlier_reset_accounts,
            prefer_earlier_reset_window=_prefer_earlier_reset_window(settings),
            routing_strategy=_routing_strategy(settings),
            budget_threshold_pct=_sticky_reallocation_primary_budget_threshold_pct(settings),
            secondary_budget_threshold_pct=_sticky_reallocation_secondary_budget_threshold_pct(settings),
            lease_kind=lease_kind,
        )

    async def _handle_proxy_error(self, account: Account, exc: ProxyResponseError) -> None:
        error = _parse_openai_error(exc.payload)
        code = _normalize_error_code(
            error.code if error else None,
            error.type if error else None,
        )
        if _is_account_neutral_error_code(code):
            return
        await self._handle_stream_error(
            account,
            _upstream_error_from_openai(error),
            code,
            http_status=exc.status_code,
        )


def _is_account_neutral_error_code(code: str | None) -> bool:
    return is_local_overload_error_code(code) or code == "proxy_unavailable"


def _is_local_account_cap_code(code: str | None) -> bool:
    return code in {"account_response_create_cap", "account_stream_cap"}


def _http_error_status_from_payload(payload: dict[str, JsonValue] | None) -> int | None:
    if not isinstance(payload, dict):
        return None
    for status_field in ("status", "status_code"):
        status = payload.get(status_field)
        if isinstance(status, int) and not isinstance(status, bool):
            return status
    return None


def _openai_error_envelope_from_response_failed_payload(
    payload: dict[str, JsonValue] | None,
) -> OpenAIErrorEnvelope:
    default_envelope = openai_error("upstream_error", "Upstream error")
    if not isinstance(payload, dict):
        return default_envelope
    response_payload = payload.get("response")
    if not isinstance(response_payload, dict):
        return default_envelope
    error_payload = response_payload.get("error")
    if not isinstance(error_payload, dict):
        return default_envelope

    message_value = error_payload.get("message")
    if isinstance(message_value, str) and message_value.strip():
        message = message_value.strip()
    else:
        message = "Upstream error"

    code_value = error_payload.get("code")
    code = code_value.strip() if isinstance(code_value, str) and code_value.strip() else "upstream_error"

    type_value = error_payload.get("type")
    error_type = type_value.strip() if isinstance(type_value, str) and type_value.strip() else "server_error"

    envelope = openai_error(code, message, error_type)
    param_value = error_payload.get("param")
    if isinstance(param_value, str) and param_value.strip():
        envelope["error"]["param"] = param_value.strip()
    error_detail = envelope["error"]
    plan_type = error_payload.get("plan_type")
    if plan_type is not None:
        error_detail["plan_type"] = str(plan_type)
    resets_at = error_payload.get("resets_at")
    if isinstance(resets_at, int | float):
        error_detail["resets_at"] = resets_at
    resets_in = error_payload.get("resets_in_seconds")
    if isinstance(resets_in, int | float):
        error_detail["resets_in_seconds"] = resets_in
    return envelope


def _is_previous_response_not_found_message(message: str | None) -> bool:
    return is_previous_response_not_found_message(message)


def _previous_response_id_from_not_found_message(message: str | None) -> str | None:
    return previous_response_id_from_not_found_message(message)


def _message_mentions_previous_response_id(message: str | None, previous_response_id: str | None) -> bool:
    if message is None or previous_response_id is None:
        return False
    normalized_message = " ".join(message.split())
    normalized_previous_response_id = previous_response_id.strip()
    if not normalized_previous_response_id:
        return False
    identifier_pattern = re.escape(normalized_previous_response_id)
    return (
        re.search(
            rf"(?<![A-Za-z0-9_-]){identifier_pattern}(?![A-Za-z0-9_-])",
            normalized_message,
        )
        is not None
    )


def _normalize_session_id(session_id: str | None) -> str | None:
    if not isinstance(session_id, str):
        return None
    stripped = session_id.strip()
    return stripped or None


def _is_missing_tool_output_error(
    *,
    code: str | None,
    param: str | None,
    message: str | None,
) -> bool:
    if code != "invalid_request_error" or param != "input" or message is None:
        return False
    normalized = " ".join(message.lower().split())
    return normalized.startswith("no tool output found for function call call_")


def _is_previous_response_not_found_error(
    *,
    code: str | None,
    param: str | None,
    message: str | None,
) -> bool:
    return is_previous_response_not_found_error(code=code, param=param, message=message)


def _compact_previous_response_not_found_error(exc: ProxyResponseError) -> ProxyResponseError | None:
    error = _parse_openai_error(exc.payload)
    if error is None:
        return None
    code = _normalize_error_code(error.code, error.type)
    if not _is_previous_response_not_found_error(
        code=code,
        param=error.param,
        message=error.message,
    ):
        return None
    return ProxyResponseError(
        502,
        previous_response_stream_incomplete_error(),
        failure_phase=exc.failure_phase,
        retryable_same_contract=False,
        failure_detail="previous_response_not_found",
        failure_exception_type=exc.failure_exception_type,
        upstream_status_code=exc.upstream_status_code if exc.upstream_status_code is not None else exc.status_code,
        upstream_error_code=code,
    )


def _proxy_response_error_code(exc: ProxyResponseError) -> str | None:
    error = _parse_openai_error(exc.payload)
    if error is None:
        return None
    return _normalize_error_code(error.code, error.type)


_LOCAL_PROXY_ERROR_CODES = frozenset(
    {
        "bridge_owner_forward_failed",
        "bridge_instance_mismatch",
        "bridge_owner_unreachable",
        "preferred_account_unavailable",
        "previous_response_owner_unavailable",
        "insufficient_image_quota",
        "ip_forbidden",
        "no_accounts",
        "no_plan_support_for_model",
        "additional_quota_data_unavailable",
        "no_additional_quota_eligible_accounts",
        "payload_too_large",
        "proxy_overloaded",
        "upstream_request_timeout",
        "upstream_unavailable",
    }
)


def _request_log_failure_metadata(
    exc: ProxyResponseError,
    *,
    bridge_stage: str | None = None,
) -> _RequestLogFailureMetadata:
    upstream_error_code = exc.upstream_error_code or _proxy_response_error_code(exc)
    resolved_bridge_stage = bridge_stage
    if resolved_bridge_stage is None and (
        exc.failure_phase in {"owner_forward", "owner_forward_status"}
        or upstream_error_code in {"bridge_owner_unreachable", "bridge_owner_forward_failed"}
    ):
        resolved_bridge_stage = "owner_forward"
    upstream_status_code = exc.upstream_status_code
    if upstream_status_code is None and _should_infer_upstream_status_from_proxy_error(exc, upstream_error_code):
        upstream_status_code = exc.status_code
    return _RequestLogFailureMetadata(
        failure_phase=exc.failure_phase,
        failure_detail=exc.failure_detail,
        failure_exception_type=exc.failure_exception_type,
        upstream_status_code=upstream_status_code,
        upstream_error_code=upstream_error_code,
        bridge_stage=resolved_bridge_stage,
    )


def _previous_response_id_from_payload(payload: Mapping[str, JsonValue] | None) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    previous_response_id = payload.get("previous_response_id")
    if isinstance(previous_response_id, str) and previous_response_id.strip():
        return previous_response_id.strip()
    return None


def _partial_output_proxy_error_event_block(
    exc: ProxyResponseError,
    *,
    response_id: str,
    previous_response_id: str | None,
    preferred_account_id: str | None,
    default_code: str,
    default_message: str,
) -> str:
    error = _parse_openai_error(exc.payload)
    error_code = _normalize_error_code(
        error.code if error else None,
        error.type if error else None,
    )
    error_message = error.message if error else None
    effective_previous_response_id = previous_response_id or _previous_response_id_from_not_found_message(
        error_message,
    )
    rewritten_error = _rewrite_previous_response_stream_error(
        previous_response_id=effective_previous_response_id,
        preferred_account_id=preferred_account_id,
        error_code=error_code,
        error_type=error.type if error else None,
        error_message=error_message,
        error_param=error.param if error else None,
    )
    if rewritten_error is not None:
        rewritten_code, rewritten_message, upstream_error_code = rewritten_error
        if upstream_error_code is None:
            event = response_failed_event(
                rewritten_code,
                rewritten_message,
                error_type="server_error",
                response_id=response_id,
            )
            return format_sse_event(event)
    event = response_failed_event(
        error_code or default_code,
        error_message or default_message,
        error_type=(error.type if error and error.type else "server_error"),
        response_id=response_id,
        error_param=error.param if error else None,
    )
    _apply_error_metadata(event["response"]["error"], error)
    return format_sse_event(event)


def _routing_strategy(settings: DashboardSettings) -> RoutingStrategy:
    value = getattr(settings, "routing_strategy", None) or "capacity_weighted"
    if value == "single_account":
        return "single_account"
    if value == "sequential_drain":
        return "sequential_drain"
    if value == "reset_drain":
        return "reset_drain"
    if value == "round_robin":
        return "round_robin"
    if value == "usage_weighted":
        return "usage_weighted"
    if value == "relative_availability":
        return "relative_availability"
    if value == "fill_first":
        return "fill_first"
    return "capacity_weighted"


async def _call_with_supported_optional_kwargs(
    func: Callable[..., Awaitable[Any]],
    /,
    *args: Any,
    optional_kwargs: Mapping[str, Any],
    **required_kwargs: Any,
) -> Any:
    return await func(*args, **_supported_optional_kwargs(func, optional_kwargs, required_kwargs))


def _supported_optional_kwargs(
    func: Callable[..., Any],
    optional_kwargs: Mapping[str, Any],
    required_kwargs: Mapping[str, Any],
) -> dict[str, Any]:
    kwargs = dict(required_kwargs)
    kwargs.update(optional_kwargs)
    if optional_kwargs:
        try:
            signature = inspect.signature(func)
        except (TypeError, ValueError):
            signature = None
        accepts_var_keyword = signature is not None and any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()
        )
        if signature is not None and not accepts_var_keyword:
            for name in optional_kwargs:
                if name not in signature.parameters:
                    kwargs.pop(name, None)
    return kwargs


def _relative_availability_power(settings: DashboardSettings) -> float:
    raw_value = getattr(settings, "relative_availability_power", None)
    value = float(raw_value) if raw_value is not None else 2.0
    return value if value > 0.0 else 2.0


def _relative_availability_top_k(settings: DashboardSettings) -> int:
    raw_value = getattr(settings, "relative_availability_top_k", None)
    value = int(raw_value) if raw_value is not None else 5
    return min(max(value, 1), 20)


def _prefer_earlier_reset_window(settings: DashboardSettings) -> ResetPreferenceWindow:
    return "primary" if getattr(settings, "prefer_earlier_reset_window", None) == "primary" else "secondary"


def _sticky_reallocation_primary_budget_threshold_pct(settings: DashboardSettings) -> float:
    value = getattr(settings, "sticky_reallocation_primary_budget_threshold_pct", None)
    if value is None:
        value = getattr(settings, "sticky_reallocation_budget_threshold_pct", None)
    return float(value if value is not None else 95.0)


def _sticky_reallocation_secondary_budget_threshold_pct(settings: DashboardSettings) -> float:
    value = getattr(settings, "sticky_reallocation_secondary_budget_threshold_pct", None)
    return float(value if value is not None else 100.0)


def _remaining_budget_seconds(deadline: float) -> float:
    return max(0.0, deadline - time.monotonic())


def _proxy_request_timeout_event(request_id: str) -> ResponseFailedEvent:
    return response_failed_event(
        "upstream_request_timeout",
        "Proxy request budget exhausted",
        response_id=request_id,
    )


def _security_work_advisory_event(
    *,
    code: str,
    message: str,
    request_id: str | None,
    action: str,
    account_id: str | None = None,
) -> dict[str, JsonValue]:
    warning: dict[str, JsonValue] = {
        "code": code,
        "message": message,
        "category": "security_work_authorization",
        "action": action,
    }
    if request_id:
        warning["request_id"] = request_id
    if account_id:
        warning["account_id"] = account_id
    return {
        "type": "codex_lb.warning",
        "warning": warning,
    }


def _is_security_work_authorization_required_error(code: str | None, message: str | None) -> bool:
    normalized_code = (code or "").strip().lower()
    if normalized_code == _SECURITY_WORK_AUTHORIZATION_REQUIRED_CODE:
        return True
    normalized_message = (message or "").strip().lower()
    if not normalized_message:
        return False
    return all(hint in normalized_message for hint in _SECURITY_WORK_AUTHORIZATION_REQUIRED_HINTS)


def _raise_proxy_budget_exhausted() -> NoReturn:
    raise ProxyResponseError(
        502,
        openai_error("upstream_request_timeout", "Proxy request budget exhausted"),
    )


def _raise_proxy_unavailable(message: str) -> NoReturn:
    raise ProxyResponseError(
        502,
        openai_error("upstream_unavailable", message),
    )


_FAILED_ACCOUNT_ATTR = "_codex_lb_failed_account"


def _raise_proxy_unavailable_for_account(message: str, account: Account) -> NoReturn:
    exc = ProxyResponseError(
        502,
        openai_error("upstream_unavailable", message),
    )
    setattr(exc, _FAILED_ACCOUNT_ATTR, account)
    raise exc


def _proxy_response_failed_account(exc: ProxyResponseError, fallback: Account) -> Account:
    account = getattr(exc, _FAILED_ACCOUNT_ATTR, None)
    return account if isinstance(account, Account) else fallback


def _refresh_error_failed_account(exc: RefreshError, fallback: Account) -> Account:
    account = getattr(exc, _FAILED_ACCOUNT_ATTR, None)
    return account if isinstance(account, Account) else fallback


def _should_failover_previsible_unary_proxy_error(exc: ProxyResponseError) -> bool:
    if exc.failure_phase != "connect":
        return False
    error = _parse_openai_error(exc.payload)
    error_code = _normalize_error_code(error.code if error else None, error.type if error else None)
    error_message = error.message if error else None
    return error_code == "upstream_unavailable" and _should_retry_transient_stream_error(
        "upstream_unavailable",
        error_message,
    )


def _is_proxy_budget_exhausted_error(exc: ProxyResponseError) -> bool:
    error = _parse_openai_error(exc.payload)
    error_code = _normalize_error_code(error.code if error else None, error.type if error else None)
    error_message = error.message if error else None
    return error_code in {"upstream_request_timeout", "upstream_unavailable"} and (
        error_message == "Proxy request budget exhausted"
    )


def _should_suppress_text_done_event(
    *,
    event_type: str | None,
    payload: dict[str, JsonValue] | None,
    suppress_text_done_events: bool,
    saw_text_delta: bool,
) -> bool:
    if not suppress_text_done_events or not saw_text_delta or event_type is None:
        return False
    if event_type == "response.output_text.done":
        return True
    if event_type == "response.content_part.done":
        return _is_text_content_part(payload)
    return False


def _is_text_content_part(payload: dict[str, JsonValue] | None) -> bool:
    if payload is None:
        return False
    part = payload.get("part")
    if not isinstance(part, dict):
        return False
    part_type = part.get("type")
    return isinstance(part_type, str) and part_type in _TEXT_DONE_CONTENT_PART_TYPES


def _input_prefix_matches_stored_context(
    input_value: JsonValue,
    *,
    stored_count: int,
    stored_fingerprint: str | None,
) -> bool:
    if stored_count <= 0 or stored_fingerprint is None:
        return False
    if not isinstance(input_value, list):
        return False
    if len(input_value) <= stored_count:
        return False
    return _fingerprint_input_items(cast(list[JsonValue], input_value)[:stored_count]) == stored_fingerprint


def _is_missing_thread_goal_protocol_error(exc: ProxyResponseError) -> bool:
    if exc.status_code not in {404, 405}:
        return False
    error = _parse_openai_error(exc.payload)
    code = _normalize_error_code(
        error.code if error else None,
        error.type if error else None,
    )
    message = (error.message if error and error.message else "").strip().lower()
    if exc.status_code == 404:
        return code == "not_found" and message == "not found"
    return code == "method_not_allowed" and message == "method not allowed"


def _detached_account_copy(account: Account) -> Account:
    data = {column.name: getattr(account, column.name) for column in Account.__table__.columns}
    return Account(**data)


def _sticky_key_from_session_header(headers: Mapping[str, str]) -> str | None:
    normalized = {key.lower(): value for key, value in headers.items()}
    for key in ("session_id", "x-codex-session-id", "x-codex-conversation-id"):
        value = normalized.get(key)
        if not isinstance(value, str):
            continue
        stripped = value.strip()
        if stripped:
            return stripped
    return None


def _sticky_key_from_turn_state_header(headers: Mapping[str, str]) -> str | None:
    normalized = {key.lower(): value for key, value in headers.items()}
    value = normalized.get("x-codex-turn-state")
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _owner_lookup_session_id_from_headers(headers: Mapping[str, str]) -> str | None:
    # `x-codex-turn-state` is per conversation turn/thread and is more specific
    # than `session_id`, which may be shared across multiple terminals.
    turn_state = _sticky_key_from_turn_state_header(headers)
    if turn_state is not None:
        return turn_state
    return _sticky_key_from_session_header(headers)


# Pattern matching turn-state values synthesized by the helpers below.
# A 32-char lowercase hex (uuid4().hex) suffix follows the prefix.
_SYNTHESIZED_TURN_STATE_PATTERN = re.compile(r"^(?:http_)?turn_[0-9a-f]{32}$")


def _is_synthesized_turn_state(value: str) -> bool:
    """True when ``value`` matches a turn-state synthesized by codex-lb itself.

    Used by the file-pin resolver to distinguish a client-supplied
    continuation marker from a synthesizer-generated placeholder so
    first-turn upload-then-converse requests still benefit from
    file_id pin routing on the websocket / HTTP entry points.
    """
    return bool(_SYNTHESIZED_TURN_STATE_PATTERN.match(value))


def ensure_downstream_turn_state(headers: Mapping[str, str]) -> str:
    existing = _sticky_key_from_turn_state_header(headers)
    if existing is not None:
        return existing
    return f"turn_{uuid4().hex}"


def _platform_error_code(payload: Mapping[str, JsonValue]) -> str | None:
    error = payload.get("error")
    if not is_json_mapping(error):
        return None
    code = error.get("code")
    return code if isinstance(code, str) else None


def _platform_error_message(payload: Mapping[str, JsonValue]) -> str | None:
    error = payload.get("error")
    if not is_json_mapping(error):
        return None
    message = error.get("message")
    return message if isinstance(message, str) else None


def ensure_http_downstream_turn_state(headers: Mapping[str, str]) -> str:
    existing = _sticky_key_from_turn_state_header(headers)
    if existing is not None:
        return existing
    return f"http_turn_{uuid4().hex}"


def build_downstream_turn_state_accept_headers(turn_state: str) -> list[tuple[bytes, bytes]]:
    return [(b"x-codex-turn-state", turn_state.encode("utf-8"))]


def build_downstream_turn_state_response_headers(turn_state: str) -> dict[str, str]:
    return {"x-codex-turn-state": turn_state}


def _upstream_turn_state_from_socket(upstream: UpstreamResponsesWebSocket | None) -> str | None:
    if upstream is None:
        return None
    getter = getattr(upstream, "response_header", None)
    if not callable(getter):
        return None
    value = getter("x-codex-turn-state")
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _response_create_client_metadata(
    payload: Mapping[str, JsonValue],
    *,
    headers: Mapping[str, str],
) -> Mapping[str, JsonValue] | None:
    raw_value = payload.get("client_metadata")
    client_metadata: dict[str, JsonValue] = {}
    if is_json_mapping(raw_value):
        for key, value in raw_value.items():
            if isinstance(key, str):
                client_metadata[key] = value

    normalized_headers = {key.lower(): value for key, value in headers.items()}
    turn_metadata = normalized_headers.get("x-codex-turn-metadata")
    if isinstance(turn_metadata, str) and turn_metadata.strip():
        client_metadata.setdefault("x-codex-turn-metadata", turn_metadata)

    return client_metadata or None


def _headers_with_turn_state(headers: Mapping[str, str], turn_state: str | None) -> dict[str, str]:
    forwarded = dict(headers)
    if turn_state:
        forwarded["x-codex-turn-state"] = turn_state
    return forwarded


def _preferred_http_bridge_reconnect_turn_state(session: "_HTTPBridgeSession") -> str | None:
    if (
        session.codex_session
        and session.downstream_turn_state is not None
        and session.affinity.kind == StickySessionKind.CODEX_SESSION
        and session.affinity.key == session.downstream_turn_state
    ):
        return session.downstream_turn_state
    return session.upstream_turn_state


def _http_bridge_turn_state_alias_key(turn_state: str, api_key_id: str | None) -> tuple[str, str | None]:
    return (turn_state, api_key_id)


def _http_bridge_previous_response_alias_key(response_id: str, api_key_id: str | None) -> tuple[str, str | None]:
    return (response_id.strip(), api_key_id)


def _http_bridge_session_allows_api_key(session: "_HTTPBridgeSession", api_key: ApiKeyData | None) -> bool:
    if api_key is None or not api_key.account_assignment_scope_enabled:
        return True
    return session.account.id in api_key.assigned_account_ids


def _http_bridge_session_reusable_for_request(
    *,
    session: "_HTTPBridgeSession",
    key: "_HTTPBridgeSessionKey",
    incoming_turn_state: str | None,
    previous_response_id: str | None,
) -> bool:
    if key.affinity_kind != "prompt_cache":
        return True
    if incoming_turn_state is not None:
        return True
    if previous_response_id is not None:
        return True
    return not session.codex_session


def _http_bridge_session_matches_preferred_account(
    *,
    session: "_HTTPBridgeSession",
    previous_response_id: str | None,
    preferred_account_id: str | None,
    require_preferred_account: bool = False,
) -> bool:
    if preferred_account_id is None:
        return True
    if previous_response_id is None and not require_preferred_account:
        return True
    return session.account.id == preferred_account_id


def _resolve_prompt_cache_key(
    payload: ResponsesRequest | ResponsesCompactRequest,
    *,
    openai_cache_affinity: bool,
    api_key: ApiKeyData | None,
) -> tuple[str | None, str]:
    cache_key = _prompt_cache_key_from_request_model(payload)
    if isinstance(cache_key, str):
        stripped = cache_key.strip()
        if stripped:
            if stripped != cache_key:
                payload.prompt_cache_key = stripped
            return stripped, "payload"
    if not openai_cache_affinity:
        return None, "none"
    settings = get_settings()
    if not settings.openai_prompt_cache_key_derivation_enabled:
        return None, "none"
    cache_key = _derive_prompt_cache_key(payload, api_key)
    payload.prompt_cache_key = cache_key
    return cache_key, "derived"


def _sticky_key_for_responses_request(
    payload: ResponsesRequest,
    headers: Mapping[str, str],
    *,
    codex_session_affinity: bool,
    openai_cache_affinity: bool,
    openai_cache_affinity_max_age_seconds: int,
    sticky_threads_enabled: bool,
    api_key: ApiKeyData | None = None,
    codex_session_budget_reallocation_enabled: bool = True,
) -> _AffinityPolicy:
    cache_key, _ = _resolve_prompt_cache_key(
        payload,
        openai_cache_affinity=openai_cache_affinity,
        api_key=api_key,
    )
    platform_key = cache_key if openai_cache_affinity and cache_key else None
    platform_kind = StickySessionKind.PROMPT_CACHE if platform_key else None
    platform_max_age_seconds = openai_cache_affinity_max_age_seconds if platform_key else None
    turn_state_key = _sticky_key_from_turn_state_header(headers)
    if turn_state_key:
        return _AffinityPolicy(
            key=turn_state_key,
            kind=StickySessionKind.CODEX_SESSION,
            budget_reallocation_enabled=codex_session_budget_reallocation_enabled,
            platform_key=platform_key,
            platform_kind=platform_kind,
            platform_max_age_seconds=platform_max_age_seconds,
        )
    if codex_session_affinity:
        session_key = _sticky_key_from_session_header(headers)
        if session_key:
            return _AffinityPolicy(
                key=session_key,
                kind=StickySessionKind.CODEX_SESSION,
                budget_reallocation_enabled=codex_session_budget_reallocation_enabled,
                platform_key=platform_key,
                platform_kind=platform_kind,
                platform_max_age_seconds=platform_max_age_seconds,
            )
    if openai_cache_affinity:
        return _AffinityPolicy(
            key=cache_key,
            kind=StickySessionKind.PROMPT_CACHE,
            max_age_seconds=openai_cache_affinity_max_age_seconds,
            platform_key=platform_key,
            platform_kind=platform_kind,
            platform_max_age_seconds=platform_max_age_seconds,
        )
    if sticky_threads_enabled:
        return _AffinityPolicy(
            key=cache_key,
            kind=StickySessionKind.STICKY_THREAD,
            reallocate_sticky=True,
            platform_key=platform_key,
            platform_kind=platform_kind,
            platform_max_age_seconds=platform_max_age_seconds,
        )
    return _AffinityPolicy()


def _make_http_bridge_session_key(
    payload: ResponsesRequest,
    *,
    headers: Mapping[str, str],
    affinity: _AffinityPolicy,
    api_key: ApiKeyData | None,
    request_id: str,
    allow_forwarded_affinity_headers: bool = False,
    forwarded_affinity_kind: str | None = None,
    forwarded_affinity_key: str | None = None,
) -> _HTTPBridgeSessionKey:
    forwarded_key = (
        _forwarded_http_bridge_session_key(
            headers,
            api_key,
            forwarded_affinity_kind=forwarded_affinity_kind,
            forwarded_affinity_key=forwarded_affinity_key,
        )
        if allow_forwarded_affinity_headers
        else None
    )
    if forwarded_key is not None:
        return forwarded_key
    turn_state_key = _sticky_key_from_turn_state_header(headers)
    if turn_state_key is not None:
        affinity_key = turn_state_key
        affinity_kind = "turn_state_header"
        strength: Literal["hard", "soft"] = "hard"
    else:
        session_key = _sticky_key_from_session_header(headers)
        if session_key is not None:
            affinity_key = session_key
            affinity_kind = "session_header"
            strength = "hard"
        else:
            affinity_key = affinity.key or request_id
            affinity_kind = affinity.kind.value if affinity.kind is not None else "request"
            strength = "soft"
    return _HTTPBridgeSessionKey(
        affinity_kind=affinity_kind,
        affinity_key=affinity_key,
        api_key_id=api_key.id if api_key is not None else None,
        strength=strength,
    )


async def _http_bridge_should_wait_for_registration(
    self,
    key: _HTTPBridgeSessionKey,
    settings: Settings,
) -> bool:
    import app.core.startup as startup_module

    if startup_module._bridge_registration_complete:
        return False
    if key.strength != "hard":
        return False
    if _http_bridge_requires_cluster_registration(settings):
        return True
    if self._ring_membership is None:
        return False
    try:
        active_members = await self._ring_membership.list_active()
    except Exception:
        logger.debug("Skipping bridge registration gate because active ring lookup failed", exc_info=True)
        return False
    current_instance = settings.http_responses_session_bridge_instance_id
    return any(member != current_instance for member in active_members)


def _durable_bridge_lookup_active_owner(lookup: DurableBridgeLookup | None) -> str | None:
    if lookup is None:
        return None
    if lookup.state == "closed":
        return None
    if lookup.owner_instance_id is None or lookup.lease_expires_at is None:
        return None
    lease_expires_at = to_utc_naive(lookup.lease_expires_at)
    if lease_expires_at <= utcnow():
        return None
    return lookup.owner_instance_id


def _durable_bridge_lookup_allows_local_reuse(
    lookup: DurableBridgeLookup | None,
    *,
    current_instance: str,
) -> bool:
    if lookup is None:
        return True
    owner_instance = _durable_bridge_lookup_active_owner(lookup)
    if owner_instance is None:
        return True
    return owner_instance == current_instance


def _http_bridge_allow_durable_takeover(lookup: DurableBridgeLookup | None) -> bool:
    owner_instance = _durable_bridge_lookup_active_owner(lookup)
    if owner_instance is None:
        return True
    if lookup is None:
        return False
    return lookup.state in {
        HttpBridgeSessionState.DRAINING,
        HttpBridgeSessionState.CLOSED,
    }


def _http_bridge_has_durable_recovery_anchor(
    *,
    previous_response_id: str | None,
    durable_lookup: DurableBridgeLookup | None,
) -> bool:
    if previous_response_id is not None:
        return True
    if durable_lookup is None or durable_lookup.latest_response_id is None:
        return False
    return durable_lookup.canonical_kind in {"turn_state_header", "session_header"}


def _http_bridge_can_local_recover_without_ring(
    *,
    key: _HTTPBridgeSessionKey,
    headers: Mapping[str, str],
    previous_response_id: str | None,
    durable_lookup: DurableBridgeLookup | None,
) -> bool:
    if _http_bridge_has_durable_recovery_anchor(
        previous_response_id=previous_response_id,
        durable_lookup=durable_lookup,
    ):
        return True
    return (
        key.affinity_kind == "session_header"
        and previous_response_id is None
        and _sticky_key_from_turn_state_header(headers) is None
    )


def _http_bridge_can_single_instance_owner_takeover_without_anchor(
    *,
    key: _HTTPBridgeSessionKey,
    owner_instance: str | None,
    current_instance: str,
    ring: tuple[str, ...],
) -> bool:
    if key.strength != "hard":
        return False
    if owner_instance is None or owner_instance == current_instance:
        return False
    if len(ring) != 1:
        return False
    if ring[0] != current_instance:
        return False
    return owner_instance not in ring


def _http_bridge_can_single_instance_prompt_cache_takeover_without_anchor(
    *,
    key: _HTTPBridgeSessionKey,
    owner_instance: str | None,
    current_instance: str,
    ring: tuple[str, ...],
) -> bool:
    if key.affinity_kind != "prompt_cache":
        return False
    if owner_instance is None or owner_instance == current_instance:
        return False
    if len(ring) != 1:
        return False
    if ring[0] != current_instance:
        return False
    return owner_instance not in ring


def _http_bridge_can_recover_during_drain(
    *,
    key: _HTTPBridgeSessionKey,
    headers: Mapping[str, str],
    previous_response_id: str | None,
    durable_lookup: DurableBridgeLookup | None,
) -> bool:
    return _http_bridge_has_durable_recovery_anchor(
        previous_response_id=previous_response_id,
        durable_lookup=durable_lookup,
    )


def _http_bridge_request_stage(
    *,
    headers: Mapping[str, str],
    payload: ResponsesRequest,
    durable_lookup: DurableBridgeLookup | None,
) -> str:
    del durable_lookup
    if (
        payload.previous_response_id is not None
        or _sticky_key_from_turn_state_header(headers) is not None
        or _sticky_key_from_session_header(headers) is not None
    ):
        return "follow_up"
    return "first_turn"


def _record_same_account_takeover(*, preferred_account_id: str | None, selected_account_id: str | None) -> None:
    if not PROMETHEUS_AVAILABLE or bridge_same_account_takeover_total is None or preferred_account_id is None:
        return
    if selected_account_id is None:
        bridge_same_account_takeover_total.labels(outcome="fail").inc()
    elif selected_account_id == preferred_account_id:
        bridge_same_account_takeover_total.labels(outcome="success").inc()
    else:
        bridge_same_account_takeover_total.labels(outcome="fallback").inc()


def _previous_response_owner_lookup_failed_error_envelope() -> OpenAIErrorEnvelope:
    return openai_error(
        "upstream_unavailable",
        "Previous response owner lookup failed; retry later.",
        error_type="server_error",
    )


def _mark_request_state_previous_response_not_found(
    request_state: _WebSocketRequestState,
    detail: str,
) -> None:
    previous_response_id = request_state.previous_response_id
    if previous_response_id is None:
        return
    payload = _http_bridge_previous_response_error_envelope(previous_response_id, detail)
    error = payload["error"]
    request_state.error_code_override = error.get("code")
    request_state.error_message_override = error.get("message")
    request_state.error_type_override = error.get("type")
    request_state.error_param_override = error.get("param")


def _http_bridge_should_attempt_local_previous_response_recovery(exc: ProxyResponseError) -> bool:
    payload = exc.payload
    if not isinstance(payload, dict):
        return False
    error = payload.get("error")
    if not isinstance(error, dict):
        return False
    code = error.get("code")
    if code in {
        "bridge_owner_unreachable",
        "previous_response_not_found",
        "bridge_instance_mismatch",
    }:
        return True
    param_value = error.get("param")
    param = param_value.strip() if isinstance(param_value, str) and param_value.strip() else None
    message_value = error.get("message")
    message = message_value.strip() if isinstance(message_value, str) and message_value.strip() else None
    return _is_previous_response_not_found_error(code=code, param=param, message=message)


def _http_bridge_is_context_overflow_error(exc: ProxyResponseError) -> bool:
    payload = exc.payload
    if not isinstance(payload, dict):
        return False
    error = payload.get("error")
    if not isinstance(error, dict):
        return False
    code_value = error.get("code")
    code = code_value.strip() if isinstance(code_value, str) and code_value.strip() else None
    type_value = error.get("type")
    error_type = type_value.strip() if isinstance(type_value, str) and type_value.strip() else None
    normalized_code = _normalize_error_code(code, error_type)
    return normalized_code == "context_length_exceeded"


def _http_bridge_should_rollover_after_context_overflow(
    exc: ProxyResponseError,
    *,
    key: _HTTPBridgeSessionKey | None = None,
) -> bool:
    if not _http_bridge_is_context_overflow_error(exc):
        return False
    if key is not None and key.strength == "hard":
        return False
    return True


def _http_bridge_should_attempt_local_bootstrap_rebind(
    exc: ProxyResponseError,
    *,
    key: _HTTPBridgeSessionKey,
    headers: Mapping[str, str],
    previous_response_id: str | None,
) -> bool:
    if key.affinity_kind != "session_header":
        return False
    if previous_response_id is not None:
        return False
    if _sticky_key_from_turn_state_header(headers) is not None:
        return False
    payload = exc.payload
    if not isinstance(payload, dict):
        return False
    error = payload.get("error")
    if not isinstance(error, dict):
        return False
    code = error.get("code")
    return code in {
        "bridge_owner_unreachable",
        "bridge_instance_mismatch",
    }


def _normalized_http_bridge_instance_ring(settings: Settings) -> tuple[str, tuple[str, ...]]:
    instance_id = settings.http_responses_session_bridge_instance_id.strip()
    if not instance_id:
        instance_id = "codex-lb"
    ring_entries: list[str] = []
    for entry in settings.http_responses_session_bridge_instance_ring:
        stripped = entry.strip()
        if stripped:
            ring_entries.append(stripped)
    if not ring_entries:
        ring_entries.append(instance_id)
    return instance_id, tuple(sorted(set(ring_entries)))


async def _active_http_bridge_instance_ring(
    settings: Settings,
    ring_membership: RingMembershipService | None,
) -> tuple[str, tuple[str, ...]]:
    instance_id, static_ring = _normalized_http_bridge_instance_ring(settings)
    if ring_membership is None:
        return instance_id, static_ring
    try:
        active_members = await ring_membership.list_active(require_endpoint=True)
    except Exception:
        logger.warning("Bridge ring lookup failed — refusing to fall back to static ring", exc_info=True)
        raise
    if not active_members:
        return instance_id, (instance_id,)
    normalized_members = tuple(
        sorted({member.strip() for member in active_members if isinstance(member, str) and member.strip()})
    )
    if not normalized_members:
        return instance_id, static_ring
    return instance_id, normalized_members


async def _http_bridge_owner_instance(
    key: _HTTPBridgeSessionKey,
    settings: Settings,
    ring_membership: RingMembershipService | None = None,
) -> str | None:
    instance_id, ring = await _active_http_bridge_instance_ring(settings, ring_membership)
    if len(ring) <= 1:
        return instance_id
    hash_input = f"{key.affinity_kind}:{key.affinity_key}:{key.api_key_id or ''}"
    return select_node(hash_input, ring)


def _http_bridge_runtime_config(
    dashboard_settings: DashboardSettings,
    app_settings: Settings,
) -> _HTTPBridgeRuntimeConfig:
    return _HTTPBridgeRuntimeConfig(
        enabled=app_settings.http_responses_session_bridge_enabled,
        idle_ttl_seconds=app_settings.http_responses_session_bridge_idle_ttl_seconds,
        codex_idle_ttl_seconds=app_settings.http_responses_session_bridge_codex_idle_ttl_seconds,
        max_sessions=app_settings.http_responses_session_bridge_max_sessions,
        queue_limit=app_settings.http_responses_session_bridge_queue_limit,
        prompt_cache_idle_ttl_seconds=float(
            dashboard_settings.http_responses_session_bridge_prompt_cache_idle_ttl_seconds,
        ),
        gateway_safe_mode=dashboard_settings.http_responses_session_bridge_gateway_safe_mode,
    )


def _http_bridge_owner_check_required(
    key: _HTTPBridgeSessionKey,
    *,
    gateway_safe_mode: bool,
) -> bool:
    if key.strength == "hard":
        return True
    return gateway_safe_mode and key.affinity_kind == "sticky_thread"


def _header_value_case_insensitive(headers: Mapping[str, str], name: str) -> str | None:
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return None


def _headers_with_authorization(headers: Mapping[str, str], authorization: str | None) -> dict[str, str]:
    merged = dict(headers)
    if authorization is None:
        return merged
    if _header_value_case_insensitive(merged, "authorization") is not None:
        return merged
    merged["Authorization"] = authorization
    return merged


def _http_bridge_key_strength(key: _HTTPBridgeSessionKey) -> str:
    return key.strength or "soft"


def _log_http_bridge_event(
    event: str,
    key: _HTTPBridgeSessionKey,
    *,
    account_id: str | None,
    model: str | None,
    pending_count: int | None = None,
    detail: str | None = None,
    cache_key_family: str | None = None,
    model_class: str | None = None,
    owner_check_applied: bool | None = None,
) -> None:
    level = logging.INFO
    if event in {
        "queue_full",
        "submit_on_closed",
        "send_failure",
        "retry_fresh_upstream",
        "retry_precreated",
        "reconnect",
        "terminal_error",
        "capacity_exhausted_active_sessions",
        "owner_mismatch",
        "owner_forward_fail",
        "prompt_cache_locality_miss",
        "reallocation_orphan",
        "context_overflow_rollover",
    }:
        level = logging.WARNING
    logger.log(
        level,
        "http_bridge_event event=%s bridge_kind=%s bridge_key=%s account_id=%s"
        " model=%s pending=%s detail=%s cache_key_family=%s model_class=%s"
        " key_strength=%s owner_check_applied=%s",
        event,
        key.affinity_kind,
        _hash_identifier(key.affinity_key),
        account_id,
        model,
        pending_count,
        detail,
        cache_key_family,
        model_class,
        _http_bridge_key_strength(key),
        owner_check_applied,
    )


def _sticky_key_from_compact_payload(payload: ResponsesCompactRequest) -> str | None:
    value = _prompt_cache_key_from_request_model(payload)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _sticky_key_for_compact_request(
    payload: ResponsesCompactRequest,
    headers: Mapping[str, str],
    *,
    codex_session_affinity: bool,
    openai_cache_affinity: bool,
    openai_cache_affinity_max_age_seconds: int,
    sticky_threads_enabled: bool,
    api_key: ApiKeyData | None = None,
    codex_session_budget_reallocation_enabled: bool = True,
) -> _AffinityPolicy:
    cache_key, _ = _resolve_prompt_cache_key(
        payload,
        openai_cache_affinity=openai_cache_affinity,
        api_key=api_key,
    )
    platform_key = cache_key if openai_cache_affinity and cache_key else None
    platform_kind = StickySessionKind.PROMPT_CACHE if platform_key else None
    platform_max_age_seconds = openai_cache_affinity_max_age_seconds if platform_key else None
    if codex_session_affinity:
        session_key = _sticky_key_from_session_header(headers)
        if session_key:
            return _AffinityPolicy(
                key=session_key,
                kind=StickySessionKind.CODEX_SESSION,
                budget_reallocation_enabled=codex_session_budget_reallocation_enabled,
                platform_key=platform_key,
                platform_kind=platform_kind,
                platform_max_age_seconds=platform_max_age_seconds,
            )
    if openai_cache_affinity:
        return _AffinityPolicy(
            key=cache_key,
            kind=StickySessionKind.PROMPT_CACHE,
            max_age_seconds=openai_cache_affinity_max_age_seconds,
            platform_key=platform_key,
            platform_kind=platform_kind,
            platform_max_age_seconds=platform_max_age_seconds,
        )
    if sticky_threads_enabled:
        return _AffinityPolicy(
            key=cache_key,
            kind=StickySessionKind.STICKY_THREAD,
            reallocate_sticky=True,
            platform_key=platform_key,
            platform_kind=platform_kind,
            platform_max_age_seconds=platform_max_age_seconds,
        )
    return _AffinityPolicy()


def _service_tier_from_compact_payload(payload: ResponsesCompactRequest) -> str | None:
    return _normalize_service_tier_value(payload.service_tier)


def _service_tier_from_response(
    response: OpenAIResponsePayload | CompactResponsePayload | None,
) -> str | None:
    if response is None:
        return None
    extra = response.model_extra
    if not isinstance(extra, Mapping):
        return None
    return _normalize_service_tier_value(extra.get("service_tier"))


def _service_tier_from_event_payload(payload: dict[str, JsonValue] | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    response = payload.get("response")
    if not isinstance(response, dict):
        return None
    return _normalize_service_tier_value(response.get("service_tier"))


def _effective_service_tier(requested_service_tier: str | None, actual_service_tier: str | None) -> str | None:
    if isinstance(actual_service_tier, str):
        return actual_service_tier
    if isinstance(requested_service_tier, str):
        return requested_service_tier
    return None


def _normalize_service_tier_value(value: JsonValue) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if stripped.lower() == "fast":
        return "priority"
    return stripped
