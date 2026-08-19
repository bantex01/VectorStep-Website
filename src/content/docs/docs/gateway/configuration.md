---
title: Configuration
description: The Gateway's config.yaml — every field, section by section.
sidebar:
  order: 2
---

Copy `samples/config.yaml.example` to `config.yaml` and edit. Values support
`${VAR_NAME}` environment variable substitution throughout.

## `server`

| Field | Default | Description |
|---|---|---|
| `host` | `0.0.0.0` | Bind address |
| `port` | `18780` | Bind port. Use a different port from OpenClaw (18789) if running both. |

## `identity`

| Field | Default | Description |
|---|---|---|
| `path` | `~/.vectorstep-gateway/identity` | Where identity files are stored. Auto-generated on first run. |

The operator token (used by VectorStep to authenticate) is written to
`<path>/device-auth.json` on first run.

**Running in a container?** The default `~/.vectorstep-gateway/identity`
resolves to a path inside the container's ephemeral filesystem, so a
recreated container regenerates its identity — including the operator
token VectorStep was configured with — and the pairing breaks. Set
`identity.path` explicitly to somewhere on your mounted `/data` volume (e.g.
`/data/identity`). See [Docker](/docs/installation/docker/) for
the full container config.

## `limits`

| Field | Default | Description |
|---|---|---|
| `max_agent_iterations` | `20` | Max LLM ↔ tool call loops before aborting a run |
| `request_timeout_seconds` | `180` | Timeout for a single LLM API call |
| `mcp_tool_timeout_seconds` | `30` | Timeout for a single MCP tool call |
| `llm_retry_attempts` | `2` | Retries on the *same* model after a retryable error (429/5xx/529/timeout/connection error) before falling over to the next entry in `model_fallbacks` |
| `llm_retry_base_delay_seconds` | `1.0` | Base delay for exponential backoff between retries (doubles each attempt: 1s, 2s, 4s, …) |
| `max_concurrent_runs` | `10` | Gateway-wide cap on simultaneously executing agent runs. Once at capacity, new requests are still accepted (`Frame 1`) but queue until a slot frees up. |
| `trace_tool_result_max_chars` | `3000` | Gateway-wide default cap on a `tool_result` trace event's `content`, truncated with a trailing `"… [truncated]"` marker. This **only** affects the trace copy — the streamed/persisted record a caller (or a downstream grounding judge) inspects. The LLM conversation itself always receives the tool's full, untruncated output regardless of this setting; nothing about the agent's own reasoning is affected by it. A caller can override this per-request via the agent request's `traceToolResultMax` (see the [WebSocket protocol](/docs/gateway/protocol/)) without changing the gateway-wide default. |

## `mcp_servers`

Each key is a server name agents can reference in their `tools:` list. The
gateway spawns each as a subprocess on startup using stdio JSON-RPC transport.

```yaml
mcp_servers:
  grafana:
    command: npx
    args: ["-y", "@grafana/mcp-grafana"]
    env:
      GRAFANA_URL: ${GRAFANA_URL}
      GRAFANA_TOKEN: ${GRAFANA_TOKEN}
```

| Field | Required | Description |
|---|---|---|
| `command` | Yes | Executable to run (`npx`, `python3`, etc.) |
| `args` | No | Arguments list |
| `env` | No | Environment variables for the subprocess. Supports `${VAR_NAME}` substitution. |

## `providers`

Each key becomes a model prefix for routing. Configure only the providers you
need. See [Providers](/docs/gateway/providers/) for how the prefix determines
routing and for Azure's deployment-name specifics.

```yaml
providers:
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
  openrouter:
    api_key: ${OPENROUTER_API_KEY}
    base_url: https://openrouter.ai/api/v1
  ollama-local:
    base_url: http://localhost:11434/v1
  ollama-cloud:
    api_key: ${OLLAMA_API_KEY}
    base_url: https://ollama.com/api
  google:
    api_key: ${GOOGLE_API_KEY}
    base_url: https://generativelanguage.googleapis.com/v1beta/openai
  azure:
    api_key: ${AZURE_OPENAI_API_KEY}
    resource_name: ${AZURE_OPENAI_RESOURCE}   # e.g. "my-company-openai"
    api_version: "2025-01-01-preview"         # optional, this is the default
  openai:
    api_key: ${OPENAI_API_KEY}
    base_url: https://api.openai.com/v1       # optional, this is the default
  yolo:
    api_key: ${YOLO_API_KEY}
    base_url: https://your-provider.example.com/v1
```

Most providers support `api_key` and `base_url`. Azure uses different fields:

| Field | Required | Description |
|---|---|---|
| `api_key` | No | API key. Empty string = no auth header sent. |
| `base_url` | No | Override the provider's default endpoint (not used for `azure`). |

**Azure-specific fields** (under `providers.azure`):

| Field | Required | Description |
|---|---|---|
| `api_key` | Yes | Azure OpenAI API key from Azure AI Foundry. |
| `resource_name` | Yes | Azure resource name — the subdomain part of `{resource_name}.openai.azure.com`. |
| `api_version` | No | Azure API version. Default: `2025-01-01-preview`. |

**Default endpoints:**

| Provider key | Default endpoint | Notes |
|---|---|---|
| `anthropic` | SDK default | Uses Anthropic Python SDK natively |
| `openrouter` | `https://openrouter.ai/api/v1` | OpenAI-compat |
| `ollama-local` | `http://localhost:11434/v1` | Local Ollama OpenAI-compat endpoint |
| `ollama-cloud` | `https://ollama.com/api` | Native Ollama `/api/chat` endpoint |
| `google` | `https://generativelanguage.googleapis.com/v1beta/openai` | OpenAI-compat |
| `azure` | `https://{resource_name}.openai.azure.com/openai/deployments/{deployment}/chat/completions` | OpenAI-compat, auth via `api-key` header |
| `openai` | `https://api.openai.com/v1` | Native OpenAI API |
| `yolo` | None — `base_url` required | Generic OpenAI-compat custom endpoint, e.g. a self-hosted or third-party API |

## `logging`

| Field | Default | Description |
|---|---|---|
| `level` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, or `ERROR` |
| `dir` | `""` (disabled) | Directory for rotating log files. Omit to log to stdout only. When set, creates `gateway.log` (all application logs, 10 MB x 5 rotating) and `access.log` (uvicorn HTTP access logs, kept separate so request noise doesn't pollute `gateway.log` or stdout) — same format and rotation policy as VectorStep's `service.log`/`access.log` split, so both services' logs can be correlated directly. |

## `observability`

Controls OpenTelemetry tracing. Disabled by default — all
`tracer.start_as_current_span()` calls are no-ops until enabled.

```yaml
observability:
  otel:
    enabled: true
    exporter: otlp                                        # otlp | console
    endpoint: https://otlp-gateway-prod-eu-west-0.grafana.net/otlp/v1/traces
    service_name: vectorstep-gateway
```

| Field | Default | Description |
|---|---|---|
| `enabled` | `false` | Enable OTel tracing |
| `exporter` | `otlp` | `otlp` sends to an OTLP HTTP endpoint; `console` prints spans to stdout |
| `endpoint` | `http://localhost:4318/v1/traces` | OTLP HTTP endpoint. For Grafana Cloud, use your region's OTLP gateway URL with a Basic Auth header set via `OTEL_EXPORTER_OTLP_HEADERS`. |
| `service_name` | `vectorstep-gateway` | `service.name` resource attribute on all spans |

When OTel is enabled, the gateway emits three span types per agent run:

| Span | Parent | Key attributes |
|---|---|---|
| `agent.run` | VectorStep `gen_ai.gateway` span (via W3C `traceparent`) | `agent.name`, `gen_ai.request.model`, `vectorstep.gateway.iterations`, `vectorstep.gateway.tool_calls`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` |
| `llm_call` | `agent.run` | `llm_call.iteration`, `llm_call.attempt`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `llm_call.error`/`llm_call.retryable` (failed attempts only) |
| `tool_call <name>` | `agent.run` | `tool.name`, `tool.is_error` |

VectorStep injects a W3C `traceparent` header into the agent WebSocket request
params, and the gateway extracts it to make `agent.run` a child of VectorStep's
pipeline span — giving you a single unified trace across both services in
Grafana Tempo.

**Grafana Cloud setup:**

1. Get your OTLP endpoint from Grafana Cloud portal → Connections → OpenTelemetry
2. Set `OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic <base64(instanceId:apiKey)>` in your environment
3. Enable `observability.otel.enabled: true` and set `endpoint` to your Grafana Cloud OTLP URL

## `tool_policy`

Optional. Operator-owned allow/deny rules evaluated on every tool call,
independent of any agent's own `tools:` allowlist. Omit it entirely for the
previous unconditional-execution behaviour. See
[Tool policy](/docs/gateway/tool-policy/) for the full schema, matching
semantics, the audit trail, and default-deny visibility filtering.

```yaml
tool_policy:
  default: allow            # allow | deny
  rules:
    - deny: {server: atlassian, tool: jira_delete_issue}
      reason: "Destructive Jira operations are operator-only"
    - allow: {server: grafana}
```

| Field | Default | Description |
|---|---|---|
| `default` | `allow` | Decision when no rule matches |
| `rules` | `[]` | Ordered list — first match wins |
| `rules[].allow` / `rules[].deny` | — | Exactly one per rule; match block: `server`, `tool` (glob), `agent` (glob), `input_regex` |
| `rules[].reason` | — | Required on `deny`, optional on `allow` |
