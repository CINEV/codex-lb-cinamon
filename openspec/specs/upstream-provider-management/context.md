# Upstream Provider Management Context

## Purpose and Scope

This capability defines how the dashboard and API manage provider-aware upstream identities, including ChatGPT-web accounts and the phase-1 OpenAI Platform fallback identity.

See `openspec/specs/upstream-provider-management/spec.md` for normative requirements.

## Decisions

- `chatgpt_web` remains the primary upstream for existing behavior.
- `openai_platform` is fallback-only in phase 1 and is intentionally narrow in scope.
- Phase 1 mixed-provider mode supports only one Platform API key.
- Provider-aware routing is explicit rather than treating Platform as an equal-weight member of the ChatGPT pool.

## Supported Fallback Routes

- `GET /v1/models`
- stateless HTTP `POST /v1/responses`
- `GET /backend-api/codex/models`
- stateless HTTP `POST /backend-api/codex/responses`

For backend Codex HTTP responses, downstream Codex session headers such as `session_id`, `x-codex-session-id`, `x-codex-conversation-id`, and `x-codex-turn-state` are treated as transport hints in phase 1. They do not, by themselves, suppress an otherwise eligible Platform fallback decision.

## Unsupported Platform-backed Routes in Phase 1

- downstream websocket `/responses`
- downstream websocket `/v1/responses`
- downstream websocket `/backend-api/codex/responses`
- `/v1/responses/compact`
- `/backend-api/codex/responses/compact`
- `/v1/chat/completions`
- continuity-dependent requests using `conversation` or `previous_response_id`

## Fallback Policy

- ChatGPT accounts remain primary whenever at least one compatible `chatgpt_web` candidate has both `primary_remaining_percent > 10` and `secondary_remaining_percent > 5`.
- Platform fallback is allowed only when every compatible ChatGPT candidate is outside that healthy window.
- Credits are not part of the fallback decision.

## Operational Constraints

- Platform fallback requires at least one active ChatGPT account.
- A Platform identity can be registered with zero eligible route families; in that state it remains unroutable until the operator opts into a supported route family.
- Repeated upstream `401` or `403` failures should deactivate the Platform identity until the operator repairs or re-enables it.

## UX Expectations

- The dashboard should describe Platform identities as fallback-only.
- Route-family labels should clarify that `public_responses_http` means stateless HTTP `/v1/responses` only.
- Route-family labels should clarify that `backend_codex_http` covers `/backend-api/codex/models` plus stateless HTTP `/backend-api/codex/responses`.
- Operators should not expect compact or websocket behavior from the Platform path in phase 1.
