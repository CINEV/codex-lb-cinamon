# proxy-runtime-observability Specification

## Purpose

Define proxy observability contracts so runtime failures, routing decisions, and admission rejections remain diagnosable.
## Requirements
### Requirement: Console runtime logs include explicit timestamps
The system SHALL emit server console logs with an explicit timestamp on each line for both application logs and HTTP access logs.

#### Scenario: Server emits an application log
- **WHEN** the runtime writes an application log line to the console
- **THEN** the line includes a timestamp before the log level and message

#### Scenario: Server emits an access log
- **WHEN** the runtime writes an HTTP access log line to the console
- **THEN** the line includes a timestamp before the access-log fields

### Requirement: Optional upstream request summary tracing
When `log_upstream_request_summary` is enabled, the system MUST log one start record and one completion record for each outbound upstream proxy request. For provider-aware routing, each record MUST include the proxy `request_id`, requested route class, selected provider kind, selected routing-subject identifier when available, and enough metadata to correlate the request with the result.

#### Scenario: Responses request tracing is enabled
- **WHEN** the proxy sends an upstream Responses request while `log_upstream_request_summary=true`
- **THEN** the console shows a start record with request metadata and a completion record with status or failure outcome

#### Scenario: Transcription request tracing is enabled
- **WHEN** the proxy sends an upstream transcription request while `log_upstream_request_summary=true`
- **THEN** the console shows the outbound request metadata without logging raw binary body contents

#### Scenario: Provider-aware upstream request tracing is enabled
- **WHEN** the proxy sends an upstream request while `log_upstream_request_summary=true`
- **THEN** the console shows start and completion records that include provider kind, route class, routing-subject identifier or label, and upstream request id when the provider returns one

### Requirement: Optional upstream payload tracing
When `log_upstream_request_payload` is enabled, the system MUST log the normalized outbound payload for JSON upstream requests and MUST log a metadata summary for multipart upstream requests.

#### Scenario: JSON upstream payload tracing is enabled
- **WHEN** the proxy sends an upstream Responses or compact request while `log_upstream_request_payload=true`
- **THEN** the console shows the normalized outbound JSON payload associated with the request id

#### Scenario: Multipart upstream payload tracing is enabled
- **WHEN** the proxy sends an upstream transcription request while `log_upstream_request_payload=true`
- **THEN** the console shows non-binary metadata such as filename, content type, prompt presence, and byte length

### Requirement: Persisted request logs include provider-aware routing fields
Persisted request logs MUST no longer be account-only records. For provider-aware routing, each persisted request log MUST include provider kind, generic routing-subject identifier, requested route class, and upstream request id when available, even when the request fails before upstream selection.

#### Scenario: Persisted request log records a selected provider
- **WHEN** a proxied request selects an upstream routing subject
- **THEN** the persisted request log includes provider kind, routing-subject identifier, route class, and upstream request id when present

#### Scenario: Persisted request log records a pre-routing capability rejection
- **WHEN** the proxy rejects a request before upstream selection because no provider supports the requested route, transport, or continuity capability
- **THEN** the persisted request log still records the requested route class and normalized rejection reason without requiring an `account_id`

#### Scenario: Reservation cleanup failure does not override the proxy result
- **WHEN** request handling has already produced a client response
- **AND** best-effort API-key reservation cleanup fails during post-response teardown
- **THEN** the proxy preserves the original response outcome
- **AND** it logs the cleanup failure without replacing the original response with a cleanup error

### Requirement: Proxy 4xx/5xx responses are logged with provider-aware rejection detail
When the proxy returns a 4xx or 5xx response for a proxied request, the system MUST log the request id, method, path, status code, error code, and error message to the console. When the failure is caused by provider capability gating before routing-subject selection, the log MUST also include the requested route class and rejection reason. For local admission rejections, the log MUST also include which admission lane or stage rejected the request.

#### Scenario: Upstream failure becomes a proxy error response
- **WHEN** an upstream 4xx or 5xx failure is returned to the client by the proxy
- **THEN** the console log includes the proxy response status plus the normalized error code and message

#### Scenario: Local proxy validation or server error is returned
- **WHEN** the proxy itself returns a 4xx or 5xx response before or without an upstream response
- **THEN** the console log includes the local response status plus the error code and message

#### Scenario: Local admission rejection is logged
- **WHEN** the proxy rejects a request locally because a downstream or expensive-work admission lane is full
- **THEN** the console log includes the local response status, normalized error code and message
- **AND** it includes which admission lane or stage rejected the request

#### Scenario: Provider capability mismatch is rejected before selection
- **WHEN** the proxy rejects a request before upstream selection because no provider supports the requested route, transport, or continuity capability
- **THEN** the console log includes the requested route class and normalized rejection code

### Requirement: Provider auth failure transitions are logged with provider context
When provider health changes because of upstream auth failures, the system MUST log the provider kind, routing-subject identifier, and normalized failure reason.

#### Scenario: Platform auth failure changes provider health
- **WHEN** an `openai_platform` identity transitions to unhealthy or deactivated after repeated auth failures
- **THEN** the runtime log includes provider kind, routing-subject identifier, and the normalized provider-auth failure reason

### Requirement: Continuity-sensitive responses flows emit explicit operator diagnostics
When the proxy resolves or fails closed a continuity-sensitive follow-up request, the system MUST emit structured diagnostics that let operators determine how continuity ownership was resolved or why the proxy returned a retryable masked error.

#### Scenario: owner resolution source is recorded for a previous-response follow-up
- **WHEN** a websocket, HTTP fallback, or HTTP bridge follow-up request includes `previous_response_id`
- **AND** the proxy resolves the required owner account from a continuity source such as a local bridge session, owner cache, or request-log lookup
- **THEN** the system emits a structured diagnostic describing the continuity surface, source, and outcome
- **AND** the diagnostic does not expose the raw `previous_response_id`

#### Scenario: fail-closed continuity masking is recorded
- **WHEN** the proxy rewrites or returns a retryable continuity error because owner metadata is unavailable, continuity state is lost, or the pinned owner account is unavailable
- **THEN** the system emits a structured diagnostic describing the continuity surface and fail-closed reason
- **AND** Prometheus counters record the low-cardinality source or reason labels for that decision

### Requirement: Full upstream conversation archive
The proxy MUST provide an opt-in durable archive of Codex-to-upstream conversation traffic. When enabled, the archive MUST write gzip-compressed newline-delimited JSON records for upstream request payloads, streamed Responses events, compact response payloads, and websocket text or binary frames without performing gzip file I/O in the request event loop during normal operation. The archive writer queue MUST be bounded and MUST apply synchronous write backpressure instead of growing without limit when the background writer is saturated. Archive records MUST include request id, timestamp, direction, traffic kind, transport, account id when known, upstream target metadata, redacted headers, and the full payload or frame body. Credential-bearing headers such as authorization, cookies, proxy authorization, token headers, and API key headers MUST be redacted before persistence. JSON records MUST preserve non-ASCII payload text as UTF-8 rather than Unicode escape sequences. When disabled, no archive file MUST be created by the archive writer.

#### Scenario: operator enables archive for audit
- **WHEN** `CODEX_LB_CONVERSATION_ARCHIVE_ENABLED=true`
- **AND** a Codex Responses request is proxied upstream
- **THEN** the archive records both the outbound upstream payload and inbound upstream events or response body as gzip JSONL
- **AND** credential-bearing headers are stored as redacted values

#### Scenario: archive remains disabled by default
- **WHEN** the archive setting is not enabled
- **THEN** the archive writer does not create conversation archive files

#### Scenario: operator views archived traffic
- **GIVEN** conversation archive files exist as `.jsonl.gz` or legacy `.jsonl`
- **WHEN** an authenticated dashboard operator opens an existing request log detail
- **THEN** the dashboard can find matching archive records by request id across archive files and display payload plus metadata for that request

### Requirement: Optional upstream payload tracing
When request-shape tracing for proxy routing is enabled, the system MUST log affinity decision metadata without exposing full prompt text or full cache keys. The trace MUST include request id, request kind, sticky kind, sticky-key source, whether a session header was present, whether a prompt-cache key was set/injected, and a stable tools hash when tools are present.

#### Scenario: Affinity request-shape tracing is enabled
- **WHEN** the proxy resolves routing for a Responses or compact request while request-shape tracing is enabled
- **THEN** the console shows the chosen sticky kind, sticky-key source, prompt-cache-key presence/injection state, and tools hash
- **AND** the console does not log raw prompt text or the full prompt-cache key unless the explicit raw-key flag is enabled

### Requirement: Proxy exposes runtime observability for bridge routing decisions
The service MUST expose metrics and structured logs for HTTP bridge routing decisions so operators can distinguish hard owner handoff from soft locality misses.

#### Scenario: owner forward metrics are emitted
- **WHEN** a hard continuity bridge request is forwarded to the owner replica
- **THEN** the service emits owner-forward counters for success or failure
- **AND** it records bridge forward latency

#### Scenario: soft locality misses are observable
- **WHEN** a prompt-cache bridge request lands on a non-owner replica and rebinds locally
- **THEN** the service emits locality miss and local rebind observability
- **AND** it logs a structured bridge event indicating soft locality rebind
