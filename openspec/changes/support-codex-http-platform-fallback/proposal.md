## Why

The current Platform fallback only covers public `/v1/models` and stateless `/v1/responses`. That is enough for OpenAI-compatible API clients, but it does not cover the ChatGPT-authenticated Codex app/CLI path that uses `/backend-api/codex/*`. In real use, that means Codex app/CLI traffic can still hit ChatGPT-web rate limits and return `429` even when a Platform API key is configured.

## What Changes

- Extend Platform fallback eligibility to HTTP `/backend-api/codex/models` and stateless HTTP `/backend-api/codex/responses`.
- Treat downstream Codex session headers on backend HTTP responses as transport hints instead of payload continuity blockers.
- Translate backend Codex HTTP requests onto the public OpenAI Platform Responses API contract.
- Keep websocket, compact, and continuity-dependent Codex request shapes explicitly unsupported in this increment.

## Impact

- Codex app/CLI traffic that stays on HTTP can still fall back to Platform even when clients replay `session_id`, `x-codex-session-id`, `x-codex-conversation-id`, or `x-codex-turn-state`.
- The routing policy remains fail-closed for websocket, compact, and payload-level continuity (`conversation`, `previous_response_id`) until dedicated support is implemented.
