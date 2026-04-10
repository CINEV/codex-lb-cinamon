## Summary

Introduce a second Platform fallback surface for ChatGPT-private Codex HTTP routes. The new increment intentionally supports only:

- `GET /backend-api/codex/models`
- stateless HTTP `POST /backend-api/codex/responses`

It explicitly does not support:

- `/backend-api/codex/responses` websocket
- compact routes
- payload-level continuity-dependent requests (`conversation`, `previous_response_id`)

## Goals

- Make Codex app/CLI HTTP traffic eligible for Platform fallback.
- Preserve the current fallback ordering: `chatgpt_web` stays primary, `openai_platform` is fallback-only.
- Fail closed on unsupported Codex-private semantics instead of silently routing them to a mismatched upstream contract.

## Non-Goals

- Platform-backed websocket support
- Platform-backed continuity/session bridge support
- Compact-route support
- Treating Platform as a first-class member of the normal ChatGPT pool

## Routing Model

Add a new route family for backend Codex HTTP fallback eligibility:

- `backend_codex_http`

Selection behavior:

1. Backend Codex HTTP requests derive `RequestCapabilities` with `route_family=backend_codex_http`, `route_class=chatgpt_private`, and `transport=http`.
2. If any compatible ChatGPT candidate remains healthy, the request stays on the ChatGPT path.
3. If the compatible ChatGPT pool is drained and an eligible Platform identity exists for `backend_codex_http`, the request may switch to the Platform adapter.
4. If the request is websocket, compact, or payload-continuity-dependent, Platform capability checks fail closed.
5. Backend Codex HTTP session headers (`session_id`, `x-codex-session-id`, `x-codex-conversation-id`, `x-codex-turn-state`) are treated as downstream transport hints only and do not by themselves block fallback.

## Translation Strategy

### `/backend-api/codex/models`

- Reuse Platform model discovery.
- Translate the discovered Platform models into the existing Codex models response shape.
- Apply the same API-key model filtering and enforced-model rules as the public `/v1/models` path.

### `/backend-api/codex/responses`

- Reuse the existing `ResponsesRequest` payload model.
- Add a backend-Codex-specific Platform path that:
  - enforces API-key model restrictions
  - rejects payload-level continuity-dependent request shapes before transport start
  - calls the Platform adapter's HTTP create/stream functions
  - returns the existing downstream SSE/JSON response envelope expected by the backend Codex HTTP route

## Adapter Seams

Primary seams:

- `ProxyService.select_routing_subject()`
  - extend capability routing to a backend Codex HTTP route family
- `OpenAIPlatformProviderAdapter.check_capabilities()`
  - allow stateless backend Codex HTTP route family
  - continue rejecting websocket and payload-level continuity-dependent Codex requests
- `app/modules/proxy/api.py`
  - replace `_backend_codex_route_rejection()` with route-specific Platform handlers for models/responses

## Risks

### Downstream shape mismatch

`/backend-api/codex/*` is treated as ChatGPT-private by clients. Even if the request body is close to `ResponsesRequest`, the response shape and streaming expectations must remain compatible after bridging to the public Platform API.

### Hidden continuity dependence

Codex app/CLI may attach session/turn-state headers even on otherwise stateless HTTP requests. Those headers must not block fallback by themselves, but true payload continuity still needs to fail closed until Platform-backed continuity is intentionally implemented.

### Operator configuration ambiguity

Using the same route-family toggle for public `/v1/*` and backend Codex HTTP routes would make it harder to enable one surface without the other. The new route family keeps those controls explicit.

## Rollout

1. Add the new route family and provider-capability rules.
2. Add backend Codex HTTP Platform handlers for models/responses.
3. Add integration coverage for:
   - healthy ChatGPT stays primary
   - drained ChatGPT pool falls back on backend Codex HTTP
   - websocket/compact/payload-continuity requests still reject or stay ChatGPT-only
   - backend Codex session headers no longer suppress otherwise eligible fallback
