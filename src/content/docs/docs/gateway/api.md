---
title: REST API
description: The Gateway's REST endpoints — health, agent management, and MCP introspection.
sidebar:
  order: 6
---

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health — status, agent count, MCP server states, active run count |
| `GET` | `/agents` | List loaded agents (name, model, model_fallbacks, tools, version) |
| `GET` | `/agents/{name}` | Combined structured view of one agent — parsed config + soul.md + raw agent.yaml text + version |
| `GET` | `/agents/{name}/soul` | Return the soul.md content for an agent |
| `GET` | `/agents/{name}/agent` | Return the agent.yaml content for an agent |
| `POST` | `/agents` | Create a new agent from raw `agent.yaml`/`soul.md` text — validates, writes, reloads |
| `PUT` | `/agents/{name}` | Update an existing agent (either or both files) — validates, writes, reloads |
| `DELETE` | `/agents/{name}` | Delete an agent — returns its prior `agent.yaml`/`soul.md` content for audit |
| `POST` | `/agents/validate` | Dry-run validation of a candidate agent — no write |
| `GET` | `/providers` | Configured providers + their model-string prefix (no API keys, no live model list) |
| `POST` | `/reload` | Reload all agent configs from disk |
| `GET` | `/mcp/tools` | List all tools across all MCP servers |
| `GET` | `/mcp/servers` | List MCP server status (pid, tool count) |
| `GET` | `/tool-policy` | Read-only view of the active [tool_policy](/docs/gateway/tool-policy/) rules (reasons included) — no write endpoint, policy changes require a config edit + restart |
| `GET` | `/metrics` | Prometheus metrics (no auth required) |

## `/health` response

```json
{
  "status": "ok",
  "version": "0.5.0",
  "agents": 3,
  "active_runs": 1,
  "max_concurrent_runs": 10,
  "mcp_servers": {
    "grafana": {"running": true, "restart_count": 0},
    "atlassian": {"running": true, "restart_count": 1}
  }
}
```

`status` is `"ok"` when all configured MCP servers are running, `"degraded"`
if any are down. A gateway with no MCP servers configured always returns
`"ok"`. No authentication is required — suitable for Kubernetes
liveness/readiness probes.

## Agent management endpoints

`POST /agents`, `PUT /agents/{name}`, and `DELETE /agents/{name}` are the
write path behind the
[Gateway MCP](/docs/gateway/integration/#gateway-mcp-agent-authoring)'s
`create_agent`/`update_agent`/`delete_agent` tools — an
`agent.yaml`/`soul.md` pair is validated (schema **and** that
`model`/`model_fallbacks` map to a configured provider and `tools:` map to
configured `mcp_servers`), atomically written, and the live registry
reloaded, all before the request returns. A candidate that fails validation
never touches disk — see `gateway/agent_writer.py`.

`POST /agents` request body:

```json
{
  "name": "sre-triage",
  "agent_yaml": "name: sre-triage\nmodel: anthropic/claude-sonnet-4-6\ntools: [grafana]\n",
  "soul_md": "You are an SRE triage agent...",
  "overwrite": false
}
```

Success response (200):

```json
{
  "agent": {"name": "sre-triage", "agent_yaml": "...", "soul_md": "..."},
  "committed": false,
  "note": "Files written and reloaded. agents/ is gitignored, so this is not a git-commit concern."
}
```

`agents/` is gitignored (personal to the deployment, unlike VectorStep's
git-controlled `pipelines/`), so `committed` is always `false` — there is
nothing to commit.

`PUT /agents/{name}` accepts `agent_yaml` and/or `soul_md` — omit one to
leave that file untouched. The YAML's own `name:` field must always match the
`name` used to create it (in the POST body) or the URL `{name}` (for PUT) — a
rename is a delete + create, not an update.

Error responses carry an explicit `type` so a caller never has to infer it
from status code + message wording:

```json
// 400 — e.g. tools: references an unconfigured MCP server, or model maps to no known provider
{"detail": {"type": "validation", "message": "...", "errors": [{"agent": "...", "field": "tools", "value": "...", "message": "...", "severity": "error"}]}}

// 404 — PUT/DELETE on an agent that doesn't exist
{"detail": {"type": "not_found", "message": "Agent 'x' not found"}}

// 409 — POST on an existing name without overwrite: true
{"detail": {"type": "collision", "message": "Agent 'x' already exists"}}
```

`POST /agents/validate` (body: `{"agent_yaml": "...", "soul_md": "..."}`,
`soul_md` optional) runs the same checks with no write — returns
`{"valid": bool, "errors": [...]}`. This is the safe iterate loop before
calling `POST`/`PUT /agents`.

`GET /providers` returns provider names, whether each has credentials
configured, and the model-string prefix to use (e.g. `"openrouter/"`) — never
API keys, and no live per-provider model enumeration:

```json
{"providers": [
  {"name": "anthropic", "configured": true, "prefix": null},
  {"name": "openrouter", "configured": false, "prefix": "openrouter/"}
]}
```

(`prefix: null` for Anthropic — a bare model name with no prefix routes there
by default, per [Model Routing](/docs/gateway/providers/#model-routing).)
