---
title: WebSocket protocol
description: The Gateway's WebSocket wire protocol — authentication, the agent request/response contract, trace event types, session keys, and cancellation.
sidebar:
  order: 5
---

Connect to `ws://<host>:<port>/rpc`.

## Authentication

```json
// Gateway sends on connect:
{"type": "event", "event": "challenge", "payload": {"nonce": "abc123"}}

// Client sends connect request:
{"type": "req", "id": "uuid-1", "method": "connect", "params": {"auth": {"token": "your-operator-token"}}}

// Gateway responds:
{"type": "res", "id": "uuid-1", "ok": true, "payload": {"protocol": 3}}
```

## Agent Request

The gateway sends **multiple frames** with the same request `id`: one
accepted frame immediately, zero or more streaming trace event frames during
execution, then the final result frame.

```json
// Client → Gateway
{
  "type": "req",
  "id": "uuid-2",
  "method": "agent",
  "params": {
    "agentId": "sre-triage",
    "sessionKey": "agent:sre-triage:pipeline:run-123:triage",
    "message": "Assess this alert: ...",
    "model": "anthropic/claude-opus-4-8",    // optional — overrides agent.yaml default
    "thinkingLevel": "medium",               // optional — Anthropic models only
    "traceToolResultMax": 8000,               // optional — overrides limits.trace_tool_result_max_chars for this request only
    "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"  // injected by VectorStep
  }
}

// Frame 1: accepted immediately (before agent runs)
{"type": "res", "id": "uuid-2", "ok": true, "payload": {"status": "accepted", "runId": "uuid-3"}}

// Frames 2..N: streaming trace events during execution (one per event)
{"type": "res", "id": "uuid-2", "ok": true, "payload": {"status": "trace_event", "event": {"type": "llm_call", "iteration": 1}}}
{"type": "res", "id": "uuid-2", "ok": true, "payload": {"status": "trace_event", "event": {"type": "tool_call", "name": "grafana_search", "input": {...}}}}
{"type": "res", "id": "uuid-2", "ok": true, "payload": {"status": "trace_event", "event": {"type": "tool_result", "name": "grafana_search", "content": "...", "is_error": false}}}

// Final frame: complete result
{
  "type": "res",
  "id": "uuid-2",
  "ok": true,
  "payload": {
    "status": "ok",
    "result": {
      "payloads": [{"text": "Agent response text here", "mediaUrl": null}],
      "meta": {
        "durationMs": 8503,
        "agentMeta": {
          "provider": "anthropic",
          "model": "claude-sonnet-4-6",
          "agentVersion": "91f02ab3c7de",
          "usage": {"input_tokens": 1234, "output_tokens": 456}
        },
        "aborted": false
      },
      "trace": [
        {"type": "llm_call", "iteration": 1},
        {"type": "tool_call", "name": "grafana_search", "input": {...}},
        {"type": "tool_result", "name": "grafana_search", "content": "...", "is_error": false},
        {"type": "text", "content": "Agent response text here"}
      ]
    }
  }
}
```

On error, the final frame is:
`{"type": "res", "id": "uuid-2", "ok": false, "error": {"message": "..."}}`

`agentMeta.provider` is the provider key (`anthropic`, `openrouter`, `azure`,
etc.) that actually served the request — if `model_fallbacks` kicked in and a
later candidate from a *different* provider ended up serving it, `provider`
reflects that final candidate, not the originally requested model. This is
deliberately distinct from `agentMeta.model`, which is whatever the
underlying LLM API itself reports as the model name — for most OpenAI-compat
providers that's the raw vendor model id (e.g. OpenRouter reports
`"deepseek/deepseek-v4-pro-..."`, not `"openrouter/deepseek/..."`), so `model`
alone can't be used to reliably reconstruct which provider served a call.

`agentMeta.agentVersion` is a content hash of the agent's full config,
including `soul.md` (see [Creating agents](/docs/gateway/agents/)) — it
changes whenever `agent.yaml` or `soul.md` changes. VectorStep uses it to scope
calibration buckets, so two runs under different `agentVersion`s are never
pooled as evidence for the same track record.

## Trace Event Types

| `type` | Fields | Description |
|---|---|---|
| `llm_call` | `iteration` | Start of an LLM call |
| `llm_retry` | `model`, `attempt`, `delay_seconds`, `error` | A retryable error occurred; retrying the same model after a backoff delay |
| `model_fallback` | `from_model`, `to_model`, `error` | Retries on `from_model` were exhausted; falling over to `to_model` |
| `thinking` | `content` | Extended thinking block (Anthropic only) |
| `text` | `content` | Text output block from the LLM |
| `tool_call` | `name`, `input` | Tool call about to be executed |
| `tool_result` | `name`, `content`, `is_error` | Result returned from MCP tool. `content` is capped at `limits.trace_tool_result_max_chars` (default 3000, overridable per-request via `traceToolResultMax` — see [Configuration](/docs/gateway/configuration/#limits)) — this is a trace-only truncation; the LLM's own conversation always sees the full result. |
| `tool_denied` | `name`, `server`, `rule_index`, `reason` | A [tool_policy](/docs/gateway/tool-policy/) rule blocked this call before it reached the MCP server. No `tool_result` event follows it — the LLM receives an `is_error` tool result instead. |

## Session Keys

Session keys must start with `agent:<agentId>:` — the gateway validates this
prefix on every request.

```
agent:sre-triage:pipeline:run-123:triage    ✅
pipeline:run-123:triage                     ❌ (missing agent prefix)
```

The VectorStep `gateway` executor generates a valid session key automatically if
`session_key` is omitted from `executor_config`.

**What session keys do and don't do:** the gateway tracks session keys in
memory (used for the `vectorstep_gateway_sessions_active` metric) but does **not**
persist message history between requests. Every agent call starts with a
fresh message list containing only the current prompt. Session keys in this
gateway provide namespace isolation and prefix validation — not
conversational continuity across calls.

This is intentional for VectorStep's usage pattern: session keys are scoped per
pipeline run and step (e.g.
`agent:sre-triage:pipeline:{{pipeline_run_id}}:triage`), so no two invocations
of the same step share a key. Context passing between steps is handled
explicitly by VectorStep via `next_step_context`, prompt templates, and
`{{loop.prior_output}}` — the pipeline author controls exactly what each step
sees, rather than the agent accumulating unbounded conversation history.

## Concurrency and Cancellation

Each `agent` request is gated by a gateway-wide semaphore sized by
`limits.max_concurrent_runs` (default `10`). The `accepted` frame (with
`runId`) is always sent immediately; if the gateway is already at capacity,
the run queues silently behind it — no trace events fire until a slot frees
up and the run actually starts.

If the client disconnects (the WebSocket closes) while a run is in flight —
whether still queued or already executing — the gateway cancels it
immediately rather than letting the agentic loop run to completion for a
response nobody will receive. Cancelled runs are recorded with
`status="aborted"` in the `vectorstep_gateway_agent_runs_total` metric.
