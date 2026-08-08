---
title: Operations
description: Prometheus metrics, environment variables, performance notes, and MCP transport behavior for running the Gateway day to day.
sidebar:
  order: 7
---

This page covers what you need to run the Gateway in production: the metrics
it exposes, the environment variables it reads, and notes on its performance
characteristics and MCP subprocess transport.

## Prometheus Metrics

The gateway exposes Prometheus-format metrics at `/metrics` (GET). No
authentication is required — Prometheus scrapers connect directly.

### Example Prometheus scrape config

```yaml
scrape_configs:
  - job_name: vectorstep-gateway
    static_configs:
      - targets: ["localhost:18780"]
```

### Exposed metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `vectorstep_gateway_agent_runs_total` | Counter | `agent`, `model`, `status` | Total agent runs by agent, model, and terminal status (`ok`/`error`/`timeout`/`max_iterations`/`aborted`) |
| `vectorstep_gateway_agent_runs_in_progress` | Gauge | — | Currently executing agent runs |
| `vectorstep_gateway_agent_run_duration_seconds` | Histogram | `agent` | Agent run wall-clock duration in seconds |
| `vectorstep_gateway_agent_iterations` | Histogram | `agent` | Number of LLM iterations per agent run |
| `vectorstep_gateway_agent_tool_calls_total` | Counter | `agent` | Total tool calls made during agent runs |
| `vectorstep_gateway_llm_tokens_total` | Counter | `agent`, `model`, `direction` | Total LLM tokens consumed (`direction`: `input`/`output`) |
| `vectorstep_gateway_tool_calls_total` | Counter | `mcp_server`, `tool`, `result` | Total MCP tool calls by server, tool, and result (`success`/`error`/`timeout`) |
| `vectorstep_gateway_tool_call_duration_seconds` | Histogram | `mcp_server` | MCP tool call duration in seconds |
| `vectorstep_gateway_tool_denials_total` | Counter | `mcp_server`, `tool`, `agent` | Total tool calls blocked by [tool_policy](/docs/gateway/tool-policy/) |
| `vectorstep_gateway_mcp_servers_running` | Gauge | `mcp_server` | 1 if MCP server is running, 0 otherwise |
| `vectorstep_gateway_mcp_restarts_total` | Counter | `mcp_server` | Total MCP server restarts |
| `vectorstep_gateway_sessions_active` | Gauge | — | Number of active sessions |
| `vectorstep_gateway_info` | Info | `version` | Build information |

### Example PromQL queries

```text
# Agent run success rate (last 5 minutes)
rate(vectorstep_gateway_agent_runs_total{status="ok"}[5m])
  / rate(vectorstep_gateway_agent_runs_total[5m])

# Average agent run duration by agent
rate(vectorstep_gateway_agent_run_duration_seconds_sum[5m])
  / rate(vectorstep_gateway_agent_run_duration_seconds_count[5m])

# MCP tool error rate by server
rate(vectorstep_gateway_tool_calls_total{result="error"}[5m])
  / rate(vectorstep_gateway_tool_calls_total[5m])

# Currently running agents
vectorstep_gateway_agent_runs_in_progress

# Active sessions
vectorstep_gateway_sessions_active
```

## Environment Variables

`${VAR_NAME}` placeholders in `config.yaml` are resolved at startup. Commonly
used:

| Variable | Used by | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | `providers.anthropic` | Anthropic API key |
| `OPENROUTER_API_KEY` | `providers.openrouter` | OpenRouter API key |
| `OLLAMA_API_KEY` | `providers.ollama-cloud` | Ollama Cloud API key — [get one here](https://ollama.com/settings/keys) |
| `GOOGLE_API_KEY` | `providers.google` | Google AI API key |
| `AZURE_OPENAI_API_KEY` | `providers.azure.api_key` | Azure OpenAI API key |
| `AZURE_OPENAI_RESOURCE` | `providers.azure.resource_name` | Azure resource name (subdomain of `.openai.azure.com`) |
| `OPENAI_API_KEY` | `providers.openai` | OpenAI API key |
| `GRAFANA_URL` | `mcp_servers.grafana` | Grafana instance URL |
| `GRAFANA_TOKEN` | `mcp_servers.grafana` | Grafana service account token |
| `TAVILY_API_KEY` | `mcp_servers.tavily` | Tavily web search API key |
| `VECTORSTEP_GATEWAY_CONFIG` | Gateway startup | Override config file path (default: `config.yaml`) |
| `OTEL_EXPORTER_OTLP_HEADERS` | OTel exporter | Auth headers for OTLP endpoint (e.g. Grafana Cloud Basic Auth) |

## Performance Notes

- **Anthropic prompt caching** — the `soul` system prompt and tool-schema
  list are sent with `cache_control: {"type": "ephemeral"}`
  (`gateway/llm/providers/anthropic.py`), so on multi-turn loops the
  unchanged prefix is served from Anthropic's cache instead of being
  re-billed as full input tokens on every iteration. Anthropic-only —
  OpenAI-compat providers don't expose this.
- **Parallel tool execution** — when an LLM turn requests multiple tools at
  once, the gateway runs them concurrently with `asyncio.gather` instead of
  one at a time (`gateway/runner/agent_runner.py`), so the turn waits for the
  slowest tool call rather than the sum of all of them.
- **Model fallback chains + retry with backoff** — a retryable error
  (429/5xx/529/timeout/connection error) is retried on the same model with
  exponential backoff (`limits.llm_retry_attempts`/`llm_retry_base_delay_seconds`);
  once exhausted, the gateway falls over to the next model in the agent's
  `model_fallbacks` list. Non-retryable errors (e.g. `400`/`401`) skip
  straight to fallover. See the `llm_retry`/`model_fallback` trace events in
  the [WebSocket protocol](/docs/gateway/protocol/#trace-event-types).

## MCP Transport Notes

The gateway spawns each MCP server as a subprocess and communicates over
stdio (JSON-RPC 2.0). The subprocess `stdout` stream is read with a 4MB line
limit — sufficient for even large tool response payloads. If an MCP server
fails to start, the gateway logs an error and continues; agents that list
that server in their `tools:` will have no tools from it for that session.

MCP servers do not hot-reload — adding or removing a server requires a
gateway restart.
