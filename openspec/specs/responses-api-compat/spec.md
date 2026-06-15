# responses-api-compat Specification

## Purpose

Define Responses API compatibility contracts so Codex, OpenCode, and OpenAI-style clients preserve expected behavior.
## Requirements
### Requirement: Validate Responses create requests
The service MUST accept POST requests to `/v1/responses` with a JSON body and MUST validate required fields according to OpenAI Responses API expectations. The request MUST include `model` and `input`, MAY omit `instructions`, MUST reject mutually exclusive fields (`input` and `messages` when both are present), and MUST reject `store=true` with an OpenAI error envelope.

#### Scenario: Minimal valid request
- **WHEN** the client sends `{ "model": "gpt-4.1", "input": "hi" }`
- **THEN** the service accepts the request and begins a response (streaming or non-streaming based on `stream`)

#### Scenario: Invalid request fields
- **WHEN** the client omits `model` or `input`, or sends both `input` and `messages`
- **THEN** the service returns a 4xx response with an OpenAI error envelope describing the invalid parameter

### Requirement: Support Responses input types and conversation constraints
The service MUST accept `input` as either a string or an array of input items. When `input` is a string, the service MUST normalize it into a single user input item with `input_text` content before forwarding upstream. The service MUST accept `previous_response_id` when `conversation` is absent and MUST continue to reject requests that include both `conversation` and `previous_response_id`.

#### Scenario: String input
- **WHEN** the client sends `input` as a string
- **THEN** the request is accepted and forwarded as a single `input_text` item

#### Scenario: Array input items
- **WHEN** the client sends `input` as an array of input items
- **THEN** the request is accepted and each item is forwarded in order

#### Scenario: conversation and previous_response_id conflict
- **WHEN** the client provides both `conversation` and `previous_response_id`
- **THEN** the service returns a 4xx response with an OpenAI error envelope indicating invalid parameters

#### Scenario: previous_response_id provided
- **WHEN** the client provides `previous_response_id` without `conversation`
- **THEN** the service accepts the request and forwards `previous_response_id` upstream unchanged

### Requirement: Reject input_file file_id in Responses
The service MUST reject `input_file.file_id` in Responses input items and return a 4xx OpenAI invalid_request_error with message "Invalid request payload".

#### Scenario: input_file file_id rejected
- **WHEN** a request includes an input item with `{"type":"input_file","file_id":"file_123"}`
- **THEN** the service returns a 4xx OpenAI invalid_request_error with message "Invalid request payload" and param `input`

### Requirement: Stream Responses events with terminal completion
When `stream=true`, the service MUST respond with `text/event-stream` and emit OpenAI Responses streaming events. The stream MUST include a terminal event of `response.completed` or `response.failed`. If upstream closes the stream without a terminal event, the service MUST emit `response.failed` with a stable error code indicating an incomplete stream.

#### Scenario: Successful streaming completion
- **WHEN** the upstream emits `response.completed`
- **THEN** the service forwards the event and closes the stream

#### Scenario: Missing terminal event
- **WHEN** the upstream closes the stream without `response.completed` or `response.failed`
- **THEN** the service emits `response.failed` with an error code indicating an incomplete stream and closes the stream

### Requirement: Responses streaming event taxonomy
When streaming, the service MUST forward the standard Responses streaming event types, including `response.created`, `response.in_progress`, and `response.completed`/`response.failed` as applicable, preserving event order and `sequence_number` fields when present.

#### Scenario: response.created and response.in_progress present
- **WHEN** the upstream emits `response.created` followed by `response.in_progress`
- **THEN** the service forwards both events in order without mutation

### Requirement: Non-streaming Responses return a full response object
When `stream` is `false` or omitted, the service MUST return a JSON response object consistent with OpenAI Responses API, including `id`, `object: "response"`, `status`, `output`, and `usage` when available.

#### Scenario: Non-streaming response
- **WHEN** the client sends a valid request with `stream=false`
- **THEN** the service returns a single JSON response object containing output items and status

### Requirement: Reconstruct non-streaming Responses output from streamed item events
When serving non-streaming `/v1/responses`, the service MUST preserve output items emitted on upstream SSE item events even when the terminal `response.completed` or `response.incomplete` payload omits `response.output` or returns it as an empty list.

#### Scenario: Reasoning item emitted before terminal response
- **WHEN** upstream emits a reasoning or other output item on `response.output_item.done` and the terminal response omits `output`
- **THEN** the final non-streaming JSON response includes that output item in `output`

#### Scenario: Terminal response already includes output
- **WHEN** the terminal response already includes a non-empty `output` array
- **THEN** the service returns the terminal `output` array unchanged

### Requirement: Error envelope parity for invalid or unsupported requests
For invalid inputs or unsupported features, the service MUST return an OpenAI-style error envelope (`{ "error": { ... } }`) with stable `type`, `code`, and `param` fields. For streaming requests, errors MUST be emitted as `response.failed` events containing the same error envelope.

#### Scenario: Unsupported feature flag
- **WHEN** the client sets an unsupported feature (e.g., `store=true`)
- **THEN** the service returns an OpenAI error envelope (or `response.failed` for streaming) with a stable error code and message

### Requirement: Validate include values
If the client supplies `include`, the service MUST accept only values documented by the Responses API and MUST return a 4xx OpenAI error envelope for unknown include values.

#### Scenario: Known include value
- **WHEN** the client includes `message.output_text.logprobs`
- **THEN** the service accepts the request and includes logprobs in the response output when available

#### Scenario: Unknown include value
- **WHEN** the client includes an unsupported include value
- **THEN** the service returns a 4xx OpenAI error envelope indicating the invalid include entry

### Requirement: Allow web_search and built-in Responses tools
The service MUST accept Responses requests that include tools with type `web_search` or `web_search_preview` and MUST normalize `web_search_preview` to `web_search` before forwarding upstream. For other built-in Responses tool types (including `file_search`, `code_interpreter`, `computer_use`, `computer_use_preview`, and `image_generation`), the service MUST accept the request and MUST forward the tool definitions to upstream unchanged except for the documented `web_search_preview` alias. The same behavior MUST apply on HTTP `/v1/responses`, HTTP `/backend-api/codex/responses`, and the WebSocket equivalents that carry `response.create` payloads. Chat Completions tool policy is out of scope for this requirement and remains governed by `chat-completions-compat`.

#### Scenario: web_search_preview tool accepted
- **WHEN** the client sends `tools=[{"type":"web_search_preview"}]`
- **THEN** the service accepts the request and forwards the tool as `web_search`

#### Scenario: built-in Responses tool accepted over HTTP
- **WHEN** the client sends `/v1/responses` or `/backend-api/codex/responses` with a built-in tool such as `image_generation`, `file_search`, `code_interpreter`, `computer_use`, or `computer_use_preview`
- **THEN** the service accepts the request and forwards the tool definition unchanged except for the documented `web_search_preview` alias

#### Scenario: built-in Responses tool accepted over WebSocket
- **WHEN** the client sends a WebSocket `response.create` payload on `/v1/responses` or `/backend-api/codex/responses` with one or more built-in tools
- **THEN** the service accepts the request and forwards the tool definitions unchanged except for the documented `web_search_preview` alias

### Requirement: Preserve supported service_tier values
When a Responses request includes `service_tier`, the service MUST preserve that field in the normalized upstream payload instead of dropping or rewriting it locally.

#### Scenario: Responses request includes fast-mode tier
- **WHEN** a client sends a valid Responses request with `service_tier: "priority"`
- **THEN** the service accepts the request and forwards `service_tier: "priority"` upstream unchanged

### Requirement: Inline input_image URLs when possible
When a request includes `input_image` parts with HTTP(S) URLs, the service MUST attempt to fetch the image and replace the URL with a data URL if the image is within size limits. If the image cannot be fetched or exceeds size limits, the service MUST preserve the original URL and allow upstream to handle the error.

#### Scenario: input_image URL fetched
- **WHEN** the request includes an HTTP(S) `input_image` URL that is reachable and within size limits
- **THEN** the service forwards the request with the image converted to a data URL

#### Scenario: input_image URL fetch fails
- **WHEN** the request includes an HTTP(S) `input_image` URL that cannot be fetched or exceeds limits
- **THEN** the service forwards the original URL unchanged

### Requirement: Reject truncation
The service MUST reject any request that includes `truncation`, returning an OpenAI error envelope indicating the unsupported parameter. The service MUST NOT forward `truncation` to upstream.

#### Scenario: truncation provided
- **WHEN** the client sends `truncation: "auto"` or `truncation: "disabled"`
- **THEN** the service returns a 4xx response with an OpenAI error envelope indicating the unsupported parameter

### Requirement: Tool call events and output items are preserved
If the upstream model emits tool call deltas or output items, the service MUST forward those events in streaming mode and MUST include tool call items in the final response output for non-streaming mode.

#### Scenario: Tool call emitted
- **WHEN** the upstream emits a tool call delta event
- **THEN** the service forwards the delta event and includes the finalized tool call in the completed response output

### Requirement: Usage mapping and propagation
When usage data is provided by the upstream, the service MUST include `input_tokens`, `output_tokens`, and `total_tokens` (and token detail fields if present) in `response.completed` events and in non-streaming responses.

#### Scenario: Usage included
- **WHEN** the upstream includes usage in `response.completed`
- **THEN** the service forwards usage fields in the completed event and in the final response object

### Requirement: Strip safety_identifier before upstream forwarding
Before forwarding Responses payloads upstream, the service MUST remove `safety_identifier` from normalized payloads for both standard and compact Responses endpoints.

#### Scenario: safety_identifier provided in Responses request
- **WHEN** a client sends a valid Responses request including `safety_identifier`
- **THEN** the service accepts the request and forwards payload without `safety_identifier`

#### Scenario: safety_identifier provided in Chat-mapped request
- **WHEN** a client sends a Chat Completions request including `safety_identifier`
- **THEN** the mapped Responses payload forwarded upstream excludes `safety_identifier`

### Requirement: Strip known unsupported advisory parameters before upstream forwarding
Before forwarding Responses payloads upstream, the service MUST remove known unsupported advisory parameters that upstream rejects with `unknown_parameter`. At minimum, the service MUST strip `prompt_cache_retention` and `temperature` from normalized payloads for both standard and compact Responses endpoints, and MUST preserve `prompt_cache_key`.

#### Scenario: prompt_cache_retention provided
- **WHEN** a client sends a valid Responses request that includes `prompt_cache_retention`
- **THEN** the service accepts the request and forwards payload without `prompt_cache_retention`

#### Scenario: temperature provided
- **WHEN** a client sends a valid Responses or Chat-mapped request that includes `temperature`
- **THEN** the service accepts the request and forwards payload without `temperature`

#### Scenario: unrelated extra field provided
- **WHEN** a client sends a valid request with an unrelated extra field not in the unsupported list
- **THEN** the service preserves that field in forwarded payload

### Requirement: Public OpenAI-compatible route eligibility is provider-aware, transport-aware, and fallback-ordered
The service MUST treat upstream execution as a provider-aware decision instead of assuming every request targets the ChatGPT-web backend. `chatgpt_web` remains primary and `openai_platform` is fallback-only. Phase-1 Platform fallback covers HTTP `/v1/models`, stateless HTTP `/v1/responses`, stateless HTTP `/v1/responses/compact`, HTTP `/backend-api/codex/models`, stateless HTTP `/backend-api/codex/responses`, and stateless HTTP `/backend-api/codex/responses/compact` when the selected routing subject supports the requested route family, transport, model, and required features.

#### Scenario: Healthy ChatGPT-web remains primary for stateless public HTTP
- **WHEN** a request targets an eligible public HTTP route
- **AND** both `chatgpt_web` and `openai_platform` are configured for that route family
- **AND** at least one compatible ChatGPT-web candidate remains healthy under the configured primary and secondary drain thresholds
- **THEN** the request continues through the ChatGPT-web path
- **AND** the service does not switch to the Platform transport for that request

#### Scenario: HTTP `/v1/responses` falls back to an OpenAI Platform upstream after the ChatGPT pool is drained
- **WHEN** the deployment includes an `openai_platform` identity
- **AND** there is at least one active `chatgpt_web` account configured in the deployment
- **AND** a compatible Platform routing subject is available for the requested model
- **AND** no compatible ChatGPT-web candidate remains healthy under the configured primary and secondary drain thresholds
- **AND** the request does not require phase-1 unsupported continuity or websocket capabilities
- **THEN** the service forwards HTTP `/v1/responses` to the public upstream contract instead of the ChatGPT-private `/codex/responses` path

#### Scenario: HTTP `/v1/responses/compact` falls back to an OpenAI Platform compact upstream after the ChatGPT pool is drained
- **WHEN** the deployment includes an `openai_platform` identity
- **AND** there is at least one active `chatgpt_web` account configured in the deployment
- **AND** a compatible Platform routing subject is available for the requested compact model
- **AND** no compatible ChatGPT-web candidate remains healthy under the configured fallback thresholds
- **THEN** the service forwards HTTP `/v1/responses/compact` through the Platform compact transport
- **AND** it does not rewrite the compact result into a normal Responses payload

#### Scenario: Backend Codex HTTP responses fall back to Platform after the ChatGPT pool is drained
- **WHEN** the deployment includes an `openai_platform` identity
- **AND** there is at least one active `chatgpt_web` account configured in the deployment
- **AND** a compatible Platform routing subject is available for the requested model
- **AND** no compatible ChatGPT-web candidate remains healthy under the configured fallback thresholds
- **AND** the request does not require websocket or payload-level continuity-dependent behavior
- **THEN** the service forwards HTTP `/backend-api/codex/responses` through the Platform transport instead of the ChatGPT-private upstream path

#### Scenario: Backend Codex HTTP compact responses fall back to Platform after the ChatGPT pool is drained
- **WHEN** the deployment includes an `openai_platform` identity
- **AND** there is at least one active `chatgpt_web` account configured in the deployment
- **AND** a compatible Platform routing subject is available for the requested compact model
- **AND** no compatible ChatGPT-web candidate remains healthy under the configured fallback thresholds
- **THEN** the service forwards HTTP `/backend-api/codex/responses/compact` through the Platform compact transport
- **AND** it preserves the compact result as the canonical next context window

#### Scenario: Backend Codex HTTP model discovery falls back to Platform after the ChatGPT pool is drained
- **WHEN** the deployment includes an `openai_platform` identity
- **AND** there is at least one active `chatgpt_web` account configured in the deployment
- **AND** a compatible Platform routing subject is available
- **AND** no compatible ChatGPT-web candidate remains healthy under the configured fallback thresholds
- **THEN** the service may satisfy HTTP `/backend-api/codex/models` from Platform model discovery translated into the backend Codex response shape

#### Scenario: Platform identity is excluded from downstream websocket route selection in phase 1
- **WHEN** a request targets downstream websocket `/responses` or `/v1/responses`
- **AND** the candidate upstream routing subject is `openai_platform`
- **THEN** the service excludes that routing subject before transport start
- **AND** if no compatible `chatgpt_web` routing subject remains it returns a stable OpenAI-format error instead of attempting a ChatGPT-shaped websocket flow on behalf of Platform mode

#### Scenario: capability mismatch fails closed
- **WHEN** routing selects or is restricted to an upstream routing subject that does not support the requested route family, transport, or feature
- **THEN** the service rejects the request with a stable OpenAI-format error
- **AND** it MUST NOT silently substitute a different upstream contract to emulate unsupported behavior

#### Scenario: Public route rejects Platform-only fallback
- **WHEN** a request targets HTTP `/v1/models`, stateless HTTP `/v1/responses`, or stateless HTTP `/v1/responses/compact`
- **AND** an `openai_platform` identity is configured for that route family
- **AND** no eligible `chatgpt_web` routing subject exists for the requested model and route
- **THEN** the service rejects the request before upstream transport start with HTTP `400`
- **AND** it returns an OpenAI-format error envelope with `type = "invalid_request_error"` and `code = "provider_fallback_requires_chatgpt"`

### Requirement: Continuity-dependent request shapes are gated before provider selection
The service MUST derive request capabilities from both route and request shape before it chooses an upstream routing subject. Requests are continuity-dependent when they rely on `conversation`, `previous_response_id`, explicit session headers, `x-codex-turn-state`, or downstream websocket continuity semantics. For HTTP `/backend-api/codex/responses`, downstream Codex session headers are transport hints and MUST NOT by themselves block Platform fallback in this increment; payload-level continuity fields remain unsupported.

#### Scenario: Platform-backed `conversation` request is rejected in phase 1
- **WHEN** a request targets HTTP `/v1/responses`
- **AND** the allowed upstream candidates are restricted to `openai_platform`
- **AND** the request includes `conversation`
- **THEN** the service rejects the request before upstream transport start with HTTP `400`
- **AND** it returns an OpenAI-format error envelope with `type = "invalid_request_error"`, `code = "provider_continuity_unsupported"`, and `param = "conversation"`

#### Scenario: Platform-backed `previous_response_id` request is rejected in phase 1
- **WHEN** a request targets HTTP `/v1/responses`
- **AND** the allowed upstream candidates are restricted to `openai_platform`
- **AND** the request includes `previous_response_id`
- **THEN** the service rejects the request before upstream transport start with HTTP `400`
- **AND** it returns an OpenAI-format error envelope with `type = "invalid_request_error"`, `code = "provider_continuity_unsupported"`, and `param = "previous_response_id"`

#### Scenario: Platform-backed session-affinity headers are rejected on public OpenAI-compatible routes in phase 1
- **WHEN** a request targets a public OpenAI-compatible route
- **AND** the allowed upstream candidates are restricted to `openai_platform`
- **AND** the request carries `session_id`, `x-codex-session-id`, `x-codex-conversation-id`, or `x-codex-turn-state`
- **THEN** the service rejects the request before upstream transport start with HTTP `400`
- **AND** it returns an OpenAI-format error envelope with `type = "invalid_request_error"`, `code = "provider_continuity_unsupported"`, and `param` set to the first offending continuity field name

#### Scenario: Backend Codex HTTP payload continuity request is rejected for Platform fallback
- **WHEN** a request targets HTTP `/backend-api/codex/responses`
- **AND** the allowed upstream candidates are restricted to `openai_platform`
- **AND** the request includes `conversation` or `previous_response_id`
- **THEN** the service rejects the request before upstream transport start with HTTP `400`
- **AND** it returns an OpenAI-format error envelope with `code = "provider_continuity_unsupported"`

#### Scenario: Backend Codex HTTP session headers do not block Platform fallback
- **WHEN** a request targets HTTP `/backend-api/codex/responses`
- **AND** the allowed upstream candidates include an eligible `openai_platform` routing subject for `backend_codex_http`
- **AND** no compatible ChatGPT-web candidate remains healthy under the configured fallback thresholds
- **AND** the request includes `session_id`, `x-codex-session-id`, `x-codex-conversation-id`, or `x-codex-turn-state`
- **AND** the request does not include `conversation` or `previous_response_id`
- **THEN** the service MAY route the request to Platform fallback
- **AND** those downstream session headers MUST NOT by themselves trigger `provider_continuity_unsupported`

### Requirement: Platform mode rejects phase-1 unsupported routes and features
When the selected upstream provider is `openai_platform`, the service MUST explicitly reject routes and features that still depend on ChatGPT-private or phase-gated contracts until equivalent public semantics are intentionally implemented and verified.

#### Scenario: Platform-backed compact request stays inside the compact contract
- **WHEN** an `openai_platform` routing subject receives `/v1/responses/compact` or `/backend-api/codex/responses/compact`
- **THEN** the service keeps the request on the provider-native compact transport
- **AND** it MUST NOT substitute a standard `/responses` request or synthesize compact output locally

#### Scenario: Backend Codex websocket remains unsupported for Platform fallback
- **WHEN** an `openai_platform` routing subject receives `/backend-api/codex/responses` over websocket transport
- **THEN** the service returns HTTP `400`
- **AND** it returns an OpenAI-format error envelope with `code = "provider_transport_unsupported"`

### Requirement: Provider mismatch errors use stable codes
For provider-specific capability failures introduced by provider-aware public-route fallback, the service MUST use stable OpenAI-style error envelopes and stable proxy-defined codes so tests and clients can distinguish route, transport, and continuity failures.

#### Scenario: transport mismatch returns a stable code
- **WHEN** a request is rejected because the selected provider does not support the requested downstream transport
- **THEN** the service returns HTTP `400`
- **AND** it returns an OpenAI-format error envelope with `type = "invalid_request_error"`, `code = "provider_transport_unsupported"`, and `param = "transport"`

#### Scenario: continuity mismatch returns a stable code
- **WHEN** a request is rejected because the selected provider does not support the required continuity behavior
- **THEN** the service returns HTTP `400`
- **AND** it returns an OpenAI-format error envelope with `type = "invalid_request_error"`, `code = "provider_continuity_unsupported"`, and a `param` pointing to the offending continuity field when one exists

#### Scenario: route or feature mismatch returns a stable code
- **WHEN** a request is rejected because the selected provider does not support the requested route family or feature such as compact or backend Codex
- **THEN** the service returns HTTP `400`
- **AND** it returns an OpenAI-format error envelope with `type = "invalid_request_error"` and `code = "provider_feature_unsupported"`

#### Scenario: fallback prerequisite returns a stable code
- **WHEN** a request is rejected because `openai_platform` is configured but no eligible `chatgpt_web` routing subject exists for fallback
- **THEN** the service returns HTTP `400`
- **AND** it returns an OpenAI-format error envelope with `type = "invalid_request_error"` and `code = "provider_fallback_requires_chatgpt"`
### Requirement: Use prompt_cache_key as OpenAI cache affinity
For OpenAI-style `/v1/responses`, `/v1/responses/compact`, and chat-completions requests mapped onto Responses, the service MUST treat a non-empty `prompt_cache_key` as a bounded upstream target affinity key for prompt-cache correctness even when a `session_id` header is present. OpenAI-style route wiring MUST NOT upgrade those requests to durable `CODEX_SESSION` affinity by default. When the selected upstream provider is `chatgpt_web`, this continues to mean bounded upstream account affinity. When the selected upstream provider is `openai_platform`, it MUST preserve affinity to the selected provider-scoped routing target without implying ChatGPT-specific session continuity or widening the request's capability set. This affinity MUST apply even when dashboard `sticky_threads_enabled` is disabled, the service MUST continue forwarding the same `prompt_cache_key` upstream unchanged, and the stored affinity MUST expire after the configured freshness window so older keys can rebalance. The freshness window MUST come from dashboard settings so operators can adjust it without restart.

#### Scenario: OpenAI-style route ignores session header for durable codex-session pinning
- **WHEN** a client sends `/v1/responses` or `/v1/responses/compact` with a non-empty `session_id` header and no explicit sticky-thread mode
- **THEN** the service does not persist a durable `codex_session` mapping solely from that header
- **AND** bounded prompt-cache affinity behavior remains in effect

#### Scenario: recent /v1 responses request reuses prompt-cache affinity
- **WHEN** a client sends repeated `/v1/responses` requests with the same non-empty `prompt_cache_key` while `sticky_threads_enabled` is disabled
- **AND** the previous mapping is still within the configured freshness window
- **THEN** the service selects the same upstream routing target for those requests

#### Scenario: recent /v1 compact request reuses prompt-cache affinity
- **WHEN** a client sends `/v1/responses/compact` after `/v1/responses` with the same non-empty `prompt_cache_key` while `sticky_threads_enabled` is disabled
- **AND** the previous mapping is still within the configured freshness window
- **THEN** the compact request reuses the previously selected upstream routing target

#### Scenario: expired prompt-cache affinity rebalances
- **WHEN** a client sends a later OpenAI-style request with the same non-empty `prompt_cache_key`
- **AND** the stored mapping is older than the configured freshness window
- **THEN** the service ignores the stale mapping, re-runs account selection, and stores a fresh mapping for the chosen account

#### Scenario: dashboard prompt-cache affinity TTL is applied
- **WHEN** an operator updates the dashboard prompt-cache affinity TTL
- **THEN** subsequent OpenAI-style prompt-cache affinity decisions use the new freshness window

#### Scenario: Platform prompt-cache affinity reuses the same provider target
- **WHEN** a client sends repeated stateless HTTP `/v1/responses` requests with the same non-empty `prompt_cache_key`
- **AND** the selected upstream provider is `openai_platform`
- **AND** the existing mapping is still within the configured freshness window
- **THEN** the service reuses the same provider-scoped routing target for those requests

#### Scenario: Prompt-cache affinity does not suppress a drained public fallback decision
- **WHEN** a public stateless HTTP request carries a bounded `prompt_cache_key` affinity
- **AND** no compatible ChatGPT-web candidate remains selectable and above the configured fallback thresholds
- **THEN** the service MAY route the request to `openai_platform`
- **AND** prompt-cache affinity alone MUST NOT keep the request on ChatGPT

### Requirement: HTTP Responses routes preserve upstream continuity only for providers that advertise it
When the selected upstream provider exposes durable upstream continuity for HTTP Responses routes, the service MUST preserve that continuity on a stable bridge key. When the selected upstream provider does not expose equivalent continuity semantics for the requested route family, the service MUST NOT synthesize ChatGPT-style continuity or silently open a different provider contract to satisfy the request.

#### Scenario: sequential HTTP /v1/responses requests reuse the same bridged upstream session
- **WHEN** a client sends repeated HTTP `/v1/responses` requests with the same stable bridge key
- **THEN** the service reuses one upstream websocket session for those requests instead of opening a fresh upstream session per request

#### Scenario: sequential backend Codex HTTP requests reuse the same bridged upstream session
- **WHEN** a client sends repeated HTTP `/backend-api/codex/responses` requests with the same stable bridge key
- **THEN** the service reuses one upstream websocket session for those requests instead of opening a fresh upstream session per request

#### Scenario: HTTP previous_response_id remains valid within a bridged /v1 session
- **WHEN** a client sends a later HTTP `/v1/responses` request with `previous_response_id` that references a response created earlier on the same bridged session
- **THEN** the service forwards that request through the same upstream websocket session so upstream can resolve the referenced prior response

#### Scenario: backend Codex HTTP previous_response_id remains valid within a bridged session
- **WHEN** a client sends a later HTTP `/backend-api/codex/responses` request with `previous_response_id` that references a response created earlier on the same bridged session
- **THEN** the service forwards that request through the same upstream websocket session so upstream can resolve the referenced prior response

#### Scenario: HTTP previous_response_id fails closed when bridged continuity is unavailable
- **WHEN** a client sends HTTP `/v1/responses` or `/backend-api/codex/responses` with `previous_response_id`
- **AND** there is no matching live bridged upstream websocket session for that continuity key
- **THEN** the service MUST fail the request without opening a fresh upstream session
- **AND** it MUST return `previous_response_not_found` on `previous_response_id`

#### Scenario: bridged HTTP requests keep external HTTP transport logging
- **WHEN** the service fulfills an HTTP `/v1/responses` or `/backend-api/codex/responses` request through an internal upstream websocket bridge
- **THEN** the persisted request log still records `transport = "http"`

#### Scenario: clean upstream close forces a fresh bridged session
- **WHEN** an existing bridged upstream websocket closes cleanly after prior HTTP `/v1/responses` or `/backend-api/codex/responses` work completes
- **THEN** the next compatible HTTP request for that same bridge key opens a fresh upstream websocket session instead of reusing the closed session

#### Scenario: active bridge pool exhaustion fails fast without evicting live sessions
- **WHEN** the HTTP Responses bridge pool has reached its configured maximum session count
- **AND** every existing bridge session still has pending in-flight requests
- **THEN** the service MUST NOT evict those active bridge sessions
- **AND** it MUST fail the new request fast with `429 rate_limit_exceeded`

#### Scenario: HTTP responses route emits a turn-state header for later continuity
- **WHEN** a client sends an HTTP `/v1/responses` or `/backend-api/codex/responses` request without `x-codex-turn-state`
- **THEN** the service returns an `x-codex-turn-state` response header
- **AND** replaying that header on a later compatible request upgrades the bridge key to Codex-session affinity

#### Scenario: codex-session bridge sessions outlive prompt-cache sessions
- **WHEN** an HTTP `/v1/responses` bridge session is keyed by Codex turn/session affinity
- **THEN** the service applies the longer Codex bridge idle TTL instead of the generic prompt-cache TTL
- **AND** when idle eviction is required the service prefers evicting non-Codex prompt-cache bridge sessions before idle Codex-affinity bridge sessions

#### Scenario: optional Codex-affinity bridge prewarm stays behind an explicit flag
- **WHEN** an HTTP `/v1/responses` bridge session is keyed by Codex turn/session affinity
- **AND** Codex bridge prewarm is disabled
- **THEN** the first client-visible request is sent upstream directly without an extra internal warmup request

#### Scenario: enabled Codex-affinity bridge prewarm preserves the HTTP contract
- **WHEN** an HTTP `/v1/responses` bridge session is keyed by Codex turn/session affinity
- **AND** Codex bridge prewarm is enabled
- **AND** the first request on that session does not already reference `previous_response_id`
- **THEN** the service sends one internal `response.create` prewarm with `generate=false` before the client-visible request
- **AND** the client-visible response contract remains unchanged

#### Scenario: bridge enforces deterministic owner instance for hard continuity keys
- **WHEN** operators configure multiple eligible bridge instance ids
- **AND** a request uses a bridge key derived from `x-codex-turn-state` or an explicit session header
- **AND** that request lands on a non-owner instance
- **THEN** the service fails the request fast with `bridge_instance_mismatch`
- **AND** it MUST NOT create a fresh local bridge session for that key on the wrong instance

#### Scenario: gateway-safe prompt-cache bridge requests tolerate wrong-replica arrival
- **WHEN** operators enable HTTP bridge gateway-safe mode
- **AND** a request uses a bridge key derived only from `prompt_cache_key` or a derived prompt-cache key
- **AND** that request lands on a non-owner instance
- **THEN** the service MAY create or reuse a local bridge session on that instance
- **AND** it MUST NOT return `bridge_instance_mismatch` solely because prompt-cache locality was missed

#### Scenario: ChatGPT-web continuity remains unchanged
- **WHEN** the selected upstream provider is `chatgpt_web`
- **THEN** existing HTTP bridge reuse and `previous_response_id` continuity guarantees continue to apply

#### Scenario: Platform continuity-dependent request fails closed when parity is unavailable
- **WHEN** the selected upstream provider is `openai_platform`
- **AND** a request depends on provider-owned continuity semantics that are not implemented for that provider in phase 1
- **THEN** the service rejects the request with code `provider_continuity_unsupported`
- **AND** it does so before upstream transport start
- **AND** it MUST NOT create a fake ChatGPT-style bridge session on the client's behalf

#### Scenario: Platform-only public-route operation is not allowed
- **WHEN** a request targets an eligible public HTTP route
- **AND** an `openai_platform` identity exists
- **AND** there is no compatible `chatgpt_web` pool available for the deployment
- **THEN** the service MUST NOT execute the request through Platform alone
- **AND** it fails closed with code `provider_fallback_requires_chatgpt`

### Requirement: Websocket responses advertise and honor Codex turn-state affinity
When serving websocket Responses endpoints, the service MUST advertise an `x-codex-turn-state` header during websocket accept. If the client reconnects and presents that same `x-codex-turn-state`, the service MUST treat it as the highest-priority Codex-affinity key for upstream routing on that websocket turn. On `/v1/responses`, a proxy-generated turn-state MUST NOT override the first request's prompt-cache routing unless the client explicitly sends the turn-state back.

#### Scenario: backend websocket generates a turn-state for native Codex clients
- **WHEN** a client opens `/backend-api/codex/responses` without an existing `x-codex-turn-state`
- **THEN** the websocket accept response includes a generated non-empty `x-codex-turn-state`
- **AND** the proxy uses that same generated turn-state as the Codex session affinity key for the upstream websocket

#### Scenario: websocket reconnect honors client-provided turn-state
- **WHEN** a client opens a websocket Responses route and provides `x-codex-turn-state`
- **THEN** the websocket accept response echoes that same turn-state
- **AND** the proxy uses that same turn-state as the Codex session affinity key

### Requirement: Auto websocket fallback remains narrow and explicit
When automatic upstream transport selection prefers websocket, the service MUST only downgrade to HTTP automatically on `426 Upgrade Required`. Handshake failures such as `403 Forbidden` or `404 Not Found` MUST surface as upstream errors instead of silently falling back to HTTP.

#### Scenario: forbidden websocket handshake does not silently downgrade
- **WHEN** auto transport chooses websocket and upstream rejects the websocket handshake with `403`
- **THEN** the service returns an upstream error
- **AND** it MUST NOT retry the same request over HTTP automatically

### Requirement: Normalize prompt cache aliases for upstream compatibility
Before forwarding Responses payloads upstream, the service MUST normalize OpenAI-compatible camelCase prompt cache controls so codex-lb applies compatibility behavior consistently. The service MUST forward `promptCacheKey` as `prompt_cache_key`, and MUST treat `promptCacheRetention` the same as `prompt_cache_retention` for stripping behavior.

#### Scenario: camelCase prompt cache fields provided
- **WHEN** a client sends `promptCacheKey` or `promptCacheRetention` on a valid Responses request
- **THEN** the service forwards `prompt_cache_key` with the same value and does not forward `prompt_cache_retention`

### Requirement: Sanitize unsupported interleaved and legacy chat input fields
Before forwarding Responses requests upstream, the service MUST remove unsupported interleaved reasoning and legacy chat fields from `input` items and content parts. The service MUST strip `reasoning_content`, `reasoning_details`, `tool_calls`, and `function_call` fields when they appear in `input` structures, and MUST remove unsupported reasoning-only content parts that are not accepted by upstream.

#### Scenario: Interleaved reasoning and legacy chat fields in input item
- **WHEN** a request includes an input item containing `reasoning_content`, `reasoning_details`, `tool_calls`, or `function_call`
- **THEN** the service strips those fields before forwarding upstream

#### Scenario: Unsupported reasoning-only content part in input
- **WHEN** a request includes a content part that represents interleaved reasoning-only payload
- **THEN** the service removes that content part before forwarding upstream

### Requirement: Preserve supported top-level reasoning controls
When sanitizing interleaved reasoning input fields, the service MUST preserve supported top-level reasoning controls (`reasoning.effort`, `reasoning.summary`) and continue forwarding them unchanged.

#### Scenario: Top-level reasoning with interleaved input fields
- **WHEN** a request includes top-level `reasoning` plus interleaved reasoning fields inside `input`
- **THEN** top-level `reasoning` is preserved while unsupported `input` fields are removed

### Requirement: Normalize assistant text content part types for upstream compatibility
Before forwarding Responses requests upstream, the service MUST normalize assistant-role text content parts in `input` so they use `output_text` (not `input_text`) to satisfy upstream role-specific validation.

#### Scenario: Assistant input message uses input_text
- **WHEN** a request includes an `input` message with `role: "assistant"` and a text content part typed as `input_text`
- **THEN** the service rewrites that content part type to `output_text` before forwarding upstream

### Requirement: Normalize tool message history for upstream compatibility
Before forwarding Responses requests upstream, the service MUST normalize tool-role message history into Responses-native function call output items. Tool messages MUST include a non-empty call identifier and MUST be rewritten as `type: "function_call_output"` with the same call identifier.

#### Scenario: Tool message in conversation history
- **WHEN** a request includes a message with `role: "tool"`, `tool_call_id`, and text content
- **THEN** the service rewrites it to a `function_call_output` input item using `call_id` and tool output text before forwarding upstream

### Requirement: Reject unsupported message roles with client errors
When coercing v1 `messages` into Responses input, the service MUST reject messages that do not include a string role or use an unsupported role value.

#### Scenario: Unsupported message role
- **WHEN** a request includes a message role outside the supported set
- **THEN** the service returns a client-facing invalid payload error referencing `messages`

### Requirement: Strip proxy identity headers before upstream forwarding
Before forwarding requests to the upstream Responses endpoint, the service MUST strip network/proxy identity headers derived from downstream edges. The service MUST remove `Forwarded`, `X-Forwarded-*`, `X-Real-IP`, `True-Client-IP`, and `CF-*` headers, and MUST continue to set upstream auth/account headers from internal account state.

#### Scenario: Request contains reverse-proxy forwarding headers
- **WHEN** the inbound request includes headers such as `X-Forwarded-For`, `X-Forwarded-Proto`, `Forwarded`, or `X-Real-IP`
- **THEN** those headers are not forwarded to upstream

#### Scenario: Request contains Cloudflare identity headers
- **WHEN** the inbound request includes headers such as `CF-Connecting-IP` or `CF-Ray`
- **THEN** those headers are not forwarded to upstream

### Requirement: Codex backend session_id preserves account affinity
When a backend Codex Responses or compact request includes a non-empty `session_id` header, the service MUST use that value as the routing affinity key for upstream account selection. This affinity MUST apply even when dashboard `sticky_threads_enabled` is disabled.

#### Scenario: Codex Responses request with session_id and sticky threads disabled
- **WHEN** `/backend-api/codex/responses` is called with a non-empty `session_id` header and `sticky_threads_enabled=false`
- **THEN** the selected upstream account is pinned to that `session_id` for later backend Codex requests on the same thread

#### Scenario: Compact request reuses pinned Codex session account
- **WHEN** `/backend-api/codex/responses/compact` is called with the same non-empty `session_id` header after routing preferences change
- **THEN** the service reuses the previously pinned upstream account for that thread instead of reallocating to a different account

#### Scenario: Compact retry uses refreshed provider account identity
- **WHEN** a pinned backend Codex compact request gets a `401` from upstream, refreshes the selected account, and retries
- **THEN** the retry forwards the refreshed account's `chatgpt-account-id` header instead of reusing the pre-refresh account header

### Requirement: Compact requests preserve upstream compaction semantics
The service MUST preserve the selected provider's native compact contract for `/backend-api/codex/responses/compact` and `/v1/responses/compact`. To preserve provider-owned remote compaction semantics, the service MUST fulfill compact requests by calling the selected provider's native compact endpoint directly and returning the upstream JSON payload as the canonical next context window without converting it into a standard buffered Responses result. The service MUST preserve provider-owned compact payload contents without pruning, reordering, or rewriting returned context items beyond generic JSON serialization. While using this direct compact transport, the service MUST preserve compact account-selection semantics, `session_id` affinity, `prompt_cache_key` affinity, bounded same-contract retries, API key settlement, and HTTP request logging. The service MUST reject `store=true` as a client payload error, and it MUST omit `store` from the direct upstream compact request instead of forwarding `store=false`. If direct upstream compact execution fails before a valid compact JSON payload is accepted, the service MUST keep the request inside the selected provider's compact contract. It MUST NOT silently substitute a standard `/responses` request, reconstruct compact output from streamed Responses events, or synthesize a compact window locally. The service MAY apply provider-specific transport timeouts and bounded retries only against the selected provider's compact endpoint when the failure occurs in a provably safe transport phase before a valid compact JSON payload is accepted.

#### Scenario: Compact request returns raw upstream compaction payload
- **WHEN** a compact request succeeds and the selected provider's compact endpoint returns `object: "response.compaction"`
- **THEN** the service returns that JSON payload without rewriting it into `object: "response"`

#### Scenario: Compact request preserves provider-owned compaction summary
- **WHEN** the upstream compact response includes nested compaction fields such as `compaction_summary.encrypted_content`
- **THEN** the service returns those nested fields unchanged in the final JSON response

#### Scenario: Compact response includes retained items and encrypted compaction state
- **WHEN** the upstream compact response returns a window that includes retained context items plus provider-owned compaction state such as encrypted content
- **THEN** the service returns that window unchanged to the client

#### Scenario: Compact response object shape differs from normal Responses
- **WHEN** the upstream compact response uses a provider-owned compact object shape instead of a standard `object: "response"` payload
- **THEN** the service returns that compact object shape unchanged instead of coercing it into a normal Responses payload

#### Scenario: Direct compact request omits store
- **WHEN** a client sends `/backend-api/codex/responses/compact` or `/v1/responses/compact` without a `store` field
- **THEN** the selected provider-native compact request omits `store`

#### Scenario: Direct compact request sets store true
- **WHEN** a client sends `/backend-api/codex/responses/compact` or `/v1/responses/compact` with `store=true`
- **THEN** the service returns a 4xx OpenAI invalid payload error
- **AND** it does not forward any `store` field upstream

#### Scenario: Direct compact upstream returns an error envelope
- **WHEN** the selected provider-native compact request returns a non-2xx OpenAI-format error payload
- **THEN** the service propagates the corresponding HTTP status and error envelope to the client

#### Scenario: Backend Codex compact falls back to public Platform compact transport
- **WHEN** a client sends `/backend-api/codex/responses/compact`
- **AND** the selected upstream provider is `openai_platform`
- **THEN** the service translates the request onto the public Platform compact contract
- **AND** it still returns the resulting compact payload unchanged to the backend Codex client

#### Scenario: Direct compact transport fails before response body is available
- **WHEN** the selected provider's compact call times out, disconnects, or otherwise fails before yielding a valid compact JSON payload
- **THEN** the service may retry only that provider's compact endpoint within a bounded retry budget
- **AND** it does not attempt a surrogate standard `/responses` request

#### Scenario: Direct compact transport gets a safe retryable upstream failure
- **WHEN** the selected provider's compact call fails with `401`, `502`, `503`, or `504` before a valid compact JSON payload is accepted
- **THEN** the service may retry only that provider's compact endpoint
- **AND** it preserves the request's established compact routing and affinity semantics except for refreshed provider identity on `401`
- **AND** it does not call a standard `/responses` endpoint

#### Scenario: Direct compact response payload is invalid
- **WHEN** the selected provider's compact call returns a non-error payload that is not valid compact JSON for pass-through
- **THEN** the service returns an upstream error to the client
- **AND** it does not retry via a standard `/responses` endpoint
- **AND** it does not synthesize or reconstruct a replacement compact window

#### Scenario: ChatGPT compact request uses no timeout by default
- **WHEN** `/responses/compact` is routed to the `chatgpt_web` compact endpoint
- **AND** no compact timeout override is configured
- **THEN** the service forwards the request without setting an upstream total or read timeout

### Requirement: Persist request log transport for Responses requests
The service MUST persist a stable `transport` value on `request_logs` for Responses proxy requests and MUST expose the same value through `/api/request-logs`. Requests accepted over HTTP on `/backend-api/codex/responses` or `/v1/responses` MUST persist `transport = "http"`. Requests accepted over WebSocket on those paths MUST persist `transport = "websocket"`.

#### Scenario: HTTP Responses request logs http transport
- **WHEN** a client completes a Responses request over HTTP on `/backend-api/codex/responses` or `/v1/responses`
- **THEN** the persisted request log has `transport = "http"`
- **AND** `/api/request-logs` returns that row with `transport = "http"`

#### Scenario: WebSocket Responses request logs websocket transport
- **WHEN** a client completes a Responses request over WebSocket on `/backend-api/codex/responses` or `/v1/responses`
- **THEN** the persisted request log has `transport = "websocket"`
- **AND** `/api/request-logs` returns that row with `transport = "websocket"`

### Requirement: Emit opt-in safe service-tier trace logs
When service-tier trace logging is enabled, the service MUST emit a diagnostic log entry for Responses requests that records `request_id`, request `kind`, `requested_service_tier`, and upstream `actual_service_tier`. The diagnostic log MUST NOT include prompt text, input content, or the full request payload.

#### Scenario: Streaming request logs requested and actual service tiers
- **WHEN** a streaming Responses request is sent with `service_tier: "priority"` and the upstream stream reports `response.service_tier: "default"`
- **THEN** the service emits a diagnostic log entry containing `requested_service_tier=priority` and `actual_service_tier=default`

#### Scenario: Compact request keeps actual tier empty when upstream omits it
- **WHEN** a compact Responses request is sent with `service_tier: "priority"` and the upstream JSON response omits `service_tier`
- **THEN** the service emits a diagnostic log entry containing `requested_service_tier=priority` and `actual_service_tier=None`

### Requirement: Streaming Responses requests use a bounded retry budget
When a streaming `/v1/responses` request encounters upstream instability, the proxy MUST enforce a configurable total request budget across selection, token refresh, and upstream stream attempts. The proxy MUST stop retrying once that budget is exhausted and MUST emit a stable `response.failed` event instead of waiting through repeated full upstream timeouts.

#### Scenario: Request budget expires before another attempt
- **WHEN** a streaming Responses request has consumed its configured request budget before the next retry attempt begins
- **THEN** the proxy emits `response.failed` with a stable timeout code
- **AND** the proxy does not start another upstream attempt

#### Scenario: Stalled stream fails within the shorter idle window
- **WHEN** the upstream opens a Responses stream but does not deliver events before the configured stream idle timeout elapses
- **THEN** the proxy emits `response.failed` for the stalled stream within that idle timeout
- **AND** the same client request does not consume multiple full idle windows retrying the same generic failure

### Requirement: Streaming Responses retries are limited to account-recoverable failures
The proxy MUST automatically retry streaming Responses requests only for failures that are recoverable by refreshing or rotating the selected account. The proxy MUST NOT automatically retry generic upstream failures such as stalled streams, upstream transport failures, or unspecified server errors.

#### Scenario: Account-specific rate limit triggers a retry
- **WHEN** the first upstream streaming event fails with an account-specific rate-limit or quota error that can be resolved by selecting another account
- **THEN** the proxy updates account state for that account
- **AND** the proxy may retry the request on another eligible account while budget remains

#### Scenario: Generic upstream failure does not trigger retry
- **WHEN** the first upstream streaming event fails with `stream_idle_timeout`, `upstream_unavailable`, or another generic upstream error
- **THEN** the proxy forwards that failure to the client
- **AND** the proxy does not automatically retry the same client request

### Requirement: Compact request-path latency is bounded without changing default CLI timeout parity
When `/responses/compact` performs account selection, token refresh, or upstream connection setup, the proxy MUST enforce a configurable request-path budget for those pre-response phases. The proxy MUST preserve the existing default compact behavior of not imposing an upstream read timeout unless an operator explicitly configures one.

#### Scenario: Compact request budget expires before upstream response handling begins
- **WHEN** a compact request exhausts its configured request-path budget during account selection, token refresh, or upstream connection setup
- **THEN** the proxy returns `502` with OpenAI-format error code `upstream_unavailable`
- **AND** it does not begin another retry attempt

#### Scenario: Default compact read path remains unbounded
- **WHEN** `/responses/compact` is called without an explicit compact read-timeout override
- **THEN** the proxy may still bound selection, refresh, and connect work
- **AND** it MUST NOT add a default upstream read timeout beyond the existing compact contract

### Requirement: Gated model selection failures expose stable proxy error codes
When account selection fails for an explicitly mapped gated model, the proxy MUST return a stable OpenAI-format error code that distinguishes plan support failures, stale additional-quota data, and zero eligible accounts. The canonical routed `quota_key` MUST drive those checks even if raw upstream `limit_name` aliases change.

#### Scenario: Missing fresh additional quota data returns a specific code
- **WHEN** a compact or streaming Responses request targets a mapped gated model and the latest persisted additional-usage snapshot for its canonical `quota_key` is unavailable or stale
- **THEN** the proxy returns an OpenAI-format error envelope with a stable code for unavailable additional quota data

#### Scenario: No eligible accounts returns a specific code
- **WHEN** a compact or streaming Responses request targets a mapped gated model and the canonical `quota_key` has fresh persisted data but no eligible accounts
- **THEN** the proxy returns an OpenAI-format error envelope with a stable code for zero eligible additional-quota accounts
### Requirement: Responses requests reject uploaded input_image references

The system SHALL accept `{"type":"input_file","file_id":"file_*"}` attached-file items in `/v1/responses`, `/backend-api/codex/responses`, and `/responses/compact` request payloads and forward them verbatim.

When an `input_image` part contains a `file_id` field or an `image_url` starting with `sediment://`, the proxy MUST return HTTP 400 with `error.code = "unsupported_input_image_format"` and an explanation that the upstream Responses API only accepts inline `data:` URLs for `input_image`. The proxy MUST NOT fetch the upload, MUST NOT inline-convert the image, and MUST NOT trim, slim, or rewrite any conversation content.

`app/core/openai/requests.py::extract_input_image_file_references` MAY be used to detect the unsupported shape. This request path MUST NOT fetch uploads, inline-convert images, or otherwise reshape inbound conversation payloads.

#### Scenario: input_image file_id is rejected before forwarding

- **WHEN** a `/v1/responses` request contains `{"type":"input_image","file_id":"file_img"}`
- **THEN** the proxy returns HTTP 400 with `error.code = "unsupported_input_image_format"`
- **AND** the response explains that inline `data:` URLs are the supported `input_image` contract

#### Scenario: sediment upload URL is rejected before forwarding

- **WHEN** a `/responses/compact` request contains `{"type":"input_image","image_url":"sediment://file_img"}`
- **THEN** the proxy returns HTTP 400 with `error.code = "unsupported_input_image_format"`
- **AND** does not fetch or inline-convert the upload

#### Scenario: large request payload routes via HTTP transport on auto

- **GIVEN** `upstream_stream_transport` is `"auto"` and the request payload size exceeds the WebSocket frame budget
- **WHEN** the proxy resolves the upstream transport
- **THEN** the request MUST be sent over HTTP `POST` instead of WebSocket
- **AND** explicit `upstream_stream_transport = "websocket"` overrides MUST still take precedence

#### Scenario: large request payload bypasses the HTTP responses bridge

- **GIVEN** the HTTP responses bridge is enabled and the request payload exceeds the WebSocket frame budget
- **WHEN** the proxy receives a `/v1/responses`, `/backend-api/codex/responses`, or `/responses/compact` request
- **THEN** the bridge MUST be bypassed for that request and the request MUST be sent over raw HTTP
- **AND** subsequent smaller requests MUST continue to use the bridge normally

### Requirement: Oversized responses request payloads fall back to HTTP
When `upstream_stream_transport` is `"auto"` and the serialized request payload size exceeds the WebSocket frame budget, the proxy MUST use upstream HTTP `POST` instead of WebSocket. If the HTTP responses bridge is enabled and the same oversized request would otherwise route through the bridge, the proxy MUST bypass the bridge for that request only and send it over raw HTTP. Explicit `upstream_stream_transport` overrides MUST still take precedence.

#### Scenario: large request payload routes via HTTP transport on auto
- **GIVEN** `upstream_stream_transport` is `"auto"` and the request payload size exceeds the WebSocket frame budget
- **WHEN** the proxy resolves the upstream transport
- **THEN** the request MUST be sent over HTTP `POST` instead of WebSocket
- **AND** explicit `upstream_stream_transport = "websocket"` overrides MUST still take precedence

#### Scenario: large request payload bypasses the HTTP responses bridge
- **GIVEN** the HTTP responses bridge is enabled and the request payload exceeds the WebSocket frame budget
- **WHEN** the proxy receives a `/v1/responses`, `/backend-api/codex/responses`, or `/responses/compact` request
- **THEN** the bridge MUST be bypassed for that request and the request MUST be sent over raw HTTP
- **AND** subsequent smaller requests MUST continue to use the bridge normally

### Requirement: Clean upstream close before any response event fails fast

When the HTTP responses bridge observes an upstream websocket close with `close_code = 1000` before any `response.*` event has been surfaced for the pending request, the proxy MUST classify the close as rejected input, surface HTTP 502 `upstream_rejected_input`, and MUST NOT trigger `retry_precreated` or `retry_fresh_upstream`.

#### Scenario: clean close before response.created is not retried

- **WHEN** upstream closes the HTTP responses bridge with `close_code = 1000` before any `response.*` event for the pending request
- **THEN** the proxy returns HTTP 502 with `error.code = "upstream_rejected_input"`
- **AND** does not transparently replay the pre-created request

### Requirement: Long Codex websocket turns tolerate extended upstream silence
The default compact request budget MUST be at least 180 seconds, and the default upstream stream idle timeout MUST be at least 600 seconds, so long-running Codex turns can survive expensive compaction or tool execution without a local proxy watchdog ending the turn prematurely.

#### Scenario: compact and stream watchdog defaults leave room for long turns
- **WHEN** the service starts with default configuration
- **THEN** `compact_request_budget_seconds` is at least 180 seconds
- **AND** `stream_idle_timeout_seconds` is at least 600 seconds

### Requirement: Upstream websocket drops penalize affected accounts
When an upstream websocket closes while one or more streamed response requests are pending and have not reached a terminal event, the proxy MUST record a transient upstream error for the account before surfacing `stream_incomplete` to those pending requests.

#### Scenario: websocket closes before pending responses complete
- **GIVEN** a streamed response request is pending on an upstream websocket
- **WHEN** the websocket closes before a terminal response event is observed
- **THEN** the pending request fails with `stream_incomplete`
- **AND** the account receives a transient upstream failure signal for routing

### Requirement: Single HTTP bridge previous-response misses recover or fail closed
When an HTTP bridge session receives an anonymous upstream `previous_response_not_found` error for a single pending follow-up request, the service MUST treat the error as an internal continuity-loss signal. It MUST either recover through the existing previous-response rebind path or rewrite the error to a retryable continuity failure instead of forwarding the raw upstream invalid-request error.

#### Scenario: single pending HTTP bridge follow-up loses previous-response continuity
- **WHEN** an HTTP `/v1/responses` or `/backend-api/codex/responses` bridge session has exactly one pending request with `previous_response_id`
- **AND** upstream emits `previous_response_not_found` without a `response.id`
- **THEN** the service attempts the existing previous-response recovery path
- **AND** if recovery is unavailable, it emits a retryable continuity failure for that request
- **AND** the downstream error code is not `previous_response_not_found`

### Requirement: WebSocket full-resend previous-response misses retry without stale anchor
When a direct WebSocket `response.create` request includes both `previous_response_id` and a full resend payload, the service MUST retain a safe replay body without `previous_response_id`. If upstream rejects the anchor with `previous_response_not_found` before `response.created`, the service MUST reconnect and replay the retained full payload as a fresh turn instead of forwarding the raw upstream invalid-request error.

#### Scenario: full-resend WebSocket follow-up loses just-completed anchor
- **WHEN** a WebSocket `/v1/responses` or `/backend-api/codex/responses` follow-up has `previous_response_id`
- **AND** the request payload also carries enough input to be treated as a full resend
- **AND** upstream emits `previous_response_not_found` before assigning a response id
- **THEN** the service reconnects the upstream WebSocket
- **AND** it replays the same request without `previous_response_id`
- **AND** the downstream client receives the recovered response events, not the raw `previous_response_not_found` error

### Requirement: Public Responses errors mask previous-response misses
Public Responses endpoints MUST NOT return an OpenAI-shaped `previous_response_not_found` error to clients. If a lower layer still raises or collects that error, the API layer MUST rewrite it to a retryable `stream_incomplete` continuity failure and remove the missing response id from the public payload.

#### Scenario: API layer receives an upstream previous-response miss
- **WHEN** a public `/responses`, `/v1/responses`, `/responses/compact`, or `/v1/responses/compact` handler receives an error with `code=previous_response_not_found`
- **OR** it receives `code=invalid_request_error` with `param=previous_response_id` and a message saying the previous response was not found
- **THEN** the response status is retryable
- **AND** the public error code is `stream_incomplete`
- **AND** the missing `previous_response_id` is not exposed in the response body

### Requirement: Public /v1 responses SSE stream emits only OpenAI Responses contract events
When serving streaming `POST /v1/responses`, the service MUST emit only event types defined by the OpenAI Responses SSE contract (the `response.*` and `error` families) on the public stream. The service MUST drop any vendor-internal event types — specifically, any event whose `type` begins with `codex.` (for example `codex.rate_limits`) — before they reach the public stream. The `/backend-api/codex/*` routes are NOT subject to this requirement and MUST continue forwarding these events unchanged.

#### Scenario: Codex-internal rate-limit event is dropped before response.created
- **WHEN** the upstream Codex backend emits `codex.rate_limits` before `response.created` for a streaming `/v1/responses` request
- **THEN** the public stream MUST NOT contain the `codex.rate_limits` event
- **AND** the first event the public stream emits MUST be `response.created`

#### Scenario: Codex-internal events on the Codex CLI route are preserved
- **WHEN** the upstream emits `codex.rate_limits` for a `POST /backend-api/codex/responses` request
- **THEN** the response stream forwards the `codex.rate_limits` event to the Codex CLI client unchanged

### Requirement: Streamed /v1 responses terminal output is backfilled from item events
When serving streaming `POST /v1/responses`, if the upstream's terminal `response.completed` or `response.incomplete` event carries `output` as missing or as an empty list, the service MUST reconstruct `output` from the `response.output_item.done` events emitted earlier in the same stream before yielding the terminal SSE event. The reconstructed `output` MUST preserve the `output_index` ordering and the raw item payloads. When the terminal `response.completed` / `response.incomplete` already carries a non-empty `output`, the service MUST forward it unchanged.

#### Scenario: Terminal response.completed with empty output is backfilled from streamed items
- **GIVEN** the upstream emits `response.output_item.done` events with valid message or function-call items
- **WHEN** the upstream's terminal `response.completed` event carries `output: []`
- **THEN** the public stream's terminal `response.completed` event MUST carry the reconstructed `output` array, populated from the streamed `output_item.done` items in `output_index` order
- **AND** an OpenAI Python SDK consumer calling `stream.get_final_response().output` MUST receive the same populated list

#### Scenario: Terminal response.completed already carries output
- **WHEN** the upstream's terminal `response.completed` event already includes a non-empty `output` array
- **THEN** the public stream's terminal event MUST carry that `output` array unchanged

### Requirement: Public /v1 responses SSE stream starts with response.created
When serving streaming `POST /v1/responses`, the first OpenAI-contract event the public stream emits MUST be `response.created`. When the upstream's first standard `response.*` event is not `response.created` (for example when the Codex backend jumps directly to `response.failed` on upstream rejection mid-stream), the service MUST synthesize a `response.created` SSE event from the source event's `response` envelope and emit it before forwarding the source event, so that consumers using the OpenAI Python SDK's `responses.stream(...)` parser do not raise `RuntimeError`.

#### Scenario: Upstream error stream that skips response.created is repaired
- **WHEN** the upstream's first standard event is `response.failed` (no preceding `response.created`)
- **THEN** the public stream MUST emit a synthesized `response.created` event derived from the failed event's `response` envelope before forwarding the `response.failed` event
- **AND** an OpenAI Python SDK consumer iterating the stream MUST NOT raise `RuntimeError` from the parser's initial-response check

#### Scenario: Normal stream is not double-emitted
- **WHEN** the upstream's first standard event is already `response.created`
- **THEN** the public stream MUST emit exactly one `response.created` event (no synthesized duplicate)

### Requirement: Upstream overload envelopes are classified as retryable transient failures

When `classify_upstream_failure` observes an upstream error envelope whose `code` is `overloaded_error`, the system MUST treat it as `retryable_transient` regardless of the accompanying HTTP status. Streamed Responses API traffic can deliver the overload envelope on a connection that has already returned HTTP 200, so a 5xx-only heuristic is insufficient to drive account fail-over and bounded retry.

#### Scenario: `overloaded_error` without a 5xx status is retryable transient

- **WHEN** `classify_upstream_failure` is called with `error_code="overloaded_error"` and `http_status` not in the 5xx range (including `None`)
- **THEN** the returned `failure_class` is `retryable_transient`
- **AND** the failover layer is eligible to retry the request or fail over to another account instead of returning a non-retryable error to the client

#### Scenario: `overloaded_error` with a 5xx status remains retryable transient

- **WHEN** `classify_upstream_failure` is called with `error_code="overloaded_error"` and `http_status` is 500, 502, 503, or 504
- **THEN** the returned `failure_class` is `retryable_transient`
- **AND** the result is the same as the no-status path, so the 5xx fallback heuristic is not the only signal driving the decision

### Requirement: Strict function tool parameter schemas are pre-validated

The service MUST pre-validate the JSON schema attached to a function tool when that tool sets `strict: true`, before opening any upstream connection. The validation rules mirror OpenAI's Structured Outputs strict-mode policy (https://platform.openai.com/docs/guides/structured-outputs) and the existing `enforce_strict_text_format` policy for `text.format.json_schema`:

- Every `object` schema node MUST set `additionalProperties: false`.
- Every property under `properties` MUST appear in `required`.
- Every schema node MUST carry a `type` key (no empty `{}` schemas).
- The same rules apply recursively to nested object / array / combinator (`anyOf` / `oneOf` / `allOf`) schemas.

When any of those rules is violated, the service MUST reject the request with `HTTP 400 invalid_request_error` carrying:

- `error.code = "invalid_function_parameters"`
- `error.message = "Invalid schema for function '<name>': In context=<path>, <reason>."`
- `error.param = "tools[<index>].parameters"` for native Responses-API requests; `error.param = "tools[<index>].function.parameters"` for chat-completions requests routed through the coercion pipeline.

This brings strict function tool schema handling into parity with `text.format.json_schema`. Without it, an invalid strict tool schema reaches the upstream Codex backend, which closes the WebSocket with `close_code=1000` and surfaces as a generic `502 server_error / upstream_rejected_input`. Real OpenAI returns `400 invalid_function_parameters` for the identical payload. A 5xx on a deterministically-broken request also triggers retry / failover loops in well-behaved clients.

#### Scenario: Strict tool missing `additionalProperties` is rejected with 400

- **WHEN** a client sends `tools: [{"type": "function", "name": "f", "parameters": {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}, "strict": true}]`
- **THEN** the proxy returns `HTTP 400` with `error.code = "invalid_function_parameters"`, `error.message` matching `/Invalid schema for function 'f': In context=\(\), 'additionalProperties' is required to be supplied and to be false\./`, and `error.param = "tools[0].parameters"`

#### Scenario: Strict tool with `additionalProperties: true` is rejected

- **WHEN** a client sends a function tool with `strict: true` and `parameters.additionalProperties = true`
- **THEN** the proxy returns `HTTP 400 invalid_function_parameters` with the same `'additionalProperties' is required to be supplied and to be false` message

#### Scenario: Strict tool with property missing from `required` is rejected

- **WHEN** a client sends a function tool with `strict: true`, `additionalProperties: false`, but `required` omits one of the listed `properties`
- **THEN** the proxy returns `HTTP 400 invalid_function_parameters` with the `'required' is required to be supplied and to be an array including every key in properties` message

#### Scenario: Compliant strict tool is accepted

- **WHEN** a client sends a function tool with `strict: true`, `additionalProperties: false`, and every property listed in `required`
- **THEN** the proxy forwards the request to the upstream unchanged and the response is `200`

#### Scenario: `strict: false` or omitted strict skips pre-validation

- **WHEN** a client sends a function tool with `strict: false` or without a `strict` key, and the schema would have violated strict mode (e.g. missing `additionalProperties`)
- **THEN** the proxy does not run the strict pre-validation and forwards the request unchanged, matching pre-fix behavior for non-strict tools

### Requirement: Same-response side-effect tool-call replays are suppressed

When the proxy receives multiple downstream `response.output_item.done` events for the same response that describe the same side-effecting local tool operation, the proxy SHALL forward only the first event to the client.

The proxy SHALL treat `exec_command`, `write_stdin`, `multi_tool_use.parallel`, and `apply_patch_call` events as side-effecting. For these tools, a changed `call_id` alone MUST NOT make a same-response replay distinct.

When a `multi_tool_use.parallel` event contains duplicate nested side-effect operations, the proxy SHALL remove the duplicate nested operations before forwarding the event. Duplicate nested `exec_command` operations MUST ignore volatile output/wait fields such as `yield_time_ms` and `max_output_tokens`. Duplicate nested `write_stdin` operations MUST be scoped by `session_id` and `chars`. Duplicate nested `wait_agent` operations MUST be scoped by the target set.

Read-only function calls and matching operations under different response ids MUST continue to pass through.

#### Scenario: side-effect call replay uses a new call id

- **WHEN** a streamed response emits two `exec_command` output items with the same response id and arguments but different call ids
- **THEN** the proxy forwards the first event
- **AND** suppresses the second event

#### Scenario: read-only call ids stay distinct

- **WHEN** a streamed response emits two read-only function calls with the same arguments and different call ids
- **THEN** the proxy forwards both events

#### Scenario: later response ids stay distinct

- **WHEN** two responses emit the same side-effecting operation under different response ids
- **THEN** the proxy forwards both events

#### Scenario: parallel batch contains duplicate shell operations

- **WHEN** a `multi_tool_use.parallel` event contains two nested `functions.exec_command` operations with the same command and only different wait/output fields
- **THEN** the proxy forwards one nested operation inside the parallel batch
- **AND** does not forward the duplicate nested operation to the client

### Requirement: Continuity-dependent Responses follow-ups fail closed with retryable errors
When a Responses follow-up depends on previously established continuity state, the service MUST return a retryable continuity error if that continuity cannot be reconstructed safely. The service MUST NOT expose raw `previous_response_not_found` for bridge-local metadata loss or similar internal continuity gaps.

#### Scenario: HTTP bridge loses local continuity metadata for a follow-up request
- **WHEN** an HTTP `/v1/responses` or `/backend-api/codex/responses` follow-up request depends on `previous_response_id` or a hard continuity turn-state
- **AND** the bridge cannot reconstruct the matching live continuity state from local or durable metadata
- **THEN** the service returns a retryable OpenAI-format error
- **AND** the error code is not `previous_response_not_found`

#### Scenario: in-flight bridge follower loses continuity while waiting on the same canonical session
- **WHEN** a follow-up request waits on an in-flight HTTP bridge session for the same hard continuity key
- **AND** the bridge still cannot reconstruct safe continuity state once the leader finishes
- **THEN** the service returns a retryable OpenAI-format error
- **AND** the error code is not `previous_response_not_found`

#### Scenario: multiplexed follow-ups fail closed only for the matching continuity anchor
- **WHEN** a websocket or HTTP bridge session has multiple pending follow-up requests with different `previous_response_id` anchors
- **AND** continuity loss is detected for exactly one of those anchors
- **THEN** the service applies the retryable fail-closed continuity error only to the matching follow-up request
- **AND** it does not expose raw `previous_response_not_found`
- **AND** unrelated pending requests continue on their own response lifecycle

#### Scenario: multiplexed follow-ups sharing one anchor fail closed together without leaking raw continuity errors
- **WHEN** a websocket or HTTP bridge session has multiple pending follow-up requests that share the same `previous_response_id` anchor
- **AND** upstream emits an anonymous continuity loss event such as `previous_response_not_found` for that shared anchor
- **THEN** the service rewrites each affected follow-up into a retryable continuity error
- **AND** no affected follow-up exposes raw `previous_response_not_found`
- **AND** the run remains usable for subsequent requests after the rewritten failures

#### Scenario: single pre-created follow-up still fails closed when continuity loss omits explicit response id in message
- **WHEN** a websocket follow-up request is pending with `previous_response_id` and has not received a stable upstream `response.id` yet
- **AND** upstream emits `previous_response_not_found` with `param=previous_response_id`
- **AND** the upstream error message omits the literal previous response identifier
- **THEN** the service still maps that continuity loss to the pending follow-up
- **AND** it rewrites the downstream terminal event to a retryable continuity error
- **AND** it does not surface raw `previous_response_not_found` to the client

### Requirement: Hard continuity owner lookup fails closed
When a request depends on hard continuity ownership, the service MUST fail closed if owner or ring lookup errors prevent safe pinning. The service MUST NOT continue with local recovery or account selection that bypasses hard owner enforcement.

#### Scenario: websocket previous-response owner lookup errors
- **WHEN** a websocket or HTTP fallback follow-up request includes `previous_response_id`
- **AND** owner lookup errors prevent the proxy from determining the required owner account
- **THEN** the service returns a retryable OpenAI-format error
- **AND** it does not continue the request on an unpinned account

#### Scenario: bridge owner or ring lookup errors for hard continuity keys
- **WHEN** an HTTP bridge request uses a hard continuity key such as turn-state, explicit session affinity, or `previous_response_id`
- **AND** owner or ring lookup errors prevent the proxy from proving the correct bridge owner
- **THEN** the service returns a retryable OpenAI-format error
- **AND** it does not create or recover a local bridge session on the current replica

### Requirement: Request logs persist requested, actual, and billable service tiers separately
For Responses proxy traffic, the system MUST persist the operator-requested tier, the upstream-reported actual tier when available, and the effective billable tier used for pricing as separate request-log fields.

#### Scenario: Upstream reports a downgraded actual tier
- **WHEN** a client sends a Responses request with `service_tier: "priority"`
- **AND** the upstream response later reports `service_tier: "default"`
- **THEN** the persisted request log entry records `requested_service_tier = "priority"`
- **AND** the persisted request log entry records `actual_service_tier = "default"`
- **AND** the persisted request log entry records billable `service_tier = "default"`

#### Scenario: Upstream omits the actual tier
- **WHEN** a client sends a Responses request with `service_tier: "priority"`
- **AND** the upstream response omits `service_tier`
- **THEN** the persisted request log entry records `requested_service_tier = "priority"`
- **AND** the persisted request log entry records `actual_service_tier = null`
- **AND** the persisted request log entry records billable `service_tier = "priority"`

### Requirement: API key service tier enforcement applies to upstream Responses requests

When an API key carries an enforced service tier, the proxy MUST override any incoming Responses request service tier with that enforced value before forwarding upstream. The legacy alias `fast` MUST be treated as `priority`.

#### Scenario: Enforced service tier overrides the request payload

- **WHEN** an API key is configured with `enforcedServiceTier: "priority"`
- **AND** an incoming Responses request asks for `service_tier: "default"`
- **THEN** the forwarded upstream payload uses `service_tier: "priority"`

#### Scenario: Fast alias is applied as priority

- **WHEN** an API key is configured with `enforcedServiceTier: "fast"`
- **THEN** the forwarded upstream payload uses the canonical value `priority`

### Requirement: OpenAI-compatible Responses payload sanitation removes provider-specific thinking aliases

The shared OpenAI-compatible Responses sanitation path MUST normalize third-party thinking aliases into the canonical `reasoning` object before upstream forwarding. Unknown provider-specific thinking controls MUST NOT be passed through unchanged to the upstream ChatGPT backend.

#### Scenario: Shared payload sanitation maps enable_thinking

- **WHEN** an internal Responses payload contains `enable_thinking: true`
- **AND** no explicit `reasoning.effort` is already present
- **THEN** the forwarded upstream payload includes `reasoning.effort: "medium"`
- **AND** the forwarded upstream payload does not include `enable_thinking`

#### Scenario: Explicit reasoning wins over provider aliases

- **WHEN** an internal Responses payload contains both `reasoning: {"effort":"high"}` and `thinking: {"type":"enabled"}`
- **THEN** the forwarded upstream payload keeps `reasoning.effort: "high"`
- **AND** the forwarded upstream payload does not include `thinking`

### Requirement: Public Responses streams expose renderable final text
For OpenAI-style streaming `/v1/responses` and `/backend-api/codex/responses`, the service MUST expose renderable `response.output_text.delta` events for assistant message text when upstream provides final text only in output item or terminal response output payloads. The service MUST NOT duplicate text deltas for an output item that already emitted a text delta.

#### Scenario: final output item text is exposed as a text delta
- **WHEN** upstream emits a `response.output_item.done` event with assistant message text and no prior text delta for that output item
- **THEN** the service emits a corresponding `response.output_text.delta` event before forwarding the final item event

#### Scenario: terminal response output text is exposed as a text delta
- **WHEN** upstream emits only a terminal `response.completed` event with assistant message text in `response.output`
- **THEN** the service emits a corresponding `response.output_text.delta` event before forwarding the terminal event

#### Scenario: existing text deltas are preserved without duplication
- **WHEN** upstream already emits a `response.output_text.delta` for an output item
- **THEN** the service forwards the stream without synthesizing another text delta for that same output item

### Requirement: Tool call events and output items are preserved
If the upstream model emits tool call deltas or output items, the service MUST forward those events in streaming mode and MUST include tool call items in the final response output for non-streaming mode.

#### Scenario: Tool call emitted
- **WHEN** the upstream emits a tool call delta event
- **THEN** the service forwards the delta event and includes the finalized tool call in the completed response output

#### Scenario: Chat Completions tool arguments avoid snapshot duplication
- **WHEN** `/v1/chat/completions` maps Responses tool-call events that include incremental deltas and later finalized snapshots for the same tool call
- **THEN** the final `tool_calls[].function.arguments` value is exactly one valid JSON string for that tool call
- **AND** the adapter MUST NOT append full snapshot payloads on top of already-collected incremental argument deltas

#### Scenario: Parallel tool calls route arguments by output_index
- **WHEN** `/v1/chat/completions` maps Responses events for two or more parallel function calls
- **THEN** the adapter MUST route each event to its `tool_calls[]` slot using the event's `output_index` as the primary routing key
- **AND** the adapter MUST preserve a stable mapping from `output_index` to the same slot across `output_item.added`, `output_item.done`, `response.function_call_arguments.delta`, and `response.function_call_arguments.done` events for that call
- **AND** parallel tool calls MUST NOT collapse to index `0` when their argument-only events identify the owning call only via `item_id`

#### Scenario: Parallel tool calls also resolve through item_id aliases
- **WHEN** an `output_item.added` or `output_item.done` event exposes both `item.id` (e.g. `"fc_..."`) and `item.call_id` (e.g. `"call_..."`)
- **THEN** the adapter MUST register `item.id` as an alias to the same `tool_calls[]` slot as the `call_id`
- **AND** subsequent argument-only events that carry only `item_id` MUST resolve to that aliased slot, even if their `output_index` has not yet been observed

#### Scenario: Internal item_id never leaks into the public call identifier
- **WHEN** the adapter exposes a tool call to the client as `tool_calls[].id` or `tool_calls[].call_id`
- **THEN** the value MUST be the upstream `call_...` identifier and MUST NOT be substituted with the internal `fc_...` item id used solely for routing

### Requirement: Responses routing prefers budget-safe accounts
When serving Responses routes, the service MUST prefer eligible accounts that are still below the configured budget threshold over eligible accounts already above that threshold. If no below-threshold candidate exists, the service MAY fall back to the pressured candidates.

#### Scenario: Fresh Responses request avoids a near-exhausted account
- **WHEN** `/backend-api/codex/responses`, `/backend-api/codex/responses/compact`, `/v1/responses`, or `/v1/responses/compact` selects among multiple eligible active accounts
- **AND** one candidate is above the configured budget threshold
- **AND** another candidate remains below that threshold
- **THEN** the below-threshold candidate is chosen first

### Requirement: Upstream Responses event size budget
The service SHALL allow upstream Responses SSE events and upstream websocket message frames up to 16 MiB by default before treating them as oversized.

#### Scenario: built-in tool output exceeds the old 2 MiB limit
- **WHEN** upstream Responses traffic includes a single SSE event or websocket message frame larger than 2 MiB but not larger than 16 MiB
- **THEN** the proxy continues processing the event instead of closing the upstream websocket locally with `1009 message too big`

### Requirement: Upstream Responses transport strategy
For streaming Codex/Responses proxy requests, the system MUST let operators choose the upstream transport strategy through dashboard settings. The resolved strategy MAY be `auto`, `http`, or `websocket`, and `default` MUST defer to the server configuration default.

#### Scenario: Dashboard forces websocket upstream transport
- **WHEN** the dashboard setting `upstream_stream_transport` is set to `"websocket"`
- **THEN** streaming Responses requests use the upstream websocket transport

#### Scenario: Dashboard forces HTTP upstream transport
- **WHEN** the dashboard setting `upstream_stream_transport` is set to `"http"`
- **THEN** streaming Responses requests use the upstream HTTP/SSE transport

#### Scenario: Auto transport falls back when websocket upgrades are rejected
- **WHEN** the resolved upstream transport strategy is `"auto"`
- **AND** auto selection chose the websocket transport
- **AND** the upstream rejects the websocket upgrade with HTTP `426`
- **THEN** the proxy retries the request over the upstream HTTP/SSE transport

#### Scenario: Session affinity alone does not trigger websocket upstream transport
- **WHEN** the resolved upstream transport strategy is `"auto"`
- **AND** a request includes a `session_id`
- **AND** it does not include an allowlisted native Codex `originator` or explicit Codex websocket feature headers
- **THEN** the auto strategy MUST keep using the existing model-preference transport selection rules

#### Scenario: Auto transport honors websocket-preferred bootstrap models before registry warmup
- **WHEN** the resolved upstream transport strategy is `"auto"`
- **AND** the model registry has not loaded a snapshot yet
- **AND** the request targets a locally bootstrapped websocket-preferred model family such as `gpt-5.4` or `gpt-5.4-*`
- **AND** the request does not include the built-in `image_generation` tool
- **THEN** the proxy chooses the upstream websocket transport

#### Scenario: Auto transport prefers HTTP for image-generation tool requests
- **WHEN** the resolved upstream transport strategy is `"auto"`
- **AND** the request includes a built-in `image_generation` tool
- **THEN** the proxy chooses the upstream HTTP/SSE transport even if the model would otherwise prefer websocket

#### Scenario: Legacy settings preserve the pre-feature default
- **WHEN** transport selection runs against a legacy settings object that does not expose the newer upstream transport fields
- **THEN** the proxy MUST preserve the pre-feature HTTP transport default for model-preference auto-selection unless an explicit legacy websocket mode or native Codex websocket signal opts in

### Requirement: Responses-compatible tool payload handling
The service SHALL accept built-in Responses tool definitions on `/backend-api/codex/responses` and `/v1/responses` without locally rejecting them. The service MAY normalize documented aliases, but upstream model/tool compatibility validation MUST remain the upstream contract.

#### Scenario: full Responses request includes built-in tools
- **WHEN** a client sends `/backend-api/codex/responses` or `/v1/responses` with built-in Responses tools such as `image_generation`, `computer_use`, `computer_use_preview`, `file_search`, or `code_interpreter`
- **THEN** the proxy forwards those tool objects upstream instead of returning a local `invalid_request_error`

### Requirement: Compact requests drop tool-only fields
The service SHALL remove `tools`, `tool_choice`, and `parallel_tool_calls` from compact request payloads before calling the upstream compact endpoint.

#### Scenario: compact request reuses a full Responses payload shape
- **WHEN** a client sends `/backend-api/codex/responses/compact` or `/v1/responses/compact` with `tools`, `tool_choice`, or `parallel_tool_calls`
- **THEN** the proxy drops those fields before the upstream compact request
- **AND** the compact request continues without a local or upstream `invalid_request_error` caused by `param="tools"`

### Requirement: Responses requests accept input_file content items with a file_id

The system SHALL accept `input_file` content items that reference an upload by `file_id` in `/backend-api/codex/responses` and `/v1/responses` request payloads (both list-form and string-form `input`). These items MUST be forwarded to upstream verbatim. The same MUST apply to `/responses/compact` request bodies. The proxy MUST NOT raise `input_file.file_id is not supported` for these items.

#### Scenario: input_file with file_id is accepted in a /responses request

- **WHEN** a client posts a `/v1/responses` request whose `input` contains a `{"type": "input_file", "file_id": "file_abc"}` content item
- **THEN** the request validates and the upstream payload includes that content item unchanged

#### Scenario: input_file with file_id is accepted in a compact request

- **WHEN** a client posts a `/responses/compact` request whose `input` contains an `input_file` item with a `file_id`
- **THEN** the request validates and is forwarded to upstream verbatim

### Requirement: Responses requests with input_file.file_id route to the upload's account

A `/v1/responses`, `/backend-api/codex/responses`, or `/responses/compact` request that references an `{type: "input_file", file_id}` content item SHALL be routed to the upstream account that registered the file via `POST /backend-api/files`, when an in-memory pin for that `file_id` is still live. Stronger affinity signals MUST take precedence over the file_id pin: an explicit `prompt_cache_key`, a session header (`StickySessionKind.CODEX_SESSION`), a turn-state header, or a `previous_response_id` MUST keep their existing routing semantics.

When multiple `file_id`s are referenced and several are pinned, the most-recently-pinned one MUST be preferred (with a deterministic lexicographic tie-break on `file_id`).

#### Scenario: file_id pin drives routing for an input_file response

- **GIVEN** a `POST /backend-api/files` registered `file_xyz` through `account_a`
- **WHEN** a `/v1/responses` request references `{"type": "input_file", "file_id": "file_xyz"}` and has no stronger affinity
- **THEN** the proxy MUST route the request to `account_a`

#### Scenario: prompt_cache_key overrides the file_id pin

- **GIVEN** a pinned `file_xyz -> account_a`
- **WHEN** a `/v1/responses` request references `file_xyz` AND sets an explicit `prompt_cache_key`
- **THEN** the proxy MUST follow the prompt-cache affinity for routing and MUST NOT use the file_id pin

### Requirement: Codex backend session_id preserves account affinity
When a backend Codex Responses or compact request includes a non-empty accepted session header, the service MUST use that value as the routing affinity key for upstream account selection. If the request lacks a client-supplied `prompt_cache_key`, the service MUST derive and attach a stable `prompt_cache_key` before upstream forwarding so account affinity and upstream prompt-cache routing can coexist. Accepted session headers are `session_id`, `x-codex-session-id`, and `x-codex-conversation-id`, in that priority order.

#### Scenario: Backend Codex request derives prompt_cache_key before codex-session routing
- **WHEN** `/backend-api/codex/responses` is called with `session_id` and without `prompt_cache_key`
- **THEN** the routing decision still uses durable `codex_session` affinity for account selection
- **AND** the forwarded upstream payload includes a derived stable `prompt_cache_key`

### Requirement: Proxy-generated prompt cache key derivation is operator-toggleable
The service MUST provide a runtime flag that disables only proxy-generated prompt-cache-key derivation. When disabled, the service MUST continue forwarding any client-supplied `prompt_cache_key` unchanged and MUST NOT synthesize a new one.

#### Scenario: Derivation disabled preserves client-supplied key
- **WHEN** the derivation flag is disabled and a client sends `prompt_cache_key`
- **THEN** the service forwards that key unchanged
- **AND** it does not generate a replacement key

### Requirement: HTTP Responses routes preserve upstream websocket session continuity
When serving HTTP `/v1/responses` or HTTP `/backend-api/codex/responses`, the service MUST preserve upstream Responses websocket session continuity on a stable per-session bridge key instead of opening a brand new upstream session for every eligible request. The bridge key MUST use an explicit session/conversation header when present; otherwise it MUST use normalized `prompt_cache_key`, and when the client omits `prompt_cache_key` the service MUST derive a stable key from the same cache-affinity inputs already used for OpenAI prompt-cache routing. While bridged, the service MUST preserve the external HTTP/SSE contract, MUST continue request logging with `transport = "http"`, and MUST keep requests from different bridge keys isolated from one another.

#### Scenario: bridge forwards hard continuity keys to the owner replica
- **WHEN** operators configure multiple eligible bridge instance ids
- **AND** a request uses a bridge key derived from `x-codex-turn-state` or an explicit session header
- **AND** that request lands on a non-owner instance
- **THEN** the service MUST forward the request internally to the owner replica
- **AND** it MUST NOT return a topology-bearing `bridge_instance_mismatch` error to the client for that owner mismatch alone

#### Scenario: gateway-style prompt-cache bridge requests tolerate wrong-replica arrival
- **WHEN** a request uses a bridge key derived only from `prompt_cache_key` or a derived prompt-cache key
- **AND** that request lands on a non-owner instance
- **THEN** the service MAY create or reuse a local bridge session on that instance
- **AND** it MUST treat the owner mismatch as a locality miss instead of a continuity failure

#### Scenario: forwarded bridge requests fail closed when owner forwarding loops
- **WHEN** a forwarded hard-continuity bridge request reaches another non-owner replica
- **THEN** the service MUST fail the request with a generic 5xx bridge-forward error
- **AND** it MUST NOT attempt another owner handoff
