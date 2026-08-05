---
title: Creating agents
description: agent.yaml and soul.md — the two files that define a Gateway agent — plus startup validation and hot reload.
sidebar:
  order: 4
---

Agents live as subdirectories under `agents_dir` (default: `./agents/`). Each
agent needs two files.

## `agent.yaml`

```yaml
name: sre-triage          # must match the directory name
model: anthropic/claude-sonnet-4-6
max_tokens: 8192
tools:                    # MCP server names from mcp_servers config
  - grafana
  - atlassian
```

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Agent identifier. Must match the directory name. Referenced as `agentId` in requests. |
| `model` | Yes | Default model string. Can be overridden per-request via `executor_config.model` in VectorStep. |
| `model_fallbacks` | No | List of model strings to try, in order, if `model` exhausts its retries (see [`limits.llm_retry_attempts`](/docs/gateway/configuration/#limits)). Once a fallback succeeds, later iterations in the same run try it first. |
| `max_tokens` | Yes | Max output tokens per LLM call. |
| `tools` | No | MCP server names, optionally scoped to specific tools (see below). Omit or leave empty for no tool access. |

```yaml
name: sre-triage
model: anthropic/claude-sonnet-4-6
model_fallbacks:
  - anthropic/claude-haiku-4-5
  - openrouter/deepseek/deepseek-chat
max_tokens: 8192
```

If `anthropic/claude-sonnet-4-6` returns a retryable error (e.g.
`529 overloaded`), the gateway retries it `llm_retry_attempts` times with
exponential backoff, then falls over to `claude-haiku-4-5`, then to the
OpenRouter model if that also fails. Non-retryable errors (e.g. `400`/`401`)
skip the retry and fall over immediately.

### Scoping `tools:` to specific tools

By default, listing an MCP server name in `tools:` grants every tool that
server exposes. To shrink the schema bloat in context (and the capability
surface) for servers that expose dozens of tools, scope an entry down to a
`{server_name: [tool_a, tool_b]}` mapping instead of a bare name:

```yaml
tools:
  - filesystem                                    # every tool from filesystem
  - atlassian: [jira_search, jira_get_issue]       # only these two from atlassian
```

Tool names here are the unscoped MCP tool names (e.g. `jira_search`), not the
namespaced `server__tool` form used internally — check `GET /mcp/tools` (see
[REST API](/docs/gateway/api/)) for the exact names a server exposes. Mixing
scoped and unscoped entries in the same list is fine.

## `soul.md`

The system prompt. Written in Markdown, sent as the `system` message to the
LLM on every call.

Good soul files are:
- **Narrow in scope** — describe exactly what this agent does and does not do
- **Explicit about output format** — tell the model to return JSON only, no preamble
- **Clear on confidence scoring** — explain what high/low confidence means for this agent's task

:::note
Editing `agent.yaml` or `soul.md` changes the agent's `version` (a content
hash over the agent's entire config, exposed as `agentMeta.agentVersion` and
on the `GET /agents` / `GET /agents/{name}` endpoints) and therefore resets
that agent's calibration history in VectorStep — see
[How confidence and calibration work](/docs/concepts/confidence/).
:::

## Startup Config Validation

When agents are loaded (at startup and on every `POST /reload` / SIGHUP), the
gateway validates each agent's `model` and `model_fallbacks` against the
configured providers:

- **Unrecognized prefix** (e.g. `my-custom/model`) — logged as `ERROR`. The agent will load but every request will fail with a `KeyError` at runtime.
- **Known prefix, missing api_key** (e.g. `openrouter/...` but `providers.openrouter.api_key` is empty) — logged as `WARNING`. The agent will load but requests will fail with auth errors.

Local Ollama (`ollama/...`) is exempt from the api_key check — it requires no
credentials by default.

These are warnings/errors in the log, not hard failures. All other agents
continue to load normally. Check startup logs if an agent behaves
unexpectedly at request time.

## Hot Reload

```bash
POST /reload          # via HTTP
kill -HUP <pid>       # via SIGHUP
```

Reloads all agent configs from disk without restarting. In-progress runs are
unaffected. Validation runs against the reloaded agents on every reload.
